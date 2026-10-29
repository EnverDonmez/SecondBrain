import hashlib
import json
import os
import secrets
import threading
import time
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, File, Form, Query, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .capture import coverage_report, normalize_app_item, normalize_hook
from .core import Brain
from .db import dumps
from .models import OWNER, EventInput, LoginInput, MemoryInput, MemoryType, Principal, SearchInput
from .security import Denied, NotFound, audit, create_token, require
from . import __version__
from .service import instance_id


def create_app(root=None, run_worker=True):
    brain = Brain(root or os.environ.get("SB_DATA_DIR", "data"))
    token_path = brain.db.root / "owner.token"
    if not token_path.exists():
        fd = os.open(token_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w") as stream:
            stream.write(secrets.token_urlsafe(48))
    owner_hash = hashlib.sha256(token_path.read_text().strip().encode()).hexdigest()

    @asynccontextmanager
    async def lifespan(app):
        thread = None
        if run_worker:
            brain.queue.recover_interrupted()
            thread = threading.Thread(target=brain.worker, daemon=True, name="brain-ingestion")
            thread.start()
        try:
            yield
        finally:
            brain.stop_event.set()
            if thread:
                thread.join(timeout=5)

    app = FastAPI(
        title="Second Brain OS",
        version=__version__,
        lifespan=lifespan,
        docs_url=None,
        openapi_url="/api/openapi.json",
    )
    app.state.brain = brain
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost", "[::1]", "testserver"])
    attempts: dict[str, list[float]] = {}

    @app.middleware("http")
    async def safety_headers(request, call_next):
        if int(request.headers.get("content-length", "0")) > 105 * 1024 * 1024:
            return JSONResponse({"error": "Request too large"}, status_code=413)
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            origin = request.headers.get("origin")
            if origin and origin != str(request.base_url).rstrip("/"):
                return JSONResponse({"error": "Cross-origin request denied"}, status_code=403)
            if request.cookies.get("brain_session") and request.headers.get("x-brain-request") != "1":
                return JSONResponse({"error": "CSRF protection header required"}, status_code=403)
        response = await call_next(request)
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.exception_handler(Denied)
    async def denied(request, exc):
        return JSONResponse({"error": str(exc)}, status_code=403)

    @app.exception_handler(NotFound)
    async def missing(request, exc):
        return JSONResponse({"error": str(exc)}, status_code=404)

    @app.exception_handler(KeyError)
    async def missing_field(request, exc):
        return JSONResponse({"error": "Required request field is missing"}, status_code=422)

    @app.exception_handler(ValueError)
    async def invalid(request, exc):
        return JSONResponse({"error": str(exc)}, status_code=422)

    @app.exception_handler(RequestValidationError)
    async def validation(request, exc):
        return JSONResponse(
            {
                "error": "Invalid request",
                "fields": [{"location": e["loc"], "message": e["msg"]} for e in exc.errors()],
            },
            status_code=422,
        )

    def authenticate(request: Request):
        token = request.headers.get("authorization", "").removeprefix("Bearer ") or request.cookies.get(
            "brain_session", ""
        )
        digest = hashlib.sha256(token.encode()).hexdigest()
        if token and secrets.compare_digest(digest, owner_hash):
            with brain.db.transaction() as con:
                audit(con, OWNER, "api.access", request.url.path)
            return OWNER
        record = brain.db.one("SELECT id,principal FROM tokens WHERE token_hash=? AND revoked=0", (digest,))
        if record:
            principal = Principal(**{**json.loads(record["principal"]), "credential_id": record["id"]})
            with brain.db.transaction() as con:
                audit(con, principal, "api.access", request.url.path)
            return principal
        raise Denied("Authentication required")

    @app.get("/api/docs", include_in_schema=False)
    def local_api_documentation():
        return FileResponse(Path(__file__).parent / "static" / "api-docs.html")

    @app.get("/healthz")
    def health():
        return {
            "status": "ok",
            "application": "second-brain-os",
            "version": __version__,
            "instance_id": instance_id(brain.db.root),
            "pid": os.getpid(),
        }

    @app.post("/api/login")
    def login(body: LoginInput, request: Request):
        address = request.client.host if request.client else "unknown"
        current = time.monotonic()
        recent = [t for t in attempts.get(address, []) if current - t < 60]
        if len(recent) >= 10:
            raise Denied("Too many login attempts; retry in one minute")
        attempts[address] = recent + [current]
        token = body.token
        if not secrets.compare_digest(hashlib.sha256(token.encode()).hexdigest(), owner_hash):
            raise Denied("Invalid owner key")
        response = JSONResponse({"authenticated": True, "remembered": body.remember})
        response.set_cookie(
            "brain_session",
            token,
            httponly=True,
            samesite="strict",
            max_age=30 * 24 * 3600 if body.remember else None,
        )
        return response

    @app.post("/api/logout")
    def logout():
        response = JSONResponse({"authenticated": False})
        response.delete_cookie("brain_session")
        return response

    @app.get("/api/status")
    def status(principal=Depends(authenticate)):
        return brain.status(principal)

    @app.get("/api/observer")
    def observer_overview(principal=Depends(authenticate)):
        from .observer import overview

        return overview(brain, principal)

    @app.get("/api/observer/activity")
    def observer_activity(offset: int = Query(0, ge=0, le=1_000_000), principal=Depends(authenticate)):
        from .observer import activity

        return activity(brain, principal, offset=offset)

    @app.get("/api/observer/memories")
    def observer_memories(
        query: str = Query("", max_length=2000),
        offset: int = Query(0, ge=0, le=1_000_000),
        principal=Depends(authenticate),
    ):
        from .observer import memories

        return memories(brain, principal, query=query, offset=offset)

    @app.get("/api/observer/memories/{identity}")
    def observer_detail(identity: str, principal=Depends(authenticate)):
        from .observer import detail

        return detail(brain, principal, identity)

    @app.get("/api/assistant-contract")
    def assistant_contract(principal=Depends(authenticate)):
        from .assistant_contract import ASSISTANT_INSTRUCTIONS, REMEMBER_EXAMPLE
        from .models import NavigateInput, ReadInput, RememberInput
        from .tool_surface import CONTRACT_VERSION, CORE_TOOLS

        require(principal, "read")
        return {
            "contract_version": CONTRACT_VERSION,
            "core_tools": CORE_TOOLS,
            "instructions": ASSISTANT_INSTRUCTIONS,
            "example": REMEMBER_EXAMPLE,
            "schema": RememberInput.model_json_schema(),
            "navigation_schema": NavigateInput.model_json_schema(),
            "read_schema": ReadInput.model_json_schema(),
            "default_engine": "economy",
            "activation_modes": {"candidate": "owner_review", "direct_user": "ordinary_user_statement"},
            "protected_types_require_review": True,
        }

    @app.post("/api/action/{operation}")
    def action(operation: str, body: dict, principal=Depends(authenticate)):
        return brain.dispatch(operation, body, principal)

    @app.post("/api/events")
    def capture(event: EventInput, principal=Depends(authenticate)):
        return brain.capture(event, principal)

    @app.get("/api/events/{identity}")
    def get_event(identity: str, principal=Depends(authenticate)):
        return brain.events.get(identity, principal)

    @app.post("/api/memories")
    def propose(candidate: MemoryInput, principal=Depends(authenticate)):
        return brain.memory.propose(candidate, principal)

    @app.post("/api/search")
    def search(query: SearchInput, principal=Depends(authenticate)):
        return brain.retrieval.search(query, principal)

    @app.get("/api/memories/{identity}")
    def get_memory(identity: str, principal=Depends(authenticate)):
        return brain.memory.get(identity, principal)

    @app.post("/api/memories/{identity}/{operation}")
    def mutate_memory(identity: str, operation: str, principal=Depends(authenticate)):
        methods = {"approve": brain.memory.commit, "reject": brain.memory.reject, "hide": brain.memory.hide}
        if operation not in methods:
            raise ValueError("Unknown memory action")
        return methods[operation](identity, principal)

    @app.get("/api/graph")
    def graph(scope: str | None = None, principal=Depends(authenticate)):
        return brain.retrieval.graph(principal, scope)

    @app.post("/api/entities/merge")
    def merge_entities(body: dict, principal=Depends(authenticate)):
        return brain.entities.merge(body["canonical"], body["alias"], principal)

    @app.post("/api/import")
    async def upload(
        file: UploadFile = File(...),
        scope: str = Form("global"),
        sensitivity: int = Form(1),
        principal=Depends(authenticate),
    ):
        content = await file.read(100 * 1024 * 1024 + 1)
        return brain.importer.submit(content, file.filename or "upload.txt", principal, scope, sensitivity)

    @app.get("/api/assets")
    def list_assets(principal=Depends(authenticate)):
        require(principal, "read")
        rows = brain.db.rows(
            "SELECT id,name,mime,size,scope,sensitivity,created_at FROM assets WHERE tenant=? AND sensitivity<=? ORDER BY created_at DESC LIMIT 500",
            (principal.tenant, principal.clearance),
        )
        return [row for row in rows if principal.permits_scope(row["scope"])]

    @app.get("/api/assets/{identity}")
    def asset(identity: str, principal=Depends(authenticate)):
        record = brain.db.one("SELECT * FROM assets WHERE id=? AND tenant=?", (identity, principal.tenant))
        if not record:
            raise NotFound("Asset not found")
        require(principal, "read", record["scope"], record["sensitivity"])
        return Response(
            brain.vault.get(identity),
            media_type="application/octet-stream",
            headers={"Content-Disposition": "attachment; filename=" + identity + ".bin"},
        )

    @app.get("/api/media/capabilities")
    def media_capabilities(principal=Depends(authenticate)):
        require(principal, "read")
        return brain.multimodal.capabilities()

    @app.post("/api/assets/{identity}/derivative")
    def media_derivative(identity: str, body: dict, principal=Depends(authenticate)):
        return brain.multimodal.derivative(
            identity,
            body["text"],
            principal,
            body.get("kind", "transcript"),
            body.get("location", ""),
            body.get("language"),
        )

    @app.post("/api/assets/{identity}/ocr")
    def image_ocr(identity: str, principal=Depends(authenticate)):
        return brain.multimodal.ocr(identity, principal)

    @app.post("/api/assets/{identity}/process")
    def process_media(identity: str, body: dict, principal=Depends(authenticate)):
        return brain.multimodal.enqueue(identity, body["operation"], principal, body.get("language"))

    @app.post("/api/jobs/{identity}/cancel")
    def cancel_job(identity: str, principal=Depends(authenticate)):
        return brain.queue.cancel(identity, principal)

    @app.post("/api/jobs/{identity}/retry")
    def retry(identity: str, principal=Depends(authenticate)):
        return brain.queue.retry(identity, principal)

    @app.get("/api/tools")
    def list_tool_configs(principal=Depends(authenticate)):
        return brain.tools.list(principal)

    @app.post("/api/tools")
    def register_tool_config(body: dict, principal=Depends(authenticate)):
        return brain.tools.register(body["name"], body["kind"], body.get("config", {}), principal)

    @app.post("/api/tools/{identity}/probe")
    def probe_tool(identity: str, principal=Depends(authenticate)):
        return brain.tools.probe(identity, principal)

    @app.post("/api/tools/{identity}/state")
    def state_tool(identity: str, body: dict, principal=Depends(authenticate)):
        if not isinstance(body.get("enabled"), bool):
            raise ValueError("enabled must be boolean")
        return brain.tools.set_state(identity, body["enabled"], principal)

    @app.get("/api/feedback")
    def feedback(principal=Depends(authenticate)):
        return brain.learning.list(principal)

    @app.post("/api/extract/{identity}")
    def extract(identity: str, body: dict, principal=Depends(authenticate)):
        if body.get("provider") == "ollama":
            event = brain.events.get(identity, principal)
            result = brain.provider.extract(event["text"], principal)
            candidates = []
            for fact in result.get("facts", [])[:20]:
                candidates.append(
                    brain.memory.propose(
                        MemoryInput(
                            memory_type=MemoryType.MODEL_INFERENCE,
                            predicate=fact["predicate"],
                            value=fact["value"],
                            source_event_ids=[identity],
                            scope=event["scope"],
                            sensitivity=event["sensitivity"],
                            confidence=0.5,
                        ),
                        principal,
                    )
                )
            return {"candidates": candidates, "approval_required": True}
        return brain.importer.extract_explicit(identity, principal)

    @app.post("/api/skills/import")
    async def skill_import(file: UploadFile = File(...), principal=Depends(authenticate)):
        return brain.skills.register(await file.read(10 * 1024 * 1024 + 1), principal)

    @app.post("/api/skills/{identity}/state")
    def skill_state(identity: str, body: dict, principal=Depends(authenticate)):
        if not isinstance(body.get("enabled"), bool):
            raise ValueError("enabled must be boolean")
        return brain.skills.state(identity, body["enabled"], principal)

    @app.post("/api/skills/{identity}/compatibility")
    def skill_compatibility(identity: str, body: dict, principal=Depends(authenticate)):
        return brain.skills.compatibility(
            identity, principal, body.get("tools"), body.get("mcp_servers"), body.get("permissions")
        )

    @app.get("/api/skills/{identity}/export")
    def skill_export(identity: str, principal=Depends(authenticate)):
        return Response(
            brain.skills.export(identity, principal),
            media_type="application/zip",
            headers={"Content-Disposition": "attachment; filename=skill.zip"},
        )

    @app.get("/api/export/{format}")
    def export(format: str, principal=Depends(authenticate)):
        suffix = {"json": "json", "jsonl": "jsonl", "markdown": "md"}.get(format)
        if not suffix:
            raise ValueError("Unknown export format")
        return Response(
            brain.export(principal, format),
            media_type="text/plain; charset=utf-8",
            headers={"Content-Disposition": "attachment; filename=brain-export." + suffix},
        )

    @app.get("/api/backups")
    def backups(principal=Depends(authenticate)):
        return brain.backups.list(principal)

    @app.post("/api/backups/import")
    async def import_backup(
        file: UploadFile = File(...), password: str = Form(...), principal=Depends(authenticate)
    ):
        require(principal, "admin")
        content = await file.read(100 * 1024 * 1024 + 1)
        if len(content) > 100 * 1024 * 1024:
            raise ValueError("Backup exceeds 100 MiB upload limit")
        with brain.backups.unpack(content, password):
            pass
        identity = secrets.token_hex(16)
        path = brain.backups.path(identity)
        path.write_bytes(content)
        try:
            result = brain.backups.verify(identity, password, principal)
        except Exception:
            path.unlink(missing_ok=True)
            raise
        return {**result, "restored": False, "approval_required": True}

    @app.post("/api/backups")
    def create_backup(body: dict, principal=Depends(authenticate)):
        return brain.backups.create(body["password"], principal)

    @app.post("/api/backups/{identity}/{operation}")
    def backup_operation(identity: str, operation: str, body: dict, principal=Depends(authenticate)):
        if operation == "verify":
            return brain.backups.verify(identity, body["password"], principal)
        if operation == "restore":
            if body.get("confirmation") != identity:
                raise Denied("Confirm the exact backup id to restore")
            return brain.backups.restore(identity, body["password"], principal)
        raise ValueError("Unknown backup action")

    @app.get("/api/backups/{identity}/download")
    def backup_download(identity: str, principal=Depends(authenticate)):
        require(principal, "admin")
        return FileResponse(brain.backups.path(identity), filename=identity + ".sbbackup")

    @app.post("/api/tokens")
    def token_create(body: dict, principal=Depends(authenticate)):
        return create_token(brain.db, principal, body["name"], Principal(**body["principal"]))

    @app.get("/api/tokens")
    def token_list(principal=Depends(authenticate)):
        require(principal, "admin")
        return brain.db.rows("SELECT id,name,principal,created_at,revoked FROM tokens")

    @app.delete("/api/tokens/{identity}")
    def revoke_token(identity: str, principal=Depends(authenticate)):
        require(principal, "admin")
        with brain.db.transaction() as con:
            record = con.execute("SELECT principal FROM tokens WHERE id=?", (identity,)).fetchone()
            if not record or json.loads(record["principal"])["tenant"] != principal.tenant:
                raise NotFound("Token not found")
            con.execute("UPDATE tokens SET revoked=1 WHERE id=?", (identity,))
            con.execute(
                "UPDATE jobs SET state='cancelled',leased_until=NULL WHERE tenant=? AND state IN ('pending','running') AND json_extract(payload,'$.principal.credential_id')=?",
                (principal.tenant, identity),
            )
            audit(con, principal, "token.revoked", identity)
        return {"revoked": identity}

    @app.get("/api/audit")
    def audit_list(principal=Depends(authenticate)):
        require(principal, "admin")
        return brain.db.rows(
            "SELECT * FROM audit WHERE tenant=? ORDER BY created_at DESC LIMIT 200", (principal.tenant,)
        )

    @app.post("/api/capture/{client}")
    def hook_capture(client: str, body: dict, scope: str = "global", principal=Depends(authenticate)):
        return brain.capture(normalize_hook(client, body, scope), principal)

    @app.post("/api/codex/items/{thread_id}")
    def app_item(thread_id: str, body: dict, scope: str = "global", principal=Depends(authenticate)):
        return brain.capture(normalize_app_item(thread_id, body, scope), principal)

    @app.get("/api/capture-coverage")
    def capture_coverage(principal=Depends(authenticate)):
        require(principal, "admin")
        return coverage_report(brain.events.list(principal, limit=1000))

    @app.post("/api/reindex")
    def reindex(body: dict, principal=Depends(authenticate)):
        if body.get("vectors"):
            require(principal, "admin")
            return brain.queue.enqueue("vector_reindex", secrets.token_hex(16), {}, principal)
        return brain.memory.rebuild(principal)

    @app.get("/api/diagnostics")
    def diagnostics(principal=Depends(authenticate)):
        require(principal, "admin")
        return {
            **brain.status(principal),
            "integrity": brain.db.one("PRAGMA quick_check"),
            "ollama": brain.provider.health(),
            "python": sys.version,
            "raw_encryption": "AES-256-GCM",
            "canonical_index_encryption": "plaintext; use OS disk encryption",
            "deletion_ledger_entries": len(brain.privacy.entries()),
        }

    @app.get("/api/benchmarks")
    def benchmarks(principal=Depends(authenticate)):
        require(principal, "admin")
        return brain.db.rows(
            "SELECT * FROM benchmark_runs WHERE tenant=? ORDER BY created_at DESC LIMIT 20",
            (principal.tenant,),
        )

    @app.post("/api/benchmarks")
    def benchmark(body: dict, principal=Depends(authenticate)):
        require(principal, "admin")
        from .benchmark import run_evaluation

        result = run_evaluation(
            brain.db.root / "evaluation",
            split=body.get("split", "validation"),
            engines=body.get("engines", ["fts", "bm25", "hybrid"]),
        )
        with brain.db.transaction() as con:
            con.execute(
                "INSERT INTO benchmark_runs VALUES(?,?,?,?)",
                (secrets.token_hex(16), principal.tenant, dumps(result), result["created_at"]),
            )
        return result

    static = Path(__file__).parent / "static"
    app.mount("/static", StaticFiles(directory=static), name="static")

    @app.get("/")
    def index():
        return FileResponse(static / "index.html")

    @app.get("/maintenance")
    def maintenance():
        return FileResponse(static / "maintenance.html")

    return app

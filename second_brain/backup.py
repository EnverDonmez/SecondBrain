import io
import json
import os
import secrets
import sqlite3
import tempfile
import zipfile
from contextlib import closing
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

from .db import dumps
from .importers import safe_zip
from .models import now
from .security import Denied, audit, require


def password_key(password, salt):
    if len(password) < 12:
        raise ValueError("Backup passphrase must contain at least 12 characters")
    return Scrypt(salt=salt, length=32, n=2**15, r=8, p=1).derive(password.encode())


class BackupManager:
    def __init__(self, core):
        self.core = core
        self.directory = core.db.root / "backups"
        self.directory.mkdir(exist_ok=True)

    def list(self, principal):
        require(principal, "admin")
        return [
            {"id": p.stem, "size": p.stat().st_size, "modified_at": p.stat().st_mtime}
            for p in sorted(self.directory.glob("*.sbbackup"), reverse=True)
        ]

    def path(self, identity):
        if len(identity) != 32 or any(c not in "0123456789abcdef" for c in identity):
            raise ValueError("Invalid backup id")
        return self.directory / (identity + ".sbbackup")

    def create(self, password, principal):
        require(principal, "admin")
        core = self.core
        with core.work_lock, core.db.lock, tempfile.TemporaryDirectory(dir=core.db.root) as temp:
            snapshot = Path(temp) / "snapshot.sqlite3"
            with core.db.connect() as con, closing(sqlite3.connect(snapshot)) as destination:
                con.backup(destination)
                destination.execute("DELETE FROM tokens")
                destination.commit()
                destination.execute("VACUUM")
            content = io.BytesIO()
            with zipfile.ZipFile(content, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                archive.write(snapshot, "brain.sqlite3")
                archive.writestr("master.key", core.vault.key)
                archive.writestr(
                    "manifest.json", dumps({"schema": 1, "created_at": now(), "tenant": principal.tenant})
                )
                archive.writestr(
                    "deletions.jsonl",
                    core.privacy.ledger.read_bytes() if core.privacy.ledger.exists() else b"",
                )
                for asset in core.db.rows("SELECT id FROM assets"):
                    archive.write(core.vault.path(asset["id"]), "assets/" + asset["id"] + ".enc")
            salt, nonce, identity = secrets.token_bytes(16), secrets.token_bytes(12), secrets.token_hex(16)
            encrypted = AESGCM(password_key(password, salt)).encrypt(
                nonce, content.getvalue(), b"SecondBrainBackup-v1"
            )
            target = self.path(identity)
            target.write_bytes(b"SBOS1" + salt + nonce + encrypted)
            with core.db.transaction() as con:
                audit(con, principal, "backup.created", identity)
        return {"id": identity, "size": target.stat().st_size, "encrypted": True}

    def unpack(self, content, password):
        if len(content) < 49 or content[:5] != b"SBOS1":
            raise ValueError("Not a Second Brain encrypted backup")
        try:
            plaintext = AESGCM(password_key(password, content[5:21])).decrypt(
                content[21:33], content[33:], b"SecondBrainBackup-v1"
            )
        except Exception as exc:
            raise ValueError("Backup password or authentication check failed") from exc
        archive = safe_zip(plaintext)
        allowed = {"brain.sqlite3", "master.key", "manifest.json", "deletions.jsonl"}
        for name in archive.namelist():
            if name not in allowed and not (
                name.startswith("assets/")
                and name.endswith(".enc")
                and len(name) == len("assets/") + 36
                and all(c in "0123456789abcdef" for c in name[7:-4])
            ):
                raise Denied("Unexpected backup member")
        manifest = json.loads(archive.read("manifest.json"))
        if manifest["schema"] != 1 or len(archive.read("master.key")) != 32:
            raise ValueError("Unsupported backup schema/key")
        return archive

    def verify(self, identity, password, principal):
        require(principal, "admin")
        with self.unpack(self.path(identity).read_bytes(), password) as archive:
            with tempfile.TemporaryDirectory(dir=self.core.db.root) as temp:
                path = Path(temp) / "check.sqlite3"
                path.write_bytes(archive.read("brain.sqlite3"))
                with closing(sqlite3.connect(path)) as con:
                    if con.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                        raise ValueError("Snapshot database is corrupt")
                    count = con.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
                    for aid, digest in con.execute("SELECT id,hash FROM assets"):
                        import hashlib

                        encrypted = archive.read("assets/" + aid + ".enc")
                        raw = AESGCM(archive.read("master.key")).decrypt(
                            encrypted[:12], encrypted[12:], aid.encode()
                        )
                        if hashlib.sha256(raw).hexdigest() != digest:
                            raise ValueError("Asset hash mismatch")
        return {"id": identity, "integrity": "ok", "memories": count}

    def restore(self, identity, password, principal):
        with self.core.work_lock:
            return self._restore(identity, password, principal)

    def _restore(self, identity, password, principal):
        require(principal, "admin")
        self.verify(identity, password, principal)
        core = self.core
        with core.db.lock, self.unpack(self.path(identity).read_bytes(), password) as archive:
            core.reset_projections()
            manifest = json.loads(archive.read("manifest.json"))
            if manifest["tenant"] != principal.tenant:
                raise Denied("Backup tenant mismatch")
            live_tokens = core.db.rows("SELECT * FROM tokens")
            entries = {entry["id"]: entry for entry in core.privacy.entries()}
            for line in archive.read("deletions.jsonl").decode().splitlines():
                entry = json.loads(line)
                entries[entry["id"]] = entry
            # Durable restore journal supports recovery if the process stops mid-swap.
            stage = core.db.root / "restore-stage"
            stage.mkdir(exist_ok=True)
            for name in archive.namelist():
                if name in {"manifest.json", "deletions.jsonl"}:
                    continue
                path = stage / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(archive.read(name))
            (stage / "deletions.jsonl").write_text(
                "".join(dumps(e) + "\n" for e in entries.values()), encoding="utf-8"
            )
            (stage / "tokens.json").write_text(dumps(live_tokens), encoding="utf-8")
            (stage / "READY").write_text("1", encoding="ascii")
            self.finish_restore(core.db.root)
            core.db.migrate()
            core.vault.key = (core.db.root / "master.key").read_bytes()
            core.privacy.replay()
            core.memory.rebuild(principal)
            with core.db.transaction() as con:
                audit(con, principal, "backup.restored", identity)
        return {"restored": identity, "deletion_entries_replayed": len(entries)}

    @staticmethod
    def finish_restore(root):
        stage = Path(root) / "restore-stage"
        if (stage / "APPLIED").exists():
            BackupManager.clean_stage(stage)
            return
        if not (stage / "READY").exists():
            return
        # Idempotent copy, stage is retained until completion. No recursive deletion.
        for name in ("brain.sqlite3-wal", "brain.sqlite3-shm"):
            (Path(root) / name).unlink(missing_ok=True)
        for name in ("brain.sqlite3", "master.key", "deletions.jsonl"):
            destination = Path(root) / name
            temporary = destination.with_suffix(destination.suffix + ".restore")
            temporary.write_bytes((stage / name).read_bytes())
            os.replace(temporary, destination)
        target_assets = Path(root) / "assets"
        target_assets.mkdir(exist_ok=True)
        for path in target_assets.glob("*.enc"):
            path.unlink()
        for path in (stage / "assets").glob("*.enc"):
            (target_assets / path.name).write_bytes(path.read_bytes())
        with closing(sqlite3.connect(Path(root) / "brain.sqlite3")) as con:
            con.execute("DELETE FROM tokens")
            for token in json.loads((stage / "tokens.json").read_text("utf-8")):
                con.execute(
                    "INSERT INTO tokens VALUES(?,?,?,?,?,?)",
                    tuple(
                        token[k] for k in ("id", "name", "token_hash", "principal", "created_at", "revoked")
                    ),
                )
            con.commit()
        (stage / "APPLIED").write_text("1", encoding="ascii")
        BackupManager.clean_stage(stage)

    @staticmethod
    def clean_stage(stage):
        # Staged raw data must not remain as an untracked backup after restore.
        for path in (stage / "assets").glob("*.enc"):
            path.unlink()
        for name in ("brain.sqlite3", "master.key", "deletions.jsonl", "tokens.json", "READY", "APPLIED"):
            (stage / name).unlink(missing_ok=True)

import json
import math
import re
import time
import threading
from typing import Any, Callable


from .db import dumps
from .memory import decode, search_text
from .models import MemoryType, SearchInput, now
from .security import Denied, normalize, require
from .language import terms
from .identity import keys as identity_keys


def tokens(text):
    stop = {
        "the",
        "a",
        "an",
        "is",
        "are",
        "what",
        "which",
        "my",
        "in",
        "of",
        "to",
        "ve",
        "veya",
        "bir",
        "bu",
        "ne",
        "nedir",
        "hangi",
        "benim",
        "icin",
        "ile",
        "mi",
        "mı",
        "mu",
        "kullanıcının",
        "kullanicinin",
    }
    return [t for t in re.findall(r"\w+", normalize(text)) if t not in stop]


def lexical_excerpt(value, query_tokens, width=900):
    """Exact source slices; no generated summary and no tokenizer-offset assumptions."""
    starts = list(range(0, max(1, len(value) - width), width // 2))
    starts.append(max(0, len(value) - width))
    best_start, best_score = 0, -1
    for start in starts:
        words = tokens(value[start : start + width])
        score = sum(any(word.startswith(term) for word in words) for term in set(query_tokens))
        if score > best_score:
            best_start, best_score = start, score
    end = min(len(value), best_start + width)
    return {"start_char": best_start, "end_char": end, "text": value[best_start:end]}


def measure_context(packet):
    """Include the size estimate itself in the conservative UTF-8 byte bound."""
    packet["estimated_tokens_upper_bound"] = 0
    while True:
        size = len(dumps(packet).encode("utf-8"))
        if size == packet["estimated_tokens_upper_bound"]:
            return size
        packet["estimated_tokens_upper_bound"] = size


class Retrieval:
    def __init__(self, db):
        self.db = db
        self.mem0_factory: Callable[[], Any] | None = None
        self.cache_lock = threading.RLock()
        self.clear_cache()

    def clear_cache(self):
        with self.cache_lock:
            self._lexical_cache = None
            self._vocabulary_cache = None
            self._vector_cache = None

    def revision(self):
        return self.db.one("SELECT revision FROM projection_revision WHERE id=1")["revision"]

    def where(self, request, principal, history=False):
        require(principal, "read", request.scope)
        at, known = request.valid_at or now(), request.known_at or now()
        clauses = [
            "m.tenant=?",
            "m.sensitivity<=?",
        ]
        args = [principal.tenant, principal.clearance]
        if history:
            clauses.append("m.approved_by IS NOT NULL")
        else:
            clauses += [
                "m.known_from<=?",
                "(m.known_to IS NULL OR m.known_to>?)",
                "m.valid_from<=?",
                "(m.valid_to IS NULL OR m.valid_to>?)",
            ]
            args += [known, known, at, at]
        if request.status:
            if request.status != "active":
                require(principal, "approve")
            clauses.append("m.status=?")
            args.append(request.status)
        elif request.include_candidates:
            require(principal, "approve")
            clauses.append("m.status IN ('candidate','disputed','active')")
        else:
            clauses.append("m.status='active'")
        if "*" not in principal.scopes:
            clauses.append("m.scope IN (" + ",".join("?" for _ in principal.scopes) + ")")
            args += principal.scopes
        for field in ("scope", "subject", "predicate", "memory_type"):
            value = getattr(request, field)
            if value:
                if field == "subject":
                    with self.db.connect() as con:
                        skey, _ = identity_keys(con, principal.tenant, value, "")
                    clauses.append("m.subject_key=?")
                    args.append(skey)
                    continue
                if field == "predicate":
                    with self.db.connect() as con:
                        _, pkey = identity_keys(con, principal.tenant, request.subject or "", value)
                    clauses.append("m.predicate_key=?")
                    args.append(pkey)
                    continue
                clauses.append(f"m.{field}=?")
                args.append(str(value))
        if request.source:
            clauses.append(
                "EXISTS (SELECT 1 FROM json_each(m.source_event_ids) s JOIN events e ON e.id=s.value WHERE e.source=? AND e.tenant=m.tenant)"
            )
            args.append(request.source)
        return " AND ".join(clauses), args

    def search(self, request: SearchInput, principal):
        started = time.perf_counter()
        warnings = []
        where, args = self.where(request, principal)
        if request.engine == "mem0":
            if self.mem0_factory is None:
                raise Denied("Mem0 projection is not configured")
            result = self.mem0_factory().retrieve(request, principal)
            result["elapsed_ms"] = round((time.perf_counter() - started) * 1000, 3)
            return result
        query_tokens = tokens(request.query)[:64]
        diagnostics = {}
        if request.query.strip() and not query_tokens:
            rows = []
            warnings.append("Query contains no searchable terms; add a subject or a concrete keyword.")
        elif not query_tokens:
            rows = self.db.rows(
                "SELECT m.* FROM memories m WHERE "
                + where
                + " ORDER BY m.importance DESC,m.known_from DESC LIMIT ? OFFSET ?",
                (*args, request.limit, request.offset),
            )
            for row in rows:
                row["score"] = 0.0
        elif request.engine in {"economy", "graph"}:
            rows, diagnostics = self._economy(request, principal, where, args)
        elif request.engine == "fts":
            match = " AND ".join('"' + t + '"*' for t in query_tokens)
            rows = self.db.rows(
                "SELECT m.*, -bm25(memory_fts) AS score FROM memory_fts JOIN memories m ON m.id=memory_fts.id WHERE memory_fts MATCH ? AND "
                + where
                + " ORDER BY score DESC,m.importance DESC LIMIT ? OFFSET ?",
                (match, *args, request.limit, request.offset),
            )
        else:
            candidates = self.db.rows("SELECT m.* FROM memories m WHERE " + where, args)
            if request.engine == "vector":
                rows = self._vector(candidates, request.query, request.limit + request.offset)[
                    request.offset :
                ]
            elif request.engine == "bm25":
                rows = self._bm25(candidates, query_tokens, request.limit + request.offset)[request.offset :]
            else:
                lexical = self._bm25(candidates, query_tokens, max((request.limit + request.offset) * 3, 50))
                vocabulary = self._vocabulary(
                    candidates, request.query, max(50, request.limit + request.offset)
                )
                graph = [
                    r
                    for r in candidates
                    if all(t in normalize(r["subject"] + " " + r["predicate"]) for t in query_tokens)
                ]
                ranked = [lexical, graph, vocabulary]
                if request.engine == "hybrid" and (
                    self.db.one("SELECT 1 FROM vectors LIMIT 1")
                    or self.db.one("SELECT 1 FROM vector_chunks LIMIT 1")
                ):
                    try:
                        ranked.append(self._vector(candidates, request.query, max(50, request.limit)))
                    except Denied:
                        warnings.append(
                            "Semantic branch unavailable; local model/index configuration is missing. Lexical and graph branches were used."
                        )
                scores: dict[str, float] = {}
                records = {}
                for ranking in ranked:
                    for rank, record in enumerate(ranking):
                        scores[record["id"]] = scores.get(record["id"], 0) + 1 / (60 + rank + 1)
                        records[record["id"]] = record
                rows = []
                for mid in sorted(scores, key=lambda identity: scores[identity], reverse=True)[
                    request.offset : request.offset + request.limit
                ]:
                    rows.append({**records[mid], "score": scores[mid]})
        items = [decode(row) for row in rows]
        self.mark_disputes(items, request, principal)
        if query_tokens:
            for item in items:
                if len(item["value"]) > 900 and not item.get("match"):
                    item["match"] = lexical_excerpt(item["value"], query_tokens)
        return {
            "items": items,
            "engine": request.engine,
            "warnings": warnings,
            "elapsed_ms": round((time.perf_counter() - started) * 1000, 3),
            "abstain": not items,
            "valid_at": request.valid_at or now(),
            "known_at": request.known_at or now(),
            **diagnostics,
        }

    def _economy(self, request, principal, where, args):
        """FTS inverted index -> bounded, authorized graph neighbors; no full corpus load."""
        wanted = terms(request.query)[:32]
        words = ["sbconcept" + word[1:] if word.startswith("@") else word for word in wanted]
        words += tokens(request.query)[:32]
        words = list(dict.fromkeys(words))[:48]
        if not words:
            return [], {"candidates_examined": 0, "candidate_limit": 96, "graph_hops": 0}
        match = " OR ".join('"' + word + '"*' for word in words)
        # Cap the amount of content fetched, even for large offsets or hub topics.
        cap = 96
        seeds = self.db.rows(
            "SELECT m.*, -bm25(memory_fts) AS score FROM memory_fts "
            "JOIN memories m ON m.id=memory_fts.id WHERE memory_fts MATCH ? AND "
            + where
            + " ORDER BY score DESC,m.importance DESC,m.id LIMIT ?",
            (match, *args, 48),
        )
        records = {row["id"]: {**row, "retrieval_path": "index"} for row in seeds}
        frontier = [row["id"] for row in seeds[:12]]
        hops = 0
        for depth in range(request.graph_hops):
            if not frontier or len(records) >= cap:
                break
            marks = ",".join("?" for _ in frontier)
            # All three paths start at indexed IDs/nodes. The final WHERE applies
            # exactly the same tenant/scope/clearance/status/time filters as seeds.
            sql = (
                "WITH connections(id,parent,relation,priority) AS ("
                "SELECT target_id,memory_id,'explicit',0 FROM memory_links WHERE memory_id IN ("
                + marks
                + ") UNION ALL "
                "SELECT memory_id,target_id,'explicit',0 FROM memory_links WHERE target_id IN ("
                + marks
                + ") UNION ALL "
                "SELECT n.memory_id,s.memory_id,s.kind,CASE s.kind WHEN 'entity' THEN 1 ELSE 2 END "
                "FROM memory_nodes s JOIN memory_nodes n ON n.node=s.node "
                "WHERE s.memory_id IN (" + marks + ")), "
                "neighbor_ids AS (SELECT *,row_number() OVER (PARTITION BY id ORDER BY priority,parent) pos "
                "FROM connections) "
                "SELECT m.*,n.parent AS via_memory_id,n.relation FROM neighbor_ids n "
                "JOIN memories m ON m.id=n.id WHERE n.pos=1 AND "
                + where
                + " AND m.id NOT IN ("
                + ",".join("?" for _ in records)
                + ") "
                "ORDER BY n.priority,m.importance DESC,m.id LIMIT ?"
            )
            neighbors = self.db.rows(
                sql, (*frontier, *frontier, *frontier, *args, *records, cap - len(records))
            )
            hops += 1
            for row in neighbors:
                records[row["id"]] = {
                    **row,
                    "score": 0.0,
                    "retrieval_path": "graph",
                    "graph_depth": depth + 1,
                }
            frontier = [row["id"] for row in neighbors[:12]]
        # Direct matches must not lose half their slots to a broad topic hub.
        # Fixed windows make offset pagination independent of the page size.
        direct = [row for row in records.values() if row["retrieval_path"] == "index"]
        linked = [row for row in records.values() if row["retrieval_path"] == "graph"]
        ranked = direct + linked
        return ranked[request.offset : request.offset + request.limit], {
            "candidates_examined": len(records),
            "candidate_limit": cap,
            "graph_hops": hops,
            "bounded_candidates": True,
            "additional_model_calls": 0,
            "more": request.offset + request.limit < len(ranked),
            "next_offset": request.offset + request.limit
            if request.offset + request.limit < len(ranked)
            else None,
            "window_saturated": len(seeds) == 48 or len(records) == cap,
        }

    def mark_disputes(self, items, request, principal):
        """Expose review state, not unapproved values, within the same read boundary."""
        identities = [item["id"] for item in items if item["status"] == "active"]
        if not identities:
            return
        marks = ",".join("?" for _ in identities)
        rows = self.db.rows(
            "SELECT m.id FROM memories m WHERE m.id IN (" + marks + ") AND EXISTS ("
            "SELECT 1 FROM memories c WHERE c.tenant=m.tenant AND c.scope=m.scope "
            "AND c.subject_key=m.subject_key AND c.predicate_key=m.predicate_key "
            "AND (c.status='disputed' OR (c.status='active' AND c.id!=m.id AND c.logical_id!=m.logical_id AND c.value!=m.value)) "
            "AND c.sensitivity<=? AND c.known_from<=? AND c.known_to IS NULL "
            "AND c.valid_from<=? AND (c.valid_to IS NULL OR c.valid_to>?))",
            (
                *identities,
                principal.clearance,
                request.known_at or now(),
                request.valid_at or now(),
                request.valid_at or now(),
            ),
        )
        pending = {row["id"] for row in rows}
        for item in items:
            if item["id"] in pending:
                item["review_required"] = True
        changed_links = self.db.rows(
            "SELECT m.id FROM memories m WHERE m.id IN (" + marks + ") AND EXISTS ("
            "SELECT 1 FROM json_each(m.related_memory_ids) j JOIN memories t ON t.id=j.value "
            "WHERE t.tenant=m.tenant AND t.scope=m.scope AND t.sensitivity<=? AND t.known_to IS NOT NULL)",
            (*identities, principal.clearance),
        )
        changed = {row["id"] for row in changed_links}
        for item in items:
            if item["id"] in changed:
                item["related_version_changed"] = True

    def _bm25(self, candidates, query_tokens, limit):
        from rank_bm25 import BM25Okapi

        if not candidates:
            return []
        key = (self.revision(), tuple(c["id"] for c in candidates))
        with self.cache_lock:
            cached = self._lexical_cache
            if cached and cached[0] == key:
                _, corpus, model = cached
            else:
                corpus = [tokens(search_text(c)) for c in candidates]
                model = BM25Okapi(corpus)
                # Bound resident text/token data; large corpora remain uncached.
                self._lexical_cache = (
                    (key, corpus, model)
                    if sum(len(search_text(c)) for c in candidates) <= 2_000_000
                    else None
                )
        scores = model.get_scores(query_tokens)
        ranked = []
        for i, record in enumerate(candidates):
            # BM25 can have non-positive IDF in small corpora; relevance still requires token evidence.
            overlap = sum(any(w.startswith(q) for w in corpus[i]) for q in query_tokens)
            if overlap >= max(1, math.ceil(len(query_tokens) * 0.75)):
                ranked.append({**record, "score": float(scores[i]) + overlap / (len(query_tokens) + 1)})
        return sorted(ranked, key=lambda r: (r["score"], r["importance"]), reverse=True)[:limit]

    def _vocabulary(self, candidates, query, limit):
        wanted = terms(query)
        if not wanted:
            return []
        key = (self.revision(), tuple(c["id"] for c in candidates))
        with self.cache_lock:
            cached = self._vocabulary_cache
            if cached and cached[0] == key:
                corpus = cached[1]
            else:
                corpus = [terms(c["value"]) for c in candidates]
                self._vocabulary_cache = (
                    (key, corpus) if sum(len(c["value"]) for c in candidates) <= 2_000_000 else None
                )
        ranked = []
        for record, words in zip(candidates, corpus, strict=True):
            hits = sum(
                any(
                    w == q
                    or (
                        not q.startswith("@")
                        and not w.startswith("@")
                        and min(len(w), len(q)) >= 4
                        and (w.startswith(q) or q.startswith(w))
                    )
                    for w in words
                )
                for q in wanted
            )
            if hits >= max(1, math.ceil(len(wanted) * 0.45)):
                score = hits / (len(wanted) + 0.15 * len(words))
                ranked.append({**record, "score": score})
        return sorted(ranked, key=lambda r: (r["score"], r["importance"]), reverse=True)[:limit]

    def _vector(self, candidates, query, limit):
        import numpy as np
        from .providers import LocalEmbedder

        if not candidates:
            return []
        embedder = LocalEmbedder(self.db.root)
        query_vector = np.asarray(embedder.embed([query])[0], dtype=np.float32)
        query_vector /= np.linalg.norm(query_vector) + 1e-12
        eligible = {r["id"]: r for r in candidates}
        ranked: dict[str, dict] = {}
        key = (self.revision(), embedder.model)
        with self.cache_lock:
            cached = self._vector_cache
            if cached and cached[0] == key:
                batches = [cached[1:]]
            else:
                batches = self._vector_batches(embedder.model, len(query_vector))
            cache_rows, cache_matrices, cache_bytes = [], [], 0
            any_vectors = False
            for metadata, matrix in batches:
                any_vectors = True
                if not cached or cached[0] != key:
                    cache_bytes += matrix.nbytes
                    if cache_bytes <= 32 * 1024 * 1024:
                        cache_rows.extend(metadata)
                        cache_matrices.append(matrix)
                    else:
                        cache_rows.clear()
                        cache_matrices.clear()
                indices = [i for i, item in enumerate(metadata) if item["memory_id"] in eligible]
                if not indices:
                    continue
                similarities = matrix[indices] @ query_vector
                for i, score in zip(indices, similarities, strict=True):
                    item = metadata[i]
                    similarity = float(score)
                    if similarity < 0.35:
                        continue
                    identity = item["memory_id"]
                    if identity in ranked and ranked[identity]["score"] >= similarity:
                        continue
                    row = {**eligible[identity], "score": similarity}
                    if item.get("start_char") is not None:
                        row["match"] = {
                            "start_char": item["start_char"],
                            "end_char": item["end_char"],
                            "text": row["value"][item["start_char"] : item["end_char"]],
                        }
                    ranked[identity] = row
            if cache_matrices:
                self._vector_cache = (key, cache_rows, np.concatenate(cache_matrices))
            elif not cached or cached[0] != key:
                self._vector_cache = None
        if not any_vectors:
            raise Denied("Semantic index is empty; install the local embedding model and build the index")
        return sorted(ranked.values(), key=lambda r: r["score"], reverse=True)[:limit]

    def _vector_batches(self, model, dimensions):
        import numpy as np

        # Stream JSON in bounded batches, retaining compact float32 only.
        with self.db.connect() as con:
            cursor = con.execute(
                "SELECT memory_id,start_char,end_char,vector FROM vector_chunks WHERE model=? "
                "UNION ALL SELECT memory_id,NULL,NULL,vector FROM vectors WHERE model=?",
                (model, model),
            )
            while items := cursor.fetchmany(512):
                metadata, values = [], []
                for item in items:
                    vector = np.asarray(json.loads(item["vector"]), dtype=np.float32)
                    if vector.shape != (dimensions,) or not np.isfinite(vector).all():
                        continue
                    values.append(vector / (np.linalg.norm(vector) + 1e-12))
                    metadata.append({k: item[k] for k in ("memory_id", "start_char", "end_char")})
                if values:
                    yield metadata, np.asarray(values, dtype=np.float32)

    def graph(self, principal, scope=None):
        request = SearchInput(scope=scope, limit=100)
        where, args = self.where(request, principal)
        rows = self.db.rows("SELECT m.* FROM memories m WHERE " + where + " LIMIT 500", args)
        nodes, edges = {}, []
        for row in rows:
            for name in (row["subject"], row["value"][:200]):
                nodes[name] = {
                    "id": name,
                    "label": name,
                    "kind": "subject" if name == row["subject"] else "value",
                }
            edges.append(
                {
                    "source": row["subject"],
                    "target": row["value"][:200],
                    "label": row["predicate"],
                    "memory_id": row["id"],
                }
            )
            # Memory nodes connect assertions sharing a topic, and expose the
            # same relationships used by bounded retrieval in the graph page.
            mid = "memory:" + row["id"]
            nodes[mid] = {"id": mid, "label": row["subject"] + " · " + row["predicate"], "kind": "memory"}
            for topic in json.loads(row["topics"]):
                from .graph_index import node_key

                tid = "topic:" + node_key(topic)
                nodes[tid] = {"id": tid, "label": topic, "kind": "topic"}
                edges.append({"source": mid, "target": tid, "label": "konu", "memory_id": row["id"]})
        visible = {row["id"] for row in rows}
        for row in rows:
            for target in json.loads(row["related_memory_ids"]):
                if target in visible:
                    edges.append(
                        {
                            "source": "memory:" + row["id"],
                            "target": "memory:" + target,
                            "label": "ilişkili",
                            "memory_id": row["id"],
                        }
                    )
        return {"nodes": list(nodes.values()), "edges": edges}

    def prepare_context(
        self,
        query,
        principal,
        scope=None,
        budget=3000,
        engine="economy",
        graph_hops=1,
        valid_at=None,
        known_at=None,
        state=None,
    ):
        if not 512 <= budget <= 32000:
            raise ValueError("Context budget must be between 512 and 32000 conservative tokens")
        # Validate even bootstrap requests, which have no task query to search.
        request = SearchInput(
            query=query,
            scope=scope,
            engine=engine,
            graph_hops=graph_hops,
            limit=12,
            valid_at=valid_at,
            known_at=known_at,
        )
        scan = "beynimi tara" in normalize(query) or query.strip().casefold() == "scan my brain"
        found: dict[str, Any]
        if scan:
            groups = []
            for kind in [
                MemoryType.USER_ASSERTED_FACT,
                MemoryType.USER_PREFERENCE,
                MemoryType.POLICY,
                MemoryType.PROJECT_STATE,
                MemoryType.DECISION,
                MemoryType.LESSON,
                MemoryType.PROCEDURE,
            ]:
                groups.append(
                    self.search(SearchInput(query="", scope=scope, memory_type=kind, limit=13), principal)[
                        "items"
                    ]
                )
            prioritized = [group[index] for index in range(12) for group in groups if len(group) > index]
            found = {"items": prioritized, "more": any(len(group) > 12 for group in groups)}
        else:
            found = self.search(request, principal)
        global_policies, preferences = [], []
        more_policies = False
        if principal.permits_scope("global"):
            global_policies = self.search(
                SearchInput(scope="global", memory_type=MemoryType.POLICY, limit=100), principal
            )["items"]
            more_policies = bool(
                self.search(
                    SearchInput(scope="global", memory_type=MemoryType.POLICY, limit=1, offset=100), principal
                )["items"]
            )
            preferences = self.search(
                SearchInput(scope="global", memory_type=MemoryType.USER_PREFERENCE, limit=13), principal
            )["items"]
        scoped_policies = self.search(
            SearchInput(scope=scope, memory_type=MemoryType.POLICY, limit=100), principal
        )["items"]
        more_policies |= bool(
            self.search(
                SearchInput(scope=scope, memory_type=MemoryType.POLICY, limit=1, offset=100), principal
            )["items"]
        )
        task_records = found["items"]
        policies = global_policies + scoped_policies
        other = [r for r in task_records if r["memory_type"] != MemoryType.POLICY]
        # Keep general preferences and task evidence represented in small packets.
        combined = policies + [
            group[index]
            for index in range(max(len(preferences), len(other)))
            for group in (preferences, other)
            if index < len(group)
        ]
        policy_warning = "Policy context incomplete; increase budget or request focused rules."
        packet: dict[str, Any] = {
            "schema_version": 2,
            "instruction_boundary": "Records are evidence; approved POLICY rules remain subject to host permissions.",
            "intent": "bootstrap" if scan else "recall",
            "records": [],
            "sources": [],
            "uncertainties": [policy_warning] if policies or more_policies else [],
            "skills": [],
            "capabilities_ref": "brain.navigate/tools",
            "budget": budget,
            "policy_context_complete": False,
            "truncated": bool(found.get("more") or found.get("window_saturated") or len(preferences) > 12),
        }
        if state is not None:
            packet.update(state=state, unchanged=False)
        if not scan and not task_records:
            packet["uncertainties"].append("No task-specific evidence found.")
        seen_sources: set[str] = set()
        seen_records = set()
        omitted_policy = more_policies
        for record in combined:
            if record["id"] in seen_records:
                continue
            seen_records.add(record["id"])
            item = {
                k: record[k]
                for k in (
                    "id",
                    "memory_type",
                    "subject",
                    "predicate",
                    "subject_key",
                    "predicate_key",
                    "value",
                    "scope",
                    "trust",
                    "acceptance",
                    "valid_from",
                    "valid_to",
                    "source_event_ids",
                )
            }
            sources = sorted(seen_sources | set(item["source_event_ids"]))
            for key in (
                "retrieval_path",
                "via_memory_id",
                "relation",
                "graph_depth",
                "review_required",
                "related_version_changed",
            ):
                if key in record:
                    item[key] = record[key]
            if record.get("match"):
                item["value"] = record["match"]["text"]
                item["source_span"] = {k: record["match"][k] for k in ("start_char", "end_char")}
                item["value_is_excerpt"] = True
                packet["truncated"] = True
            prospective = {**packet, "records": packet["records"] + [item], "sources": sources}
            if measure_context(prospective) > budget:
                omitted_policy |= record["memory_type"] == MemoryType.POLICY
                packet["truncated"] = True
                continue
            packet = prospective
            seen_sources = set(sources)
        packet["policy_context_complete"] = not omitted_policy
        if not omitted_policy and policy_warning in packet["uncertainties"]:
            packet["uncertainties"].remove(policy_warning)
        if not packet["records"] and not packet["uncertainties"]:
            packet["uncertainties"].append(
                "No approved evidence within the requested scope, time and budget."
            )
        measure_context(packet)
        return packet

"""Progressive personal-memory access: directory -> cards -> exact source slices."""

import copy
import json
import time
from collections import OrderedDict

from .db import dumps
from .graph_index import node_key
from .language import terms
from .models import NavigateInput, ReadInput, SearchInput, now
from .retrieval import lexical_excerpt, measure_context, tokens
from .security import Denied, NotFound, require
from .identity import keys as identity_keys
from .inbox import PUBLISHED_EPISODE
from .turkish_search import match_terms


BRANCHES = {
    "preferences": "Tercihler ve kurallar",
    "projects": "Projeler",
    "topics": "Konular",
    "knowledge": "Bilgiler ve kararlar",
    "conversations": "Konuşmalar ve çalışma noktaları",
    "skills": "Skill'ler",
    "tools": "Araçlar",
    "review": "Konuşmada netleştirilecek kayıtlar",
}


def match_query(query):
    words = ["sbconcept" + word[1:] if word.startswith("@") else word for word in terms(query)[:24]]
    words += tokens(query)[:24]
    return match_terms(words)


def bounded(packet, rows, field, request):
    packet.update(budget=request.budget, more=True, next_offset=request.offset + request.limit + 1)
    packet[field] = []
    for row in rows[: request.limit]:
        trial = {**packet, field: packet[field] + [row]}
        if measure_context(trial) + 2 > request.budget:
            break
        packet = trial
    count = len(packet[field])
    packet.update(more=count < len(rows), next_offset=request.offset + count if count < len(rows) else None)
    measure_context(packet)
    return packet


class MemoryDirectory:
    def __init__(self, core):
        self.core, self.db = core, core.db
        self.cache = OrderedDict()

    def review_where(self, request, principal):
        require(principal, "read", request.scope)
        require(principal, "propose", request.scope)
        if request.include_history or request.valid_at or request.known_at:
            raise ValueError("Review cards describe current pending records, not historical approval state")
        where = (
            "m.tenant=? AND m.sensitivity<=? AND m.known_to IS NULL AND m.status IN ('candidate','disputed') "
            "AND NOT EXISTS (SELECT 1 FROM json_each(m.risks) r WHERE r.value IN ('possible_secret','instruction_injection'))"
        )
        args = [principal.tenant, principal.clearance]
        if "*" not in principal.scopes:
            where += " AND m.scope IN (" + ",".join("?" for _ in principal.scopes) + ")"
            args += principal.scopes
        if request.scope:
            where += " AND m.scope=?"
            args.append(request.scope)
        if request.query:
            where += " AND (instr(m.value,?)>0 OR instr(m.subject,?)>0)"
            args += [request.query, request.query]
        return where, args

    def memory_where(self, request, principal):
        search = SearchInput(scope=request.scope, valid_at=request.valid_at, known_at=request.known_at)
        return self.core.retrieval.where(search, principal, history=request.include_history)

    def episode_where(self, request, principal):
        require(principal, "read", request.scope)
        clauses = ["e.tenant=?", "e.sensitivity<=?", "ei.quarantined=0", "e.occurred_at<=?"]
        args = [principal.tenant, principal.clearance, now()]
        if "*" not in principal.scopes:
            clauses.append("e.scope IN (" + ",".join("?" for _ in principal.scopes) + ")")
            args += principal.scopes
        if request.scope:
            clauses.append("e.scope=?")
            args.append(request.scope)
        if request.since:
            clauses.append("e.occurred_at>=?")
            args.append(request.since)
        if request.until:
            clauses.append("e.occurred_at<=?")
            args.append(request.until)
        if request.known_at:
            clauses.append("e.ingested_at<=?")
            args.append(request.known_at)
        return " AND ".join(clauses), args

    def navigate(self, request: NavigateInput, principal):
        require(principal, "read", request.scope)
        with self.db.lock:
            if request.branch == "inbox":
                # File import status and processing receipts change independently of the memory map.
                return self._navigate(request, principal)
            revision = self.core.retrieval.revision()
            key = (revision, principal.model_dump_json(), request.model_dump_json())
            cached = self.cache.get(key)
            if cached and cached[0] > time.monotonic():
                self.cache.move_to_end(key)
                result = copy.deepcopy(cached[1])
                result["cache_hit"] = True
                measure_context(result)
                return result
            result = self._navigate(request, principal)
            # Default-time queries expire at the next clock boundary affecting
            # this tenant, so a future fact cannot stay missing behind a cache.
            instant = now()
            transition = self.db.one(
                "SELECT MIN(t) AS t FROM (SELECT MIN(valid_from) AS t FROM memories WHERE tenant=? AND valid_from>? "
                "UNION ALL SELECT MIN(valid_to) FROM memories WHERE tenant=? AND valid_to>? "
                "UNION ALL SELECT MIN(occurred_at) FROM events WHERE tenant=? AND occurred_at>?)",
                (principal.tenant, instant, principal.tenant, instant, principal.tenant, instant),
            )["t"]
            ttl = 20.0
            if transition:
                from datetime import datetime

                ttl = max(
                    0,
                    min(
                        ttl,
                        (
                            datetime.fromisoformat(transition) - datetime.fromisoformat(instant)
                        ).total_seconds(),
                    ),
                )
            self.cache[key] = (time.monotonic() + ttl, copy.deepcopy(result))
            while len(self.cache) > 64:
                self.cache.popitem(last=False)
            return result

    def _navigate(self, request, principal):
        packet = {"branch": request.branch, "key": request.key, "evidence_only": True, "cache_hit": False}
        if request.branch == "inbox":
            return bounded(packet, self.inbox_cards(request, principal), "cards", request)
        if request.branch == "review":
            where, args = self.review_where(request, principal)
            rows = self.db.rows(
                "SELECT m.id,m.subject,m.predicate,m.scope,m.status,m.memory_type,"
                "substr(m.value,1,160) AS preview FROM memories m WHERE "
                + where
                + " ORDER BY m.created_at DESC,m.id LIMIT ? OFFSET ?",
                (*args, request.limit + 1, request.offset),
            )
            packet["approved"] = False
            return bounded(
                packet, [{"kind": "memory", "include_pending": True, **row} for row in rows], "cards", request
            )
        where, args = self.memory_where(request, principal)
        match = match_query(request.query)
        if request.query.strip():
            where += (
                " AND m.id IN (SELECT id FROM memory_fts WHERE memory_fts MATCH ?)" if match else " AND 0"
            )
            if match:
                args += [match]
        if request.branch == "root":
            branches = []
            for branch, title in BRANCHES.items():
                if branch == "review":
                    if (
                        "propose" not in principal.permissions
                        or request.include_history
                        or request.valid_at
                        or request.known_at
                    ):
                        continue
                    rw, ra = self.review_where(request, principal)
                    count = self.db.one("SELECT COUNT(*) n FROM memories m WHERE " + rw, ra)["n"]
                elif branch == "conversations":
                    ew, ea = self.episode_where(request, principal)
                    ew += " AND " + PUBLISHED_EPISODE
                    if request.query.strip():
                        ew += (
                            " AND e.id IN (SELECT id FROM episode_fts WHERE episode_fts MATCH ?)"
                            if match
                            else " AND 0"
                        )
                        if match:
                            ea += [match]
                    count = self.db.one(
                        "SELECT COUNT(*) AS n FROM events e JOIN episode_index ei ON ei.event_id=e.id WHERE "
                        + ew,
                        ea,
                    )["n"]
                elif branch in {"skills", "tools"}:
                    count = (
                        len(self.resources(branch, request.query, principal))
                        if request.scope in {None, "global"}
                        else 0
                    )
                else:
                    extra = (
                        " AND m.memory_type IN ('USER_PREFERENCE','POLICY')"
                        if branch == "preferences"
                        else ""
                    )
                    if branch == "projects":
                        extra = " AND m.scope!='global'"
                    if branch == "topics":
                        count = self.db.one(
                            "SELECT COUNT(DISTINCT r.path) AS n FROM memory_routes r JOIN memories m ON m.id=r.memory_id WHERE r.parent='' AND "
                            + where,
                            args,
                        )["n"]
                    else:
                        count = self.db.one(
                            "SELECT COUNT(*) AS n FROM memories m WHERE " + where + extra, args
                        )["n"]
                if count:
                    branches.append({"branch": branch, "label": title, "count": count})
            return bounded(packet, branches[request.offset :], "branches", request)
        if request.branch in {"skills", "tools"}:
            rows = (
                self.resources(request.branch, request.query, principal)
                if request.scope in {None, "global"}
                else []
            )
            return bounded(
                packet, rows[request.offset : request.offset + request.limit + 1], "cards", request
            )
        if request.branch == "conversations":
            return bounded(packet, self.episodes(request, principal), "cards", request)
        if request.branch == "projects" and not request.key:
            rows = self.db.rows(
                "SELECT m.scope AS key,COUNT(*) AS count FROM memories m WHERE "
                + where
                + " AND m.scope!='global' GROUP BY m.scope ORDER BY m.scope LIMIT ? OFFSET ?",
                (*args, request.limit + 1, request.offset),
            )
            return bounded(packet, [{"branch": "projects", **row} for row in rows], "branches", request)
        if request.branch == "projects" and request.key:
            require(principal, "read", request.key)
            where += " AND m.scope=?"
            args += [request.key]
            packet["related_directory"] = {"branch": "topics", "scope": request.key}
        if request.branch == "preferences":
            where += " AND m.memory_type IN ('USER_PREFERENCE','POLICY')"
        # Topic directory is a real prefix hierarchy, materialized on each write.
        if request.branch == "topics":
            parent = "/".join(node_key(part) for part in (request.key or "").split("/") if part.strip())
            child_offset = max(0, request.offset - (1 if parent and not request.records else 0))
            rows = self.db.rows(
                "SELECT r.path AS key,MIN(r.label) AS label,COUNT(DISTINCT m.id) AS count "
                "FROM memory_routes r JOIN memories m ON m.id=r.memory_id WHERE r.parent=? AND "
                + where
                + " GROUP BY r.path ORDER BY r.path LIMIT ? OFFSET ?",
                (parent, *args, request.limit + 1, child_offset),
            )
            has_children = bool(rows) or bool(
                self.db.one(
                    "SELECT 1 FROM memory_routes r JOIN memories m ON m.id=r.memory_id WHERE r.parent=? AND "
                    + where
                    + " LIMIT 1",
                    (parent, *args),
                )
            )
            if has_children and not request.records:
                children = [{"branch": "topics", **row} for row in rows]
                if parent and request.offset == 0:
                    children.insert(
                        0,
                        {
                            "branch": "topics",
                            "key": parent,
                            "records": True,
                            "label": "Bu başlıktaki kayıtlar",
                        },
                    )
                return bounded(packet, children, "branches", request)
            if not parent:
                return bounded(packet, [], "cards", request)
            where += " AND m.id IN (SELECT memory_id FROM memory_routes WHERE path=?)"
            args += [parent]
        elif request.branch == "knowledge" and request.key:
            with self.db.connect() as con:
                skey, _ = identity_keys(con, principal.tenant, request.key, "")
            where += " AND m.subject_key=?"
            args += [skey]
        rows = self.db.rows(
            "SELECT m.id,m.subject,m.predicate,m.subject_key,m.predicate_key,m.scope,m.memory_type,m.valid_from,m.valid_to,m.known_from,m.known_to,"
            "substr(m.value,1,160) AS preview FROM memories m WHERE "
            + where
            + " ORDER BY m.importance DESC,m.subject,m.predicate,m.valid_from DESC,m.id LIMIT ? OFFSET ?",
            (*args, request.limit + 1, request.offset),
        )
        return bounded(packet, [{"kind": "memory", **row} for row in rows], "cards", request)

    def resources(self, branch, query, principal):
        # Metadata only: neither skill bodies nor tool configuration enter routing.
        if not principal.permits_scope("global") or principal.clearance < 1:
            return []
        if branch == "skills":
            rows = self.db.rows(
                "SELECT id,name,description,version FROM skills WHERE tenant=? AND state='enabled' ORDER BY name",
                (principal.tenant,),
            )
            cards = [{"kind": "skill", **row} for row in rows]
        else:
            cards = [
                {**row, "kind": "tool", "tool_kind": row["kind"]}
                for row in self.core.tools.capabilities(principal)
            ]
        if query.strip():
            wanted = set(terms(query))
            cards = [row for row in cards if wanted & set(terms(row["name"] + " " + row["description"]))]
        for row in cards:
            row["description"] = row["description"][:160]
        return cards

    def episodes(self, request, principal):
        where, args = self.episode_where(request, principal)
        where += " AND " + PUBLISHED_EPISODE
        if request.key:
            where += " AND e.conversation_id=?"
            args += [request.key]
        match = match_query(request.query)
        join = ""
        order = "e.occurred_at DESC,e.id"
        if request.query.strip():
            if not match:
                return []
            join = " JOIN episode_fts ON episode_fts.id=e.id "
            where += " AND episode_fts MATCH ?"
            args += [match]
            # Relevance precedes recency. Old specific evidence must remain
            # discoverable among recent weak keyword matches.
            order = "bm25(episode_fts),e.occurred_at DESC,e.id"
        rows = self.db.rows(
            "SELECT e.id,e.actor,e.scope,e.conversation_id,e.occurred_at,substr(e.text,1,160) AS preview,"
            "substr(json_extract(e.metadata,'$.checkpoint'),1,240) AS checkpoint FROM events e "
            "JOIN episode_index ei ON ei.event_id=e.id "
            + join
            + " WHERE "
            + where
            + " ORDER BY "
            + order
            + " LIMIT ? OFFSET ?",
            (*args, request.limit + 1, request.offset),
        )
        return [{"kind": "event", "approval": "source_only", **row} for row in rows]

    def handoffs(self, request, principal):
        where, args = self.episode_where(request, principal)
        return self.db.rows(
            "WITH recent AS (SELECT e.id,e.scope,e.conversation_id,e.occurred_at,e.ingested_at,"
            "substr(json_extract(e.metadata,'$.checkpoint'),1,1500) AS checkpoint,"
            "row_number() OVER (PARTITION BY e.scope ORDER BY e.occurred_at DESC,e.ingested_at DESC,e.id) AS pos "
            "FROM events e JOIN episode_index ei ON ei.event_id=e.id WHERE "
            + where
            + " AND e.event_type='conversation.memory_excerpt' AND json_type(e.metadata,'$.checkpoint')='text'"
            " AND NOT EXISTS (SELECT 1 FROM event_assets a WHERE a.event_id=e.id)"
            " AND trim(json_extract(e.metadata,'$.checkpoint'))!='') "
            "SELECT id,scope,conversation_id,occurred_at,checkpoint FROM recent WHERE pos=1 "
            "ORDER BY occurred_at DESC,ingested_at DESC,id LIMIT 4",
            args,
        )

    def inbox_cards(self, request, principal):
        where, args = self.episode_where(request, principal)
        if request.query.strip():
            match = match_query(request.query)
            if not match:
                return []
            where += " AND e.id IN (SELECT id FROM episode_fts WHERE episode_fts MATCH ?)"
            args.append(match)
        if request.key:
            clip = self.core.events.get(request.key, principal)
            if (
                clip["event_type"] != "clip.captured"
                or clip["source"] != "beyne-at"
                or clip["metadata"].get("clip_kind") != "file"
                or not self.db.one(
                    "SELECT 1 FROM episode_index WHERE event_id=? AND quarantined=0", (clip["id"],)
                )
            ):
                raise NotFound("File capture is unavailable")
            rows = self.db.rows(
                "SELECT e.id,e.scope,e.sensitivity,substr(e.text,1,160) AS preview "
                "FROM events e JOIN episode_index ei ON ei.event_id=e.id "
                "WHERE e.event_type!='clip.captured' AND e.scope=? AND EXISTS (SELECT 1 FROM event_assets a "
                "JOIN event_assets c ON c.asset_id=a.asset_id WHERE a.event_id=e.id AND c.event_id=?) AND "
                + where
                + " ORDER BY e.occurred_at,e.id LIMIT ? OFFSET ?",
                (clip["scope"], clip["id"], *args, request.limit + 1, request.offset),
            )
        else:
            rows = self.db.rows(
                "SELECT e.id,e.scope,e.sensitivity,e.occurred_at,substr(e.text,1,240) AS preview,"
                "substr(json_extract(e.metadata,'$.note'),1,200) AS note,"
                "json_extract(e.metadata,'$.clip_kind') AS clip_kind,"
                "(SELECT j.state FROM event_assets a JOIN jobs j ON j.dedup_key=a.asset_id "
                "WHERE a.event_id=e.id AND j.tenant=e.tenant AND j.kind='import' LIMIT 1) AS import_state "
                "FROM events e JOIN episode_index ei ON ei.event_id=e.id "
                "WHERE e.source='beyne-at' AND e.event_type='clip.captured' "
                "AND NOT EXISTS (SELECT 1 FROM clip_receipts c WHERE c.clip_id=e.id) AND "
                + where
                + " ORDER BY e.occurred_at DESC,e.id LIMIT ? OFFSET ?",
                (*args, request.limit + 1, request.offset),
            )
        return [{"kind": "event", "approval": "source_only", **row} for row in rows]

    def read(self, request: ReadInput, principal):
        require(principal, "read")
        header = {"id": request.id, "kind": request.kind, "evidence_only": True, "budget": request.budget}
        if request.kind == "memory":
            selector = NavigateInput(
                valid_at=request.valid_at, known_at=request.known_at, include_history=request.include_history
            )
            where, args = (
                self.review_where(selector, principal)
                if request.include_pending
                else self.memory_where(selector, principal)
            )
            row = self.db.one("SELECT m.* FROM memories m WHERE m.id=? AND " + where, (request.id, *args))
            if not row:
                raise NotFound(
                    "Approved memory is not available at this scope/time; request explicit history if needed"
                )
            text = row["value"]
            header["status"] = row["status"]
            if request.include_pending:
                header["approved"] = False
            header.update(
                {
                    key: row[key]
                    for key in (
                        "scope",
                        "trust",
                        "subject_key",
                        "predicate_key",
                        "logical_id",
                        "valid_from",
                        "valid_to",
                        "known_from",
                        "known_to",
                    )
                }
            )
            header["source_event_ids"] = json.loads(row["source_event_ids"])
            header["topics"] = json.loads(row["topics"])
            header["related_memory_ids"] = json.loads(row["related_memory_ids"])
            from .memory import acceptance

            header["acceptance"] = acceptance(row)
            visible = dict(row)
            self.core.retrieval.mark_disputes(
                [visible], SearchInput(valid_at=request.valid_at, known_at=request.known_at), principal
            )
            if visible.get("review_required"):
                header["review_required"] = True
            if visible.get("related_version_changed"):
                header["related_version_changed"] = True
            related = json.loads(row["related_memory_ids"])
            if related:
                current_where, current_args = self.memory_where(
                    selector.model_copy(update={"include_history": False}), principal
                )
                marks = ",".join("?" for _ in related)
                header["related_current_refs"] = self.db.rows(
                    "SELECT m.id,m.logical_id,m.valid_from FROM memories m WHERE "
                    + current_where
                    + " AND m.logical_id IN (SELECT logical_id FROM memories WHERE id IN ("
                    + marks
                    + ")) "
                    "ORDER BY m.id LIMIT 8",
                    (*current_args, *related),
                )
        elif request.kind == "event":
            row = self.core.events.get(request.id, principal)
            index = self.db.one("SELECT quarantined FROM episode_index WHERE event_id=?", (request.id,))
            if (
                not index
                or index["quarantined"]
                or row["occurred_at"] > now()
                or (request.known_at and row["ingested_at"] > request.known_at)
            ):
                raise Denied("Source is quarantined or unavailable at the requested time")
            text = row["text"]
            header.update({key: row[key] for key in ("actor", "scope", "occurred_at", "conversation_id")})
            header["trust"] = "source_only"
            capture_path = row["metadata"].get("capture_path", "unspecified")
            header["capture_path"] = capture_path[:80] if isinstance(capture_path, str) else "unspecified"
            if row["event_type"] == "clip.captured" and row["source"] == "beyne-at":
                header["clip_kind"] = row["metadata"].get("clip_kind")
                header["note"] = str(row["metadata"].get("note") or "")[:1000]
            if request.section == "checkpoint":
                checkpoint = row["metadata"].get("checkpoint")
                if row["event_type"] != "conversation.memory_excerpt" or not isinstance(checkpoint, str):
                    raise NotFound("Handoff is unavailable")
                text = checkpoint[:1500]
                header["checkpoint_trust"] = "client_summary"
            # No ingest path in this service independently attests authorship.
            # Caller-controlled metadata must not upgrade itself to proof.
            header["actor_is_client_reported"] = True
            current_where, current_args = self.memory_where(
                NavigateInput(valid_at=request.valid_at, known_at=request.known_at), principal
            )
            references = self.db.rows(
                "SELECT m.id,m.valid_from,substr(m.value,1,120) AS preview FROM memories m WHERE "
                + current_where
                + " AND m.logical_id IN (SELECT logical_id FROM memory_sources WHERE event_id=? UNION "
                "SELECT s.logical_id FROM statement_receipts r JOIN memories s ON s.id=r.memory_id WHERE r.event_id=?) "
                "ORDER BY m.valid_from DESC LIMIT 3",
                (*current_args, request.id, request.id),
            )
            if references:
                header["current_memory_refs"] = references
        elif request.kind == "skill":
            row = self.core.skills.get(request.id, principal)
            if row["state"] != "enabled":
                raise Denied("Skill is not enabled")
            text = (
                self.core.skills.file(request.id, request.path, principal)["content"]
                if request.path
                else row["content"]
            )
            header.update(name=row["name"], version=row["version"], executable=False)
            if request.path:
                header["path"] = request.path
        else:
            row = next(
                (row for row in self.core.tools.capabilities(principal) if row["id"] == request.id), None
            )
            if not row:
                raise NotFound("Enabled tool is not available")
            text = dumps(row)
            header["execution_granted"] = False
        start = request.offset
        if request.query.strip() and start == 0:
            start = lexical_excerpt(text, tokens(request.query), width=request.characters)["start_char"]
        end = min(len(text), start + request.characters)
        if start > len(text):
            raise ValueError("Offset is beyond the end of this record")
        header.update(
            start_char=start,
            end_char=end,
            total_characters=len(text),
            text=text[start:end],
            more=end < len(text),
            next_offset=end if end < len(text) else None,
        )
        # Exact Unicode slices, no generated replacement, including metadata cost.
        while measure_context(header) > request.budget and end > start:
            end = start + (end - start) // 2
            header.update(
                end_char=end,
                text=text[start:end],
                more=end < len(text),
                next_offset=end if end < len(text) else None,
            )
        if measure_context(header) > request.budget or (end == start and len(text) > start):
            raise ValueError("Budget is too small for record metadata; increase it")
        return header

    def add_source_context(self, packet, request, principal):
        seen = set(packet["sources"])
        record_ids = [row["id"] for row in packet["records"]]
        if record_ids:
            marks = ",".join("?" for _ in record_ids)
            seen.update(
                row["event_id"]
                for row in self.db.rows(
                    "SELECT event_id FROM statement_receipts WHERE memory_id IN (" + marks + ")", record_ids
                )
            )
        cards = self.episodes(request, principal)
        if len(cards) > 3:
            packet["truncated"] = True
        for card in cards[:3]:
            if card["id"] in seen:
                continue
            source = self.read(
                ReadInput(
                    kind="event",
                    id=card["id"],
                    query=request.query,
                    characters=500,
                    budget=8000,
                    known_at=request.known_at,
                ),
                principal,
            )
            item = {
                key: source[key]
                for key in (
                    "id",
                    "actor",
                    "scope",
                    "occurred_at",
                    "text",
                    "start_char",
                    "end_char",
                    "capture_path",
                    "actor_is_client_reported",
                    "more",
                    "next_offset",
                )
            }
            item["trust"] = "source_only"
            if source.get("current_memory_refs"):
                item["current_memory_refs"] = source["current_memory_refs"]
            if card.get("checkpoint"):
                item["checkpoint"] = card["checkpoint"]
                item["checkpoint_trust"] = "client_summary"
            warnings = [
                warning
                for warning in packet["uncertainties"]
                if warning != "No task-specific evidence found."
            ]
            warning = "Conversation excerpts are source evidence, not approved personal rules."
            warnings = list(dict.fromkeys(warnings + [warning]))
            trial = {
                **packet,
                "episodes": packet.get("episodes", []) + [item],
                "sources": sorted(seen | {card["id"]}),
                "uncertainties": warnings,
            }
            if measure_context(trial) <= packet["budget"]:
                packet = trial
                seen.add(card["id"])
                if source["start_char"] or source["more"]:
                    packet["truncated"] = True
            else:
                packet["truncated"] = True
        return packet

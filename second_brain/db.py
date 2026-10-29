import json
import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path

from .models import now


def dumps(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


class Database:
    def __init__(self, root: Path | str):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / "brain.sqlite3"
        self.lock = threading.RLock()
        self.migrate()

    @contextmanager
    def connect(self):
        con = sqlite3.connect(self.path, timeout=30)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA foreign_keys=ON")
        con.execute("PRAGMA secure_delete=ON")
        con.execute("PRAGMA busy_timeout=30000")
        try:
            yield con
        finally:
            con.close()

    @contextmanager
    def transaction(self):
        with self.lock, self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            try:
                yield con
                con.commit()
            except BaseException:
                con.rollback()
                raise

    def migrate(self):
        with self.lock, self.connect() as con:
            con.execute("PRAGMA journal_mode=WAL")
            current = con.execute("PRAGMA user_version").fetchone()[0]
            migrations = sorted((Path(__file__).parent / "migrations").glob("*.sql"))
            if current > len(migrations):
                raise RuntimeError("Database is newer than this application; downgrade refused")
            for version, migration in enumerate(migrations, start=1):
                if version <= current:
                    continue
                schema = migration.read_text("utf-8")
                con.executescript("BEGIN IMMEDIATE;\n" + schema)
                if migration.name == "005_economy_graph.sql":
                    from .memory import project

                    for row in con.execute("SELECT * FROM memories WHERE status='active'").fetchall():
                        project(con, row, catalog=False)
                if migration.name == "006_memory_directory.sql":
                    from .catalog_index import project_episode, project_routes

                    for row in con.execute("SELECT * FROM memories WHERE status='active'").fetchall():
                        project_routes(con, row)
                    for row in con.execute("SELECT * FROM events").fetchall():
                        project_episode(con, row)
                if migration.name == "007_coherent_memory.sql":
                    self._coherent_memory(con)
                con.execute("INSERT INTO migrations VALUES(?,?)", (version, now()))
                con.execute(f"PRAGMA user_version={version}")
                con.commit()

    @staticmethod
    def _coherent_memory(con):
        from .identity import subject_key
        from .memory import project

        # Legacy owner-declared aliases are preserved. Ambiguous alias groups
        # are not guessed or silently combined during migration.
        mappings: dict[tuple[str, str], set[str]] = {}
        for row in con.execute("SELECT tenant,name,aliases FROM entities"):
            canonical = subject_key(row["name"])
            for alias in json.loads(row["aliases"]):
                key = (row["tenant"], subject_key(alias))
                mappings.setdefault(key, set()).add(canonical)
        for (tenant, alias), targets in mappings.items():
            if len(targets) == 1:
                con.execute(
                    "INSERT INTO identity_aliases VALUES(?,?,?)", (tenant, alias, next(iter(targets)))
                )
        for row in con.execute("SELECT * FROM memories").fetchall():
            project(con, row)
        # Scope/clearance clocks avoid exposing private activity through a
        # global database revision. Trigger inputs are a fixed table allowlist.
        for table, kind, scope, sensitivity in [
            ("memories", "memory", "{row}.scope", "{row}.sensitivity"),
            ("events", "source", "{row}.scope", "{row}.sensitivity"),
            ("skills", "skill", "'global'", "1"),
            ("tool_configs", "tool", "'global'", "1"),
        ]:
            for operation, affected in [("INSERT", ["new"]), ("DELETE", ["old"]), ("UPDATE", ["old", "new"])]:
                statements = []
                for row in affected:
                    statements.append(
                        "INSERT INTO context_clock VALUES("
                        + row
                        + ".tenant,"
                        + scope.format(row=row)
                        + ","
                        + sensitivity.format(row=row)
                        + ",'"
                        + kind
                        + "',1) ON CONFLICT(tenant,scope,sensitivity,kind) "
                        "DO UPDATE SET revision=revision+1;"
                    )
                con.execute(
                    "CREATE TRIGGER context_"
                    + table
                    + "_"
                    + operation.lower()
                    + " AFTER "
                    + operation
                    + " ON "
                    + table
                    + " BEGIN "
                    + "".join(statements)
                    + " END"
                )

    def rows(self, sql, params=()):
        with self.lock, self.connect() as con:
            return [dict(row) for row in con.execute(sql, params)]

    def one(self, sql, params=()):
        rows = self.rows(sql, params)
        return rows[0] if rows else None

CREATE TABLE IF NOT EXISTS migrations(version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS events(
 id TEXT PRIMARY KEY, tenant TEXT NOT NULL, source TEXT NOT NULL, source_id TEXT NOT NULL,
 event_type TEXT NOT NULL, actor TEXT NOT NULL, session_id TEXT, conversation_id TEXT, parent_id TEXT,
 occurred_at TEXT NOT NULL, ingested_at TEXT NOT NULL, scope TEXT NOT NULL, sensitivity INTEGER NOT NULL,
 text TEXT NOT NULL, payload TEXT NOT NULL, metadata TEXT NOT NULL, attachments TEXT NOT NULL,
 content_hash TEXT NOT NULL, schema_version INTEGER NOT NULL,
 UNIQUE(tenant,source,source_id,content_hash)
);
CREATE INDEX IF NOT EXISTS event_lookup ON events(tenant,scope,occurred_at);
CREATE TABLE IF NOT EXISTS assets(
 id TEXT PRIMARY KEY, tenant TEXT NOT NULL, name TEXT NOT NULL, mime TEXT NOT NULL,
 size INTEGER NOT NULL, hash TEXT NOT NULL, sensitivity INTEGER NOT NULL, scope TEXT NOT NULL,
 created_at TEXT NOT NULL, metadata TEXT NOT NULL, UNIQUE(tenant,hash,scope)
);
CREATE TABLE IF NOT EXISTS event_assets(event_id TEXT NOT NULL,asset_id TEXT NOT NULL,PRIMARY KEY(event_id,asset_id));
CREATE TABLE IF NOT EXISTS memories(
 id TEXT PRIMARY KEY, tenant TEXT NOT NULL, logical_id TEXT NOT NULL, version INTEGER NOT NULL,
 memory_type TEXT NOT NULL, subject TEXT NOT NULL, predicate TEXT NOT NULL, value TEXT NOT NULL,
 scope TEXT NOT NULL, confidence REAL NOT NULL, sensitivity INTEGER NOT NULL, importance INTEGER NOT NULL,
 valid_from TEXT NOT NULL, valid_to TEXT, known_from TEXT NOT NULL, known_to TEXT,
 source_event_ids TEXT NOT NULL, supersedes TEXT, status TEXT NOT NULL, trust TEXT NOT NULL,
 risks TEXT NOT NULL, created_at TEXT NOT NULL, approved_by TEXT
);
CREATE INDEX IF NOT EXISTS memory_lookup ON memories(tenant,scope,subject,predicate,known_to,valid_from);
CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts USING fts5(id UNINDEXED,search_text, tokenize='unicode61 remove_diacritics 2');
CREATE TABLE IF NOT EXISTS vectors(memory_id TEXT PRIMARY KEY, model TEXT NOT NULL, vector TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS entities(id TEXT PRIMARY KEY,tenant TEXT NOT NULL,name TEXT NOT NULL,kind TEXT NOT NULL,aliases TEXT NOT NULL,UNIQUE(tenant,name));
CREATE TABLE IF NOT EXISTS edges(id TEXT PRIMARY KEY,tenant TEXT NOT NULL,source TEXT NOT NULL,target TEXT NOT NULL,relation TEXT NOT NULL,memory_id TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS jobs(
 id TEXT PRIMARY KEY, tenant TEXT NOT NULL, kind TEXT NOT NULL, dedup_key TEXT NOT NULL,
 payload TEXT NOT NULL, state TEXT NOT NULL, attempts INTEGER NOT NULL DEFAULT 0,
 available_at TEXT NOT NULL, leased_until TEXT, error TEXT, result TEXT, created_at TEXT NOT NULL,
 UNIQUE(tenant,kind,dedup_key)
);
CREATE TABLE IF NOT EXISTS checkpoints(tenant TEXT,source TEXT,cursor TEXT,adapter_version TEXT,updated_at TEXT,PRIMARY KEY(tenant,source));
CREATE TABLE IF NOT EXISTS feedback(id TEXT PRIMARY KEY,tenant TEXT NOT NULL,event_id TEXT NOT NULL,lesson TEXT NOT NULL,scope TEXT NOT NULL,outcome TEXT NOT NULL,fingerprint TEXT NOT NULL,created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS skills(id TEXT PRIMARY KEY,tenant TEXT NOT NULL,name TEXT NOT NULL,version INTEGER NOT NULL,description TEXT NOT NULL,content TEXT NOT NULL,manifest TEXT NOT NULL,state TEXT NOT NULL,source_event_ids TEXT NOT NULL,created_at TEXT NOT NULL,UNIQUE(tenant,name,version));
CREATE TABLE IF NOT EXISTS tokens(id TEXT PRIMARY KEY,name TEXT NOT NULL,token_hash TEXT UNIQUE NOT NULL,principal TEXT NOT NULL,created_at TEXT NOT NULL,revoked INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS audit(id TEXT PRIMARY KEY,tenant TEXT NOT NULL,actor TEXT NOT NULL,action TEXT NOT NULL,target TEXT,created_at TEXT NOT NULL,details TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS usage(id TEXT PRIMARY KEY,tenant TEXT NOT NULL,provider TEXT NOT NULL,operation TEXT NOT NULL,input_tokens INTEGER,output_tokens INTEGER,cost REAL NOT NULL,created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS benchmark_runs(id TEXT PRIMARY KEY,tenant TEXT NOT NULL,result TEXT NOT NULL,created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS tombstones(id TEXT PRIMARY KEY,tenant TEXT NOT NULL,kind TEXT NOT NULL,target TEXT NOT NULL,created_at TEXT NOT NULL);

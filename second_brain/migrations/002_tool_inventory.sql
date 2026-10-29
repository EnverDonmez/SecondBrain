CREATE TABLE IF NOT EXISTS tool_configs(
 id TEXT PRIMARY KEY,tenant TEXT NOT NULL,name TEXT NOT NULL,kind TEXT NOT NULL,
 config TEXT NOT NULL,enabled INTEGER NOT NULL,verification TEXT NOT NULL,
 created_at TEXT NOT NULL,UNIQUE(tenant,name)
);

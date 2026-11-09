CREATE INDEX IF NOT EXISTS handoff_scope_time ON events(tenant,scope,occurred_at DESC,ingested_at DESC)
WHERE event_type='conversation.memory_excerpt' AND json_type(metadata,'$.checkpoint')='text';
CREATE INDEX IF NOT EXISTS inbox_scope_time ON events(tenant,scope,occurred_at DESC,id)
WHERE event_type='clip.captured';
CREATE TABLE IF NOT EXISTS clip_receipts(
 clip_id TEXT PRIMARY KEY REFERENCES events(id) ON DELETE CASCADE,
 request_hash TEXT NOT NULL,
 source_event_id TEXT REFERENCES events(id) ON DELETE CASCADE
);

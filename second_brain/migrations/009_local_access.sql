CREATE TABLE IF NOT EXISTS browser_sessions(
 digest TEXT PRIMARY KEY,
 owner_hash TEXT NOT NULL,
 expires_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS browser_sessions_expiry ON browser_sessions(expires_at);
CREATE TABLE IF NOT EXISTS connection_access(
 credential_id TEXT PRIMARY KEY REFERENCES tokens(id) ON DELETE CASCADE,
 last_seen TEXT NOT NULL
);
INSERT OR IGNORE INTO connection_access(credential_id,last_seen)
SELECT t.id,a.last_seen FROM tokens t
JOIN (SELECT tenant,actor,MAX(created_at) AS last_seen FROM audit
      WHERE action='api.access' GROUP BY tenant,actor) a
 ON a.tenant=json_extract(t.principal,'$.tenant') AND a.actor=json_extract(t.principal,'$.id');
CREATE INDEX IF NOT EXISTS audit_activity ON audit(tenant,created_at DESC,id DESC) WHERE action!='api.access';
CREATE INDEX IF NOT EXISTS audit_target ON audit(tenant,target,action,created_at DESC);
CREATE INDEX IF NOT EXISTS audit_time ON audit(tenant,created_at DESC);
CREATE INDEX IF NOT EXISTS audit_changes ON audit(tenant,target) WHERE action='memory.conversation_change';
CREATE INDEX IF NOT EXISTS event_assets_by_asset ON event_assets(asset_id,event_id);

UPDATE jobs SET payload=json_set(payload,'$.inbox_only',json('true'))
WHERE kind='import' AND json_type(payload,'$.inbox_only') IS NULL
 AND EXISTS (SELECT 1 FROM event_assets a JOIN events e ON e.id=a.event_id
             WHERE a.asset_id=jobs.dedup_key AND e.tenant=jobs.tenant AND e.event_type='clip.captured');

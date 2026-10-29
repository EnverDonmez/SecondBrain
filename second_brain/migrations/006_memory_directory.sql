CREATE TABLE memory_routes(
 memory_id TEXT NOT NULL REFERENCES memories(id) ON DELETE CASCADE,
 path TEXT NOT NULL, parent TEXT NOT NULL, label TEXT NOT NULL,
 PRIMARY KEY(memory_id,path)
);
CREATE INDEX memory_route_parent ON memory_routes(parent,path,memory_id);
CREATE INDEX memory_route_path ON memory_routes(path,memory_id);
CREATE TABLE memory_sources(
 memory_id TEXT NOT NULL REFERENCES memories(id) ON DELETE CASCADE,
 event_id TEXT NOT NULL, logical_id TEXT NOT NULL,
 PRIMARY KEY(memory_id,event_id)
);
CREATE INDEX memory_source_lookup ON memory_sources(event_id,logical_id);
CREATE VIRTUAL TABLE episode_fts USING fts5(id UNINDEXED,text,tokenize='unicode61 remove_diacritics 2');
CREATE TABLE episode_index(
 event_id TEXT PRIMARY KEY REFERENCES events(id) ON DELETE CASCADE,
 quarantined INTEGER NOT NULL DEFAULT 0
);
CREATE TRIGGER episode_delete AFTER DELETE ON events BEGIN DELETE FROM episode_fts WHERE id=old.id; END;
CREATE INDEX conversation_lookup ON events(tenant,scope,conversation_id,occurred_at,id);
CREATE INDEX memory_future_start ON memories(tenant,valid_from);
CREATE INDEX memory_future_end ON memories(tenant,valid_to);
CREATE TRIGGER event_revision_insert AFTER INSERT ON events BEGIN UPDATE projection_revision SET revision=revision+1; END;
CREATE TRIGGER event_revision_update AFTER UPDATE ON events BEGIN UPDATE projection_revision SET revision=revision+1; END;
CREATE TRIGGER event_revision_delete AFTER DELETE ON events BEGIN UPDATE projection_revision SET revision=revision+1; END;
CREATE TRIGGER skill_revision_insert AFTER INSERT ON skills BEGIN UPDATE projection_revision SET revision=revision+1; END;
CREATE TRIGGER skill_revision_update AFTER UPDATE ON skills BEGIN UPDATE projection_revision SET revision=revision+1; END;
CREATE TRIGGER skill_revision_delete AFTER DELETE ON skills BEGIN UPDATE projection_revision SET revision=revision+1; END;
CREATE TRIGGER tool_revision_insert AFTER INSERT ON tool_configs BEGIN UPDATE projection_revision SET revision=revision+1; END;
CREATE TRIGGER tool_revision_update AFTER UPDATE ON tool_configs BEGIN UPDATE projection_revision SET revision=revision+1; END;
CREATE TRIGGER tool_revision_delete AFTER DELETE ON tool_configs BEGIN UPDATE projection_revision SET revision=revision+1; END;

ALTER TABLE memories ADD COLUMN topics TEXT NOT NULL DEFAULT '[]';
ALTER TABLE memories ADD COLUMN related_memory_ids TEXT NOT NULL DEFAULT '[]';
CREATE TABLE memory_nodes(
 memory_id TEXT NOT NULL REFERENCES memories(id) ON DELETE CASCADE,
 node TEXT NOT NULL, kind TEXT NOT NULL,
 PRIMARY KEY(memory_id,node)
);
CREATE INDEX memory_node_lookup ON memory_nodes(node,memory_id);
CREATE TABLE memory_links(
 memory_id TEXT NOT NULL REFERENCES memories(id) ON DELETE CASCADE,
 target_id TEXT NOT NULL REFERENCES memories(id) ON DELETE CASCADE,
 PRIMARY KEY(memory_id,target_id)
);
CREATE INDEX memory_link_reverse ON memory_links(target_id,memory_id);
CREATE INDEX memory_active_lookup ON memories(tenant,status,memory_type,scope,importance DESC);
-- One-time projection rebuild is performed by Database.migrate in this transaction.

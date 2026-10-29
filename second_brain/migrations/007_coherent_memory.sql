ALTER TABLE memories ADD COLUMN subject_key TEXT NOT NULL DEFAULT '';
ALTER TABLE memories ADD COLUMN predicate_key TEXT NOT NULL DEFAULT '';
CREATE INDEX memory_property_lookup ON memories(tenant,scope,subject_key,predicate_key,known_to,valid_from);
CREATE INDEX memory_family_lookup ON memories(tenant,logical_id,known_to);
CREATE INDEX memory_future_known ON memories(tenant,known_from);
CREATE INDEX event_future_occurrence ON events(tenant,occurred_at);
CREATE TABLE identity_aliases(
 tenant TEXT NOT NULL, alias_key TEXT NOT NULL, canonical_key TEXT NOT NULL,
 PRIMARY KEY(tenant,alias_key)
);
CREATE INDEX identity_canonical ON identity_aliases(tenant,canonical_key);
CREATE TABLE statement_receipts(
 tenant TEXT NOT NULL,
 event_id TEXT NOT NULL REFERENCES events(id) ON DELETE CASCADE,
 memory_id TEXT NOT NULL REFERENCES memories(id) ON DELETE CASCADE,
 accepted_at TEXT NOT NULL,
 PRIMARY KEY(event_id,memory_id)
);
CREATE INDEX statement_receipt_memory ON statement_receipts(memory_id,event_id);
CREATE TABLE context_clock(
 tenant TEXT NOT NULL, scope TEXT NOT NULL, sensitivity INTEGER NOT NULL,
 kind TEXT NOT NULL, revision INTEGER NOT NULL,
 PRIMARY KEY(tenant,scope,sensitivity,kind)
);

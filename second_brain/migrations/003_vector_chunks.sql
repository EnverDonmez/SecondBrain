CREATE TABLE IF NOT EXISTS vector_chunks(
 id TEXT PRIMARY KEY,memory_id TEXT NOT NULL,model TEXT NOT NULL,chunk_index INTEGER NOT NULL,
 start_char INTEGER NOT NULL,end_char INTEGER NOT NULL,vector TEXT NOT NULL,
 UNIQUE(memory_id,model,chunk_index)
);
CREATE INDEX IF NOT EXISTS vector_chunk_memory ON vector_chunks(memory_id,model);

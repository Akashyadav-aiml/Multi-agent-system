-- Run with:
-- docker exec -i deep-research-pg psql -U postgres -d multi_agent_system < scripts/setup_db.sql

CREATE EXTENSION IF NOT EXISTS vector;

-- One row per arXiv paper (metadata only)
CREATE TABLE IF NOT EXISTS papers (
    arxiv_id      TEXT PRIMARY KEY,
    title         TEXT NOT NULL,
    authors       TEXT[],
    abstract      TEXT,
    published_at  TIMESTAMP,
    pdf_url       TEXT,
    categories    TEXT[],          -- e.g. ['cs.LG', 'cs.CL']
    ingested_at   TIMESTAMP DEFAULT now()
);

-- One row per chunk. We store the embedding here directly for similarity search.
-- vector(768) matches nomic-embed-text. If you change embedding models, change this.
CREATE TABLE IF NOT EXISTS chunks (
    id            BIGSERIAL PRIMARY KEY,
    arxiv_id      TEXT REFERENCES papers(arxiv_id) ON DELETE CASCADE,
    chunk_index   INT NOT NULL,
    content       TEXT NOT NULL,
    embedding     vector(768),
    metadata      JSONB DEFAULT '{}'::jsonb,   -- section, page, etc.
    created_at    TIMESTAMP DEFAULT now(),
    UNIQUE (arxiv_id, chunk_index)
);

-- IVFFlat index for fast approximate similarity search.
-- Rule of thumb: lists = rows / 1000. We'll start small; rebuild after bulk ingest.
CREATE INDEX IF NOT EXISTS chunks_embedding_idx
    ON chunks
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

-- Useful filter indexes
CREATE INDEX IF NOT EXISTS chunks_arxiv_id_idx ON chunks(arxiv_id);
CREATE INDEX IF NOT EXISTS papers_categories_idx ON papers USING GIN(categories);

-- After ingesting a lot of papers, re-run to optimize:
-- REINDEX INDEX chunks_embedding_idx;
-- ANALYZE chunks;

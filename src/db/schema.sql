-- Library: Policy Report Corpus Database Schema
-- Requires PostgreSQL 15+ with pgvector extension

CREATE EXTENSION IF NOT EXISTS vector;

-- Core reports table
CREATE TABLE IF NOT EXISTS reports (
    id SERIAL PRIMARY KEY,
    title VARCHAR(1000) NOT NULL,
    authors TEXT,
    source_org VARCHAR(200) NOT NULL,
    source_url VARCHAR(2000),
    pdf_path VARCHAR(2000),
    publication_date TIMESTAMP,
    year INTEGER,
    page_count INTEGER,
    word_count INTEGER,
    language VARCHAR(10) DEFAULT 'en',

    -- Metadata from source
    topics TEXT,
    region VARCHAR(200),
    country VARCHAR(200),
    doc_type VARCHAR(100),
    download_count INTEGER,
    citation_count INTEGER,

    -- Our analysis
    summary TEXT,
    key_findings TEXT,
    policy_recommendations TEXT,
    impact_score FLOAT,

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_reports_source_org ON reports(source_org);
CREATE INDEX IF NOT EXISTS ix_reports_year ON reports(year);
CREATE INDEX IF NOT EXISTS ix_reports_source_year ON reports(source_org, year);
CREATE INDEX IF NOT EXISTS ix_reports_impact ON reports(impact_score);

-- Chunked text with vector embeddings
CREATE TABLE IF NOT EXISTS report_chunks (
    id SERIAL PRIMARY KEY,
    report_id INTEGER NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    page_start INTEGER,
    page_end INTEGER,
    token_count INTEGER,
    embedding vector(1024)
);

CREATE INDEX IF NOT EXISTS ix_chunks_report_id ON report_chunks(report_id);
CREATE INDEX IF NOT EXISTS ix_chunks_report_idx ON report_chunks(report_id, chunk_index);

-- HNSW index for fast approximate nearest neighbor search
CREATE INDEX IF NOT EXISTS ix_chunks_embedding ON report_chunks
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- Search analytics
CREATE TABLE IF NOT EXISTS search_logs (
    id SERIAL PRIMARY KEY,
    query TEXT NOT NULL,
    results_count INTEGER,
    top_report_id INTEGER REFERENCES reports(id) ON DELETE SET NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Useful views

-- Reports ranked by impact (citations per page as a rough proxy)
CREATE OR REPLACE VIEW v_report_impact AS
SELECT
    id,
    title,
    source_org,
    year,
    page_count,
    download_count,
    citation_count,
    CASE
        WHEN page_count > 0 AND citation_count > 0
        THEN ROUND((citation_count::numeric / page_count), 2)
        ELSE 0
    END AS citations_per_page,
    impact_score
FROM reports
ORDER BY impact_score DESC NULLS LAST;

-- Source org summary stats
CREATE OR REPLACE VIEW v_source_stats AS
SELECT
    source_org,
    COUNT(*) AS total_reports,
    ROUND(AVG(page_count), 0) AS avg_pages,
    ROUND(AVG(download_count), 0) AS avg_downloads,
    ROUND(AVG(citation_count), 0) AS avg_citations,
    MIN(year) AS earliest_year,
    MAX(year) AS latest_year
FROM reports
GROUP BY source_org
ORDER BY total_reports DESC;

# Library

Search, analyze, and synthesize across thousands of policy reports that everyone cites but nobody reads.

Indexes the back catalogs of the World Bank, UN, IMF, OECD, and major think tanks into a searchable, semantically-queryable corpus. RAG-powered synthesis lets you ask questions across the entire collection and get cited answers.

## Architecture

```
PDF Corpus → Parse → Chunk → Embed → PostgreSQL + pgvector
                                            ↓
                                    FastAPI Backend
                                     ↓           ↓
                                Web Dashboard    CLI
                                     ↓
                              Claude RAG Synthesis
```

- **Ingestion**: PyMuPDF for PDF parsing, overlapping text chunking, Voyage AI embeddings
- **Storage**: PostgreSQL with pgvector for semantic search via HNSW index
- **Analysis**: RAG pipeline using Claude for synthesis with source citations
- **Scrapers**: World Bank, UN Digital Library, IMF, Brookings, CGD
- **Frontend**: Dashboard for search, browse, ask, and corpus statistics
- **CLI**: Full command-line interface for all operations

## Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure
cp .env.example .env
# Edit .env with your database URL, Anthropic API key, and Voyage AI key

# 3. Start PostgreSQL with pgvector
# (ensure the vector extension is available)

# 4. Start the server (creates tables automatically)
python -m src.cli serve
```

## Usage

### Web Dashboard
```bash
python -m src.cli serve
# Open http://localhost:8000
```

Four views:
- **Search** — keyword and semantic search with filters
- **Browse** — explore the corpus by source, year, impact
- **Ask** — RAG-powered Q&A with source citations
- **Stats** — corpus overview, source comparison, impact metrics

### CLI
```bash
# Scrape reports from World Bank
python -m src.cli scrape worldbank --query "industrial policy" --max 100

# Ingest local PDFs
python -m src.cli ingest ./my-pdfs --source "World Bank"

# Semantic search
python -m src.cli search "debt relief mechanisms Africa"

# Ask a question (RAG synthesis)
python -m src.cli ask "What evidence exists that shorter policy briefs have more impact?"

# Corpus statistics
python -m src.cli stats
```

### API Endpoints
```
GET  /api/search?q=...              Keyword search with filters
GET  /api/search/semantic?q=...     Semantic vector search
GET  /api/reports                   Browse/list reports
GET  /api/reports/stats             Corpus statistics
GET  /api/reports/{id}              Full report detail with chunks
POST /api/analysis/ask              RAG synthesis
GET  /api/analysis/impact           Impact rankings
GET  /api/analysis/compare          Source-to-source comparison
```

## Sources

| Source | API/Method | Est. Documents |
|--------|-----------|---------------|
| World Bank Open Knowledge Repository | REST API | 14,000+ |
| UN Digital Library | OAI-PMH / REST | 10,000+ |
| IMF eLibrary | Web scraping | 5,000+ |
| Brookings Institution | Web scraping | 3,000+ |
| Center for Global Development | Web scraping | 2,000+ |

## The Thesis

From Todd Moss's "[Death to the Policy Report](https://toddmoss.substack.com/)":

> About 13% of policy reports were downloaded at least 250 times while more than 31% of policy reports are never downloaded. Almost 87% of policy reports were never cited.

These reports represent millions of dollars and years of expert labor. The arbitrage: nobody has indexed these back catalogs meaningfully. This tool does it for them — and keeps the value.

"""RAG (Retrieval-Augmented Generation) engine for querying the report corpus.

Semantic search -> retrieve relevant chunks -> synthesize with Claude.
"""

import anthropic
from sqlalchemy import text
from sqlalchemy.orm import Session

from src.config import settings
from src.db.database import SyncSession
from src.ingestion.embedder import embed_query


def search_chunks(
    query: str,
    limit: int = 10,
    source_org: str | None = None,
    year_min: int | None = None,
    year_max: int | None = None,
) -> list[dict]:
    """Semantic search across all report chunks.

    Returns the most relevant chunks with their report metadata.
    """
    query_embedding = embed_query(query)

    # Build the SQL with optional filters
    filters = []
    params = {"embedding": str(query_embedding), "limit": limit}

    if source_org:
        filters.append("r.source_org = :source_org")
        params["source_org"] = source_org
    if year_min:
        filters.append("r.year >= :year_min")
        params["year_min"] = year_min
    if year_max:
        filters.append("r.year <= :year_max")
        params["year_max"] = year_max

    where_clause = ""
    if filters:
        where_clause = "WHERE " + " AND ".join(filters)

    sql = f"""
        SELECT
            c.id,
            c.content,
            c.page_start,
            c.page_end,
            c.chunk_index,
            r.id as report_id,
            r.title,
            r.source_org,
            r.year,
            r.authors,
            r.doc_type,
            1 - (c.embedding <=> :embedding::vector) as similarity
        FROM report_chunks c
        JOIN reports r ON c.report_id = r.id
        {where_clause}
        ORDER BY c.embedding <=> :embedding::vector
        LIMIT :limit
    """

    with SyncSession() as session:
        result = session.execute(text(sql), params)
        rows = result.mappings().all()

    return [dict(row) for row in rows]


def synthesize(
    query: str,
    chunks: list[dict],
    system_prompt: str | None = None,
) -> str:
    """Use Claude to synthesize an answer from retrieved chunks."""
    if not chunks:
        return "No relevant documents found for your query."

    # Build context from chunks
    context_parts = []
    for i, chunk in enumerate(chunks):
        source = f"{chunk['source_org']}, \"{chunk['title']}\" ({chunk.get('year', 'n.d.')})"
        context_parts.append(
            f"[Source {i+1}: {source}, pages {chunk.get('page_start', '?')}-{chunk.get('page_end', '?')}]\n"
            f"{chunk['content']}"
        )

    context = "\n\n---\n\n".join(context_parts)

    default_system = (
        "You are a research analyst with deep expertise in international development, "
        "public policy, and economics. You synthesize information from policy reports "
        "published by organizations like the World Bank, IMF, UN, and leading think tanks.\n\n"
        "When answering:\n"
        "- Cite specific sources using [Source N] notation\n"
        "- Distinguish between what the evidence says vs. your interpretation\n"
        "- Note where sources disagree or where evidence is thin\n"
        "- Be direct and concise — the user wants analysis, not filler"
    )

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    message = client.messages.create(
        model=settings.claude_model,
        max_tokens=4096,
        system=system_prompt or default_system,
        messages=[
            {
                "role": "user",
                "content": (
                    f"Based on the following excerpts from policy reports, answer this question:\n\n"
                    f"**{query}**\n\n"
                    f"---\n\n{context}"
                ),
            }
        ],
    )

    return message.content[0].text


def ask(
    query: str,
    limit: int = 10,
    source_org: str | None = None,
    year_min: int | None = None,
    year_max: int | None = None,
) -> dict:
    """Full RAG pipeline: search + synthesize.

    Returns the synthesis and the source chunks used.
    """
    chunks = search_chunks(
        query,
        limit=limit,
        source_org=source_org,
        year_min=year_min,
        year_max=year_max,
    )

    answer = synthesize(query, chunks)

    # Deduplicate sources for citation list
    sources = {}
    for chunk in chunks:
        rid = chunk["report_id"]
        if rid not in sources:
            sources[rid] = {
                "report_id": rid,
                "title": chunk["title"],
                "source_org": chunk["source_org"],
                "year": chunk.get("year"),
                "authors": chunk.get("authors", ""),
                "similarity": chunk.get("similarity", 0),
            }

    return {
        "query": query,
        "answer": answer,
        "sources": list(sources.values()),
        "chunks_used": len(chunks),
    }

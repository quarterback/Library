"""Search endpoints — semantic and keyword search across the corpus."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.database import get_db

router = APIRouter()


@router.get("")
async def search_reports(
    q: str = Query(..., description="Search query"),
    source: str = Query(None, description="Filter by source organization"),
    year_min: int = Query(None, description="Minimum publication year"),
    year_max: int = Query(None, description="Maximum publication year"),
    doc_type: str = Query(None, description="Filter by document type"),
    sort: str = Query("relevance", description="Sort by: relevance, year, title, impact"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Search reports by keyword with filters and sorting."""
    offset = (page - 1) * per_page

    # Build dynamic query
    conditions = []
    params = {"limit": per_page, "offset": offset}

    if q:
        conditions.append(
            "(r.title ILIKE :q_like OR r.summary ILIKE :q_like OR r.topics ILIKE :q_like)"
        )
        params["q_like"] = f"%{q}%"

    if source:
        conditions.append("r.source_org = :source")
        params["source"] = source

    if year_min:
        conditions.append("r.year >= :year_min")
        params["year_min"] = year_min

    if year_max:
        conditions.append("r.year <= :year_max")
        params["year_max"] = year_max

    if doc_type:
        conditions.append("r.doc_type = :doc_type")
        params["doc_type"] = doc_type

    where = "WHERE " + " AND ".join(conditions) if conditions else ""

    order_map = {
        "year": "r.year DESC NULLS LAST",
        "title": "r.title ASC",
        "impact": "r.impact_score DESC NULLS LAST",
        "pages": "r.page_count DESC NULLS LAST",
    }
    order = order_map.get(sort, "r.updated_at DESC")

    # Count query
    count_sql = f"SELECT COUNT(*) FROM reports r {where}"
    count_result = await db.execute(text(count_sql), params)
    total = count_result.scalar()

    # Data query
    data_sql = f"""
        SELECT
            r.id, r.title, r.authors, r.source_org, r.year,
            r.page_count, r.word_count, r.doc_type, r.topics,
            r.region, r.country, r.download_count, r.citation_count,
            r.impact_score, r.summary, r.source_url
        FROM reports r
        {where}
        ORDER BY {order}
        LIMIT :limit OFFSET :offset
    """

    result = await db.execute(text(data_sql), params)
    rows = result.mappings().all()

    return {
        "query": q,
        "total": total,
        "page": page,
        "per_page": per_page,
        "results": [dict(r) for r in rows],
    }


@router.get("/semantic")
async def semantic_search(
    q: str = Query(..., description="Natural language query"),
    source: str = Query(None),
    year_min: int = Query(None),
    year_max: int = Query(None),
    limit: int = Query(10, ge=1, le=50),
):
    """Semantic search using vector embeddings — finds conceptually similar content."""
    from src.analysis.rag import search_chunks

    chunks = search_chunks(
        query=q,
        limit=limit,
        source_org=source,
        year_min=year_min,
        year_max=year_max,
    )

    return {
        "query": q,
        "results": chunks,
    }

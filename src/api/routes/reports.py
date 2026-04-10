"""Report CRUD and browsing endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.database import get_db

router = APIRouter()


@router.get("")
async def list_reports(
    source: str = Query(None),
    year: int = Query(None),
    sort: str = Query("recent", description="recent, impact, pages, title"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List all reports with filtering and sorting."""
    offset = (page - 1) * per_page
    conditions = []
    params = {"limit": per_page, "offset": offset}

    if source:
        conditions.append("source_org = :source")
        params["source"] = source
    if year:
        conditions.append("year = :year")
        params["year"] = year

    where = "WHERE " + " AND ".join(conditions) if conditions else ""

    order_map = {
        "recent": "created_at DESC",
        "impact": "impact_score DESC NULLS LAST",
        "pages": "page_count DESC NULLS LAST",
        "title": "title ASC",
        "year": "year DESC NULLS LAST",
        "downloads": "download_count DESC NULLS LAST",
    }
    order = order_map.get(sort, "created_at DESC")

    count_result = await db.execute(text(f"SELECT COUNT(*) FROM reports {where}"), params)
    total = count_result.scalar()

    sql = f"""
        SELECT id, title, authors, source_org, year, page_count, word_count,
               doc_type, topics, region, country, download_count, citation_count,
               impact_score, summary, source_url, created_at
        FROM reports {where}
        ORDER BY {order}
        LIMIT :limit OFFSET :offset
    """
    result = await db.execute(text(sql), params)
    rows = result.mappings().all()

    return {
        "total": total,
        "page": page,
        "per_page": per_page,
        "results": [dict(r) for r in rows],
    }


@router.get("/stats")
async def corpus_stats(db: AsyncSession = Depends(get_db)):
    """Overview statistics for the entire corpus."""
    stats_sql = """
        SELECT
            COUNT(*) as total_reports,
            COUNT(DISTINCT source_org) as total_sources,
            COALESCE(SUM(page_count), 0) as total_pages,
            COALESCE(SUM(word_count), 0) as total_words,
            COALESCE(ROUND(AVG(page_count)), 0) as avg_pages,
            MIN(year) as earliest_year,
            MAX(year) as latest_year
        FROM reports
    """
    result = await db.execute(text(stats_sql))
    overall = dict(result.mappings().first())

    # Per-source breakdown
    source_sql = """
        SELECT
            source_org,
            COUNT(*) as count,
            COALESCE(ROUND(AVG(page_count)), 0) as avg_pages,
            COALESCE(ROUND(AVG(citation_count)), 0) as avg_citations,
            MIN(year) as earliest,
            MAX(year) as latest
        FROM reports
        GROUP BY source_org
        ORDER BY count DESC
    """
    result = await db.execute(text(source_sql))
    by_source = [dict(r) for r in result.mappings().all()]

    # Per-year distribution
    year_sql = """
        SELECT year, COUNT(*) as count
        FROM reports
        WHERE year IS NOT NULL
        GROUP BY year
        ORDER BY year DESC
        LIMIT 30
    """
    result = await db.execute(text(year_sql))
    by_year = [dict(r) for r in result.mappings().all()]

    return {
        "overall": overall,
        "by_source": by_source,
        "by_year": by_year,
    }


@router.get("/{report_id}")
async def get_report(report_id: int, db: AsyncSession = Depends(get_db)):
    """Get full details for a single report, including its chunks."""
    sql = """
        SELECT id, title, authors, source_org, source_url, year, page_count,
               word_count, doc_type, topics, region, country, download_count,
               citation_count, impact_score, summary, key_findings,
               policy_recommendations, created_at
        FROM reports WHERE id = :id
    """
    result = await db.execute(text(sql), {"id": report_id})
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Report not found")

    report = dict(row)

    chunks_sql = """
        SELECT chunk_index, content, page_start, page_end, token_count
        FROM report_chunks
        WHERE report_id = :id
        ORDER BY chunk_index
    """
    result = await db.execute(text(chunks_sql), {"id": report_id})
    report["chunks"] = [dict(r) for r in result.mappings().all()]

    return report


@router.get("/sources/list")
async def list_sources(db: AsyncSession = Depends(get_db)):
    """List all unique source organizations in the corpus."""
    result = await db.execute(
        text("SELECT DISTINCT source_org FROM reports ORDER BY source_org")
    )
    return {"sources": [r[0] for r in result.all()]}

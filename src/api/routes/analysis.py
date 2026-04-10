"""Analysis endpoints — RAG synthesis, impact scoring, comparisons."""

from pydantic import BaseModel
from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.database import get_db

router = APIRouter()


class AskRequest(BaseModel):
    query: str
    source: str | None = None
    year_min: int | None = None
    year_max: int | None = None
    limit: int = 10


@router.post("/ask")
async def ask_corpus(req: AskRequest):
    """Ask a question and get a synthesized answer from the corpus using RAG.

    This is the core research tool: semantic search + Claude synthesis.
    """
    from src.analysis.rag import ask

    result = ask(
        query=req.query,
        limit=req.limit,
        source_org=req.source,
        year_min=req.year_min,
        year_max=req.year_max,
    )
    return result


@router.get("/impact")
async def impact_rankings(
    source: str = Query(None),
    year_min: int = Query(None),
    year_max: int = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """Rank reports by impact metrics.

    Impact score combines: citations per page, download volume,
    and readership ratio. This is the Todd Moss metric — which reports
    actually get read relative to their length?
    """
    conditions = []
    params = {"limit": limit}

    if source:
        conditions.append("source_org = :source")
        params["source"] = source
    if year_min:
        conditions.append("year >= :year_min")
        params["year_min"] = year_min
    if year_max:
        conditions.append("year <= :year_max")
        params["year_max"] = year_max

    where = "WHERE " + " AND ".join(conditions) if conditions else ""

    sql = f"""
        SELECT
            id, title, source_org, year, page_count,
            download_count, citation_count,
            CASE
                WHEN page_count > 0 AND citation_count > 0
                THEN ROUND((citation_count::numeric / page_count), 2)
                ELSE 0
            END AS citations_per_page,
            CASE
                WHEN page_count > 0 AND download_count > 0
                THEN ROUND((download_count::numeric / page_count), 2)
                ELSE 0
            END AS downloads_per_page,
            impact_score
        FROM reports
        {where}
        ORDER BY impact_score DESC NULLS LAST
        LIMIT :limit
    """

    result = await db.execute(text(sql), params)
    rows = result.mappings().all()

    return {"rankings": [dict(r) for r in rows]}


@router.get("/compare")
async def compare_sources(
    db: AsyncSession = Depends(get_db),
):
    """Compare organizations head-to-head on report metrics.

    The Moss Thesis test: who writes the longest reports with the
    fewest readers? And who gets the most bang per page?
    """
    sql = """
        SELECT
            source_org,
            COUNT(*) as total_reports,
            ROUND(AVG(page_count)) as avg_pages,
            ROUND(AVG(word_count)) as avg_words,
            ROUND(AVG(COALESCE(download_count, 0))) as avg_downloads,
            ROUND(AVG(COALESCE(citation_count, 0))) as avg_citations,
            CASE
                WHEN AVG(page_count) > 0 AND AVG(COALESCE(citation_count, 0)) > 0
                THEN ROUND((AVG(COALESCE(citation_count, 0)) / AVG(page_count))::numeric, 3)
                ELSE 0
            END as citations_per_page,
            CASE
                WHEN AVG(page_count) > 0 AND AVG(COALESCE(download_count, 0)) > 0
                THEN ROUND((AVG(COALESCE(download_count, 0)) / AVG(page_count))::numeric, 3)
                ELSE 0
            END as downloads_per_page,
            ROUND(AVG(COALESCE(impact_score, 0))::numeric, 2) as avg_impact
        FROM reports
        GROUP BY source_org
        ORDER BY total_reports DESC
    """
    result = await db.execute(text(sql))
    rows = result.mappings().all()

    return {"comparison": [dict(r) for r in rows]}

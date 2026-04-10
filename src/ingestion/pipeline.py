"""Full ingestion pipeline: PDF -> parse -> chunk -> embed -> store."""

from pathlib import Path
from datetime import datetime

from sqlalchemy.orm import Session

from src.config import settings
from src.db.models import Report, ReportChunk
from src.db.database import SyncSession
from src.ingestion.pdf_parser import parse_pdf
from src.ingestion.chunker import chunk_document
from src.ingestion.embedder import embed_texts


def ingest_pdf(
    pdf_path: str | Path,
    source_org: str,
    source_url: str = "",
    doc_type: str = "report",
    topics: str = "",
    region: str = "",
    country: str = "",
) -> int:
    """Ingest a single PDF: parse, chunk, embed, and store.

    Returns the report ID.
    """
    # 1. Parse
    doc = parse_pdf(pdf_path)

    # 2. Chunk
    chunks = chunk_document(doc)

    # 3. Embed all chunks
    chunk_texts = [c.content for c in chunks]
    embeddings = embed_texts(chunk_texts)

    # 4. Store
    with SyncSession() as session:
        report = Report(
            title=doc.title,
            authors=doc.metadata.get("author", ""),
            source_org=source_org,
            source_url=source_url,
            pdf_path=str(pdf_path),
            page_count=doc.page_count,
            word_count=doc.word_count,
            doc_type=doc_type,
            topics=topics,
            region=region,
            country=country,
        )

        # Try to extract year from metadata
        if doc.metadata.get("creationDate"):
            try:
                date_str = doc.metadata["creationDate"]
                if date_str.startswith("D:"):
                    date_str = date_str[2:]
                year = int(date_str[:4])
                report.year = year
                report.publication_date = datetime(year, 1, 1)
            except (ValueError, IndexError):
                pass

        session.add(report)
        session.flush()  # get the report ID

        for chunk, embedding in zip(chunks, embeddings):
            db_chunk = ReportChunk(
                report_id=report.id,
                chunk_index=chunk.index,
                content=chunk.content,
                page_start=chunk.page_start,
                page_end=chunk.page_end,
                token_count=chunk.token_count,
                embedding=embedding,
            )
            session.add(db_chunk)

        session.commit()
        return report.id


def ingest_directory(
    directory: str | Path,
    source_org: str,
    **kwargs,
) -> list[int]:
    """Ingest all PDFs in a directory. Returns list of report IDs."""
    directory = Path(directory)
    report_ids = []

    for pdf_path in sorted(directory.glob("*.pdf")):
        print(f"Ingesting: {pdf_path.name}")
        try:
            report_id = ingest_pdf(pdf_path, source_org=source_org, **kwargs)
            report_ids.append(report_id)
            print(f"  -> Report #{report_id} ({pdf_path.name})")
        except Exception as e:
            print(f"  -> FAILED: {e}")

    return report_ids

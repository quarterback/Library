"""Base scraper interface for policy report repositories."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path

import httpx

from src.config import settings


@dataclass
class ReportMetadata:
    """Metadata scraped about a report before downloading the PDF."""
    title: str
    source_org: str
    source_url: str
    authors: str = ""
    year: int | None = None
    pdf_url: str = ""
    topics: str = ""
    region: str = ""
    country: str = ""
    doc_type: str = "report"
    download_count: int | None = None
    citation_count: int | None = None
    extra: dict = field(default_factory=dict)


class BaseScraper(ABC):
    """Base class for scraping report repositories."""

    name: str = "base"

    def __init__(self):
        self.client = httpx.AsyncClient(
            timeout=60.0,
            follow_redirects=True,
            headers={"User-Agent": "Library-Corpus-Builder/1.0 (research)"},
        )
        self.corpus_dir = settings.corpus_dir / self.name
        self.corpus_dir.mkdir(parents=True, exist_ok=True)

    async def close(self):
        await self.client.aclose()

    @abstractmethod
    async def search(self, query: str = "", page: int = 1, per_page: int = 20) -> list[ReportMetadata]:
        """Search the repository for reports."""
        ...

    @abstractmethod
    async def fetch_metadata(self, report_url: str) -> ReportMetadata:
        """Fetch full metadata for a single report."""
        ...

    async def download_pdf(self, meta: ReportMetadata) -> Path | None:
        """Download the PDF for a report. Returns local path or None on failure."""
        if not meta.pdf_url:
            return None

        filename = _safe_filename(meta.title, meta.year) + ".pdf"
        local_path = self.corpus_dir / filename

        if local_path.exists():
            return local_path

        try:
            response = await self.client.get(meta.pdf_url)
            response.raise_for_status()
            local_path.write_bytes(response.content)
            return local_path
        except httpx.HTTPError as e:
            print(f"Download failed for {meta.title}: {e}")
            return None

    async def scrape_and_download(
        self, query: str = "", max_reports: int = 100
    ) -> list[tuple[ReportMetadata, Path | None]]:
        """Search, fetch metadata, download PDFs. Returns (metadata, path) pairs."""
        results = []
        page = 1
        per_page = 50

        while len(results) < max_reports:
            batch = await self.search(query=query, page=page, per_page=per_page)
            if not batch:
                break

            for meta in batch:
                if len(results) >= max_reports:
                    break
                pdf_path = await self.download_pdf(meta)
                results.append((meta, pdf_path))

            page += 1

        return results


def _safe_filename(title: str, year: int | None = None) -> str:
    """Create a safe filename from a report title."""
    safe = "".join(c if c.isalnum() or c in " -_" else "" for c in title)
    safe = safe.strip()[:100]
    safe = safe.replace(" ", "_")
    if year:
        safe = f"{year}_{safe}"
    return safe

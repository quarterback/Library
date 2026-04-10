"""Scraper for World Bank Open Knowledge Repository.

The World Bank's documents API provides access to 14,000+ policy reports,
working papers, and research publications.

API docs: https://documents.worldbank.org/en/publication/documents-reports/api
"""

from src.scrapers.base import BaseScraper, ReportMetadata


class WorldBankScraper(BaseScraper):
    name = "worldbank"

    API_BASE = "https://search.worldbank.org/api/v2/wds"

    # Document types we care about
    DOC_TYPES = [
        "Policy Research Working Paper",
        "World Development Report",
        "Country Economic Memorandum",
        "Public Expenditure Review",
        "Economic and Sector Work",
    ]

    async def search(
        self, query: str = "", page: int = 1, per_page: int = 20
    ) -> list[ReportMetadata]:
        params = {
            "format": "json",
            "rows": per_page,
            "os": (page - 1) * per_page,
            "fl": "id,title,authors,docdt,count,pdfurl,docty,topic,regionname,countryname,abstracts",
            "srt": "docdt",
            "order": "desc",
        }
        if query:
            params["qterm"] = query

        response = await self.client.get(self.API_BASE, params=params)
        response.raise_for_status()
        data = response.json()

        results = []
        documents = data.get("documents", {})

        for key, doc in documents.items():
            if key == "facets":
                continue

            pdf_url = doc.get("pdfurl", "")
            if not pdf_url:
                continue

            year = None
            docdt = doc.get("docdt", "")
            if docdt and len(docdt) >= 4:
                try:
                    year = int(docdt[:4])
                except ValueError:
                    pass

            results.append(ReportMetadata(
                title=doc.get("title", {}).get("en", "") if isinstance(doc.get("title"), dict) else doc.get("title", ""),
                source_org="World Bank",
                source_url=f"https://documents.worldbank.org/en/publication/documents-reports/documentdetail/{doc.get('id', '')}",
                authors=doc.get("authors", ""),
                year=year,
                pdf_url=pdf_url,
                topics=doc.get("topic", ""),
                region=doc.get("regionname", ""),
                country=doc.get("countryname", ""),
                doc_type=doc.get("docty", "report"),
                extra={"abstract": doc.get("abstracts", {})},
            ))

        return results

    async def fetch_metadata(self, report_url: str) -> ReportMetadata:
        """Fetch metadata for a single World Bank document by URL."""
        # Extract document ID from URL
        doc_id = report_url.rstrip("/").split("/")[-1]

        params = {
            "format": "json",
            "fl": "id,title,authors,docdt,count,pdfurl,docty,topic,regionname,countryname,abstracts",
            "id": doc_id,
        }

        response = await self.client.get(self.API_BASE, params=params)
        response.raise_for_status()
        data = response.json()

        documents = data.get("documents", {})
        for key, doc in documents.items():
            if key == "facets":
                continue

            year = None
            docdt = doc.get("docdt", "")
            if docdt and len(docdt) >= 4:
                try:
                    year = int(docdt[:4])
                except ValueError:
                    pass

            return ReportMetadata(
                title=doc.get("title", {}).get("en", "") if isinstance(doc.get("title"), dict) else doc.get("title", ""),
                source_org="World Bank",
                source_url=report_url,
                authors=doc.get("authors", ""),
                year=year,
                pdf_url=doc.get("pdfurl", ""),
                topics=doc.get("topic", ""),
                region=doc.get("regionname", ""),
                country=doc.get("countryname", ""),
                doc_type=doc.get("docty", "report"),
            )

        raise ValueError(f"Document not found: {report_url}")

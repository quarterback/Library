"""Scraper for UN Digital Library.

The UN Digital Library provides access to UN documents, reports, resolutions,
and publications. Uses the OAI-PMH and REST APIs.

Catalog: https://digitallibrary.un.org
"""

from src.scrapers.base import BaseScraper, ReportMetadata


class UNScraper(BaseScraper):
    name = "un"

    API_BASE = "https://digitallibrary.un.org/api/v1"
    SEARCH_URL = "https://digitallibrary.un.org/search"

    async def search(
        self, query: str = "", page: int = 1, per_page: int = 20
    ) -> list[ReportMetadata]:
        """Search the UN Digital Library.

        Uses the web search endpoint with JSON output format.
        """
        params = {
            "ln": "en",
            "p": query or "report",
            "f": "",
            "c": "Resource Type",
            "sf": "year",
            "so": "d",
            "rg": per_page,
            "jrec": (page - 1) * per_page + 1,
            "of": "recjson",
        }

        response = await self.client.get(self.SEARCH_URL, params=params)
        response.raise_for_status()

        results = []
        try:
            records = response.json()
        except Exception:
            return results

        if not isinstance(records, list):
            records = [records]

        for record in records:
            title = ""
            authors = ""
            year = None
            pdf_url = ""

            # Extract title
            if "title" in record:
                title = record["title"] if isinstance(record["title"], str) else str(record["title"])

            # Extract authors
            if "authors" in record:
                if isinstance(record["authors"], list):
                    authors = ", ".join(
                        a.get("full_name", "") if isinstance(a, dict) else str(a)
                        for a in record["authors"]
                    )

            # Extract year
            if "year" in record:
                try:
                    year = int(record["year"])
                except (ValueError, TypeError):
                    pass

            # Extract PDF URL from files/urls
            for url_info in record.get("urls", []):
                if isinstance(url_info, dict):
                    url = url_info.get("url", "")
                    if url.endswith(".pdf"):
                        pdf_url = url
                        break

            rec_id = record.get("recid", "")
            results.append(ReportMetadata(
                title=title,
                source_org="United Nations",
                source_url=f"https://digitallibrary.un.org/record/{rec_id}" if rec_id else "",
                authors=authors,
                year=year,
                pdf_url=pdf_url,
                doc_type="report",
            ))

        return results

    async def fetch_metadata(self, report_url: str) -> ReportMetadata:
        """Fetch metadata for a single UN document."""
        rec_id = report_url.rstrip("/").split("/")[-1]
        url = f"https://digitallibrary.un.org/record/{rec_id}"

        params = {"of": "recjson"}
        response = await self.client.get(url, params=params)
        response.raise_for_status()
        record = response.json()

        title = record.get("title", "")
        if not isinstance(title, str):
            title = str(title)

        year = None
        if "year" in record:
            try:
                year = int(record["year"])
            except (ValueError, TypeError):
                pass

        pdf_url = ""
        for url_info in record.get("urls", []):
            if isinstance(url_info, dict) and url_info.get("url", "").endswith(".pdf"):
                pdf_url = url_info["url"]
                break

        return ReportMetadata(
            title=title,
            source_org="United Nations",
            source_url=report_url,
            year=year,
            pdf_url=pdf_url,
            doc_type="report",
        )

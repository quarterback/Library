"""Scrapers for major US think tanks.

Covers: Brookings, CGD, Urban Institute, RAND, Carnegie.
Each has different site structures, so we implement per-org search methods.
"""

from bs4 import BeautifulSoup

from src.scrapers.base import BaseScraper, ReportMetadata


class BrookingsScraper(BaseScraper):
    name = "brookings"

    async def search(
        self, query: str = "", page: int = 1, per_page: int = 20
    ) -> list[ReportMetadata]:
        params = {
            "s": query,
            "paged": page,
            "post_type": "research",
        }
        response = await self.client.get(
            "https://www.brookings.edu/search/", params=params
        )
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        results = []
        for item in soup.select("article, .search-result, .list-content-item"):
            title_el = item.select_one("h2 a, h3 a, .title a")
            if not title_el:
                continue

            title = title_el.get_text(strip=True)
            link = title_el.get("href", "")

            year = None
            date_el = item.select_one("time, .date")
            if date_el:
                date_text = date_el.get("datetime", "") or date_el.get_text(strip=True)
                for part in date_text.split("-"):
                    if part.isdigit() and len(part) == 4:
                        year = int(part)
                        break

            results.append(ReportMetadata(
                title=title,
                source_org="Brookings Institution",
                source_url=link,
                year=year,
                doc_type="report",
            ))

        return results

    async def fetch_metadata(self, report_url: str) -> ReportMetadata:
        response = await self.client.get(report_url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        title = soup.select_one("h1").get_text(strip=True) if soup.select_one("h1") else ""

        pdf_url = ""
        for a in soup.select("a[href$='.pdf']"):
            pdf_url = a.get("href", "")
            break

        return ReportMetadata(
            title=title,
            source_org="Brookings Institution",
            source_url=report_url,
            pdf_url=pdf_url,
        )


class CGDScraper(BaseScraper):
    """Center for Global Development."""
    name = "cgd"

    async def search(
        self, query: str = "", page: int = 1, per_page: int = 20
    ) -> list[ReportMetadata]:
        params = {
            "search_api_fulltext": query,
            "page": page - 1,
        }
        response = await self.client.get(
            "https://www.cgdev.org/publications", params=params
        )
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        results = []
        for item in soup.select(".views-row, .node--type-publication"):
            title_el = item.select_one("h3 a, h2 a, .field--name-title a")
            if not title_el:
                continue

            title = title_el.get_text(strip=True)
            link = title_el.get("href", "")
            if link and not link.startswith("http"):
                link = f"https://www.cgdev.org{link}"

            results.append(ReportMetadata(
                title=title,
                source_org="Center for Global Development",
                source_url=link,
                doc_type="working paper",
            ))

        return results

    async def fetch_metadata(self, report_url: str) -> ReportMetadata:
        response = await self.client.get(report_url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        title = soup.select_one("h1").get_text(strip=True) if soup.select_one("h1") else ""

        pdf_url = ""
        for a in soup.select("a[href$='.pdf']"):
            pdf_url = a.get("href", "")
            if not pdf_url.startswith("http"):
                pdf_url = f"https://www.cgdev.org{pdf_url}"
            break

        return ReportMetadata(
            title=title,
            source_org="Center for Global Development",
            source_url=report_url,
            pdf_url=pdf_url,
        )

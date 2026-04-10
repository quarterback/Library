"""Scraper for IMF eLibrary / Publications.

The IMF publishes working papers, country reports, World Economic Outlook,
Global Financial Stability Report, and other policy publications.

API: https://www.imf.org/en/Publications
"""

from src.scrapers.base import BaseScraper, ReportMetadata


class IMFScraper(BaseScraper):
    name = "imf"

    SEARCH_API = "https://www.imf.org/en/Publications/Search"

    async def search(
        self, query: str = "", page: int = 1, per_page: int = 20
    ) -> list[ReportMetadata]:
        """Search IMF publications.

        IMF doesn't have a clean public JSON API, so we scrape the search
        results page and extract structured data from it.
        """
        from bs4 import BeautifulSoup

        params = {
            "searchtext": query,
            "page": page,
            "count": per_page,
            "series": "All",
        }

        response = await self.client.get(self.SEARCH_API, params=params)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        results = []

        for item in soup.select(".result-item, .pub-row, .search-result"):
            title_el = item.select_one("h3 a, .title a, h2 a")
            if not title_el:
                continue

            title = title_el.get_text(strip=True)
            link = title_el.get("href", "")
            if link and not link.startswith("http"):
                link = f"https://www.imf.org{link}"

            # Try to extract year from date text
            year = None
            date_el = item.select_one(".date, .pub-date, time")
            if date_el:
                date_text = date_el.get_text(strip=True)
                for word in date_text.split():
                    if word.isdigit() and len(word) == 4:
                        year = int(word)
                        break

            # Extract doc type
            type_el = item.select_one(".type, .pub-type, .series")
            doc_type = type_el.get_text(strip=True) if type_el else "working paper"

            results.append(ReportMetadata(
                title=title,
                source_org="IMF",
                source_url=link,
                year=year,
                doc_type=doc_type,
            ))

        return results

    async def fetch_metadata(self, report_url: str) -> ReportMetadata:
        """Fetch metadata for a single IMF publication page."""
        from bs4 import BeautifulSoup

        response = await self.client.get(report_url)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        title = ""
        title_el = soup.select_one("h1, .pub-title")
        if title_el:
            title = title_el.get_text(strip=True)

        authors = ""
        author_els = soup.select(".author a, .pub-author")
        if author_els:
            authors = ", ".join(a.get_text(strip=True) for a in author_els)

        # Look for PDF download link
        pdf_url = ""
        for a in soup.select("a[href]"):
            href = a.get("href", "")
            if href.endswith(".pdf") or "/ft/wp/" in href:
                if not href.startswith("http"):
                    href = f"https://www.imf.org{href}"
                pdf_url = href
                break

        return ReportMetadata(
            title=title,
            source_org="IMF",
            source_url=report_url,
            authors=authors,
            pdf_url=pdf_url,
            doc_type="working paper",
        )

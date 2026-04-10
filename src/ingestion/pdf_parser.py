"""Extract text from PDFs using PyMuPDF (fitz)."""

from pathlib import Path
from dataclasses import dataclass

import fitz  # pymupdf


@dataclass
class ParsedPage:
    page_number: int
    text: str


@dataclass
class ParsedPDF:
    path: str
    title: str
    page_count: int
    word_count: int
    pages: list[ParsedPage]
    metadata: dict

    @property
    def full_text(self) -> str:
        return "\n\n".join(p.text for p in self.pages)


def parse_pdf(path: str | Path) -> ParsedPDF:
    """Extract all text and metadata from a PDF file."""
    path = Path(path)
    doc = fitz.open(str(path))

    metadata = doc.metadata or {}
    title = metadata.get("title", "") or path.stem.replace("_", " ").replace("-", " ")

    pages = []
    total_words = 0
    for i, page in enumerate(doc):
        text = page.get_text("text")
        pages.append(ParsedPage(page_number=i + 1, text=text))
        total_words += len(text.split())

    doc.close()

    return ParsedPDF(
        path=str(path),
        title=title,
        page_count=len(pages),
        word_count=total_words,
        pages=pages,
        metadata=metadata,
    )

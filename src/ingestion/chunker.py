"""Split parsed PDF text into overlapping chunks for embedding."""

from dataclasses import dataclass

from src.config import settings
from src.ingestion.pdf_parser import ParsedPDF


@dataclass
class Chunk:
    index: int
    content: str
    page_start: int
    page_end: int
    token_count: int  # approximate


def chunk_document(
    doc: ParsedPDF,
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
) -> list[Chunk]:
    """Split a parsed PDF into overlapping text chunks.

    Uses page boundaries as natural break points, then splits large pages
    by paragraph/sentence boundaries. Each chunk tracks which pages it spans.
    """
    chunk_size = chunk_size or settings.chunk_size
    chunk_overlap = chunk_overlap or settings.chunk_overlap

    chunks: list[Chunk] = []
    current_text = ""
    current_page_start = 1
    current_page_end = 1

    for page in doc.pages:
        paragraphs = _split_paragraphs(page.text)

        for para in paragraphs:
            para_tokens = _approx_tokens(para)

            if _approx_tokens(current_text) + para_tokens > chunk_size and current_text.strip():
                chunks.append(Chunk(
                    index=len(chunks),
                    content=current_text.strip(),
                    page_start=current_page_start,
                    page_end=current_page_end,
                    token_count=_approx_tokens(current_text),
                ))

                # Keep overlap from end of current chunk
                overlap_text = _get_overlap(current_text, chunk_overlap)
                current_text = overlap_text + para + "\n"
                current_page_start = current_page_end
            else:
                current_text += para + "\n"

            current_page_end = page.page_number

    # Final chunk
    if current_text.strip():
        chunks.append(Chunk(
            index=len(chunks),
            content=current_text.strip(),
            page_start=current_page_start,
            page_end=current_page_end,
            token_count=_approx_tokens(current_text),
        ))

    return chunks


def _split_paragraphs(text: str) -> list[str]:
    """Split text into paragraphs, preserving meaningful blocks."""
    paragraphs = []
    current = ""
    for line in text.split("\n"):
        if line.strip() == "":
            if current.strip():
                paragraphs.append(current.strip())
            current = ""
        else:
            current += line + " "
    if current.strip():
        paragraphs.append(current.strip())
    return paragraphs


def _approx_tokens(text: str) -> int:
    """Rough token count (words * 1.3 is a decent approximation)."""
    return int(len(text.split()) * 1.3)


def _get_overlap(text: str, overlap_tokens: int) -> str:
    """Get the last N approximate tokens of text for overlap."""
    words = text.split()
    overlap_words = int(overlap_tokens / 1.3)
    if len(words) <= overlap_words:
        return text
    return " ".join(words[-overlap_words:]) + " "

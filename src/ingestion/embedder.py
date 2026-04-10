"""Generate vector embeddings for text chunks using Voyage AI."""

import voyageai

from src.config import settings


_client: voyageai.Client | None = None


def get_client() -> voyageai.Client:
    global _client
    if _client is None:
        _client = voyageai.Client(api_key=settings.voyage_api_key)
    return _client


def embed_texts(texts: list[str], input_type: str = "document") -> list[list[float]]:
    """Embed a batch of texts. Returns list of embedding vectors.

    Args:
        texts: List of text strings to embed
        input_type: "document" for corpus, "query" for search queries
    """
    client = get_client()

    # Voyage AI has a batch limit, process in chunks of 128
    all_embeddings = []
    batch_size = 128
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        result = client.embed(
            batch,
            model=settings.embedding_model,
            input_type=input_type,
        )
        all_embeddings.extend(result.embeddings)

    return all_embeddings


def embed_query(query: str) -> list[float]:
    """Embed a single search query."""
    return embed_texts([query], input_type="query")[0]

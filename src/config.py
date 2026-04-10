from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://localhost:5432/library"
    database_url_sync: str = "postgresql://localhost:5432/library"
    anthropic_api_key: str = ""
    voyage_api_key: str = ""
    corpus_dir: Path = Path("./corpus/pdfs")
    host: str = "0.0.0.0"
    port: int = 8000
    embedding_model: str = "voyage-3"
    embedding_dimensions: int = 1024
    chunk_size: int = 1000
    chunk_overlap: int = 200
    claude_model: str = "claude-sonnet-4-20250514"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()

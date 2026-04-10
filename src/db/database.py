from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from src.config import settings
from src.db.models import Base

async_engine = create_async_engine(settings.database_url, echo=False)
async_session = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)

sync_engine = create_engine(settings.database_url_sync, echo=False)
SyncSession = sessionmaker(sync_engine)


async def get_db() -> AsyncSession:
    async with async_session() as session:
        yield session


async def init_db():
    """Create all tables. For production, use alembic migrations instead."""
    async with async_engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)

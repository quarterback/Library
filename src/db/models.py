from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    Float,
    ForeignKey,
    Index,
    func,
)
from sqlalchemy.orm import DeclarativeBase, relationship
from pgvector.sqlalchemy import Vector

from src.config import settings


class Base(DeclarativeBase):
    pass


class Report(Base):
    """A policy report from any source organization."""

    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(1000), nullable=False)
    authors = Column(Text)  # comma-separated or JSON
    source_org = Column(String(200), nullable=False, index=True)
    source_url = Column(String(2000))
    pdf_path = Column(String(2000))
    publication_date = Column(DateTime)
    year = Column(Integer, index=True)
    page_count = Column(Integer)
    word_count = Column(Integer)
    language = Column(String(10), default="en")

    # Metadata from source
    topics = Column(Text)  # comma-separated tags
    region = Column(String(200))
    country = Column(String(200))
    doc_type = Column(String(100))  # working paper, flagship report, brief, etc.
    download_count = Column(Integer)
    citation_count = Column(Integer)

    # Our analysis
    summary = Column(Text)
    key_findings = Column(Text)
    policy_recommendations = Column(Text)
    impact_score = Column(Float)  # computed: citations / page_count ratio etc.

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    chunks = relationship("ReportChunk", back_populates="report", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_reports_source_year", "source_org", "year"),
        Index("ix_reports_impact", "impact_score"),
    )


class ReportChunk(Base):
    """A chunk of text from a report, with its embedding for semantic search."""

    __tablename__ = "report_chunks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    report_id = Column(Integer, ForeignKey("reports.id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    page_start = Column(Integer)
    page_end = Column(Integer)
    token_count = Column(Integer)
    embedding = Column(Vector(settings.embedding_dimensions))

    report = relationship("Report", back_populates="chunks")

    __table_args__ = (
        Index("ix_chunks_report_idx", "report_id", "chunk_index"),
    )


class SearchLog(Base):
    """Track queries for analytics and improving results."""

    __tablename__ = "search_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    query = Column(Text, nullable=False)
    results_count = Column(Integer)
    top_report_id = Column(Integer, ForeignKey("reports.id", ondelete="SET NULL"))
    created_at = Column(DateTime, server_default=func.now())

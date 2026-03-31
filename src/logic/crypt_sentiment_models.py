"""
db/models.py — SQLAlchemyモデル定義（SQLite使用・個人利用向け）
"""
from datetime import datetime
from sqlalchemy import (
    create_engine, Column, Integer, String, Text,
    DateTime, Float, Boolean, Index
)
from sqlalchemy.orm import DeclarativeBase, sessionmaker
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./finnews.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
    echo=False,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


class Article(Base):
    """ニュース記事テーブル"""
    __tablename__ = "articles"

    id          = Column(Integer, primary_key=True, index=True)
    ticker      = Column(String(20), nullable=False, index=True)   # "AAPL", "7203.T"
    title       = Column(Text, nullable=False)
    url         = Column(String(512), unique=True, nullable=False)
    source      = Column(String(50), nullable=False)               # "yahoo_finance", "reddit", etc.
    published_at= Column(DateTime, nullable=True, index=True)
    summary     = Column(Text, nullable=True)
    sentiment   = Column(String(10), nullable=True)                # "positive","negative","neutral"
    score       = Column(Float, nullable=True)                     # 感情スコア -1.0〜1.0
    lang        = Column(String(5), default="en")                  # "en" or "ja"
    created_at  = Column(DateTime, default=datetime.utcnow)
    is_processed= Column(Boolean, default=False)

    __table_args__ = (
        Index("ix_ticker_published", "ticker", "published_at"),
    )


class CrawlJob(Base):
    """クロールジョブ履歴テーブル"""
    __tablename__ = "crawl_jobs"

    id          = Column(Integer, primary_key=True)
    ticker      = Column(String(20), nullable=False, index=True)
    status      = Column(String(20), default="pending")  # pending/running/done/error
    sources     = Column(String(200))                    # カンマ区切りソース名
    total_found = Column(Integer, default=0)
    started_at  = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)
    error_msg   = Column(Text, nullable=True)


def init_db():
    """テーブル作成"""
    Base.metadata.create_all(bind=engine)
    print("✅ Database initialized")


def get_db():
    """FastAPI依存性注入用"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

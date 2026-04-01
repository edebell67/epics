import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()

DEFAULT_SQLITE_URL = "sqlite:///./data/marketing_engine.db"
PROJECT_ROOT = Path(__file__).resolve().parents[4]


def _normalize_database_url(database_url: str) -> str:
    if not database_url.startswith("sqlite:///"):
        return database_url
    sqlite_path = database_url.removeprefix("sqlite:///")
    if sqlite_path == ":memory:":
        return database_url
    path = Path(sqlite_path)
    if path.is_absolute():
        return database_url
    return f"sqlite:///{(PROJECT_ROOT / path).resolve().as_posix()}"


def get_database_url() -> str:
    return _normalize_database_url(os.getenv("DATABASE_URL", DEFAULT_SQLITE_URL))


DATABASE_URL = get_database_url()

if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
    )
else:
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

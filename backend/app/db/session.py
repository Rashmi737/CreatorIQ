from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings


settings = get_settings()

db_url = settings.database_url
if db_url.startswith("sqlite:///./"):
    backend_dir = Path(__file__).resolve().parent.parent.parent
    db_file = (backend_dir / db_url[len("sqlite:///./"):]).resolve()
    db_url = f"sqlite:///{db_file.as_posix()}"

connect_args = {"check_same_thread": False} if db_url.startswith("sqlite") else {}
engine = create_engine(db_url, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db() -> Generator[Session, None, None]:
    database = SessionLocal()
    try:
        yield database
    finally:
        database.close()
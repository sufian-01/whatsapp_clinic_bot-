"""SQLAlchemy 2.x Engine and Session Management.

Provides:
- Thread-safe lazy engine initialization with pooling and health checks.
- Per-request Session generation for FastAPI dependencies.
- Graceful degradation when DATABASE_URL is not configured in development.
- Safe testing utilities.
"""

from collections.abc import Generator
import logging
from threading import Lock
from typing import Optional

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from ..core.config import get_settings

logger = logging.getLogger(__name__)

_ENGINE: Optional[Engine] = None
_SESSION_FACTORY: Optional[sessionmaker[Session]] = None
_LOCK = Lock()


def normalize_database_url(url: str) -> str:
    """Normalize database URL to modern psycopg 3 driver if unspecified."""
    trimmed = url.strip()
    if trimmed.startswith("postgresql://"):
        return "postgresql+psycopg://" + trimmed[len("postgresql://"):]
    if trimmed.startswith("postgres://"):
        return "postgresql+psycopg://" + trimmed[len("postgres://"):]
    return trimmed


def is_db_configured(url: Optional[str] = None) -> bool:
    """Check whether a database URL is configured in settings or provided."""
    try:
        target = get_settings().database_url if url is None else url
        return bool(target.strip())
    except Exception:
        return False


def get_engine(database_url: Optional[str] = None) -> Engine:
    """Return the cached SQLAlchemy Engine, creating it lazily if necessary."""
    global _ENGINE, _SESSION_FACTORY
    url = (get_settings().database_url if database_url is None else database_url).strip()
    if not url:
        raise RuntimeError(
            "DATABASE_URL is not configured. Set the DATABASE_URL environment variable "
            "(e.g., postgresql+psycopg://user:password@localhost:5432/clinic_crm) to connect to the database."
        )

    with _LOCK:
        if _ENGINE is not None:
            # Check if URL matches current engine URL
            current_url = str(_ENGINE.url)
            norm_url = normalize_database_url(url)
            if current_url == norm_url or current_url.startswith("sqlite://"):
                return _ENGINE
            # If URL changed, dispose previous engine
            _ENGINE.dispose()
            _ENGINE = None
            _SESSION_FACTORY = None

        norm_url = normalize_database_url(url)
        if norm_url.startswith("sqlite://"):
            connect_args = {"check_same_thread": False}
            if ":memory:" in norm_url:
                engine = create_engine(
                    norm_url,
                    connect_args=connect_args,
                    poolclass=StaticPool,
                )
            else:
                engine = create_engine(
                    norm_url,
                    connect_args=connect_args,
                )
        else:
            engine = create_engine(
                norm_url,
                pool_size=10,
                max_overflow=20,
                pool_pre_ping=True,
                pool_recycle=300,
            )

        _ENGINE = engine
        _SESSION_FACTORY = sessionmaker(
            bind=engine,
            autoflush=False,
            expire_on_commit=False,
        )
        logger.info("SQLAlchemy database engine initialized successfully.")
        return _ENGINE


def get_session_factory(database_url: Optional[str] = None) -> sessionmaker[Session]:
    """Return the configured sessionmaker factory."""
    global _SESSION_FACTORY
    if _SESSION_FACTORY is None or database_url is not None:
        get_engine(database_url)
    assert _SESSION_FACTORY is not None
    return _SESSION_FACTORY


def get_db(database_url: Optional[str] = None) -> Generator[Session, None, None]:
    """FastAPI dependency: Yield a request-scoped database session.

    Commits on successful completion, rolls back on exception, and closes on exit.
    """
    factory = get_session_factory(database_url)
    session: Session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def reset_db_state() -> None:
    """Dispose of the engine and reset session factory (useful for isolated tests)."""
    global _ENGINE, _SESSION_FACTORY
    with _LOCK:
        if _ENGINE is not None:
            _ENGINE.dispose()
            _ENGINE = None
        _SESSION_FACTORY = None


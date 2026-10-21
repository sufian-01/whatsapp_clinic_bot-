"""LangGraph production checkpointer integration.

Provides:
- PostgreSQL-backed persistent checkpointer (`PostgresSaver`) for production.
- Automatic table setup on PostgreSQL initialization.
- Graceful in-memory fallback (`MemorySaver`) for development, SQLite, and isolated tests.
"""

import logging
from typing import Any, Optional
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver

logger = logging.getLogger(__name__)


def get_graph_checkpointer(database_url: Optional[str] = None) -> BaseCheckpointSaver:
    """Return a configured LangGraph checkpointer.
    
    If database_url is provided and points to PostgreSQL, initializes PostgresSaver
    and ensures checkpoint tables exist. Otherwise falls back to MemorySaver.
    """
    clean_url = (database_url or "").strip()
    # Normalize URL if needed
    if clean_url.startswith("postgresql+psycopg://"):
        conn_string = "postgresql://" + clean_url[len("postgresql+psycopg://"):]
    elif clean_url.startswith("postgresql+psycopg2://"):
        conn_string = "postgresql://" + clean_url[len("postgresql+psycopg2://"):]
    elif clean_url.startswith("postgres://"):
        conn_string = "postgresql://" + clean_url[len("postgres://"):]
    else:
        conn_string = clean_url

    if conn_string.startswith("postgresql://"):
        try:
            from langgraph.checkpoint.postgres import PostgresSaver
            from psycopg_pool import ConnectionPool
            from psycopg.rows import dict_row

            logger.info("[CHECKPOINT] Initializing PostgreSQL-backed LangGraph checkpointer with connection pool...")
            pool = ConnectionPool(
                conn_string,
                min_size=1,
                max_size=10,
                kwargs={"autocommit": True, "prepare_threshold": 0, "row_factory": dict_row},
            )
            saver = PostgresSaver(pool)
            try:
                saver.setup()
                logger.info("[CHECKPOINT] PostgreSQL LangGraph checkpoint tables verified/created successfully.")
            except Exception as setup_err:
                logger.warning("[CHECKPOINT] PostgresSaver.setup() returned: %s. Continuing...", setup_err)
            return saver
        except Exception as exc:
            logger.warning(
                "[CHECKPOINT] Could not initialize PostgresSaver (%s). Falling back to MemorySaver for conversation state.",
                exc,
            )
            return MemorySaver()

    logger.info("[CHECKPOINT] Non-PostgreSQL database detected or test environment; using MemorySaver checkpointer.")
    return MemorySaver()

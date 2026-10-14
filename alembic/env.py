from logging.config import fileConfig
import os

from sqlalchemy import engine_from_config, pool

from alembic import context
from app.core.config import get_settings
from app.db.base import Base
import app.db.models  # ensure all models are registered on Base.metadata
from app.db.session import normalize_database_url

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Target metadata for autogenerate support
target_metadata = Base.metadata


def get_url() -> str:
    """Retrieve and normalize database URL from application settings or environment."""
    env_url = os.getenv("DATABASE_URL", "").strip()
    if not env_url:
        try:
            env_url = get_settings().database_url.strip()
        except Exception:
            env_url = ""
    if not env_url:
        ini_url = config.get_main_option("sqlalchemy.url", "").strip()
        if ini_url and "driver://user:pass" not in ini_url:
            env_url = ini_url
    if not env_url or "driver://user:pass" in env_url:
        # Default placeholder to prevent crashes when executing dry-run tests
        env_url = "sqlite:///./data/clinic_dev.db"
    return normalize_database_url(env_url)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = get_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()


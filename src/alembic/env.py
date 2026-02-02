import sys
from pathlib import Path

# alembic runs from the project root, but all imports (config, db, etc.)
# live inside src/. add it to sys.path so they resolve the same way
# they do when you run `python main.py` from src/.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import create_engine
from sqlalchemy import pool
from alembic import context

from config.settings import settings
from db.models.base import Base
from db.models.user import User                        # noqa: F401 — must be imported for autogenerate
from db.models.message_mapping import MessageMapping   # noqa: F401


# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# logging is configured in main.py — no need for fileConfig here.

# target_metadata is what autogenerate diffs against.
# must be Base.metadata, and all models must be imported above
# or autogenerate won't see them.
target_metadata = Base.metadata


def _syncUrl(asyncUrl: str) -> str:
    """
    Strip the async driver from a SQLAlchemy URL.

        sqlite+aiosqlite:///bot.db          -> sqlite:///bot.db
        postgresql+asyncpg://user:pass@...  -> postgresql://user:pass@...
    """
    dialect = asyncUrl.split("+")[0]
    rest = asyncUrl.split("://", 1)[1]
    return f"{dialect}://{rest}"


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = _syncUrl(settings.DATABASE_URL)
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
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = create_engine(
        _syncUrl(settings.DATABASE_URL),
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
    
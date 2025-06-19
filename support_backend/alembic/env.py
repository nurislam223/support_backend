from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool
import sys
import os
from alembic import context
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from models import Base

# this is the Alembic Config object, which provides
config = context.config

# Set SQLALCHEMY_DATABASE_URL from environment variable
config.set_main_option("sqlalchemy.url", os.getenv("DATABASE_URL", "postgresql://admin:admin@db/users"))

# Interpret the config file for Python logging.
fileConfig(config.config_file_name)

# Добавьте ваши модели сюда
target_metadata = Base.metadata

def run_migrations_offline():
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_scheme="postgresql",
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

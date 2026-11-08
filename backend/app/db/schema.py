import logging

from sqlalchemy import inspect, text

from app.db.session import engine

logger = logging.getLogger("creatoriq.schema")

_USER_COLUMN_PATCHES: tuple[tuple[str, str], ...] = (
    ("google_id", "VARCHAR(255)"),
    ("avatar_url", "VARCHAR(512)"),
    ("auth_provider", "VARCHAR(50) DEFAULT 'local'"),
    ("email_verified", "BOOLEAN NOT NULL DEFAULT 0"),
)

_PLATFORM_ACCOUNT_PATCHES: tuple[tuple[str, str], ...] = (
    ("channel_title", "VARCHAR(255)"),
    ("avatar_url", "VARCHAR(512)"),
    ("subscribers_count", "INTEGER NOT NULL DEFAULT 0"),
    ("total_views", "INTEGER NOT NULL DEFAULT 0"),
    ("video_count", "INTEGER NOT NULL DEFAULT 0"),
    ("total_posts", "INTEGER NOT NULL DEFAULT 0"),
    ("total_impressions", "INTEGER NOT NULL DEFAULT 0"),
    ("engagement_rate", "FLOAT NOT NULL DEFAULT 0.0"),
)

_SOCIAL_CONTENT_PATCHES: tuple[tuple[str, str], ...] = (
    ("dwell_time_mins", "FLOAT NOT NULL DEFAULT 3.5"),
    ("duration_secs", "INTEGER NOT NULL DEFAULT 240"),
    ("external_url", "VARCHAR(512)"),
)


_INDEX_STATEMENTS: tuple[str, ...] = (
    "CREATE INDEX IF NOT EXISTS ix_platform_accounts_platform_user_id ON platform_accounts (platform_user_id)",
    "CREATE INDEX IF NOT EXISTS ix_platform_accounts_created_at ON platform_accounts (created_at)",
    "CREATE INDEX IF NOT EXISTS ix_platform_accounts_updated_at ON platform_accounts (updated_at)",
    "CREATE INDEX IF NOT EXISTS ix_platform_accounts_plat_handle ON platform_accounts (platform_name, platform_user_id)",
    "CREATE INDEX IF NOT EXISTS ix_social_contents_published_at ON social_contents (published_at)",
    "CREATE INDEX IF NOT EXISTS ix_social_contents_created_at ON social_contents (created_at)",
    "CREATE INDEX IF NOT EXISTS ix_social_contents_updated_at ON social_contents (updated_at)",
    "CREATE INDEX IF NOT EXISTS ix_social_contents_plat_ext ON social_contents (platform, external_id)",
    "CREATE INDEX IF NOT EXISTS ix_social_contents_account_pub ON social_contents (platform_account_id, published_at)",
)


def ensure_user_schema() -> None:
    """Add columns, indexes and tables that may be missing from older SQLite databases."""
    from app.db.base import Base
    Base.metadata.create_all(bind=engine)

    if not engine.url.get_backend_name().startswith("sqlite"):
        return

    inspector = inspect(engine)
    if "users" in inspector.get_table_names():
        existing_users = {column["name"] for column in inspector.get_columns("users")}
        missing_users = [(name, ddl) for name, ddl in _USER_COLUMN_PATCHES if name not in existing_users]
        if missing_users:
            with engine.begin() as connection:
                for name, ddl in missing_users:
                    connection.execute(text(f"ALTER TABLE users ADD COLUMN {name} {ddl}"))
                    logger.info("Added missing users.%s column", name)

    if "platform_accounts" in inspector.get_table_names():
        existing_pa = {column["name"] for column in inspector.get_columns("platform_accounts")}
        missing_pa = [(name, ddl) for name, ddl in _PLATFORM_ACCOUNT_PATCHES if name not in existing_pa]
        if missing_pa:
            with engine.begin() as connection:
                for name, ddl in missing_pa:
                    connection.execute(text(f"ALTER TABLE platform_accounts ADD COLUMN {name} {ddl}"))
                    logger.info("Added missing platform_accounts.%s column", name)

    if "social_contents" in inspector.get_table_names():
        existing_sc = {column["name"] for column in inspector.get_columns("social_contents")}
        missing_sc = [(name, ddl) for name, ddl in _SOCIAL_CONTENT_PATCHES if name not in existing_sc]
        if missing_sc:
            with engine.begin() as connection:
                for name, ddl in missing_sc:
                    connection.execute(text(f"ALTER TABLE social_contents ADD COLUMN {name} {ddl}"))
                    logger.info("Added missing social_contents.%s column", name)

    # Ensure performance indexes for handles and timestamps
    with engine.begin() as connection:
        for stmt in _INDEX_STATEMENTS:
            try:
                connection.execute(text(stmt))
            except Exception as e:
                logger.debug("Index creation skipped or already present: %s (%s)", stmt, e)

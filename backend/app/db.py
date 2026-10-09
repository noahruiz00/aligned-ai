from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import DATABASE_URL

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Columns added after a table first shipped. create_all never alters existing tables,
# so these are added here until the project adopts a migration tool.
_ADDED_COLUMNS = [
    ("methodology_questions", "section", "VARCHAR(160) NOT NULL DEFAULT ''"),
    ("methodology_questions", "classification", "VARCHAR(12) NOT NULL DEFAULT 'core'"),
    ("methodology_modules", "follow_up_mode", "VARCHAR(10) NOT NULL DEFAULT 'pool'"),
    ("discovery_sessions", "opted_modules", "JSON"),
    ("answers", "follow_up_question_id", "INTEGER"),
    ("answers", "skip_reason", "VARCHAR(20)"),
    ("purpose_statements", "sections", "JSON"),
    ("purpose_statements", "status", "VARCHAR(20) NOT NULL DEFAULT 'draft'"),
    ("discovery_sessions", "token", "VARCHAR(64)"),
    ("discovery_sessions", "sharing", "VARCHAR(24) NOT NULL DEFAULT 'private'"),
    ("discovery_sessions", "rejected_insight_count", "INTEGER NOT NULL DEFAULT 0"),
    ("discovery_sessions", "extraction_runs", "INTEGER NOT NULL DEFAULT 0"),
]


def ensure_columns() -> None:
    insp = inspect(engine)
    with engine.begin() as conn:
        for table, column, ddl in _ADDED_COLUMNS:
            if insp.has_table(table) and column not in {c["name"] for c in insp.get_columns(table)}:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}"))

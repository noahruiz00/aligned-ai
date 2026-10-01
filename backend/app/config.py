import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# PostgreSQL in production, e.g. postgresql+psycopg://user:pass@host:5432/aligned
# Falls back to a local SQLite file so the prototype runs with zero setup.
DATABASE_URL = os.getenv("DATABASE_URL") or f"sqlite:///{Path(__file__).resolve().parent.parent / 'aligned.db'}"
if DATABASE_URL.startswith("postgres://"):  # Railway/Heroku style URL
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg://", 1)
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)

CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-opus-5-5")

# Demo mode runs a deterministic stand-in for Claude. It is on automatically when
# no credentials are configured, so the demo never breaks on stage.
HAS_CLAUDE_CREDENTIALS = bool(os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_AUTH_TOKEN"))
DEMO_MODE = os.getenv("DEMO_MODE", "").lower() in ("1", "true", "yes") or not HAS_CLAUDE_CREDENTIALS

CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",") if o.strip()]

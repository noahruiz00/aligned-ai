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

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
# Server-side only: never expose this to the frontend or log it.
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "").strip()
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL") or "openai/gpt-5.6-luna"

# Demo mode runs a deterministic stand-in for the model. It is on automatically when
# no credentials are configured, so the demo never breaks on stage.
DEMO_MODE = os.getenv("DEMO_MODE", "").lower() in ("1", "true", "yes") or not OPENROUTER_API_KEY

CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",") if o.strip()]

# --- Private-beta security -----------------------------------------------------------
# development: lax cookies, generated secret, warnings instead of hard failures.
# production:  Secure cookies; SECRET_KEY, a staff password and a model key are required at startup.
APP_ENV = os.getenv("APP_ENV", "development").lower()
IS_PRODUCTION = APP_ENV == "production"
SECRET_KEY = os.getenv("SECRET_KEY", "").strip()
if not SECRET_KEY and not IS_PRODUCTION:
    import secrets as _secrets
    SECRET_KEY = _secrets.token_hex(32)  # per-process: staff sessions end on restart, which is fine for development
ADVISOR_PASSWORD = os.getenv("ADVISOR_PASSWORD", "").strip()
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "").strip()
SECURE_COOKIES = IS_PRODUCTION or os.getenv("SECURE_COOKIES", "").lower() in ("1", "true", "yes")
STAFF_SESSION_HOURS = int(os.getenv("STAFF_SESSION_HOURS", "12"))
# Real beta mode never serves stand-in AI output. Demo mode in production must be switched on deliberately.
ALLOW_DEMO_IN_PRODUCTION = os.getenv("ALLOW_DEMO_IN_PRODUCTION", "").lower() in ("1", "true", "yes")
STRICT_AI = not DEMO_MODE  # with a real model configured, AI failures surface as errors, never as demo insights


def validate_runtime_config() -> list[str]:
    """Problems that must stop a production start; in development they are only reported."""
    problems = []
    if IS_PRODUCTION:
        if not os.getenv("SECRET_KEY", "").strip():
            problems.append("SECRET_KEY is required in production (staff sessions are signed with it)")
        if not (ADMIN_PASSWORD or ADVISOR_PASSWORD):
            problems.append("ADMIN_PASSWORD (or ADVISOR_PASSWORD) is required in production")
        if DEMO_MODE and not ALLOW_DEMO_IN_PRODUCTION:
            problems.append("No OPENROUTER_API_KEY (or DEMO_MODE=true) in production: set the key, or set ALLOW_DEMO_IN_PRODUCTION=true to run a rehearsal with stand-in AI")
    return problems

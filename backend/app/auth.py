"""Private-beta authentication.

Two kinds of principal:
- Clients hold an unguessable resume token for their discovery session, delivered as an HttpOnly
  cookie when the session starts or is resumed. Client endpoints resolve the session from that cookie;
  no client id ever appears in a public URL.
- Staff (advisor | admin) log in with a password from the environment and receive an HMAC-signed,
  expiring role cookie. admin includes advisor rights.

Cookies are HttpOnly, SameSite=Lax and Secure in production. The frontend proxies the API under its
own origin, so these cookies are first-party in every deployment.
"""

import base64
import hashlib
import hmac
import json
import logging
import secrets
import threading
import time
from collections import deque

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import metrics
from .config import ADMIN_PASSWORD, ADVISOR_PASSWORD, SECRET_KEY, SECURE_COOKIES, STAFF_SESSION_HOURS
from .db import get_db
from .models import DiscoverySession


class RateLimiter:
    """Sliding-window limiter, in-process, keyed by caller address. Sized for a small private beta."""

    def __init__(self, limit: int, window_seconds: int):
        self.limit, self.window = limit, window_seconds
        self._hits: dict[str, deque] = {}
        self._lock = threading.Lock()

    def check(self, key: str) -> int | None:
        """Returns None when allowed, otherwise seconds until the caller may retry."""
        now = time.time()
        with self._lock:
            q = self._hits.setdefault(key, deque())
            while q and q[0] <= now - self.window:
                q.popleft()
            if len(q) >= self.limit:
                return max(1, int(q[0] + self.window - now))
            q.append(now)
            return None

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


LOGIN_LIMITER = RateLimiter(limit=10, window_seconds=15 * 60)   # per address
RESUME_LIMITER = RateLimiter(limit=30, window_seconds=15 * 60)  # per address


def caller_key(request: Request) -> str:
    # Behind the Next.js proxy / Railway the real address is the first X-Forwarded-For entry.
    fwd = request.headers.get("x-forwarded-for", "")
    return (fwd.split(",")[0].strip() if fwd else (request.client.host if request.client else "unknown")) or "unknown"


def enforce(limiter: RateLimiter, request: Request, what: str) -> None:
    wait = limiter.check(caller_key(request))
    if wait is not None:
        metrics.bump("rate_limited", what)
        log.warning("rate limit hit: %s", what)
        raise HTTPException(429, f"Too many attempts. Try again in {wait // 60 + 1} minute(s).", headers={"Retry-After": str(wait)})

log = logging.getLogger("aligned.auth")

CLIENT_COOKIE = "aligned_client"
STAFF_COOKIE = "aligned_staff"
CLIENT_COOKIE_DAYS = 90
ROLE_RANK = {"client": 0, "advisor": 1, "admin": 2}


def new_resume_token() -> str:
    return secrets.token_urlsafe(32)  # 256 bits, URL-safe, unguessable


def token_fingerprint(token: str) -> str:
    """Safe representation for logs: never the token itself."""
    return hashlib.sha256(token.encode()).hexdigest()[:12]


def _set(resp: Response, key: str, value: str, max_age: int) -> None:
    resp.set_cookie(key, value, max_age=max_age, httponly=True, samesite="lax", secure=SECURE_COOKIES, path="/")


def set_client_cookie(resp: Response, token: str) -> None:
    _set(resp, CLIENT_COOKIE, token, CLIENT_COOKIE_DAYS * 24 * 3600)


def clear_client_cookie(resp: Response) -> None:
    resp.delete_cookie(CLIENT_COOKIE, path="/")


# --- Staff tokens: role + expiry, HMAC-signed with SECRET_KEY --------------------------

def _b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode().rstrip("=")


def _unb64(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def sign_staff(role: str) -> str:
    payload = json.dumps({"role": role, "exp": int(time.time()) + STAFF_SESSION_HOURS * 3600, "n": secrets.token_hex(8)}).encode()
    sig = hmac.new(SECRET_KEY.encode(), payload, hashlib.sha256).digest()
    return f"{_b64(payload)}.{_b64(sig)}"


def verify_staff(token: str | None) -> str | None:
    """Returns the role for a valid, unexpired staff token, else None."""
    if not token or "." not in token:
        return None
    try:
        p64, s64 = token.split(".", 1)
        payload = _unb64(p64)
        if not hmac.compare_digest(hmac.new(SECRET_KEY.encode(), payload, hashlib.sha256).digest(), _unb64(s64)):
            return None
        data = json.loads(payload)
        if data.get("exp", 0) < time.time() or data.get("role") not in ("advisor", "admin"):
            return None
        return data["role"]
    except Exception:  # malformed token
        return None


def _role_for_password(password: str) -> str | None:
    # Constant-time comparisons; check admin first so one shared password still yields the higher role.
    if ADMIN_PASSWORD and hmac.compare_digest(password.encode(), ADMIN_PASSWORD.encode()):
        return "admin"
    if ADVISOR_PASSWORD and hmac.compare_digest(password.encode(), ADVISOR_PASSWORD.encode()):
        return "advisor"
    return None


def backfill_tokens(db: Session) -> int:
    """Sessions created before resume tokens existed get one, so they can still be resumed via a link."""
    n = 0
    for s in db.scalars(select(DiscoverySession).where(DiscoverySession.token.is_(None))).all():
        s.token = new_resume_token()
        n += 1
    if n:
        db.commit()
    return n


# --- Dependencies ------------------------------------------------------------------------

def staff_role(request: Request) -> str | None:
    return verify_staff(request.cookies.get(STAFF_COOKIE))


def require_role(minimum: str):
    def dep(request: Request) -> str:
        role = staff_role(request)
        if role is None:
            raise HTTPException(401, "Sign in required")
        if ROLE_RANK[role] < ROLE_RANK[minimum]:
            raise HTTPException(403, f"{minimum} access required")
        return role
    return dep


require_advisor = require_role("advisor")
require_admin = require_role("admin")


def current_session(request: Request, db: Session = Depends(get_db)) -> DiscoverySession:
    """The client's own discovery session, from the resume-token cookie. Anything else is 401."""
    token = request.cookies.get(CLIENT_COOKIE)
    s = db.scalar(select(DiscoverySession).where(DiscoverySession.token == token)) if token else None
    if s is None:
        raise HTTPException(401, "No active discovery session on this device")
    return s


def optional_session(request: Request, db: Session = Depends(get_db)) -> DiscoverySession | None:
    token = request.cookies.get(CLIENT_COOKIE)
    return db.scalar(select(DiscoverySession).where(DiscoverySession.token == token)) if token else None


# --- Router ------------------------------------------------------------------------------

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    password: str = Field(min_length=1, max_length=200)


@router.post("/login")
def login(req: LoginRequest, request: Request, response: Response):
    enforce(LOGIN_LIMITER, request, "login")
    role = _role_for_password(req.password)
    if role is None:
        log.warning("staff login failed")
        raise HTTPException(401, "Incorrect password")
    _set(response, STAFF_COOKIE, sign_staff(role), STAFF_SESSION_HOURS * 3600)
    log.info("staff login: role=%s", role)
    return {"role": role}


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(STAFF_COOKIE, path="/")
    return {"ok": True}


@router.get("/me")
def me(request: Request):
    role = staff_role(request)
    if role is None:
        raise HTTPException(401, "Not signed in")
    return {"role": role}

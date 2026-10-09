import logging
import re
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from . import ai, auth, discovery, insights, methodology, metrics, scoring
from .auth import backfill_tokens, new_resume_token, optional_session, require_admin, require_advisor, staff_role
from sqlalchemy import delete
from .models import Answer, ClientInsight, EvidenceLink, InsightEvent
from pydantic import BaseModel, Field
from .config import APP_ENV, CORS_ORIGINS, DEMO_MODE, IS_PRODUCTION, OPENROUTER_MODEL, validate_runtime_config
from .db import Base, SessionLocal, engine, ensure_columns, get_db
from .models import AdvisorNote, AlignmentScore, Conversation, DiscoverySession, PurposeStatement, User, ValueProfile
from .schemas import ChatRequest, ChatResponse, ConversationRef, NoteRequest, ScoreRequest, UserRef
from .seed import seed


class RedactFilter(logging.Filter):
    """Masks secrets that might reach a log line: API keys, passwords, tokens, cookies."""

    PATTERNS = [
        re.compile(r"sk-or-[A-Za-z0-9_\-]+"),
        re.compile(r"(?i)\b(password|token|secret|authorization|cookie)(\s*[=:]\s*)\S+"),
        re.compile(r"(?i)bearer\s+\S+"),
    ]

    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        red = msg
        for pat in self.PATTERNS:
            red = pat.sub(lambda m: (m.group(1) + m.group(2) + "***") if m.lastindex and m.lastindex >= 2 else "***", red)
        if red != msg:
            record.msg, record.args = red, ()
        return True


logging.basicConfig(level=logging.INFO)
for _h in logging.getLogger().handlers:
    _h.addFilter(RedactFilter())
log = logging.getLogger("aligned.main")


@asynccontextmanager
async def lifespan(_: FastAPI):
    problems = validate_runtime_config()
    if problems and IS_PRODUCTION:
        raise RuntimeError("Refusing to start in production: " + "; ".join(problems))
    for pr in problems:
        log.warning("config: %s", pr)
    if DEMO_MODE:
        log.warning("DEMO MODE: stand-in AI. Not for real beta users.")
    Base.metadata.create_all(engine)
    ensure_columns()
    with SessionLocal() as db:
        seed(db)
        n = backfill_tokens(db)
        if n:
            log.info("assigned resume tokens to %d pre-existing session(s)", n)
    yield


app = FastAPI(
    title="Aligned AI — Wealth Purpose Companion",
    description="Discovery conversation, Wealth Purpose Statement, and Wealth Alignment Score.",
    version="0.1.0",
    lifespan=lifespan,
)
app.add_middleware(CORSMiddleware, allow_origins=CORS_ORIGINS, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(auth.router)
app.include_router(methodology.router)
app.include_router(methodology.admin)
app.include_router(discovery.router)
app.include_router(insights.router)


def _latest(db: Session, model, user_id: int):
    return db.scalars(select(model).where(model.user_id == user_id).order_by(model.id.desc()).limit(1)).first()


def _get_user(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if not user or user.role != "client":
        raise HTTPException(404, "Client not found")
    return user


@app.get("/health")
def health():
    return {"ok": True, "demo_mode": DEMO_MODE, "model": None if DEMO_MODE else OPENROUTER_MODEL, "app_env": APP_ENV}


# --- Access helpers ---------------------------------------------------------

def _latest_session(db: Session, user_id: int) -> DiscoverySession | None:
    return db.scalars(select(DiscoverySession).where(DiscoverySession.user_id == user_id).order_by(DiscoverySession.id.desc()).limit(1)).first()


def _is_shared(sess: DiscoverySession | None) -> bool:
    # Clients without a discovery session are the seeded demo families, which exist for the advisor.
    return sess is None or sess.sharing == "shared_with_advisor"


def _authorize_client_data(request: Request, db: Session, user_id: int) -> str:
    """Who may read this client's data: the client (matching cookie) or staff, and staff only once shared."""
    role = staff_role(request)
    if role is not None:
        if not _is_shared(_latest_session(db, user_id)):
            raise HTTPException(403, "This client has not shared their profile")
        return role
    s = optional_session(request, db)
    if s is None:
        raise HTTPException(401, "Sign in required")
    if s.user_id != user_id:
        raise HTTPException(403, "Not your profile")
    return "client"


# --- Client journey ---------------------------------------------------------

@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest, db: Session = Depends(get_db), _role: str = Depends(require_advisor)):
    if req.conversation_id is None:
        if not req.name or not req.name.strip():
            raise HTTPException(422, "name is required to start a conversation")
        advisor = db.scalars(select(User).where(User.role == "advisor")).first()
        user = User(name=req.name.strip(), household_type=req.household_type, advisor_id=advisor.id if advisor else None)
        db.add(user)
        db.flush()
        convo = Conversation(user_id=user.id, messages=[{"role": "assistant", "content": ai.opening_message(user.name), "stage": "discover"}])
        db.add(convo)
        db.commit()
        return ChatResponse(conversation_id=convo.id, user_id=user.id, reply=convo.messages[0]["content"], stage="discover", answered=0, ready=False, demo_mode=DEMO_MODE)

    convo = db.get(Conversation, req.conversation_id)
    if not convo:
        raise HTTPException(404, "Conversation not found")
    if not req.message or not req.message.strip():
        raise HTTPException(422, "message is required")

    user = convo.user
    answered = sum(1 for m in convo.messages if m["role"] == "user") + 1
    history = convo.messages + [{"role": "user", "content": req.message.strip(), "stage": ai.stage_for(answered - 1)}]
    # The API requires the first message to come from the user; the opening question is ours.
    api_history = [{"role": "user", "content": f"(My name is {user.name}. I'm ready to begin.)"}] + history
    reply, _ = ai.chat_reply(user.name, user.household_type, api_history, answered)
    stage = ai.stage_for(answered)
    convo.messages = history + [{"role": "assistant", "content": reply, "stage": stage}]
    db.commit()
    return ChatResponse(
        conversation_id=convo.id, user_id=user.id, reply=reply, stage=stage,
        answered=answered, ready=answered >= ai.READY_AFTER, demo_mode=DEMO_MODE,
    )


@app.post("/analyze-values")
def analyze_values(req: ConversationRef, db: Session = Depends(get_db), _role: str = Depends(require_advisor)):
    convo = db.get(Conversation, req.conversation_id)
    if not convo:
        raise HTTPException(404, "Conversation not found")
    if not any(m["role"] == "user" for m in convo.messages):
        raise HTTPException(422, "The conversation has no answers yet")
    data, used_llm =ai.analyze_values(convo.messages)
    profile = ValueProfile(user_id=convo.user_id, conversation_id=convo.id, data=data)
    convo.status = "complete"
    db.add(profile)
    db.commit()
    return {"user_id": convo.user_id, "values": data, "generated_by": "openrouter" if used_llm else "demo"}


@app.post("/generate-purpose")
def generate_purpose(req: UserRef, db: Session = Depends(get_db), _role: str = Depends(require_advisor)):
    user = _get_user(db, req.user_id)
    profile = _latest(db, ValueProfile, user.id)
    if not profile:
        raise HTTPException(422, "Run /analyze-values first")
    data, used_llm =ai.generate_purpose(user.name, user.household_type, profile.data)
    prev = _latest(db, PurposeStatement, user.id)
    statement = PurposeStatement(user_id=user.id, data=data, version=(prev.version + 1) if prev else 1)
    db.add(statement)
    db.commit()
    return {"user_id": user.id, "purpose": data, "version": statement.version, "generated_by": "openrouter" if used_llm else "demo"}


@app.post("/calculate-score")
def calculate_score(req: ScoreRequest, request: Request, db: Session = Depends(get_db)):
    _authorize_client_data(request, db, req.user_id)
    user = _get_user(db, req.user_id)
    profile = _latest(db, ValueProfile, user.id)
    purpose = _latest(db, PurposeStatement, user.id)
    values = profile.data if profile else None
    result = scoring.calculate(req.portrait, values)
    insights, used_llm =ai.advisor_insights(user.name, values, purpose.data if purpose else None, result)
    insights["generated_by"] = "openrouter" if used_llm else "demo"
    row = AlignmentScore(
        user_id=user.id, overall=result["overall"],
        categories={**result["categories"], "_meta": {"themes": result["themes"], "weighting_rationale": result["weighting_rationale"]}},
        portrait=req.portrait.model_dump(), insights=insights,
    )
    db.add(row)
    db.commit()
    return {"user_id": user.id, **result}


def _score_payload(score: AlignmentScore | None) -> dict | None:
    if not score:
        return None
    cats = dict(score.categories)
    meta = cats.pop("_meta", {})
    return {
        "overall": score.overall, "categories": cats, "themes": meta.get("themes", []),
        "weighting_rationale": meta.get("weighting_rationale", []), "portrait": score.portrait,
        "created_at": score.created_at.isoformat(),
    }


def _status(user_id: int, db: Session) -> str:
    if _latest(db, AlignmentScore, user_id):
        return "aligned"
    if _latest(db, PurposeStatement, user_id):
        return "statement"
    return "discovery"


@app.get("/client-dashboard")
def client_dashboard(user_id: int, request: Request, db: Session = Depends(get_db)):
    _authorize_client_data(request, db, user_id)
    return _dashboard(db, user_id)


def _dashboard(db: Session, user_id: int) -> dict:
    user = _get_user(db, user_id)
    profile = _latest(db, ValueProfile, user.id)
    purpose = _latest(db, PurposeStatement, user.id)
    sess = _latest_session(db, user.id)
    return {
        "user": {"id": user.id, "name": user.name, "household_type": user.household_type, "status": _status(user.id, db)},
        "sharing": sess.sharing if sess else "legacy",
        "values": profile.data if profile else None,
        "purpose": purpose.data if purpose else None,
        "purpose_sections": purpose.sections if purpose else None,
        "purpose_status": purpose.status if purpose else None,
        "purpose_created_at": purpose.created_at.isoformat() if purpose else None,
        "score": _score_payload(_latest(db, AlignmentScore, user.id)),
    }


# --- Advisor ----------------------------------------------------------------

@app.get("/advisor/clients")
def advisor_clients(db: Session = Depends(get_db), _role: str = Depends(require_advisor)):
    clients = db.scalars(select(User).where(User.role == "client").order_by(User.created_at.desc())).all()
    out = []
    for c in clients:
        sess = _latest_session(db, c.id)
        if sess is not None and sess.status == "abandoned":
            continue  # the client started fresh; nothing here is theirs any more
        shared = _is_shared(sess)
        purpose = _latest(db, PurposeStatement, c.id) if shared else None
        score = _latest(db, AlignmentScore, c.id) if shared else None
        profile = _latest(db, ValueProfile, c.id) if shared else None
        out.append({
            "id": c.id, "name": c.name, "household_type": c.household_type, "status": _status(c.id, db),
            "sharing": sess.sharing if sess else "legacy", "shared": shared,
            "discovery_status": sess.status if sess else None,
            "last_activity_at": sess.last_activity_at.isoformat() if sess else c.created_at.isoformat(),
            "purpose": purpose.data["purpose_statement"] if purpose else None,
            "values": [v["name"] for v in profile.data.get("values", [])] if profile else [],
            "overall": score.overall if score else None,
            "created_at": c.created_at.isoformat(),
        })
    return out


@app.get("/advisor/clients/{client_id}")
def advisor_client(client_id: int, db: Session = Depends(get_db), role: str = Depends(require_advisor)):
    user = _get_user(db, client_id)
    sess = _latest_session(db, user.id)
    notes = db.scalars(select(AdvisorNote).where(AdvisorNote.client_id == client_id).order_by(AdvisorNote.id.desc())).all()
    base = {"notes": [{"id": n.id, "body": n.body, "created_at": n.created_at.isoformat()} for n in notes],
            "qa": {"rejected_insight_count": sess.rejected_insight_count, "extraction_runs": sess.extraction_runs} if sess and role == "admin" else None}
    if not _is_shared(sess):
        # The client has not shared: identity and progress only. No answers, insights, purpose, values or score.
        return {
            **base, "shared": False,
            "user": {"id": user.id, "name": user.name, "household_type": user.household_type, "status": _status(user.id, db)},
            "sharing": sess.sharing, "discovery_status": sess.status,
            "values": None, "purpose": None, "purpose_sections": None, "purpose_status": None, "purpose_created_at": None, "score": None,
            "insights": None, "transcript": [],
        }
    score = _latest(db, AlignmentScore, client_id)
    convo = _latest(db, Conversation, client_id)
    return {
        **_dashboard(db, client_id), **base, "shared": True,
        "discovery_status": sess.status if sess else None,
        "insights": score.insights if score else None,
        "transcript": convo.messages if convo else [],
    }


@app.get("/admin/qa")
def admin_qa(db: Session = Depends(get_db), _role: str = Depends(require_admin)):
    """Product QA only. Counts, never content: rejected AI items are discarded, not stored or shown."""
    sessions = db.scalars(select(DiscoverySession)).all()
    live = [s for s in sessions if s.status != "abandoned"]
    m = metrics.snapshot()
    return {
        "app_env": APP_ENV, "demo_mode": DEMO_MODE, "model": None if DEMO_MODE else OPENROUTER_MODEL,
        "sessions": len(live), "completed": sum(1 for s in live if s.status == "complete"),
        "abandoned": len(sessions) - len(live),
        "shared_with_advisor": sum(1 for s in live if s.sharing == "shared_with_advisor"),
        "extraction_runs": sum(s.extraction_runs or 0 for s in sessions),
        "rejected_insight_count": sum(s.rejected_insight_count or 0 for s in sessions),
        "needs_clarification_count": db.scalar(select(func.count()).select_from(ClientInsight).where(ClientInsight.active.is_(True), ClientInsight.status == "needs_clarification")) or 0,
        "insights_total": db.scalar(select(func.count()).select_from(ClientInsight).where(ClientInsight.active.is_(True))) or 0,
        "model_errors": m["counters"].get("model_errors", 0),
        "extraction_failures": m["counters"].get("extraction_failures", 0),
        "rate_limited": m["counters"].get("rate_limited", 0),
        "last": m["last"],  # {name: {at, detail}} where detail is an error class/status, never a message
        "usage": m["usage"],  # model calls and tokens since restart, for cost estimates
        "since_restart": True,
    }


class DeleteClientRequest(BaseModel):
    confirm_name: str = Field(min_length=1, max_length=120)  # the client's name, typed by the admin


@app.post("/admin/clients/{client_id}/revoke-token")
def admin_revoke_token(client_id: int, db: Session = Depends(get_db), _role: str = Depends(require_admin)):
    """Rotate the client's resume token: every existing link and device cookie stops working at once.
    Returns the new private link path so the advisor can hand it to the client."""
    user = _get_user(db, client_id)
    sess = _latest_session(db, user.id)
    if sess is None:
        raise HTTPException(404, "This client has no discovery session")
    sess.token = new_resume_token()
    db.commit()
    log.info("resume token rotated for client %s by admin", client_id)
    return {"client_id": client_id, "resume_link_path": f"/discover/resume/{sess.token}"}


@app.delete("/admin/clients/{client_id}")
def admin_delete_client(client_id: int, req: DeleteClientRequest, db: Session = Depends(get_db), _role: str = Depends(require_admin)):
    """Permanently delete a client's beta data. The admin must type the client's name to confirm."""
    user = _get_user(db, client_id)
    if req.confirm_name.strip().casefold() != user.name.strip().casefold():
        raise HTTPException(400, "Confirmation name does not match")
    session_ids = list(db.scalars(select(DiscoverySession.id).where(DiscoverySession.user_id == user.id)).all())
    insight_ids = list(db.scalars(select(ClientInsight.id).where(ClientInsight.client_id == user.id)).all())
    counts = {}
    # Explicit, dependency-ordered deletes: SQLite does not enforce ON DELETE CASCADE by default.
    counts["evidence_links"] = db.execute(delete(EvidenceLink).where(EvidenceLink.insight_id.in_(insight_ids))).rowcount if insight_ids else 0
    counts["insight_events"] = db.execute(delete(InsightEvent).where(InsightEvent.insight_id.in_(insight_ids))).rowcount if insight_ids else 0
    counts["insights"] = db.execute(delete(ClientInsight).where(ClientInsight.client_id == user.id)).rowcount
    counts["answers"] = db.execute(delete(Answer).where(Answer.user_id == user.id)).rowcount
    counts["sessions"] = db.execute(delete(DiscoverySession).where(DiscoverySession.user_id == user.id)).rowcount
    counts["purpose_statements"] = db.execute(delete(PurposeStatement).where(PurposeStatement.user_id == user.id)).rowcount
    counts["values"] = db.execute(delete(ValueProfile).where(ValueProfile.user_id == user.id)).rowcount
    counts["scores"] = db.execute(delete(AlignmentScore).where(AlignmentScore.user_id == user.id)).rowcount
    counts["notes"] = db.execute(delete(AdvisorNote).where(AdvisorNote.client_id == user.id)).rowcount
    counts["conversations"] = db.execute(delete(Conversation).where(Conversation.user_id == user.id)).rowcount
    db.delete(user)
    db.commit()
    log.info("client %s deleted by admin: %s", client_id, counts)
    return {"deleted": True, "client_id": client_id, "removed": counts, "sessions": len(session_ids)}


@app.post("/advisor/clients/{client_id}/notes")
def add_note(client_id: int, req: NoteRequest, db: Session = Depends(get_db), _role: str = Depends(require_advisor)):
    _get_user(db, client_id)
    advisor = db.scalars(select(User).where(User.role == "advisor")).first()
    note = AdvisorNote(client_id=client_id, advisor_id=advisor.id if advisor else None, body=req.body.strip())
    db.add(note)
    db.commit()
    return {"id": note.id, "body": note.body, "created_at": note.created_at.isoformat()}

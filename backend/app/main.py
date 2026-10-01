import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import ai, scoring
from .config import CLAUDE_MODEL, CORS_ORIGINS, DEMO_MODE
from .db import Base, SessionLocal, engine, get_db
from .models import AdvisorNote, AlignmentScore, Conversation, PurposeStatement, User, ValueProfile
from .schemas import ChatRequest, ChatResponse, ConversationRef, NoteRequest, ScoreRequest, UserRef
from .seed import seed

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        seed(db)
    yield


app = FastAPI(
    title="Aligned AI — Wealth Purpose Companion",
    description="Discovery conversation, Wealth Purpose Statement, and Wealth Alignment Score.",
    version="0.1.0",
    lifespan=lifespan,
)
app.add_middleware(CORSMiddleware, allow_origins=CORS_ORIGINS, allow_methods=["*"], allow_headers=["*"])


def _latest(db: Session, model, user_id: int):
    return db.scalars(select(model).where(model.user_id == user_id).order_by(model.id.desc()).limit(1)).first()


def _get_user(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if not user or user.role != "client":
        raise HTTPException(404, "Client not found")
    return user


@app.get("/health")
def health():
    return {"ok": True, "demo_mode": DEMO_MODE, "model": None if DEMO_MODE else CLAUDE_MODEL}


# --- Client journey ---------------------------------------------------------

@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest, db: Session = Depends(get_db)):
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
def analyze_values(req: ConversationRef, db: Session = Depends(get_db)):
    convo = db.get(Conversation, req.conversation_id)
    if not convo:
        raise HTTPException(404, "Conversation not found")
    if not any(m["role"] == "user" for m in convo.messages):
        raise HTTPException(422, "The conversation has no answers yet")
    data, used_claude = ai.analyze_values(convo.messages)
    profile = ValueProfile(user_id=convo.user_id, conversation_id=convo.id, data=data)
    convo.status = "complete"
    db.add(profile)
    db.commit()
    return {"user_id": convo.user_id, "values": data, "generated_by": "claude" if used_claude else "demo"}


@app.post("/generate-purpose")
def generate_purpose(req: UserRef, db: Session = Depends(get_db)):
    user = _get_user(db, req.user_id)
    profile = _latest(db, ValueProfile, user.id)
    if not profile:
        raise HTTPException(422, "Run /analyze-values first")
    data, used_claude = ai.generate_purpose(user.name, user.household_type, profile.data)
    prev = _latest(db, PurposeStatement, user.id)
    statement = PurposeStatement(user_id=user.id, data=data, version=(prev.version + 1) if prev else 1)
    db.add(statement)
    db.commit()
    return {"user_id": user.id, "purpose": data, "version": statement.version, "generated_by": "claude" if used_claude else "demo"}


@app.post("/calculate-score")
def calculate_score(req: ScoreRequest, db: Session = Depends(get_db)):
    user = _get_user(db, req.user_id)
    profile = _latest(db, ValueProfile, user.id)
    purpose = _latest(db, PurposeStatement, user.id)
    values = profile.data if profile else None
    result = scoring.calculate(req.portrait, values)
    insights, used_claude = ai.advisor_insights(user.name, values, purpose.data if purpose else None, result)
    insights["generated_by"] = "claude" if used_claude else "demo"
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
def client_dashboard(user_id: int, db: Session = Depends(get_db)):
    user = _get_user(db, user_id)
    profile = _latest(db, ValueProfile, user.id)
    purpose = _latest(db, PurposeStatement, user.id)
    return {
        "user": {"id": user.id, "name": user.name, "household_type": user.household_type, "status": _status(user.id, db)},
        "values": profile.data if profile else None,
        "purpose": purpose.data if purpose else None,
        "purpose_created_at": purpose.created_at.isoformat() if purpose else None,
        "score": _score_payload(_latest(db, AlignmentScore, user.id)),
    }


# --- Advisor ----------------------------------------------------------------

@app.get("/advisor/clients")
def advisor_clients(db: Session = Depends(get_db)):
    clients = db.scalars(select(User).where(User.role == "client").order_by(User.created_at.desc())).all()
    out = []
    for c in clients:
        purpose = _latest(db, PurposeStatement, c.id)
        score = _latest(db, AlignmentScore, c.id)
        profile = _latest(db, ValueProfile, c.id)
        out.append({
            "id": c.id, "name": c.name, "household_type": c.household_type, "status": _status(c.id, db),
            "purpose": purpose.data["purpose_statement"] if purpose else None,
            "values": [v["name"] for v in profile.data.get("values", [])] if profile else [],
            "overall": score.overall if score else None,
            "created_at": c.created_at.isoformat(),
        })
    return out


@app.get("/advisor/clients/{client_id}")
def advisor_client(client_id: int, db: Session = Depends(get_db)):
    dashboard = client_dashboard(client_id, db)
    score = _latest(db, AlignmentScore, client_id)
    convo = _latest(db, Conversation, client_id)
    notes = db.scalars(select(AdvisorNote).where(AdvisorNote.client_id == client_id).order_by(AdvisorNote.id.desc())).all()
    return {
        **dashboard,
        "insights": score.insights if score else None,
        "transcript": convo.messages if convo else [],
        "notes": [{"id": n.id, "body": n.body, "created_at": n.created_at.isoformat()} for n in notes],
    }


@app.post("/advisor/clients/{client_id}/notes")
def add_note(client_id: int, req: NoteRequest, db: Session = Depends(get_db)):
    _get_user(db, client_id)
    advisor = db.scalars(select(User).where(User.role == "advisor")).first()
    note = AdvisorNote(client_id=client_id, advisor_id=advisor.id if advisor else None, body=req.body.strip())
    db.add(note)
    db.commit()
    return {"id": note.id, "body": note.body, "created_at": note.created_at.isoformat()}

"""Progressive discovery sessions.

Core questions, one at a time, in methodology order. Each answer gets a short
reflection and, at most once per question, a follow-up drawn from the advisor's own
follow-up questions for that section (or composed by the AI in modules that allow
it). Clients can skip, go back, clarify an earlier answer, go deeper into a module's
optional questions, pause, and resume. When a module is finished the client sees a
short "what we're hearing" reflection to confirm or correct.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import ai, insights
from .ai import AIUnavailable
from . import metrics
from .auth import RESUME_LIMITER, clear_client_cookie, current_session, enforce, new_resume_token, optional_session, set_client_cookie, token_fingerprint
from .config import DEMO_MODE
from .db import get_db
from .methodology import LEGACY_STAGE, flow_questions, follow_up_pool, is_live, load_modules
from .models import Answer, Conversation, DiscoverySession, MethodologyModule, MethodologyQuestion, PurposeStatement, User, ValueProfile
from .schemas import AnswerRequest, DeeperRequest, DiscoveryStart, GotoRequest, ReflectionFeedback, ResumeRequest, ShareRequest, SkipRequest

import logging

log = logging.getLogger("aligned.discovery")
router = APIRouter(prefix="/discovery", tags=["discovery"])

SESSION_LABELS = {1: "Purpose + Love", 2: "Play + Work", 3: "Service + Community", 4: "Alignment + Evolution", 5: "Review + Wealth Purpose Statement"}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _touch(s: DiscoverySession) -> None:
    s.last_activity_at = _now()
    if s.status == "paused":
        s.status = "active"


# --- Answer bookkeeping --------------------------------------------------------

def _top_answers(s: DiscoverySession) -> dict[int, Answer]:
    """Latest top-level answer (not a follow-up) per question id."""
    out: dict[int, Answer] = {}
    for a in s.answers:
        if a.parent_answer_id is None:
            out[a.question_id] = a
    return out


def _children(s: DiscoverySession) -> dict[int, Answer]:
    out: dict[int, Answer] = {}
    for a in s.answers:
        if a.parent_answer_id is not None:
            out[a.parent_answer_id] = a
    return out


def _used_follow_ups(s: DiscoverySession) -> set[int]:
    return {a.follow_up_question_id for a in s.answers if a.follow_up_question_id}


def _answer_payload(a: Answer | None) -> dict | None:
    if a is None:
        return None
    return {"id": a.id, "text": a.text, "skipped": a.skipped, "declined": a.skip_reason == "prefer_not", "reflection": a.ai_reflection, "created_at": a.created_at.isoformat()}


def _exchanges(module: MethodologyModule, top: dict[int, Answer], children: dict[int, Answer]) -> list[dict]:
    out = []
    for q in module.questions:
        if not is_live(q) or q.id not in top:
            continue
        a = top[q.id]
        out.append({
            "question_id": q.id, "key": q.key, "section": q.section, "classification": q.classification, "prompt": a.prompt_text, "answer": _answer_payload(a),
            "follow_up": {"prompt": a.ai_follow_up, "question_id": a.follow_up_question_id, "answer": _answer_payload(children.get(a.id))} if a.ai_follow_up else None,
        })
    return out


def _next_unanswered(questions: list[MethodologyQuestion], top: dict[int, Answer]) -> MethodologyQuestion | None:
    return next((q for q in questions if q.id not in top), None)


def _question_in(questions: list[MethodologyQuestion], qid: int | None) -> MethodologyQuestion | None:
    return next((q for q in questions if q.id == qid), None)


def _flow(db: Session, s: DiscoverySession) -> tuple[list[MethodologyModule], list[MethodologyQuestion]]:
    modules = load_modules(db, active_only=True)
    return modules, flow_questions(modules, s.opted_modules)


# --- State ----------------------------------------------------------------------

def state(db: Session, s: DiscoverySession) -> dict:
    modules, questions = _flow(db, s)
    top, children = _top_answers(s), _children(s)
    total = len(questions)
    answered = sum(1 for q in questions if q.id in top)
    opted = set(s.opted_modules or [])

    current_q = _question_in(questions, s.current_question_id)
    if current_q is None and s.status != "complete":
        current_q = _next_unanswered(questions, top)
    current_module_id = current_q.module_id if current_q else None

    steps = []
    for i, m in enumerate(modules, start=1):
        qs = [q for q in questions if q.module_id == m.id]
        done = sum(1 for q in qs if q.id in top)
        if qs and done == len(qs) and m.id != current_module_id:
            status = "completed"
        elif m.id == current_module_id or done:
            status = "in_progress"
        else:
            status = "upcoming"
        optional_left = sum(1 for q in m.questions if is_live(q) and q.classification == "optional" and q.id not in top)
        steps.append({"key": m.key, "title": m.title, "kind": "module", "status": status, "session_group": m.session_group,
                      "total": len(qs), "answered": done, "index": i, "optional_available": 0 if m.key in opted else optional_left})
    n = len(modules)
    last_group = max((m.session_group for m in modules), default=4) + 1
    review_status = "completed" if s.status == "complete" else ("in_progress" if current_q is None else "upcoming")
    steps.append({"key": "review", "title": "Review", "kind": "review", "status": review_status, "session_group": last_group, "total": 0, "answered": 0, "index": n + 1, "optional_available": 0})
    steps.append({"key": "purpose_statement", "title": "Wealth Purpose", "kind": "purpose", "status": "completed" if s.status == "complete" else "upcoming",
                  "session_group": last_group, "total": 0, "answered": 0, "index": n + 2, "optional_available": 0})

    current = None
    if current_q is not None:
        m = current_q.module
        in_module = [q for q in questions if q.module_id == m.id]
        existing = top.get(current_q.id)
        pending = None
        if existing and existing.ai_follow_up and existing.id not in children and not existing.skipped:
            pending = {"parent_answer_id": existing.id, "prompt": existing.ai_follow_up}
        current = {
            "module": {"key": m.key, "title": m.title, "intro": m.intro, "description": m.description, "session_group": m.session_group,
                       "session_label": SESSION_LABELS.get(m.session_group, f"Session {m.session_group}"),
                       "index": next(st["index"] for st in steps if st["key"] == m.key)},
            "question": {"id": current_q.id, "key": current_q.key, "section": current_q.section, "classification": current_q.classification,
                         "prompt": current_q.prompt, "required": current_q.required, "position": in_module.index(current_q) + 1, "total": len(in_module)},
            "existing_answer": None if pending else _answer_payload(existing),
            "pending_follow_up": pending,
            "exchanges": [e for e in _exchanges(m, top, children) if e["question_id"] != current_q.id or pending],
            "is_first": bool(questions) and questions[0].id == current_q.id,
        }

    # Only core questions gate completion; optional ones opened via "go deeper" never block the statement.
    required_open = [q for q in questions if q.required and q.classification == "core" and q.id not in top]
    return {
        "session": {
            "id": s.id, "user_id": s.user_id, "name": s.user.name, "household_type": s.user.household_type, "status": s.status,
            "resume_token": s.token, "sharing": s.sharing,
            "started_at": s.started_at.isoformat(), "last_activity_at": s.last_activity_at.isoformat(),
            "completed_at": s.completed_at.isoformat() if s.completed_at else None,
        },
        "demo_mode": DEMO_MODE,
        "progress_pct": round(answered / total * 100) if total else 0,
        "steps": steps,
        "sessions": [{"group": g, "label": SESSION_LABELS.get(g, f"Session {g}")} for g in sorted({st["session_group"] for st in steps if st["session_group"]})],
        "current": current,
        "modules": [{"key": m.key, "title": m.title, "exchanges": _exchanges(m, top, children)} for m in modules],
        "module_reflections": s.module_reflections or {},
        "can_complete": not required_open and answered > 0,
    }


# --- Advancing ------------------------------------------------------------------

def _advance(db: Session, s: DiscoverySession, from_q: MethodologyQuestion) -> dict:
    """Move to the first unanswered question. Produces the module reflection when a module is finished."""
    db.flush()
    db.refresh(s)
    modules, questions = _flow(db, s)
    top = _top_answers(s)
    nxt = _next_unanswered(questions, top)
    s.current_question_id = nxt.id if nxt else None

    module = from_q.module
    module_done = all(q.id in top for q in questions if q.module_id == module.id)
    leaving = nxt is None or nxt.module_id != module.id
    out = {"module_completed": None, "suggest_pause": False, "next_module": None, "optional_available": 0}
    if module_done and leaving and module.key not in (s.module_reflections or {}):
        try:
            found, used, _rejected = insights.run_extraction(db, s, module)
            if found or insights.answer_rows(s, module):
                data = insights.module_reflection(found, module)
            else:
                data = {"summary": "You chose to move past this section for now. You can come back to it any time.", "themes": []}
        except AIUnavailable:
            # Never show stand-in insights to a real client: say so, and extract this module on the review page.
            metrics.bump("extraction_failures", f"module {module.key}")
            found, used = [], False
            data = {"summary": f"We couldn't reflect on {module.title} just now. Nothing is lost: your answers are saved and this section will be processed on the review page.", "themes": [], "pending": True}
        s.module_reflections = {
            **(s.module_reflections or {}),
            module.key: {**data, "feedback": None, "correction": None, "generated_by": "openrouter" if used else "demo", "created_at": _now().isoformat()},
        }
        out["module_completed"] = module.key
        out["optional_available"] = 0 if module.key in (s.opted_modules or []) else sum(
            1 for q in module.questions if is_live(q) and q.classification == "optional" and q.id not in top
        )
        if nxt is not None:
            out["next_module"] = {"key": nxt.module.key, "title": nxt.module.title}
            out["suggest_pause"] = nxt.module.session_group != module.session_group
    return out


def _module_context(s: DiscoverySession, q: MethodologyQuestion) -> tuple[list[tuple[str, str]], list[str]]:
    top, children = _top_answers(s), _children(s)
    prior: list[tuple[str, str]] = []
    upcoming: list[str] = []
    for other in q.module.questions:
        if not is_live(other) or other.id == q.id:
            continue
        if other.id in top and not top[other.id].skipped:
            prior.append((top[other.id].prompt_text, top[other.id].text))
            child = children.get(top[other.id].id)
            if child and not child.skipped:
                prior.append((top[other.id].ai_follow_up or "", child.text))
        elif other.id not in top and other.classification == "core":
            upcoming.append(other.prompt)
    return prior, upcoming


# --- Endpoints ------------------------------------------------------------------

@router.post("/start")
def start(req: DiscoveryStart, response: Response, db: Session = Depends(get_db)):
    advisor = db.scalars(select(User).where(User.role == "advisor")).first()
    user = User(name=req.name.strip(), email=req.email, household_type=req.household_type, advisor_id=advisor.id if advisor else None)
    db.add(user)
    db.flush()
    questions = flow_questions(load_modules(db, active_only=True))
    if not questions:
        raise HTTPException(503, "No active discovery questions are configured")
    s = DiscoverySession(user_id=user.id, token=new_resume_token(), current_question_id=questions[0].id, opted_modules=[])
    db.add(s)
    db.commit()
    db.refresh(s)
    set_client_cookie(response, s.token)
    log.info("discovery started: session %s token=%s", s.id, token_fingerprint(s.token))
    return state(db, s)


@router.post("/resume")
def resume(req: ResumeRequest, request: Request, response: Response, db: Session = Depends(get_db)):
    """Exchange a private resume link for the session cookie. Unknown tokens are simply not found."""
    enforce(RESUME_LIMITER, request, "resume")
    s = db.scalar(select(DiscoverySession).where(DiscoverySession.token == req.token.strip())) if req.token.strip() else None
    if s is None:
        log.info("resume failed: unknown token fingerprint=%s", token_fingerprint(req.token))
        raise HTTPException(404, "That link is not valid")
    set_client_cookie(response, s.token)
    return state(db, s)


@router.post("/forget")
def forget(response: Response, db: Session = Depends(get_db), s: DiscoverySession | None = Depends(optional_session)):
    """Start fresh: this device forgets its session. An unfinished session is abandoned and its link
    stops working, so the old answers are never reachable from the new session or the old link."""
    if s is not None and s.status != "complete":
        s.status, s.token = "abandoned", new_resume_token()  # rotated: the old link is dead; row kept for QA counts
        db.commit()
    clear_client_cookie(response)
    return {"ok": True}


@router.get("/me")
def get_state(db: Session = Depends(get_db), s: DiscoverySession = Depends(current_session)):
    return state(db, s)


@router.post("/me/share")
def share(req: ShareRequest, db: Session = Depends(get_db), s: DiscoverySession = Depends(current_session)):
    """Explicit consent. Nothing is visible to the advisor until the client chooses to share."""
    _touch(s)
    if req.sharing == "private":
        s.sharing = "private"
    else:
        s.sharing = "shared_with_advisor" if s.status == "complete" else "pending_share"
    db.commit()
    return state(db, s)


def _live_question(db: Session, qid: int) -> MethodologyQuestion:
    q = db.get(MethodologyQuestion, qid)
    if not q or not is_live(q) or not q.module.active:
        raise HTTPException(404, "Question not found")
    return q


@router.post("/me/answer")
def answer(req: AnswerRequest, db: Session = Depends(get_db), s: DiscoverySession = Depends(current_session)):
    if s.status == "complete":
        raise HTTPException(409, "This discovery is complete")
    q = _live_question(db, req.question_id)
    text = req.text.strip()
    _touch(s)
    top, children = _top_answers(s), _children(s)
    prior, upcoming = _module_context(s, q)
    turn: dict = {"reflection": None, "follow_up": None}

    if req.parent_answer_id is not None:
        parent = db.get(Answer, req.parent_answer_id)
        if not parent or parent.session_id != s.id or parent.question_id != q.id or not parent.ai_follow_up:
            raise HTTPException(422, "No follow-up is pending for that answer")
        if parent.id in children:
            db.delete(children[parent.id])
        child = Answer(session_id=s.id, user_id=s.user_id, question_id=parent.follow_up_question_id or q.id, parent_answer_id=parent.id,
                       prompt_text=parent.ai_follow_up, text=text, input_mode=req.input_mode)
        result, _ = ai.discovery_turn(s.user.name, s.user.household_type, q.module.title, parent.ai_follow_up, q.follow_up_guidance, text,
                                      is_follow_up=True, prior=prior + [(parent.prompt_text, parent.text)], upcoming=upcoming, candidates=[], compose=False)
        child.ai_reflection = result["reflection"]
        db.add(child)
        turn["reflection"] = child.ai_reflection
    else:
        a = top.get(q.id)
        if a:  # re-answer / clarify: the follow-up no longer applies
            if a.id in children:
                db.delete(children[a.id])
            a.text, a.skipped, a.skip_reason, a.ai_follow_up, a.follow_up_question_id, a.prompt_text, a.input_mode = text, False, None, None, None, q.prompt, req.input_mode
        else:
            a = Answer(session_id=s.id, user_id=s.user_id, question_id=q.id, prompt_text=q.prompt, text=text, input_mode=req.input_mode)
            db.add(a)
        pool = follow_up_pool(q, _used_follow_ups(s)) if q.max_follow_ups > 0 else []
        compose = q.max_follow_ups > 0 and not pool and q.module.follow_up_mode == "compose"
        result, _ = ai.discovery_turn(s.user.name, s.user.household_type, q.module.title, q.prompt, q.follow_up_guidance, text,
                                      is_follow_up=False, prior=prior, upcoming=upcoming, candidates=[p.prompt for p in pool], compose=compose)
        a.ai_reflection = result["reflection"]
        turn["reflection"] = a.ai_reflection
        if result.get("needs_follow_up") and result.get("follow_up_question"):
            idx = int(result.get("follow_up_index") or 0)
            chosen = pool[idx - 1] if pool and 1 <= idx <= len(pool) else None
            a.ai_follow_up = chosen.prompt if chosen else result["follow_up_question"].strip()
            a.follow_up_question_id = chosen.id if chosen else None
            s.current_question_id = q.id
            db.commit()
            db.refresh(s)
            return {"turn": {**turn, "follow_up": a.ai_follow_up, "module_completed": None, "suggest_pause": False, "next_module": None, "optional_available": 0}, "state": state(db, s)}

    turn.update(_advance(db, s, q))
    db.commit()
    db.refresh(s)
    return {"turn": turn, "state": state(db, s)}


@router.post("/me/skip")
def skip(req: SkipRequest, db: Session = Depends(get_db), s: DiscoverySession = Depends(current_session)):
    if s.status == "complete":
        raise HTTPException(409, "This discovery is complete")
    q = _live_question(db, req.question_id)
    _touch(s)
    top, children = _top_answers(s), _children(s)
    if req.parent_answer_id is not None:
        parent = db.get(Answer, req.parent_answer_id)
        if not parent or parent.session_id != s.id or not parent.ai_follow_up:
            raise HTTPException(422, "No follow-up is pending for that answer")
        if parent.id not in children:
            db.add(Answer(session_id=s.id, user_id=s.user_id, question_id=parent.follow_up_question_id or q.id, parent_answer_id=parent.id,
                          prompt_text=parent.ai_follow_up, text="", skipped=True, skip_reason=req.reason))
    elif q.id not in top:
        db.add(Answer(session_id=s.id, user_id=s.user_id, question_id=q.id, prompt_text=q.prompt, text="", skipped=True, skip_reason=req.reason))
    else:  # re-visiting an answered question and choosing not to answer after all
        a = top[q.id]
        if a.id in children:
            db.delete(children[a.id])
        a.text, a.skipped, a.skip_reason, a.ai_follow_up, a.follow_up_question_id, a.ai_reflection = "", True, req.reason, None, None, None
    turn = {"reflection": None, "follow_up": None, **_advance(db, s, q)}
    db.commit()
    db.refresh(s)
    return {"turn": turn, "state": state(db, s)}


@router.post("/me/back")
def back(db: Session = Depends(get_db), s: DiscoverySession = Depends(current_session)):
    _, questions = _flow(db, s)
    top = _top_answers(s)
    current = _question_in(questions, s.current_question_id) or _next_unanswered(questions, top)
    idx = questions.index(current) if current in questions else len(questions)
    if idx == 0:
        raise HTTPException(409, "Already at the first question")
    _touch(s)
    s.current_question_id = questions[idx - 1].id
    db.commit()
    return state(db, s)


@router.post("/me/next")
def next_question(db: Session = Depends(get_db), s: DiscoverySession = Depends(current_session)):
    """Continue past an already-answered question without changing it."""
    _, questions = _flow(db, s)
    top = _top_answers(s)
    current = _question_in(questions, s.current_question_id)
    _touch(s)
    if current is not None and current.id in top:
        i = questions.index(current)
        after = questions[i + 1] if i + 1 < len(questions) else None
        nxt = next((q for q in questions[i + 1:] if q.id not in top), None)
        # Walk forward one at a time through answered questions; jump only when the next one is unanswered.
        s.current_question_id = after.id if after and after.id in top and nxt and questions.index(after) < questions.index(nxt) else (nxt.id if nxt else None)
    db.commit()
    return state(db, s)


@router.post("/me/goto")
def goto(req: GotoRequest, db: Session = Depends(get_db), s: DiscoverySession = Depends(current_session)):
    """Jump to an answered question (to clarify it) or to the next unanswered one."""
    _, questions = _flow(db, s)
    q = _question_in(questions, req.question_id)
    if q is None:
        raise HTTPException(404, "Question not found")
    top = _top_answers(s)
    nxt = _next_unanswered(questions, top)
    if q.id not in top and (nxt is None or nxt.id != q.id):
        raise HTTPException(409, "Answer the earlier questions first")
    _touch(s)
    s.current_question_id = q.id
    db.commit()
    return state(db, s)


@router.post("/me/deeper")
def deeper(req: DeeperRequest, db: Session = Depends(get_db), s: DiscoverySession = Depends(current_session)):
    """Opt into a module's optional questions; the flow continues with the first unanswered one."""
    if s.status == "complete":
        raise HTTPException(409, "This discovery is complete")
    module = next((m for m in load_modules(db, active_only=True) if m.key == req.module_key), None)
    if module is None:
        raise HTTPException(404, "Module not found")
    top = _top_answers(s)
    optional = [q for q in module.questions if is_live(q) and q.classification == "optional" and q.id not in top]
    if not optional:
        raise HTTPException(409, "No optional questions are available in that module")
    _touch(s)
    s.opted_modules = sorted(set(s.opted_modules or []) | {module.key})
    s.current_question_id = optional[0].id
    db.commit()
    return state(db, s)


@router.post("/me/pause")
def pause(db: Session = Depends(get_db), s: DiscoverySession = Depends(current_session)):
    if s.status != "complete":
        s.status = "paused"
        s.last_activity_at = _now()
    db.commit()
    return state(db, s)


@router.post("/me/reflections/{module_key}/feedback")
def reflection_feedback(module_key: str, req: ReflectionFeedback, db: Session = Depends(get_db), s: DiscoverySession = Depends(current_session)):
    refl = (s.module_reflections or {}).get(module_key)
    if not refl:
        raise HTTPException(404, "No reflection for that module yet")
    _touch(s)
    s.module_reflections = {**s.module_reflections, module_key: {**refl, "feedback": req.feedback, "correction": (req.correction or "").strip() or None}}
    if req.feedback == "yes":
        insights.confirm_insights(db, s.user_id, [t["insight_id"] for t in refl.get("themes", []) if t.get("insight_id")])
    db.commit()
    return state(db, s)


@router.post("/me/complete")
def complete(db: Session = Depends(get_db), s: DiscoverySession = Depends(current_session)):
    """Flatten the session into a transcript and run the existing values + purpose pipeline."""
    st = state(db, s)
    if not st["can_complete"]:
        raise HTTPException(422, "Some required questions have not been answered yet")
    messages = []
    for m in load_modules(db, active_only=True):
        stage = LEGACY_STAGE.get(m.key, "harvest")
        for e in next(x for x in st["modules"] if x["key"] == m.key)["exchanges"]:
            if e["answer"]["skipped"]:
                continue
            messages.append({"role": "assistant", "content": f"**{e['prompt']}**", "stage": stage})
            messages.append({"role": "user", "content": e["answer"]["text"], "stage": stage})
            fu = e["follow_up"]
            if fu and fu["answer"] and not fu["answer"]["skipped"]:
                messages.append({"role": "assistant", "content": fu["prompt"], "stage": stage})
                messages.append({"role": "user", "content": fu["answer"]["text"], "stage": stage})
    for key, refl in (s.module_reflections or {}).items():
        if refl.get("correction"):
            messages.append({"role": "user", "content": f"(Correction to what was heard about {key}: {refl['correction']})", "stage": "harvest"})

    convo = db.get(Conversation, s.conversation_id) if s.conversation_id else None
    if convo is None:
        convo = Conversation(user_id=s.user_id, status="complete")
        db.add(convo)
        db.flush()
    convo.messages, convo.status = messages, "complete"
    s.conversation_id = convo.id

    # Final cross-module extraction (tensions, open questions, anything a module pass missed), then the draft.
    try:
        _found, used_extract, _rejected = insights.run_extraction(db, s, None)
        all_insights = insights.active_insights(db, s.user_id)
        sections, measures, used_synth = insights.synthesize(db, s)
    except AIUnavailable:
        db.rollback()
        metrics.bump("extraction_failures", "complete")
        raise HTTPException(503, "The AI service is unavailable right now. Nothing was lost; please try again in a moment.")
    db.add(ValueProfile(user_id=s.user_id, conversation_id=convo.id, data=insights.derive_values_profile(all_insights)))
    prev = db.scalars(select(PurposeStatement).where(PurposeStatement.user_id == s.user_id).order_by(PurposeStatement.id.desc()).limit(1)).first()
    db.add(PurposeStatement(user_id=s.user_id, data=insights.derive_legacy_purpose(sections, measures, all_insights), sections=sections,
                            status="draft", version=(prev.version + 1) if prev else 1))

    s.status, s.completed_at, s.current_question_id = "complete", _now(), None
    if s.sharing == "pending_share":
        s.sharing = "shared_with_advisor"
    db.commit()
    return {"user_id": s.user_id, "conversation_id": convo.id,
            "generated_by": {"extraction": "openrouter" if used_extract else "demo", "synthesis": "openrouter" if used_synth else "demo"}}

"""Discovery methodology as data.

The modules, section headings and questions come verbatim from Mimi's source
documents (see methodology_source.py), plus a short beta "Purpose" opening module.
They are loaded once into `methodology_modules` / `methodology_questions`; after
that the database is the source of truth and the advisor edits it through the
/admin/methodology API.

Question classification drives the client flow:
  core       asked in the main flow
  follow_up  available to the AI as the one follow-up for a core question in the same section
  optional   offered as "go deeper" once a module's core questions are done
  inactive   kept in the database, never shown to clients
"""

import re

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from .auth import optional_session, require_admin, staff_role
from .db import get_db
from .methodology_source import DRAFT_V1_KEYS, KNOWN_ISSUES, METHODOLOGY_SOURCE, OPENING_MODULE, SECTION_ISSUES, beta_classification
from .models import Answer, MethodologyModule, MethodologyQuestion
from .schemas import ModuleIn, QuestionIn, ReorderRequest

# Where each module sits in the legacy discover/harvest/architect stages (used when
# flattening a session into a conversation for the existing values pipeline).
LEGACY_STAGE = {"purpose": "discover", "alignment": "architect", "evolution": "architect"}

CLASSIFICATIONS = ("core", "follow_up", "optional", "inactive")


def _build_module(spec, order: int, *, follow_up_mode: str) -> MethodologyModule:
    key, title, family, group, sections = spec
    module = MethodologyModule(key=key, title=title, description=family, intro="", order=order, session_group=group, follow_up_mode=follow_up_mode)
    q_order = 0
    for s_idx, (heading, questions) in enumerate(sections, start=1):
        for q_idx, prompt in enumerate(questions, start=1):
            q_order += 1
            qkey = f"{key}_s{s_idx}_q{q_idx}"
            module.questions.append(MethodologyQuestion(key=qkey, section=heading, prompt=prompt, order=q_order, classification=beta_classification(qkey)))
    return module


def seed_methodology(db: Session) -> None:
    """Load the methodology into an empty database, replace the pre-import draft set if it is
    still present (and unanswered), and make sure the beta opening module exists."""
    existing_keys = set(db.scalars(select(MethodologyQuestion.key)).all())
    if existing_keys and existing_keys <= DRAFT_V1_KEYS and not db.scalar(select(func.count()).select_from(Answer)):
        for m in db.scalars(select(MethodologyModule)).all():
            db.delete(m)
        db.flush()
        existing_keys = set()
    if not existing_keys:
        db.add(_build_module(OPENING_MODULE, 1, follow_up_mode="compose"))
        for i, spec in enumerate(METHODOLOGY_SOURCE, start=2):
            db.add(_build_module(spec, i, follow_up_mode="pool"))
        db.commit()
        return
    # Imported earlier without the opening module: add it in front, leave the questions alone.
    if not db.scalar(select(MethodologyModule).where(MethodologyModule.key == OPENING_MODULE[0])):
        first = db.scalar(select(func.min(MethodologyModule.order))) or 1
        db.add(_build_module(OPENING_MODULE, first - 1, follow_up_mode="compose"))
        db.commit()
    # A database that has never been classified (everything still `core`) and never answered gets the
    # approved beta structure and classification once. After that the advisor's edits are authoritative.
    pristine = not db.scalar(select(func.count()).select_from(Answer)) and not db.scalar(
        select(func.count()).select_from(MethodologyQuestion).where(MethodologyQuestion.classification != "core")
    )
    if pristine:
        by_key = {m.key: m for m in db.scalars(select(MethodologyModule)).all()}
        for i, (key, _title, _family, group, _sections) in enumerate([OPENING_MODULE, *METHODOLOGY_SOURCE], start=1):
            if key in by_key:
                by_key[key].order, by_key[key].session_group = i, group
                by_key[key].follow_up_mode = "compose" if key == OPENING_MODULE[0] else "pool"
        for q in db.scalars(select(MethodologyQuestion)).all():
            q.classification = beta_classification(q.key)
        db.commit()


# --- Queries used by the discovery flow -------------------------------------

def load_modules(db: Session, *, active_only: bool) -> list[MethodologyModule]:
    stmt = select(MethodologyModule).options(selectinload(MethodologyModule.questions)).order_by(MethodologyModule.order, MethodologyModule.id)
    if active_only:
        stmt = stmt.where(MethodologyModule.active.is_(True))
    return list(db.scalars(stmt).all())


def is_live(q: MethodologyQuestion) -> bool:
    return q.active and q.classification != "inactive"


def flow_questions(modules: list[MethodologyModule], opted: list[str] | None = None) -> list[MethodologyQuestion]:
    """Questions a client is walked through: core, plus optional ones in modules they chose to go deeper into."""
    opted = set(opted or [])
    return [
        q for m in modules if m.active for q in m.questions
        if is_live(q) and (q.classification == "core" or (q.classification == "optional" and m.key in opted))
    ]


def follow_up_pool(q: MethodologyQuestion, used_ids: set[int]) -> list[MethodologyQuestion]:
    """The advisor's follow-up questions for the same section, not yet used in this session."""
    return [o for o in q.module.questions if is_live(o) and o.classification == "follow_up" and o.section == q.section and o.id not in used_ids]


def question_payload(q: MethodologyQuestion, answer_count: int | None = None, flags: list[str] | None = None) -> dict:
    out = {
        "id": q.id, "module_id": q.module_id, "key": q.key, "section": q.section, "prompt": q.prompt, "follow_up_guidance": q.follow_up_guidance,
        "classification": q.classification, "required": q.required, "max_follow_ups": q.max_follow_ups, "order": q.order, "active": q.active,
    }
    if answer_count is not None:
        out["answer_count"] = answer_count
    if flags is not None:
        out["flags"] = flags
    return out


def module_payload(m: MethodologyModule, *, active_only: bool, counts: dict[int, int] | None = None, flags: dict[int, list[str]] | None = None) -> dict:
    qs = [q for q in m.questions if is_live(q)] if active_only else list(m.questions)
    return {
        "id": m.id, "key": m.key, "title": m.title, "description": m.description, "intro": m.intro,
        "order": m.order, "session_group": m.session_group, "follow_up_mode": m.follow_up_mode, "active": m.active,
        "counts": {c: sum(1 for q in m.questions if q.classification == c and q.active) for c in CLASSIFICATIONS},
        "questions": [question_payload(q, None if counts is None else counts.get(q.id, 0), None if flags is None else flags.get(q.id, [])) for q in qs],
    }


def review_flags(modules: list[MethodologyModule]) -> dict[int, list[str]]:
    """Duplicates (detected from the data) plus the transcription notes. Shown to the advisor, never auto-fixed."""
    out: dict[int, list[str]] = {}
    seen: dict[str, MethodologyQuestion] = {}
    for m in modules:
        for q in m.questions:
            norm = q.prompt.strip().lower()
            if norm in seen:
                first = seen[norm]
                pos = sum(1 for o in first.module.questions if o.section == first.section and o.order <= first.order)
                out.setdefault(q.id, []).append(f"Duplicate of {first.module.title} › {first.section or 'opening'} #{pos}.")
            else:
                seen[norm] = q
            if q.key in KNOWN_ISSUES and KNOWN_ISSUES[q.key] not in out.get(q.id, []):
                out.setdefault(q.id, []).append(KNOWN_ISSUES[q.key])
            if q.section in SECTION_ISSUES and q.order == min(o.order for o in m.questions if o.section == q.section):
                out.setdefault(q.id, []).append(SECTION_ISSUES[q.section])
    return out


# --- Routers ------------------------------------------------------------------

router = APIRouter(tags=["methodology"])


@router.get("/methodology")
def get_methodology(request: Request, db: Session = Depends(get_db)):
    if staff_role(request) is None and optional_session(request, db) is None:
        raise HTTPException(401, "Sign in or start a discovery first")
    return [module_payload(m, active_only=True) for m in load_modules(db, active_only=True)]


admin = APIRouter(prefix="/admin/methodology", tags=["admin"], dependencies=[Depends(require_admin)])


def _answer_counts(db: Session) -> dict[int, int]:
    rows = db.execute(select(Answer.question_id, func.count()).group_by(Answer.question_id)).all()
    return {qid: n for qid, n in rows}


def _slug(text: str, taken: set[str]) -> str:
    base = re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")[:40] or "item"
    key, i = base, 2
    while key in taken:
        key, i = f"{base}_{i}", i + 1
    return key


@admin.get("")
def admin_methodology(db: Session = Depends(get_db)):
    modules = load_modules(db, active_only=False)
    counts, flags = _answer_counts(db), review_flags(modules)
    return [module_payload(m, active_only=False, counts=counts, flags=flags) for m in modules]


@admin.post("/modules")
def create_module(req: ModuleIn, db: Session = Depends(get_db)):
    if not req.title or not req.title.strip():
        raise HTTPException(422, "title is required")
    taken = set(db.scalars(select(MethodologyModule.key)).all())
    key = req.key.strip() if req.key else _slug(req.title, taken)
    if key in taken:
        raise HTTPException(409, "A module with that key already exists")
    order = (db.scalar(select(func.max(MethodologyModule.order))) or 0) + 1
    m = MethodologyModule(
        key=key, title=req.title.strip(), description=req.description or "", intro=req.intro or "",
        order=order, session_group=req.session_group or 1, follow_up_mode=req.follow_up_mode or "pool",
        active=True if req.active is None else req.active,
    )
    db.add(m)
    db.commit()
    return module_payload(m, active_only=False, counts={}, flags={})


@admin.put("/modules/{module_id}")
def update_module(module_id: int, req: ModuleIn, db: Session = Depends(get_db)):
    m = db.get(MethodologyModule, module_id)
    if not m:
        raise HTTPException(404, "Module not found")
    for field in ("title", "description", "intro", "session_group", "follow_up_mode", "active"):
        value = getattr(req, field)
        if value is not None:
            setattr(m, field, value.strip() if field == "title" else value)
    db.commit()
    return module_payload(m, active_only=False, counts=_answer_counts(db), flags=review_flags([m]))


@admin.delete("/modules/{module_id}")
def delete_module(module_id: int, db: Session = Depends(get_db)):
    m = db.get(MethodologyModule, module_id)
    if not m:
        raise HTTPException(404, "Module not found")
    qids = [q.id for q in m.questions]
    used = qids and db.scalar(select(func.count()).select_from(Answer).where(Answer.question_id.in_(qids)))
    if used:
        m.active = False  # answers reference its questions: keep history, hide from clients
        db.commit()
        return {"deleted": False, "deactivated": True}
    db.delete(m)
    db.commit()
    return {"deleted": True, "deactivated": False}


@admin.post("/questions")
def create_question(req: QuestionIn, db: Session = Depends(get_db)):
    if not req.module_id or not db.get(MethodologyModule, req.module_id):
        raise HTTPException(422, "module_id is required")
    if not req.prompt or not req.prompt.strip():
        raise HTTPException(422, "prompt is required")
    taken = set(db.scalars(select(MethodologyQuestion.key)).all())
    key = req.key.strip() if req.key else _slug(req.prompt, taken)
    if key in taken:
        raise HTTPException(409, "A question with that key already exists")
    order = (db.scalar(select(func.max(MethodologyQuestion.order)).where(MethodologyQuestion.module_id == req.module_id)) or 0) + 1
    q = MethodologyQuestion(
        module_id=req.module_id, key=key, section=(req.section or "").strip(), prompt=req.prompt.strip(), follow_up_guidance=req.follow_up_guidance or "",
        classification=req.classification or "core", required=True if req.required is None else req.required,
        max_follow_ups=1 if req.max_follow_ups is None else req.max_follow_ups, order=order, active=True if req.active is None else req.active,
    )
    db.add(q)
    db.commit()
    return question_payload(q, 0, [])


@admin.put("/questions/{question_id}")
def update_question(question_id: int, req: QuestionIn, db: Session = Depends(get_db)):
    q = db.get(MethodologyQuestion, question_id)
    if not q:
        raise HTTPException(404, "Question not found")
    if req.module_id is not None and req.module_id != q.module_id:
        if not db.get(MethodologyModule, req.module_id):
            raise HTTPException(422, "module not found")
        q.module_id = req.module_id
        q.order = (db.scalar(select(func.max(MethodologyQuestion.order)).where(MethodologyQuestion.module_id == req.module_id)) or 0) + 1
    for field in ("section", "prompt", "follow_up_guidance", "classification", "required", "max_follow_ups", "active"):
        value = getattr(req, field)
        if value is not None:
            setattr(q, field, value.strip() if field in ("prompt", "section") else value)
    db.commit()
    return question_payload(q, _answer_counts(db).get(q.id, 0), review_flags([q.module]).get(q.id, []))


@admin.delete("/questions/{question_id}")
def delete_question(question_id: int, db: Session = Depends(get_db)):
    q = db.get(MethodologyQuestion, question_id)
    if not q:
        raise HTTPException(404, "Question not found")
    if db.scalar(select(func.count()).select_from(Answer).where(Answer.question_id == q.id)):
        q.active, q.classification = False, "inactive"
        db.commit()
        return {"deleted": False, "deactivated": True}
    db.delete(q)
    db.commit()
    return {"deleted": True, "deactivated": False}


@admin.post("/reorder")
def reorder(req: ReorderRequest, db: Session = Depends(get_db)):
    model = MethodologyModule if req.kind == "modules" else MethodologyQuestion
    rows = {r.id: r for r in db.scalars(select(model).where(model.id.in_(req.ids))).all()}
    if len(rows) != len(req.ids):
        raise HTTPException(422, "Unknown id in list")
    if req.kind == "questions" and len({r.module_id for r in rows.values()}) > 1:
        raise HTTPException(422, "Questions must belong to one module")
    for i, id_ in enumerate(req.ids, start=1):
        rows[id_].order = i
    db.commit()
    return {"ok": True}

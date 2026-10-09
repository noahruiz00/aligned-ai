"""Client insights: validation, merging, audit history, client review, and the derived
records that keep the existing values / purpose / scoring pipeline working."""

import logging
import re
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from . import ai_insights, metrics
from .ai import AIUnavailable
from .ai_insights import INSIGHT_TYPES, MAX_OPEN_PER_PASS, MAX_PER_PASS, MAX_WEALTH_PURPOSE, OPEN_TYPES, SECTION_KEYS
from .auth import current_session
from .db import get_db
from .models import INSIGHT_BASES, Answer, ClientInsight, DiscoverySession, EvidenceLink, InsightEvent, MethodologyModule
from .schemas import InsightFeedback

log = logging.getLogger("aligned.insights")

PROTECTED = ("client_confirmed", "client_corrected", "advisor_confirmed")
MIN_CONFIDENCE = 0.6  # rubric: 0.60 or below is needs-clarification territory
MAX_EVIDENCE = 6  # per insight; beyond this an insight is becoming a catch-all
HEDGES = ("i suppose", "maybe", "not sure", "i guess", "probably", "i think", "hard to say", "mainly", "nothing special", "i don't know", "dont know", "no idea", "fairly", "much the same")
DECLINES = ("prefer not", "rather not", "not get into", "skip this", "prefer to skip", "don't want to talk", "do not want to talk", "not talk about")
PRIMARY_LIMIT = 17  # strongest non-open cards shown first (+ up to 3 open items = ~20 primary)
STOP = set("""i me my we our you your the a an and or of to in on at for with that this it is was were be been have has had do does not no
as by from than then so if but about into over after before when where who what which there here they them their he she just very really
also only more most much many some any all every both few each other such own same too can could would should will may might must""".split())


def _words(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z']+", text.casefold()) if w not in STOP and len(w) > 2}


def _similar(a: str, b: str) -> float:
    A, B = _words(a), _words(b)
    return len(A & B) / len(A | B) if A | B else 0.0


GENERIC = ("something", "anything", "things", "stuff", "whatever", "general", "normal", "fine", "okay", "nothing much")


def _is_hedged(text: str) -> bool:
    """Vague, hedged, generic or incomplete evidence. Length alone is not a reason: "My children" or
    "Cooking for my parents in the evening" are short, concrete and unambiguous."""
    t = text.casefold()
    content = _words(t)
    if any(h in t for h in HEDGES) or not content:
        return True
    return any(g in t for g in GENERIC) and len(content) <= 2


def _is_decline(text: str) -> bool:
    t = text.casefold()
    return any(d in t for d in DECLINES)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9 ]+", "", text.casefold()).strip()


def _squash(text: str) -> str:
    """Normalise quotes/dashes/whitespace so a verbatim excerpt matches despite typography."""
    t = text.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"').replace("—", "-").replace("–", "-")
    return re.sub(r"\s+", " ", t).strip().casefold()


# --- Answers in scope -------------------------------------------------------------

def answer_rows(s: DiscoverySession, module: MethodologyModule | None = None) -> list[dict]:
    """Non-skipped answers (including follow-up replies) as plain rows for the extraction engine."""
    rows = []
    for a in s.answers:
        q = a.question
        if a.skipped or not a.text.strip() or (module is not None and q.module_id != module.id):
            continue
        rows.append({"answer_id": a.id, "question_id": q.id, "question_key": q.key, "module": q.module.title, "module_key": q.module.key,
                     "section": q.section, "prompt": a.prompt_text, "text": a.text})
    return rows


# --- Validation: nothing enters the database without real evidence -------------------

def validate_insights(raw: list[dict], rows: list[dict]) -> tuple[list[dict], list[str]]:
    """Returns (clean insights, rejection notes). Evidence must cite a provided answer with a verbatim excerpt;
    interpretations without surviving evidence are rejected; weak ones become needs_clarification; repeats merge."""
    by_answer = {r["answer_id"]: r for r in rows}
    clean: dict[tuple[str, str], dict] = {}
    rejected: list[str] = []
    for item in raw or []:
        if not isinstance(item, dict):
            continue
        type_ = item.get("type")
        label = str(item.get("label") or "").strip()[:120]
        summary = str(item.get("summary") or "").strip()
        if type_ not in INSIGHT_TYPES or not label or not summary:
            rejected.append(f"malformed insight {label!r}")
            continue
        basis = item.get("basis") if item.get("basis") in INSIGHT_BASES else "ai_interpretation"
        try:
            confidence = max(0.0, min(1.0, float(item.get("confidence", 0.5))))
        except (TypeError, ValueError):
            confidence = 0.5
        evidence = []
        for ev in item.get("evidence") or []:
            if not isinstance(ev, dict):
                continue
            row = by_answer.get(ev.get("answer_id"))
            excerpt = str(ev.get("excerpt") or "").strip()
            if row is None or not excerpt:
                continue
            if _squash(excerpt) not in _squash(row["text"]):
                rejected.append(f"{label}: excerpt not found verbatim in answer {ev.get('answer_id')}")
                continue
            if all(not (e["answer_id"] == row["answer_id"] and _squash(e["excerpt"]) == _squash(excerpt)) for e in evidence):
                evidence.append({"answer_id": row["answer_id"], "question_id": row["question_id"], "module": row["module"], "section": row["section"], "excerpt": excerpt[:600]})
        if type_ not in OPEN_TYPES and not evidence:
            rejected.append(f"{label}: unsupported {basis} rejected (no verbatim evidence)")
            continue
        if type_ not in OPEN_TYPES:
            distinct = {e["answer_id"] for e in evidence}
            # Declining, skipping or discomfort is never evidence of a value: it becomes a declined topic.
            if all(_is_decline(e["excerpt"]) for e in evidence):
                type_, basis, confidence = "declined_topic", "client_statement", min(confidence, 0.5)
            elif type_ == "tensions" and len(distinct) < 2:
                rejected.append(f"{label}: tension needs evidence from both sides")
                continue
            else:
                # Confidence rubric, enforced: 0.9+ needs the idea in two answers; interpretations sit below statements;
                # hedged / very short evidence is needs-clarification territory.
                if len(distinct) < 2:
                    confidence = min(confidence, 0.89 if basis != "ai_interpretation" else 0.85)
                if all(_is_hedged(e["excerpt"]) for e in evidence):
                    confidence = min(confidence, 0.6)
                elif basis == "ai_interpretation" and len(distinct) < 2 and _is_hedged(evidence[0]["excerpt"]):
                    confidence = min(confidence, 0.6)
        status = "needs_clarification" if type_ in OPEN_TYPES or confidence <= MIN_CONFIDENCE else "ai_detected"
        key = (type_, _norm(label))
        if key in clean:  # duplicate within one extraction: merge
            prev = clean[key]
            prev["confidence"] = max(prev["confidence"], confidence)
            prev["status"] = "needs_clarification" if prev["type"] in OPEN_TYPES or prev["confidence"] < MIN_CONFIDENCE else "ai_detected"
            for ev in evidence:
                if all(not (e["answer_id"] == ev["answer_id"] and _squash(e["excerpt"]) == _squash(ev["excerpt"])) for e in prev["evidence"]):
                    prev["evidence"].append(ev)
            continue
        clean[key] = {"type": type_, "label": label, "summary": summary, "basis": basis, "confidence": confidence, "status": status, "evidence": evidence}
    # Per-pass caps: strongest first, at most one wealth purpose, at most three open items, at most MAX_PER_PASS in all.
    items = sorted(clean.values(), key=lambda c: (len({e["answer_id"] for e in c["evidence"]}), c["confidence"]), reverse=True)
    kept, n_wp, n_open, n_main = [], 0, 0, 0
    for c in items:
        if c["type"] == "wealth_purpose":
            if n_wp >= MAX_WEALTH_PURPOSE:
                rejected.append(f"{c['label']}: extra wealth_purpose dropped (one per client)")
                continue
            n_wp += 1
        if c["type"] in OPEN_TYPES:
            if n_open >= MAX_OPEN_PER_PASS:
                rejected.append(f"{c['label']}: extra open item dropped (cap {MAX_OPEN_PER_PASS} per pass)")
                continue
            n_open += 1
        else:
            if n_main >= MAX_PER_PASS:
                rejected.append(f"{c['label']}: dropped (cap {MAX_PER_PASS} per pass)")
                continue
            n_main += 1
        kept.append(c)
    return kept, rejected


# --- Merging into the client's insight set ---------------------------------------------

def _snapshot(i: ClientInsight) -> dict:
    return {"label": i.label, "summary": i.summary, "basis": i.basis, "confidence": i.confidence, "status": i.status,
            "client_feedback": i.client_feedback, "client_correction": i.client_correction}


def _add_evidence(i: ClientInsight, evidence: list[dict]) -> int:
    added = 0
    for ev in evidence:
        if all(not (e.answer_id == ev["answer_id"] and _squash(e.excerpt) == _squash(ev["excerpt"])) for e in i.evidence):
            i.evidence.append(EvidenceLink(question_id=ev["question_id"], answer_id=ev["answer_id"], module=ev["module"], section=ev["section"], excerpt=ev["excerpt"]))
            added += 1
    return added


def _find_existing(existing: list[ClientInsight], c: dict) -> ClientInsight | None:
    """Same type and the same label, or a label / summary close enough that this is the same theme."""
    same_type = [i for i in existing if i.type == c["type"]]
    for i in same_type:
        if _norm(i.label) == _norm(c["label"]):
            return i
    best, best_score = None, 0.0
    for i in same_type:
        score = max(_similar(i.label, c["label"]), _similar(i.summary, c["summary"]))
        if score > best_score:
            best, best_score = i, score
    return best if best_score >= 0.6 else None


def merge_insights(db: Session, s: DiscoverySession, module_key: str, clean: list[dict]) -> list[ClientInsight]:
    """Insert new insights; enrich existing ones. The existing summary is kept unless the new one says the same thing
    more clearly; evidence is appended only when it belongs to the same meaning; confirmed / corrected insights only
    ever gain evidence. One wealth_purpose per client."""
    existing_list = active_insights(db, s.user_id)
    touched: list[ClientInsight] = []
    for c in clean:
        i = _find_existing(existing_list, c)
        if i is None and c["type"] == "wealth_purpose":
            i = next((x for x in existing_list if x.type == "wealth_purpose"), None)  # add to the one that exists
        if i is None:
            i = ClientInsight(client_id=s.user_id, session_id=s.id, module_key=module_key, type=c["type"], label=c["label"], summary=c["summary"],
                              basis=c["basis"], confidence=c["confidence"], status=c["status"],
                              original={"label": c["label"], "summary": c["summary"], "basis": c["basis"], "confidence": c["confidence"], "evidence": c["evidence"]})
            _add_evidence(i, c["evidence"][:MAX_EVIDENCE])
            i.events.append(InsightEvent(event="ai_detected", before=None, after=_snapshot(i)))
            db.add(i)
            existing_list.append(i)
        else:
            before = _snapshot(i)
            related = _similar(i.summary, c["summary"]) >= 0.2 or _similar(i.label, c["label"]) >= 0.5 or i.type == "wealth_purpose"
            if not related:
                log.info("insight restated with unrelated evidence; not merged: %s", c["label"])
                continue
            room = max(0, MAX_EVIDENCE - len(i.evidence))
            added = _add_evidence(i, c["evidence"][:room]) if room else 0
            if i.status not in PROTECTED:
                distinct = {e.answer_id for e in i.evidence}
                if _similar(i.summary, c["summary"]) >= 0.5 and c["confidence"] > i.confidence:
                    i.summary = c["summary"]  # same meaning, said more clearly
                if added:
                    # more supporting answers can raise confidence, never beyond what the rubric allows for the basis
                    i.confidence = min(1.0 if len(distinct) >= 2 else 0.89, max(i.confidence, c["confidence"]))
                i.status = "needs_clarification" if i.type in OPEN_TYPES or i.confidence <= MIN_CONFIDENCE else "ai_detected"
            if added or _snapshot(i) != before:
                i.events.append(InsightEvent(event="re_extracted", before=before, after={**_snapshot(i), "evidence_added": added}))
        touched.append(i)
    db.flush()
    return touched


def active_insights(db: Session, client_id: int) -> list[ClientInsight]:
    stmt = (select(ClientInsight).options(selectinload(ClientInsight.evidence), selectinload(ClientInsight.events))
            .where(ClientInsight.client_id == client_id, ClientInsight.active.is_(True)).order_by(ClientInsight.id))
    return list(db.scalars(stmt).all())


def run_extraction(db: Session, s: DiscoverySession, module: MethodologyModule | None) -> tuple[list[ClientInsight], bool, list[str]]:
    """Extract for one module (or everything when module is None), validate, merge. Returns (insights, used_llm, rejections)."""
    rows = answer_rows(s, module)
    if not rows:
        return [], False, []
    existing = [{"type": i.type, "label": i.label, "summary": i.client_correction or i.summary, "status": i.status, "evidence_count": len(i.evidence)}
                for i in active_insights(db, s.user_id)]
    raw, used = ai_insights.extract_insights(s.user.name, s.user.household_type, module.title if module else "all modules", rows, existing)
    clean, rejected = validate_insights(raw, rows)
    s.extraction_runs = (s.extraction_runs or 0) + 1
    s.rejected_insight_count = (s.rejected_insight_count or 0) + len(rejected)
    if rejected:  # QA signal only: counts, types and labels; never the client's text
        log.info("extraction: %d insight(s) rejected (session %s): %s", len(rejected), s.id, "; ".join(n.split(":")[0] for n in rejected))
    return merge_insights(db, s, module.key if module else "", clean), used, rejected


# --- Payloads --------------------------------------------------------------------------

# Relevance of each type to the Wealth Purpose Statement sections.
RELEVANCE = {"wealth_purpose": 3.0, "meaningful_life_themes": 2.5, "money_role": 2.5, "personal_values": 2.0, "financial_values": 2.0,
             "family_context": 2.0, "legacy_themes": 2.0, "community_priorities": 2.0, "philanthropic_interests": 2.0, "money_story": 2.0,
             "money_beliefs": 1.5, "tensions": 2.0, "goals": 1.5, "work_themes": 1.0, "service_themes": 1.5, "emotional_themes": 1.0,
             "open_questions": 1.0, "uncertainties": 0.5, "declined_topic": 0.5}


def rank_score(i: ClientInsight) -> float:
    """Client confirmed/corrected first, then evidence strength, relevance, recurrence, confidence."""
    status = {"advisor_confirmed": 3, "client_corrected": 3, "client_confirmed": 3, "ai_detected": 1, "needs_clarification": 0}.get(i.status, 0)
    answers = len({e.answer_id for e in i.evidence})
    strength = min(answers, 4) + min(sum(len(e.excerpt.split()) for e in i.evidence), 60) / 60
    modules = len({e.module for e in i.evidence})
    return status * 10 + strength * 2 + RELEVANCE.get(i.type, 1.0) * 1.5 + min(modules, 3) + i.confidence


def ranked(insights: list[ClientInsight]) -> list[ClientInsight]:
    return sorted(insights, key=rank_score, reverse=True)


def primary_ids(insights: list[ClientInsight], limit: int = PRIMARY_LIMIT) -> set[int]:
    """The cards shown first: the strongest non-open insights up to the limit, plus up to three open items."""
    main = [i for i in ranked(insights) if i.type not in OPEN_TYPES][:limit]
    opens = [i for i in ranked(insights) if i.type in OPEN_TYPES][:3]
    return {i.id for i in main} | {i.id for i in opens}


def insight_payload(i: ClientInsight, primary: set[int] | None = None, position: int | None = None) -> dict:
    return {
        "id": i.id, "client_id": i.client_id, "type": i.type, "label": i.label, "summary": i.summary, "basis": i.basis,
        "confidence": round(i.confidence, 2), "status": i.status, "module_key": i.module_key,
        "primary": (i.id in primary) if primary is not None else True, "rank": position,
        "client_feedback": i.client_feedback, "client_correction": i.client_correction, "original": i.original,
        "evidence": [{"id": e.id, "question_id": e.question_id, "answer_id": e.answer_id, "module": e.module, "section": e.section, "excerpt": e.excerpt} for e in i.evidence],
        "history": [{"event": ev.event, "before": ev.before, "after": ev.after, "at": ev.created_at.isoformat()} for ev in i.events],
        "created_at": i.created_at.isoformat(), "updated_at": i.updated_at.isoformat(),
    }


def module_reflection(insights: list[ClientInsight], module: MethodologyModule) -> dict:
    """What we're hearing: the module's strongest insights, each tied to its evidence, not generic prose."""
    # Rank by what this module actually said: evidence from this module first, insights first found here
    # before ones merely re-confirmed here, then confidence. Otherwise the strongest global themes
    # (Family, Education, ...) would be repeated after every module.
    def rank(i: ClientInsight):
        here = sum(1 for e in i.evidence if e.module == module.title)
        return (here, 1 if i.module_key == module.key else 0, i.confidence)
    candidates = [i for i in insights if i.type not in OPEN_TYPES and i.status != "needs_clarification" and any(e.module == module.title for e in i.evidence)]
    strong, seen = [], set()
    for i in sorted(candidates, key=rank, reverse=True):
        if i.label.casefold() not in seen:  # one line per theme, even when two types share a label
            seen.add(i.label.casefold())
            strong.append(i)
        if len(strong) == 4:
            break
    themes = [{"name": i.label, "note": i.client_correction or i.summary, "insight_id": i.id} for i in strong]
    unclear = [i for i in insights if i.status == "needs_clarification"]
    if themes:
        summary = f"Here is what stood out in {module.title}. Each line comes from something you said; you can see the words behind it on the review page."
    elif unclear:
        summary = f"We didn't catch a clear theme in {module.title} yet, and we'd rather ask than guess. You'll see what needs clarifying on the review page."
    else:
        summary = f"You moved through {module.title} quickly. Nothing to confirm here yet."
    return {"summary": summary, "themes": themes}


def confirm_insights(db: Session, client_id: int, ids: list[int]) -> None:
    for i in db.scalars(select(ClientInsight).where(ClientInsight.id.in_(ids), ClientInsight.client_id == client_id)).all():
        if i.status in ("ai_detected", "needs_clarification"):
            before = _snapshot(i)
            i.status, i.client_feedback = "client_confirmed", "accurate"
            i.events.append(InsightEvent(event="client_feedback", before=before, after=_snapshot(i)))


def apply_feedback(db: Session, i: ClientInsight, req: InsightFeedback) -> None:
    """The original AI output is never changed; the client's view is stored beside it with a history event."""
    before = _snapshot(i)
    text = (req.text or "").strip() or None
    i.client_feedback = req.feedback
    if req.feedback == "accurate":
        i.status, i.client_correction = "client_confirmed", None
    elif req.feedback == "partly":
        if not text:
            raise HTTPException(422, "Tell us what's not quite right")
        i.status, i.client_correction = "client_corrected", text
    elif req.feedback == "edit":
        if not text:
            raise HTTPException(422, "Tell us what it should say")
        i.status, i.client_correction = "client_corrected", text
    elif req.feedback == "clarify":
        if not text:
            raise HTTPException(422, "Add a few words of clarification")
        i.status, i.client_correction = "client_corrected", text
    i.events.append(InsightEvent(event="client_feedback", before=before, after=_snapshot(i)))


# --- Synthesis + derived legacy records ------------------------------------------------

def usable_for_synthesis(insights: list[ClientInsight]) -> list[dict]:
    """Only what may shape the statement: client-confirmed / corrected insights, or well-evidenced detections
    (two or more supporting answers, confidence >= 0.7). Everything else is left for clarification."""
    def strong(i: ClientInsight) -> bool:
        if i.status != "ai_detected":
            return False
        if i.confidence >= 0.7 and len({e.answer_id for e in i.evidence}) >= 2:
            return True  # A: supported by two different answers (any basis)
        # B: one explicit, specific, unambiguous statement in the client's words; never an interpretation
        return (i.basis in ("client_fact", "client_statement") and i.confidence >= 0.85
                and bool(i.evidence) and not any(_is_hedged(e.excerpt) for e in i.evidence))
    chosen = [i for i in ranked(insights) if i.type not in OPEN_TYPES and (i.status in PROTECTED or strong(i))]
    return [insight_payload(i) for i in chosen[:30]]


def synthesize(db: Session, s: DiscoverySession) -> tuple[dict, list[str], bool]:
    insights = active_insights(db, s.user_id)
    draft, used = ai_insights.synthesize_purpose(s.user.name, s.user.household_type, usable_for_synthesis(insights))
    valid_ids = {i.id for i in insights}
    sections = {}
    for key in SECTION_KEYS:
        sec = draft.get(key) if isinstance(draft.get(key), dict) else {"text": str(draft.get(key) or ""), "insight_ids": []}
        ids = [int(x) for x in (sec.get("insight_ids") or []) if isinstance(x, (int, float)) and int(x) in valid_ids]
        sections[key] = {"title": ai_insights.SECTION_TITLES[key], "text": str(sec.get("text") or "").strip() or "Needs clarification: nothing supported this section yet.", "insight_ids": ids}
    measures = [str(m) for m in (draft.get("accountability_measures") or []) if str(m).strip()][:5]
    return sections, measures, used


def _texts(insights: list[ClientInsight], type_: str, n: int = 5) -> list[ClientInsight]:
    rank = {"advisor_confirmed": 0, "client_corrected": 0, "client_confirmed": 0, "ai_detected": 1, "needs_clarification": 2}
    items = [i for i in insights if i.type == type_ and i.active]
    items.sort(key=lambda i: (rank.get(i.status, 3), -i.confidence))
    return items[:n]


def derive_values_profile(insights: list[ClientInsight]) -> dict:
    """The legacy `values` record (used by scoring and the advisor sidebar), derived from insights rather than a second LLM call."""
    def label_list(type_):
        return [i.label for i in _texts(insights, type_)]
    story = _texts(insights, "money_story", 1)
    return {
        "values": [{"name": i.label, "why": i.client_correction or i.summary} for i in _texts(insights, "personal_values")],
        "financial_priorities": label_list("financial_values"),
        "life_goals": [i.client_correction or i.summary for i in _texts(insights, "goals")],
        "family_goals": [i.client_correction or i.summary for i in _texts(insights, "family_context", 3)],
        "legacy_goals": [i.client_correction or i.summary for i in _texts(insights, "legacy_themes", 3)],
        "philanthropy": label_list("philanthropic_interests") + label_list("community_priorities"),
        "emotional_cues": [i.client_correction or i.summary for i in _texts(insights, "emotional_themes", 3)],
        "money_script": (story[0].client_correction or story[0].summary) if story else "",
    }


def derive_legacy_purpose(sections: dict, measures: list[str], insights: list[ClientInsight]) -> dict:
    """The legacy `purpose_statements.data` shape so the dashboard, advisor list and statement page keep working."""
    return {
        "purpose_statement": sections["purpose_of_wealth"]["text"],
        "core_values": [{"name": i.label, "meaning": i.client_correction or i.summary} for i in _texts(insights, "personal_values")],
        "meaningful_life_vision": {"summary": sections["meaningful_life"]["text"], "pillars": [i.label for i in _texts(insights, "meaningful_life_themes", 3)]},
        "wealth_philosophy": sections["money_role"]["text"],
        "legacy_statement": sections["family_legacy"]["text"],
        "accountability_measures": measures,
        "guides": {"investments": "", "estate": "", "philanthropy": "", "cash_flow": ""},
    }


# --- Router -------------------------------------------------------------------------------

router = APIRouter(prefix="/discovery", tags=["insights"])


@router.get("/me/insights")
def list_insights(db: Session = Depends(get_db), s: DiscoverySession = Depends(current_session)):
    items = ranked(active_insights(db, s.user_id))
    prim = primary_ids(items)
    return {"client_id": s.user_id, "primary_limit": PRIMARY_LIMIT, "insights": [insight_payload(i, prim, n) for n, i in enumerate(items, start=1)]}


@router.post("/me/insights/{insight_id}/feedback")
def insight_feedback(insight_id: int, req: InsightFeedback, db: Session = Depends(get_db), s: DiscoverySession = Depends(current_session)):
    i = db.get(ClientInsight, insight_id)
    if not i or i.client_id != s.user_id or not i.active:  # another client's insight is simply not found
        raise HTTPException(404, "Insight not found")
    apply_feedback(db, i, req)
    s.last_activity_at = _now()
    db.commit()
    db.refresh(i)
    return insight_payload(i)


@router.post("/me/insights/refresh")
def refresh_insights(db: Session = Depends(get_db), s: DiscoverySession = Depends(current_session)):
    """Re-run extraction over everything answered so far (used by the review page when answers were clarified)."""
    try:
        found, used, rejected = run_extraction(db, s, None)
    except AIUnavailable:
        db.rollback()
        metrics.bump("extraction_failures", "refresh")
        raise HTTPException(503, "The AI service is unavailable right now. Please try again in a moment.")
    s.last_activity_at = _now()
    db.commit()
    items = ranked(active_insights(db, s.user_id))
    prim = primary_ids(items)
    return {"generated_by": "openrouter" if used else "demo", "touched": len(found), "rejected": len(rejected),
            "insights": [insight_payload(i, prim, n) for n, i in enumerate(items, start=1)]}

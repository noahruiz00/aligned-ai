"""Extraction and synthesis engines.

Kept apart from the conversation engine in ai.py on purpose:
  B. extract_insights   answers -> structured, evidence-linked insights (strict JSON schema)
  C. synthesize_purpose insights -> readable Wealth Purpose Statement draft
Each has a deterministic demo implementation and raises nothing: on any model
failure the demo path is used so a session never dead-ends.
"""

import re

from .ai import CAUSES, PHILOSOPHY, VALUE_LIBRARY, AIUnavailable, _STR, _STRS, _llm_json, _obj
from .config import DEMO_MODE, STRICT_AI

INSIGHT_TYPES = [
    "wealth_purpose", "personal_values", "financial_values", "goals", "meaningful_life_themes", "money_role",
    "money_story", "money_beliefs", "family_context", "legacy_themes", "community_priorities", "philanthropic_interests",
    "work_themes", "service_themes", "emotional_themes", "tensions", "open_questions", "uncertainties", "declined_topic",
]
OPEN_TYPES = ("open_questions", "uncertainties", "declined_topic")
# Per extraction pass (one module, or the final cross-module pass)
MAX_PER_PASS = 8
MAX_WEALTH_PURPOSE = 1
MAX_OPEN_PER_PASS = 3
BASES = ["client_fact", "client_statement", "ai_interpretation"]

# ---------------------------------------------------------------------------
# B. Extraction engine

EXTRACT_SCHEMA = _obj(
    insights={"type": "array", "items": _obj(
        type={"type": "string", "enum": INSIGHT_TYPES},
        label=_STR,
        summary=_STR,
        basis={"type": "string", "enum": BASES},
        confidence={"type": "number"},
        evidence={"type": "array", "items": _obj(answer_id={"type": "integer"}, excerpt=_STR)},
    )},
)

EXTRACT_SYSTEM = f"""You build a structured understanding of a client from their discovery answers, for a private \
wealth advisory firm. You assist the advisor; you never advise the client.

{PHILOSOPHY}

Insight types:
- wealth_purpose: what they want wealth to make possible (at most ONE per client; add evidence to the existing one).
- personal_values / financial_values: values that recur.  - goals.  - meaningful_life_themes.
- money_role: the role money plays in their life.  - money_story: how they came to relate to money.
- money_beliefs: inherited or held beliefs about money.  - family_context.  - legacy_themes.
- community_priorities.  - philanthropic_interests.  - work_themes.  - service_themes.
- emotional_themes: feelings that showed up.  - tensions: answers that pull against each other.
- open_questions / uncertainties: what remains unclear.  - declined_topic: something the client chose not to go into.

You are given the client's EXISTING insights. Return only what is genuinely new in this material, or add \
evidence to an existing insight by returning its EXACT existing type and label. Do not restate an existing theme \
under a new label. If nothing new appears, return an empty list. At most {MAX_PER_PASS} insights per pass, \
at most {MAX_OPEN_PER_PASS} of them open_questions/uncertainties/declined_topic.

Evidence: every insight except the open types must cite one or more answers by answer_id with an excerpt \
copied verbatim (at most 30 words). Each excerpt must itself express the insight; never cite a sentence merely \
because it sits in the same answer. Only cite answer_ids you were given. Any excerpt that is not an exact copy \
is discarded. A tension needs evidence from BOTH sides, from different answers; do not build tensions from \
brief or generic answers.

Labels: two or three words, specific to this insight (e.g. "Family Presence", "Intergenerational Care", \
"Fear Of Loss"), never a label already used for a different type, and never a generic one like "Family" if a \
more specific label is supported. Do not invent distinctions the evidence does not support.

basis: client_fact for concrete facts (people, events, numbers); client_statement for a value, wish or feeling in \
the client's own words; ai_interpretation for anything inferred. Never present an interpretation as a fact.

confidence rubric:
- 0.90–1.00 only when the client clearly states the same idea in at least two meaningful answers.
- 0.70–0.89 for one strong, direct answer with clear meaning.
- 0.60 or below for anything inferred, hedged, vague, very short or incomplete ("I suppose", "maybe", "not \
sure", "family, mainly", "a quiet day", "nothing special"). An interpretation is normally lower than a statement.

Use needs-clarification territory (confidence ≤ 0.6, or an open_questions / uncertainties item) when evidence \
is vague, short or hedged, when a single weak excerpt supports an interpretation, when evidence conflicts, or \
when you would have to infer motive, value or identity. Declining, skipping or discomfort is never evidence of \
a value or belief: record it as declined_topic. Never fill a gap with a guess.

summary: one sentence addressed to the client ("Your answers..."), grounded in their words, neutral in tone: \
no diagnosis, no judgment, no praise, no advice. Prefer at most three strong open questions, the ones that \
would most improve the Purpose of Wealth, Meaningful Life, Money's Role, Family / Legacy or Community sections; \
never several versions of the same question.
Never give financial, investment, tax or legal advice."""


def _format_answers(rows: list[dict]) -> str:
    return "\n\n".join(f"[answer_id={r['answer_id']}] {r['module']} › {r['section'] or 'opening'}\nQ: {r['prompt']}\nA: {r['text']}" for r in rows)


def _format_existing(existing: list[dict]) -> str:
    if not existing:
        return "(none yet)"
    return "\n".join(f"- {e['type']} | {e['label']} | {e['status']} | {e['evidence_count']} excerpt(s): {e['summary']}" for e in existing)


def extract_insights(name: str, household: str, scope: str, rows: list[dict], existing: list[dict]) -> tuple[list[dict], bool]:
    """rows: [{answer_id, question_id, module, module_key, section, prompt, text}]; existing: the client's current
    insights [{type, label, summary, status, evidence_count}]. Returns (raw insights, used_llm).
    Raw output still needs validate_insights() before it is trusted."""
    if not DEMO_MODE:
        prompt = (
            f"Client: {name} (planning as: {household})\nScope: {scope}\n"
            f"<existing_insights>\n{_format_existing(existing)}\n</existing_insights>\n"
            f"<answers>\n{_format_answers(rows)}\n</answers>"
        )
        try:
            out = _llm_json(EXTRACT_SYSTEM, prompt, EXTRACT_SCHEMA, effort="medium", max_tokens=6000)
            return list(out.get("insights") or []), True
        except AIUnavailable:
            if STRICT_AI:
                raise  # real clients never receive stand-in insights
    return _demo_extract(rows, existing), False


# --- demo extraction: keyword-grounded, never invents ---------------------------

_SENT = re.compile(r"(?<=[.!?])\s+")
_VAGUE = ("not sure", "don't know", "dont know", "no idea", "i guess", "maybe", "hard to say", "can't say", "nothing comes to mind")
_WORRY = ("worry", "anxious", "afraid", "scared", "guilt", "fear", "stress", "losing everything")
_SCRIPTS = [
    (("never talked", "didn't talk", "taboo", "silence", "not discussed"), "Silence", "Money was not talked about openly in the home you grew up in."),
    (("scarcity", "never enough", "tight", "struggled", "went without"), "Scarcity", "You describe growing up with a sense that there was never quite enough."),
    (("work hard", "hard work", "earned every", "saved everything"), "Hard Work", "You link money to hard work and responsibility, as the adults around you did."),
]
_CONTEXT = [
    ("family_context", "Family", ("daughter", "son", "kids", "children", "wife", "husband", "partner", "parents", "mother", "father", "family"), "Family members appear throughout your answers as the people your wealth is for."),
    ("legacy_themes", "Legacy", ("legacy", "generation", "inherit", "outlast", "after i'm gone", "grandchild", "pass on"), "You speak about what should outlast you and pass to the next generation."),
    ("community_priorities", "Community", ("community", "neighbo", "local", "town", "church", "school district"), "Community shows up as somewhere you belong and want to give back to."),
    ("work_themes", "Work", ("work", "career", "business", "company", "job", "profession"), "Work carries meaning for you beyond its income."),
    ("service_themes", "Service", ("help", "serve", "service", "volunteer", "give back", "mentor", "giving"), "Being useful to others is part of how you describe a good life."),
    ("money_role", "Time & Freedom", ("free", "freedom", "time", "control", "choice", "flexib"), "You associate wealth with having more control over your time and choices."),
    ("money_role", "Security", ("security", "secure", "safe", "stability", "cushion", "protect"), "Money's role for you includes protection and peace of mind."),
]
_GOAL = re.compile(r"\b(i|we) (want|hope|would love|plan|intend|would like) to ([^.!?]{8,80})", re.I)


def _excerpt_for(text: str, words: tuple[str, ...]) -> str:
    for sent in _SENT.split(text):
        if any(w in sent.lower() for w in words):
            return sent.strip()
    return text.strip()[:160]


def _demo_extract(rows: list[dict], existing: list[dict] | None = None) -> list[dict]:
    out: list[dict] = []
    known = {(e["type"], e["label"].casefold()) for e in (existing or [])}

    def add(type_, label, summary, basis, conf, row, excerpt):
        # one line per (type, label) per pass; a repeat adds evidence rather than a new insight
        for o in out:
            if o["type"] == type_ and o["label"].casefold() == label.casefold():
                o["evidence"].append({"answer_id": row["answer_id"], "excerpt": excerpt})
                return
        out.append({"type": type_, "label": label, "summary": summary, "basis": basis, "confidence": conf,
                    "evidence": [{"answer_id": row["answer_id"], "excerpt": excerpt}]})

    for r in rows:
        t = r["text"]
        low = t.lower()
        words = len(t.split())
        if any(v in low for v in ("prefer not", "rather not", "not get into", "skip this", "prefer to skip")):
            add("declined_topic", f"Declined: {r['section'] or r['module']}",
                f"You chose not to go into “{r['prompt'][:60]}…”; that is entirely your call, and it is simply left open.",
                "client_statement", 0.3, r, t.strip()[:160])
            continue
        if words < 6 or any(v in low for v in _VAGUE):
            add("uncertainties", f"Unclear: {r['section'] or r['module']}",
                f"Your answer to “{r['prompt'][:70]}…” was brief or tentative; a little more would help us understand it.",
                "ai_interpretation", 0.3, r, t.strip()[:160])
            continue
        if r.get("question_key") == "purpose_s1_q1" and ("wealth_purpose", "purpose of wealth") not in known:
            add("wealth_purpose", "Purpose of Wealth", f"In your words: “{_SENT.split(t)[0].strip()}”", "client_statement", 0.9, r, _SENT.split(t)[0].strip())
        if r.get("question_key") == "purpose_s1_q2":
            add("meaningful_life_themes", "Meaningful Life", f"You describe a meaningful life as: “{_SENT.split(t)[0].strip()}”", "client_statement", 0.85, r, _SENT.split(t)[0].strip())
        for name, kws, why, prio in VALUE_LIBRARY:
            hits = sum(low.count(w) for w in kws)
            if hits:
                add("personal_values", name, f"Your answers return to {name.lower()}: {why[0].lower() + why[1:]}", "ai_interpretation", min(0.95, 0.6 + 0.1 * hits), r, _excerpt_for(t, kws))
                add("financial_values", prio, f"You want money to fund {prio.lower()}.", "ai_interpretation", min(0.9, 0.55 + 0.1 * hits), r, _excerpt_for(t, kws))
        for cause, kws in CAUSES:
            if any(w in low for w in kws):
                add("philanthropic_interests", cause, f"{cause} is a cause you name directly.", "client_statement", 0.8, r, _excerpt_for(t, kws))
        for type_, label, kws, summary in _CONTEXT:
            if any(w in low for w in kws):
                add(type_, label, summary, "ai_interpretation", 0.7, r, _excerpt_for(t, kws))
        for kws, label, summary in _SCRIPTS:
            if any(w in low for w in kws):
                add("money_story", label, summary, "ai_interpretation", 0.75, r, _excerpt_for(t, kws))
                add("money_beliefs", f"{label} Script", f"An inherited belief: {summary[0].lower() + summary[1:]}", "ai_interpretation", 0.6, r, _excerpt_for(t, kws))
        if any(w in low for w in _WORRY):
            add("emotional_themes", "Worry", "Worry surfaced when you talked about money; security and reassurance seem to matter.", "ai_interpretation", 0.7, r, _excerpt_for(t, _WORRY))
        m = _GOAL.search(t)
        if m:
            add("goals", m.group(3).strip().rstrip(",;")[:60].title(), f"You say you {m.group(2).lower()} to {m.group(3).strip()}.", "client_statement", 0.8, r, m.group(0).strip())
    # tensions: freedom and obligation/security both present in the same scope
    joined = " ".join(r["text"].lower() for r in rows)
    if any(w in joined for w in ("freedom", "my own time", "independence")) and any(w in joined for w in ("obligation", "duty", "expected", "security", "afraid", "worry")):
        a = next(r for r in rows if any(w in r["text"].lower() for w in ("freedom", "my own time", "independence")))
        b = next(r for r in rows if any(w in r["text"].lower() for w in ("obligation", "duty", "expected", "security", "afraid", "worry")))
        out.append({"type": "tensions", "label": "Freedom vs. Security", "summary": "You describe wanting freedom and, at the same time, feeling held by obligation or the need for security.",
                    "basis": "ai_interpretation", "confidence": 0.65,
                    "evidence": [{"answer_id": a["answer_id"], "excerpt": _excerpt_for(a["text"], ("freedom", "my own time", "independence"))},
                                 {"answer_id": b["answer_id"], "excerpt": _excerpt_for(b["text"], ("obligation", "duty", "expected", "security", "afraid", "worry"))}]})
    if not any(i["type"] not in OPEN_TYPES for i in out) and rows:
        out.append({"type": "open_questions", "label": "What Matters Most", "summary": "We could not yet tell what matters most to you from these answers; it would help to hear a specific example.",
                    "basis": "ai_interpretation", "confidence": 0.3, "evidence": []})
    return out


# ---------------------------------------------------------------------------
# C. Synthesis engine

SECTION_KEYS = ["vision", "money_role", "purpose_of_wealth", "personal_values", "financial_values", "meaningful_life", "family_legacy", "community_philanthropy", "money_story"]
SECTION_TITLES = {
    "vision": "Vision", "money_role": "Money's Role", "purpose_of_wealth": "Purpose of Wealth", "personal_values": "Personal Values",
    "financial_values": "Financial Values", "meaningful_life": "Meaningful Life", "family_legacy": "Family / Legacy Themes",
    "community_philanthropy": "Community / Philanthropic Purpose", "money_story": "Money Story / Money Scripts",
}
_SECTION = _obj(text=_STR, insight_ids={"type": "array", "items": {"type": "integer"}})
SYNTH_SCHEMA = _obj(**{k: _SECTION for k in SECTION_KEYS}, accountability_measures=_STRS)

SYNTH_SYSTEM = f"""You draft a Wealth Purpose Statement for a client of a private wealth advisory firm, from a list of \
insights that were extracted from the client's own discovery answers and reviewed by the client.

{PHILOSOPHY}

Write nine sections, each two to four sentences, warm and specific, never generic:
vision · money_role · purpose_of_wealth · personal_values · financial_values · meaningful_life · family_legacy · \
community_philanthropy · money_story.
For each section list the insight ids you drew on.

Voice: the prompt states the household. For an individual use "I / my" throughout. For a couple or a family use \
"we / our" throughout. Never mix the two.

Rules:
- Use only the insights provided; they have already been filtered to what the client confirmed or corrected and to \
well-evidenced findings. Where a client correction is given, the client's words override the AI summary.
- A section needs real support: at least one confirmed or corrected insight, or two well-evidenced ones. If it \
does not have that, write exactly one sentence beginning "Needs clarification:" that says what is missing. Never \
turn thin or hedged material into polished certainty, and never present a reluctance to answer as a value.
- accountability_measures: three questions the client could ask themselves each year to check their financial life \
is living up to the statement.
- This is a draft for the client to refine. No investment, tax, legal or estate recommendations, no products, no numbers."""


def _format_insights(insights: list[dict]) -> str:
    lines = []
    for i in insights:
        line = f"#{i['id']} [{i['type']} | {i['status']} | {i['basis']} | confidence {i['confidence']:.2f} | {len(i.get('evidence') or [])} excerpt(s)] {i['label']} — {i['summary']}"
        if i.get("client_correction"):
            line += f"  (Client correction: {i['client_correction']})"
        lines.append(line)
    return "\n".join(lines) or "(no insights yet)"


def synthesize_purpose(name: str, household: str, insights: list[dict]) -> tuple[dict, bool]:
    """insights: payload dicts (id, type, label, summary, basis, confidence, status, client_correction)."""
    if not DEMO_MODE:
        prompt = f"Client: {name}\nPlanning as: {household}\n<insights>\n{_format_insights(insights)}\n</insights>"
        try:
            return _llm_json(SYNTH_SYSTEM, prompt, SYNTH_SCHEMA, effort="medium", max_tokens=5000), True
        except AIUnavailable:
            if STRICT_AI:
                raise
    return _demo_synthesize(household, insights), False


def _demo_synthesize(household: str, insights: list[dict]) -> dict:
    my, me = ("Our", "us") if household in ("couple", "family") else ("My", "me")
    usable = list(insights)  # already gated by insights.usable_for_synthesis
    by = {}
    for i in usable:
        by.setdefault(i["type"], []).append(i)

    def text_of(i):  # the client's correction overrides the AI summary
        return i["client_correction"] if i.get("client_correction") else i["summary"]

    def section(types, template, missing):
        items = [i for t in types for i in by.get(t, [])][:4]
        if not items:
            return {"text": f"Needs clarification: {missing}", "insight_ids": []}
        body = " ".join(text_of(i) for i in items)
        return {"text": template.format(labels=", ".join(i["label"].lower() for i in items), body=body), "insight_ids": [i["id"] for i in items]}

    return {
        "vision": section(("meaningful_life_themes", "goals"), f"{my} wealth exists to support a life centred on {{labels}}. {{body}}", "what a fully aligned life looks like has not yet come through clearly."),
        "money_role": section(("money_role", "emotional_themes"), f"For {me}, money's role is {{labels}}. {{body}}", "the role money plays day to day was not described."),
        "purpose_of_wealth": section(("wealth_purpose",), "{body}", "the purpose of the wealth has not been stated in the client's own words."),
        "personal_values": section(("personal_values",), f"{my} core values are {{labels}}. {{body}}", "no recurring personal values were identified yet."),
        "financial_values": section(("financial_values",), f"{my} money should fund {{labels}} first. {{body}}", "what the money should fund first is not yet clear."),
        "meaningful_life": section(("meaningful_life_themes", "work_themes"), "{body}", "a picture of a meaningful life is still missing."),
        "family_legacy": section(("family_context", "legacy_themes"), "{body}", "family and legacy themes have not surfaced yet."),
        "community_philanthropy": section(("community_priorities", "philanthropic_interests", "service_themes"), "{body}", "no community or philanthropic focus was named."),
        "money_story": section(("money_story", "money_beliefs"), "{body}", "the family money story has not been shared."),
        "accountability_measures": [
            f"Did {my.lower()} spending this year reflect what {me} said matters most?",
            "Can we explain how each part of our financial life connects to this statement?",
            "Did we revisit this statement together with our advisor?",
        ],
    }

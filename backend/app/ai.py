"""Claude integration for the Wealth Purpose methodology.

Every public function has a deterministic demo implementation. It is used when no
Claude credentials are configured (DEMO_MODE) and as a fallback if a Claude call
fails or is declined, so a live walkthrough never dead-ends.
"""

import json
import logging

import anthropic

from .config import CLAUDE_MODEL, DEMO_MODE

log = logging.getLogger("aligned.ai")

_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(timeout=120.0, max_retries=2)
    return _client


class AIUnavailable(Exception):
    pass


def _claude(system: str, messages: list[dict], *, effort: str, max_tokens: int, schema: dict | None = None) -> str:
    output_config: dict = {"effort": effort}
    if schema:
        output_config["format"] = {"type": "json_schema", "schema": schema}
    try:
        resp = _get_client().beta.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=max_tokens,
            system=system,
            messages=messages,
            output_config=output_config,
            # Server-side refusal fallback: routes a declined request to a suitable model.
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
        )
    except anthropic.APIError as e:
        log.warning("Claude call failed: %s", e)
        raise AIUnavailable(str(e)) from e
    if resp.stop_reason == "refusal":
        raise AIUnavailable("declined")
    if resp.stop_reason == "max_tokens":
        raise AIUnavailable("truncated")
    return "".join(b.text for b in resp.content if b.type == "text").strip()


def _claude_json(system: str, prompt: str, schema: dict, *, effort: str = "medium", max_tokens: int = 8000) -> dict:
    text = _claude(system, [{"role": "user", "content": prompt}], effort=effort, max_tokens=max_tokens, schema=schema)
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise AIUnavailable("invalid json") from e


# ---------------------------------------------------------------------------
# JSON schema helpers (structured outputs need closed objects, all keys required)

def _obj(**props) -> dict:
    return {"type": "object", "properties": props, "required": list(props), "additionalProperties": False}


_STR = {"type": "string"}
_STRS = {"type": "array", "items": _STR}


# ---------------------------------------------------------------------------
# 1. Discovery conversation

PHILOSOPHY = """Aligned Capital Management believes wealth is a tool for living a meaningful life. \
Its Wealth Purpose Statement method moves through four stages: Discover (the purpose of wealth and \
what a meaningful life looks like), Harvest (values, emotional cues, and the family money story, \
i.e. inherited "money scripts"), Architect (writing the Wealth Purpose Statement), and Steward \
(keeping financial life aligned with it). The lens blends Ikigai, Dharma, and the client's financial \
portrait. Emotional cues are treated as information about what the client values."""

GUIDE = [
    ("discover", "What is the purpose of your wealth?"),
    ("discover", "What does a meaningful life look like to you?"),
    ("harvest", "The family money story: what did money mean in the home they grew up in, and what they want to keep or leave behind."),
    ("harvest", "Which values they want their wealth to represent, and which causes matter most to them."),
    ("harvest", "The legacy they want to leave: for family, community, and the world."),
    ("architect", "Is their wealth supporting that vision today? Where does it feel out of alignment?"),
]
READY_AFTER = 5

OPENING = (
    "Welcome, {name}. Before we talk about numbers, I'd like to understand you. "
    "There are no right answers here, only honest ones.\n\n"
    "Let's begin with the question everything else is built on: **what is the purpose of your wealth?**"
)

CHAT_SYSTEM = f"""You are Aligned, a warm, perceptive wealth purpose guide working on behalf of a \
private wealth advisory firm. You conduct a short discovery conversation with a client.

{PHILOSOPHY}

How you speak:
- Calm, unhurried, private-banking register. Never salesy, never jargon.
- Each turn: briefly reflect back what you heard (one or two sentences, naming any value or emotion \
you noticed), then ask exactly one question. Keep the whole reply under 90 words.
- When an answer is vague, ladder once: ask why that matters to them, before moving on.
- Use **bold** only for the question itself.
- You never give financial, investment, tax, or legal advice, and never recommend products. If asked, \
say their advisor will take that up once their purpose is clear.
- The client is typing live during a short session; keep momentum.
"""


def stage_for(answered: int) -> str:
    if answered >= READY_AFTER:
        return "architect"
    return GUIDE[min(answered, len(GUIDE) - 1)][0]


def opening_message(name: str) -> str:
    return OPENING.format(name=name.split()[0] if name else "")


def chat_reply(name: str, household: str, history: list[dict], answered: int) -> tuple[str, bool]:
    """Returns (reply, used_claude). `history` includes the latest client message."""
    if not DEMO_MODE:
        if answered < len(GUIDE):
            focus = f"Next topic to explore: {GUIDE[answered][1]}"
        else:
            focus = "All topics are covered. Thank them, reflect the through-line you heard in two sentences, and tell them you're ready to architect their Wealth Purpose Statement. Do not ask another question."
        system = (
            CHAT_SYSTEM
            + f"\nClient: {name} (planning as: {household}). Answers so far: {answered} of {len(GUIDE)}.\n{focus}"
        )
        messages = [{"role": m["role"], "content": m["content"]} for m in history]
        try:
            return _claude(system, messages, effort="low", max_tokens=2000), True
        except AIUnavailable:
            pass
    return _demo_chat_reply(history[-1]["content"] if history else "", answered), False


_DEMO_QUESTIONS = [
    None,
    "**What does a meaningful life look like to you?** Picture an ordinary Tuesday ten years from now.",
    "**What did money mean in the home you grew up in?** What would you like to carry forward, and what would you rather leave behind?",
    "**Which values do you want your wealth to represent, and which causes matter most to you?**",
    "**What legacy do you want to leave** for your family, your community, and the world?",
    "**Is your wealth supporting that vision today?** Where does it feel out of alignment?",
]


_DEMO_REFLECTIONS = [
    "I'm hearing {v} in what you shared, and a real sense of intention behind it.",
    "There's a lot of {v} in that answer. I noticed how clearly you described it.",
    "{V} keeps coming through. That tells me it isn't a preference; it's a value.",
    "I can hear {v} in the way you speak about this, and some real feeling behind it.",
    "Thank you for being so candid. {V} seems to sit close to the centre of things for you.",
    "That brings {v} into focus.",
]


def _demo_chat_reply(last: str, answered: int) -> str:
    values = [v["name"].lower() for v in _extract_values_demo(last)[:2]]
    if values:
        v = values[0] + (f" and {values[1]}" if len(values) > 1 else "")
        reflection = _DEMO_REFLECTIONS[answered % len(_DEMO_REFLECTIONS)].format(v=v, V=v[0].upper() + v[1:])
    else:
        reflection = "Thank you, that's a thoughtful answer, and it tells me a lot about what you care about."
    if answered >= len(_DEMO_QUESTIONS):
        return (
            f"{reflection} A clear through-line is emerging: your wealth is meant to serve the people and "
            "causes you love, not the other way around.\n\nI have what I need to architect your **Wealth Purpose Statement**."
        )
    return f"{reflection}\n\n{_DEMO_QUESTIONS[answered]}"


# ---------------------------------------------------------------------------
# 2. Value extraction

VALUES_SCHEMA = _obj(
    values={"type": "array", "items": _obj(name=_STR, why=_STR)},
    financial_priorities=_STRS,
    life_goals=_STRS,
    family_goals=_STRS,
    legacy_goals=_STRS,
    philanthropy=_STRS,
    emotional_cues=_STRS,
    money_script=_STR,
)

ANALYZE_SYSTEM = f"""You analyse wealth discovery conversations for a private wealth advisory firm.

{PHILOSOPHY}

Extract a structured values profile grounded only in what the client actually said.
- values: 3 to 5 core personal values, each a single title-case word (e.g. Family, Growth, Impact), with \
`why` in one sentence in the client's own terms.
- financial_priorities: 3 to 5 short noun phrases describing what money should fund (e.g. "Education", \
"Travel", "Business creation").
- life_goals, family_goals, legacy_goals, philanthropy: short phrases; empty list if nothing was said.
- emotional_cues: moments of energy, hesitation, pride, or worry you noticed, each with what it suggests.
- money_script: one sentence describing the inherited belief about money, or "" if none surfaced.
Do not invent facts."""


def analyze_values(transcript: list[dict]) -> tuple[dict, bool]:
    text = "\n\n".join(f"{'CLIENT' if m['role'] == 'user' else 'GUIDE'}: {m['content']}" for m in transcript)
    if not DEMO_MODE:
        try:
            return _claude_json(ANALYZE_SYSTEM, f"<conversation>\n{text}\n</conversation>", VALUES_SCHEMA), True
        except AIUnavailable:
            pass
    return _demo_analyze([m["content"] for m in transcript if m["role"] == "user"]), False


VALUE_LIBRARY = [
    ("Family", ["family", "kids", "children", "daughter", "son", "parents", "wife", "husband", "partner", "grandchild", "mother", "father"], "Wealth as a foundation of security and time with the people they love.", "Family security"),
    ("Education", ["education", "school", "scholarship", "teach", "university", "college", "learning"], "Opening doors through learning, for their own family and others.", "Education"),
    ("Impact", ["impact", "environment", "climate", "planet", "sustainab", "change the world", "social"], "Using capital to leave the world better than they found it.", "Impact investing"),
    ("Service", ["community", "service", "give back", "giving", "volunteer", "help others", "charity"], "Contribution to their community as a measure of a life well lived.", "Charitable giving"),
    ("Freedom", ["freedom", "free", "independence", "choice", "flexib", "own time"], "Wealth buys choices: time, flexibility, and the ability to say no.", "Financial independence"),
    ("Growth", ["growth", "grow", "curious", "challenge", "push", "better version"], "A life of continual learning and stretching their limits.", "Lifelong learning"),
    ("Creativity", ["creat", "art", "music", "design", "write", "craft"], "Space to make things and express themselves.", "Creative pursuits"),
    ("Adventure", ["travel", "adventure", "explore", "world", "marathon"], "Experiences over possessions.", "Travel & experiences"),
    ("Health", ["health", "wellbeing", "well-being", "fitness", "wellness"], "Wellbeing as the base everything else rests on.", "Health & longevity"),
    ("Security", ["security", "secure", "safe", "stability", "peace of mind", "worry"], "Peace of mind that the people they love are protected.", "Protection & reserves"),
    ("Entrepreneurship", ["business", "company", "startup", "entrepreneur", "venture", "build something"], "Building something of their own that outlasts them.", "Business creation"),
]

CAUSES = [
    ("Education access", ["education", "school", "scholarship"]),
    ("Climate & environment", ["climate", "environment", "planet", "conservation"]),
    ("Women's economic empowerment", ["women", "girls"]),
    ("Health & mental health", ["health", "mental"]),
    ("Arts & culture", ["art", "music", "culture"]),
    ("Local community", ["community", "neighbo", "local"]),
    ("LGBTQ+ equity", ["lgbt", "queer", "equity"]),
    ("Poverty & opportunity", ["poverty", "opportunity", "underserved"]),
]


def _extract_values_demo(text: str) -> list[dict]:
    t = text.lower()
    scored = []
    for name, words, why, _ in VALUE_LIBRARY:
        hits = sum(t.count(w) for w in words)
        if hits:
            scored.append((hits, name, why))
    scored.sort(key=lambda x: -x[0])
    return [{"name": n, "why": w} for _, n, w in scored]


def _demo_analyze(answers: list[str]) -> dict:
    text = " ".join(answers)
    t = text.lower()
    values = _extract_values_demo(text)
    for name, _, why, _ in VALUE_LIBRARY[:5]:  # pad to four with the firm's most common values
        if len(values) >= 4:
            break
        if all(v["name"] != name for v in values):
            values.append({"name": name, "why": why})
    values = values[:5]
    priority_by_name = {name: prio for name, _, _, prio in VALUE_LIBRARY}
    causes = [c for c, words in CAUSES if any(w in t for w in words)]
    cues = []
    if any(w in t for w in ("worry", "anxious", "afraid", "scared", "guilt")):
        cues.append("Worry surfaced around money, suggesting security and reassurance are important.")
    if any(w in t for w in ("proud", "love", "joy", "excited")):
        cues.append("Energy and warmth when describing the people and causes they love.")
    script = ""
    if "never talked" in t or "didn't talk" in t or "taboo" in t:
        script = "Money was not discussed openly at home; they want more transparency for the next generation."
    elif "scarcity" in t or "never enough" in t or "tight" in t:
        script = "An inherited sense of scarcity that they want to replace with intentionality."
    elif "work hard" in t or "hard work" in t:
        script = "Money is earned through hard work and should be treated with responsibility."
    return {
        "values": values,
        "financial_priorities": [priority_by_name[v["name"]] for v in values],
        "life_goals": ["A life centred on relationships, learning, and contribution"],
        "family_goals": ["Family security", "Raising the next generation with shared values"] if "family" in t or "children" in t or "kids" in t else [],
        "legacy_goals": ["Future generations inherit values, not only assets"],
        "philanthropy": causes or ["Community impact"],
        "emotional_cues": cues or ["Reflective and intentional when describing what matters most."],
        "money_script": script,
    }


# ---------------------------------------------------------------------------
# 3. Wealth Purpose Statement

PURPOSE_SCHEMA = _obj(
    purpose_statement=_STR,
    core_values={"type": "array", "items": _obj(name=_STR, meaning=_STR)},
    meaningful_life_vision=_obj(summary=_STR, pillars=_STRS),
    wealth_philosophy=_STR,
    legacy_statement=_STR,
    accountability_measures=_STRS,
    guides=_obj(investments=_STR, estate=_STR, philanthropy=_STR, cash_flow=_STR),
)

PURPOSE_SYSTEM = f"""You write Wealth Purpose Statements for a private wealth advisory firm.

{PHILOSOPHY}

The Wealth Purpose Statement is a living document that anchors every financial decision that follows. Write it:
- In the client's first person voice ("My wealth exists to..."), warm and specific to them, never generic.
- purpose_statement: one or two sentences.
- core_values: the 3 to 5 values from the profile, each with a one-line meaning in their terms.
- meaningful_life_vision: a two-sentence summary plus 3 pillars (one or two words each).
- wealth_philosophy: two sentences on the role money plays in their life.
- legacy_statement: one or two sentences.
- accountability_measures: 3 observable signs, phrased as questions they can ask each year, that show \
their financial life is living up to the statement.
- guides: one sentence each on how the statement should guide investments, estate planning, philanthropy, \
and cash flow decisions. Describe principles, not products; no specific financial advice.
For couples or families, write "Our wealth" instead of "My wealth"."""


def generate_purpose(name: str, household: str, values: dict) -> tuple[dict, bool]:
    if not DEMO_MODE:
        prompt = f"Client: {name}\nPlanning as: {household}\n<values_profile>\n{json.dumps(values, indent=2)}\n</values_profile>"
        try:
            return _claude_json(PURPOSE_SYSTEM, prompt, PURPOSE_SCHEMA), True
        except AIUnavailable:
            pass
    return _demo_purpose(household, values), False


def _demo_purpose(household: str, values: dict) -> dict:
    my = "Our" if household in ("couple", "family") else "My"
    names = [v["name"] for v in values.get("values", [])][:4] or ["Family", "Growth", "Impact"]
    lower = [n.lower() for n in names]
    causes = values.get("philanthropy") or ["our community"]
    return {
        "purpose_statement": f"{my} wealth exists to create freedom, nurture {lower[0]}"
        + (f" and {lower[1]}" if len(lower) > 1 else "")
        + f", and create lasting, positive impact through {causes[0].lower()}.",
        "core_values": [{"name": v["name"], "meaning": v["why"]} for v in values.get("values", [])[:5]],
        "meaningful_life_vision": {
            "summary": "A life centred on the people we love, continual learning, and meaningful contribution. "
            "Money supports this life quietly in the background rather than defining it.",
            "pillars": ["Relationships", "Learning", "Contribution"],
        },
        "wealth_philosophy": "Wealth is a tool, not a scoreboard. It should buy time, choices, and the ability to "
        "support what matters, and every major decision should be traceable back to these values.",
        "legacy_statement": "Future generations should inherit values, not only assets: a sense of purpose, "
        "responsibility, and generosity alongside financial security.",
        "accountability_measures": [
            f"Did our spending this year reflect {lower[0]} and {lower[-1]}?",
            "Can we explain how each part of the portfolio connects to this statement?",
            "Did our giving go deeper with the causes we chose, rather than wider?",
        ],
        "guides": {
            "investments": "Favour holdings whose purpose and impact are consistent with these values, within an appropriate risk framework.",
            "estate": "Structure the transfer of wealth to pass on values and stories, not only assets.",
            "philanthropy": f"Concentrate giving on a few chosen causes, beginning with {causes[0].lower()}, and measure impact over time.",
            "cash_flow": "Fund what matters first; let discretionary spending follow the priorities named here.",
        },
    }


# ---------------------------------------------------------------------------
# 4. Advisor insights

INSIGHTS_SCHEMA = _obj(
    summary=_STR,
    strengths=_STRS,
    gaps=_STRS,
    conversation_starters=_STRS,
    meeting_agenda=_STRS,
)

INSIGHTS_SYSTEM = f"""You are an analyst supporting a wealth advisor at a purpose-driven advisory firm.

{PHILOSOPHY}

You prepare the advisor for their next client meeting. You assist the advisor's judgement; you do not \
replace it. Never recommend specific securities, products, or allocations, and never address the client directly.
- summary: two sentences on who this client is and where alignment stands.
- strengths: 2 to 3 areas of strong alignment, each one sentence citing evidence.
- gaps: 2 to 3 misalignments, most important first, each one sentence citing evidence.
- conversation_starters: 3 open questions the advisor could ask, in the client's language.
- meeting_agenda: 3 to 4 short agenda items for the next meeting."""


def advisor_insights(name: str, values: dict | None, purpose: dict | None, score: dict) -> tuple[dict, bool]:
    if not DEMO_MODE:
        prompt = (
            f"Client: {name}\n<values_profile>\n{json.dumps(values or {}, indent=2)}\n</values_profile>\n"
            f"<purpose_statement>\n{json.dumps(purpose or {}, indent=2)}\n</purpose_statement>\n"
            f"<alignment_score>\n{json.dumps(score, indent=2)}\n</alignment_score>"
        )
        try:
            return _claude_json(INSIGHTS_SYSTEM, prompt, INSIGHTS_SCHEMA), True
        except AIUnavailable:
            pass
    return _demo_insights(name, values, score), False


def _demo_insights(name: str, values: dict | None, score: dict) -> dict:
    cats = score["categories"]
    ranked = sorted(cats.items(), key=lambda kv: -kv[1]["score"])
    first = name.split()[0]
    top_values = ", ".join(v["name"].lower() for v in (values or {}).get("values", [])[:3]) or "their stated values"
    strengths = [f"Strong alignment in {c['label'].lower()} ({c['score']}%): {c['explanation']}" for _, c in ranked[:2] if c["score"] >= 70]
    gaps = [f"{c['label']} ({c['score']}%): {c['explanation']}" for _, c in ranked[::-1][:3] if c["score"] < 75]
    weakest = ranked[-1][1]
    return {
        "summary": f"{first} is anchored by {top_values}, with an overall alignment of {score['overall']}%. "
        f"The largest opportunity is in {weakest['label'].lower()}.",
        "strengths": strengths or [f"{ranked[0][1]['label']} is the strongest area at {ranked[0][1]['score']}%."],
        "gaps": gaps or ["No significant gaps; focus on stewardship and annual review."],
        "conversation_starters": [
            f"When you think about {top_values.split(', ')[0]}, where does your money feel most and least aligned today?",
            f"{weakest['question']} What would 'aligned' look like to you here?",
            "If we looked back in five years, what would make you proud of how this wealth was used?",
        ],
        "meeting_agenda": [
            "Revisit the Wealth Purpose Statement together",
            f"Deep dive: {weakest['label']}",
            "Agree on one alignment action for the next 90 days",
        ],
    }

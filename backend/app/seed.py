"""Demo book of business so the advisor view is populated on first run.

All clients are fictional.
"""

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import ai, scoring
from .models import AdvisorNote, AlignmentScore, Conversation, PurposeStatement, User, ValueProfile
from .schemas import FinancialPortrait

SARAH_TRANSCRIPT = [
    ("assistant", ai.opening_message("Sarah Johnson")),
    ("user", "Honestly, I've never framed it that way. I think it exists to give my kids the education and choices I had to fight for, and to do something real about climate."),
    ("assistant", "I'm hearing education as a door you want to hold open for your children, and a sense of responsibility to the planet.\n\n**What does a meaningful life look like to you?**"),
    ("user", "Time with my two daughters, teaching, being outdoors. Mentoring young women in science. Not being chained to a job I don't believe in."),
    ("assistant", "Freedom, family, and passing knowledge on. There's real warmth when you talk about mentoring.\n\n**What did money mean in the home you grew up in?**"),
    ("user", "My parents were teachers. Money was tight and we never talked about it. I want my girls to understand it, not fear it."),
    ("assistant", "You want to replace silence with openness for the next generation.\n\n**Which values do you want your wealth to represent, and which causes matter most?**"),
    ("user", "Education, the environment, and family. Girls in STEM and climate resilience are the causes I care about."),
    ("assistant", "**What legacy do you want to leave?**"),
    ("user", "That my daughters are generous and curious, and that a few thousand kids got a science education because of us."),
]

SARAH_VALUES = {
    "values": [
        {"name": "Education", "why": "Holding open the doors she had to fight to walk through."},
        {"name": "Impact", "why": "Doing something real about climate in her lifetime."},
        {"name": "Family", "why": "Time with her two daughters and raising them to be generous and curious."},
        {"name": "Freedom", "why": "Never being chained to work she doesn't believe in."},
    ],
    "financial_priorities": ["Education", "Impact investing", "Charitable giving", "Financial independence"],
    "life_goals": ["Teaching and mentoring young women in science", "Time outdoors"],
    "family_goals": ["Fund daughters' education", "Raise daughters to understand money, not fear it"],
    "legacy_goals": ["Generous, curious daughters", "Thousands of children reached with science education"],
    "philanthropy": ["Girls in STEM", "Climate resilience"],
    "emotional_cues": ["Warmth and energy when discussing mentoring", "Tension recalling money silence growing up"],
    "money_script": "Money was scarce and unspoken at home; she wants openness and confidence for her daughters.",
}

SARAH_PURPOSE = {
    "purpose_statement": "My wealth exists to open doors through education, give my daughters freedom and confidence with money, and create lasting environmental impact.",
    "core_values": [
        {"name": "Education", "meaning": "Every generation should have more doors open than the last."},
        {"name": "Impact", "meaning": "Capital should leave the climate better than it found it."},
        {"name": "Family", "meaning": "Time and openness with my daughters come first."},
        {"name": "Freedom", "meaning": "Money buys the choice to do work I believe in."},
    ],
    "meaningful_life_vision": {
        "summary": "A life of teaching, time outdoors, and raising curious, generous daughters. Money works quietly in the background so that I can say yes to what matters.",
        "pillars": ["Learning", "Family", "Stewardship"],
    },
    "wealth_philosophy": "Money was never talked about in my home; in mine, it will be a tool we understand and use with intention. It should buy freedom and fund impact, not anxiety.",
    "legacy_statement": "My daughters inherit curiosity and generosity along with security, and thousands of young people gain access to science because of what we built.",
    "accountability_measures": [
        "Did we fund education (ours and others') before discretionary spending this year?",
        "Can I explain how the portfolio supports climate resilience?",
        "Have the girls been part of at least one real conversation about our money this year?",
    ],
    "guides": {
        "investments": "Prefer strategies with measurable environmental outcomes, within a risk framework that protects education funding.",
        "estate": "Pair the estate plan with a legacy letter so the story behind the wealth is passed on.",
        "philanthropy": "Concentrate giving on girls in STEM and climate resilience, and track outcomes each year.",
        "cash_flow": "Fund education, mentoring time, and giving first; let lifestyle spending follow.",
    },
}

SARAH_PORTRAIT = FinancialPortrait(
    spending_on_priorities_pct=85, has_spending_plan=True,
    values_aligned_allocation_pct=18, portfolio_values_review="partly",
    has_will=True, has_trust=True, has_legacy_letter=False, family_conversations="regular",
    annual_giving_pct=4, giving_alignment="intentional", has_giving_vehicle=True,
    emergency_reserve_months=9, insurance_reviewed_recently=False, concentrated_position=False,
)

MEHTA_ANSWERS = [
    "We want our wealth to keep our family close and to give back to the community that raised us.",
    "Travel with our kids, time with our parents, and building a business together one day.",
    "Priya's family worked hard and saved everything. Mine never talked about money at all.",
    "Family, community, and entrepreneurship. Education access and local community causes.",
]


def seed(db: Session) -> None:
    if db.scalars(select(User).where(User.role == "advisor")).first():
        return
    now = datetime.now(timezone.utc)
    advisor = User(name="Aligned Advisory Team", role="advisor", email="advisor@example.com")
    db.add(advisor)
    db.flush()

    # 1. Fully onboarded client
    sarah = User(name="Sarah Johnson", household_type="family", advisor_id=advisor.id, created_at=now - timedelta(days=12))
    db.add(sarah)
    db.flush()
    db.add(Conversation(
        user_id=sarah.id, status="complete",
        messages=[{"role": r, "content": c, "stage": ai.stage_for(i // 2)} for i, (r, c) in enumerate(SARAH_TRANSCRIPT)],
    ))
    db.add(ValueProfile(user_id=sarah.id, data=SARAH_VALUES))
    db.add(PurposeStatement(user_id=sarah.id, data=SARAH_PURPOSE))
    result = scoring.calculate(SARAH_PORTRAIT, SARAH_VALUES)
    insights = {
        "summary": "Sarah is a purpose-led parent anchored by education, climate impact, and openness with her daughters. "
        f"Overall alignment is {result['overall']}%, strongest in cash flow and estate, with the portfolio lagging her climate values.",
        "strengths": [
            "Strong alignment in spending: 85% of discretionary spending goes to education, family, and giving, guided by a written plan.",
            "Giving is intentional and concentrated on girls in STEM and climate resilience through a donor-advised fund.",
        ],
        "gaps": [
            "Portfolio lacks values-aligned allocation: 18% versus the emphasis she places on climate impact.",
            "Estate purpose document incomplete: no legacy letter to carry the family money story forward.",
            "Insurance has not been reviewed recently despite two dependants.",
        ],
        "conversation_starters": [
            "You said you want to do something real about climate. How much of that do you want your portfolio to carry, versus your giving?",
            "What would you want your daughters to read in a letter about why this money exists?",
            "If something happened tomorrow, what would you want to be certain is protected?",
        ],
        "meeting_agenda": [
            "Revisit the Wealth Purpose Statement",
            "Discuss investment alignment and climate goals",
            "Begin a legacy letter together",
            "Schedule an insurance review",
        ],
        "generated_by": "seed",
    }
    db.add(AlignmentScore(
        user_id=sarah.id, overall=result["overall"],
        categories={**result["categories"], "_meta": {"themes": result["themes"], "weighting_rationale": result["weighting_rationale"]}},
        portrait=SARAH_PORTRAIT.model_dump(), insights=insights,
    ))
    db.add(AdvisorNote(client_id=sarah.id, advisor_id=advisor.id, body="Intro call went well. Sarah lit up talking about mentoring; open to a family meeting with the girls in spring."))

    # 2. Couple with a statement, portrait not yet completed
    mehta = User(name="Daniel & Priya Mehta", household_type="couple", advisor_id=advisor.id, created_at=now - timedelta(days=4))
    db.add(mehta)
    db.flush()
    values = ai._demo_analyze(MEHTA_ANSWERS)
    msgs = [{"role": "assistant", "content": ai.opening_message("Daniel"), "stage": "discover"}]
    for i, a in enumerate(MEHTA_ANSWERS):
        msgs.append({"role": "user", "content": a, "stage": ai.stage_for(i)})
        msgs.append({"role": "assistant", "content": ai._demo_chat_reply(a, i + 1), "stage": ai.stage_for(i + 1)})
    db.add(Conversation(user_id=mehta.id, status="complete", messages=msgs))
    db.add(ValueProfile(user_id=mehta.id, data=values))
    db.add(PurposeStatement(user_id=mehta.id, data=ai._demo_purpose("couple", values)))

    # 3. Prospect mid-discovery
    james = User(name="James Whitfield", household_type="individual", advisor_id=advisor.id, created_at=now - timedelta(days=1))
    db.add(james)
    db.flush()
    db.add(Conversation(user_id=james.id, messages=[
        {"role": "assistant", "content": ai.opening_message("James"), "stage": "discover"},
        {"role": "user", "content": "I sold my company last year. I honestly don't know what the money is for yet.", "stage": "discover"},
        {"role": "assistant", "content": ai._demo_chat_reply("", 1), "stage": "discover"},
    ]))
    db.commit()

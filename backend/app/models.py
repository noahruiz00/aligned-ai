from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str | None] = mapped_column(String(200), nullable=True)
    role: Mapped[str] = mapped_column(String(20), default="client")  # client | advisor
    household_type: Mapped[str] = mapped_column(String(20), default="individual")  # individual | couple | family
    advisor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    conversations: Mapped[list["Conversation"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    # [{"role": "user"|"assistant", "content": str, "stage": str}]
    messages: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(20), default="active")  # active | complete
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    user: Mapped[User] = relationship(back_populates="conversations")


class ValueProfile(Base):
    """Structured values extracted from a discovery conversation (the "Values" table)."""

    __tablename__ = "values"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    conversation_id: Mapped[int | None] = mapped_column(ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True)
    data: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class PurposeStatement(Base):
    __tablename__ = "purpose_statements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    data: Mapped[dict] = mapped_column(JSON)  # legacy shape (purpose_statement, core_values, ...), derived from `sections` for new drafts
    # {vision|money_role|purpose_of_wealth|personal_values|financial_values|meaningful_life|family_legacy|
    #  community_philanthropy|money_story: {text, insight_ids}}  -- DRAFT generated from discovery insights
    sections: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="draft")  # draft | legacy
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AlignmentScore(Base):
    __tablename__ = "alignment_scores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    overall: Mapped[int] = mapped_column(Integer)
    categories: Mapped[dict] = mapped_column(JSON)  # {key: {score, label, question, explanation, recommendations}}
    portrait: Mapped[dict] = mapped_column(JSON)  # the financial snapshot the score was computed from
    insights: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # AI advisor insights
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AdvisorNote(Base):
    __tablename__ = "advisor_notes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    advisor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


# ---------------------------------------------------------------------------
# Progressive discovery. The methodology (modules and questions) is stored as
# data so the advisor can edit it; sessions and answers are the structured
# record every later insight points back to.


class MethodologyModule(Base):
    __tablename__ = "methodology_modules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(40), unique=True)
    title: Mapped[str] = mapped_column(String(80))
    description: Mapped[str] = mapped_column(Text, default="")  # one line, shown in the stepper
    intro: Mapped[str] = mapped_column(Text, default="")  # shown when the module begins
    order: Mapped[int] = mapped_column(Integer, default=0)
    session_group: Mapped[int] = mapped_column(Integer, default=1)  # suggested sitting; a change of group is a natural pause
    # pool: follow-ups are chosen from this module's `follow_up` questions (the advisor's wording only)
    # compose: the AI may write its own follow-up (used for the beta opening questions, which have no pool)
    follow_up_mode: Mapped[str] = mapped_column(String(10), default="pool")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    questions: Mapped[list["MethodologyQuestion"]] = relationship(
        back_populates="module", cascade="all, delete-orphan", order_by="MethodologyQuestion.order"
    )


class MethodologyQuestion(Base):
    __tablename__ = "methodology_questions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    module_id: Mapped[int] = mapped_column(ForeignKey("methodology_modules.id", ondelete="CASCADE"))
    key: Mapped[str] = mapped_column(String(60), unique=True)
    section: Mapped[str] = mapped_column(String(160), default="")  # heading within the module, verbatim from the methodology
    prompt: Mapped[str] = mapped_column(Text)
    follow_up_guidance: Mapped[str] = mapped_column(Text, default="")  # advisor-facing: what to listen for
    # core: asked in the main flow | follow_up: available to the AI as the follow-up for a core question in the
    # same section | optional: offered as "go deeper" after the module | inactive: kept, never shown to clients
    classification: Mapped[str] = mapped_column(String(12), default="core")
    required: Mapped[bool] = mapped_column(Boolean, default=True)
    max_follow_ups: Mapped[int] = mapped_column(Integer, default=1)
    order: Mapped[int] = mapped_column(Integer, default=0)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    module: Mapped[MethodologyModule] = relationship(back_populates="questions")


class DiscoverySession(Base):
    __tablename__ = "discovery_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    # Unguessable resume token (secrets.token_urlsafe(32)); the only public handle for a session.
    token: Mapped[str | None] = mapped_column(String(64), unique=True, index=True, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active")  # active | paused | complete
    # private | pending_share (client agreed to share; completes on finishing) | shared_with_advisor
    sharing: Mapped[str] = mapped_column(String(24), default="private")
    rejected_insight_count: Mapped[int] = mapped_column(Integer, default=0)  # QA: AI items discarded by validation
    extraction_runs: Mapped[int] = mapped_column(Integer, default=0)
    current_question_id: Mapped[int | None] = mapped_column(ForeignKey("methodology_questions.id", ondelete="SET NULL"), nullable=True)
    # {module_key: {summary, themes: [{name, note}], feedback, correction, generated_by, created_at}}
    module_reflections: Mapped[dict] = mapped_column(JSON, default=dict)
    # modules whose optional questions the client chose to go deeper into
    opted_modules: Mapped[list | None] = mapped_column(JSON, nullable=True)
    # Legacy transcript built on completion so the existing values/purpose pipeline keeps working.
    conversation_id: Mapped[int | None] = mapped_column(ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_activity_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped[User] = relationship()
    answers: Mapped[list["Answer"]] = relationship(back_populates="session", cascade="all, delete-orphan", order_by="Answer.id")


class Answer(Base):
    """One client answer. A follow-up answer points at the answer it elaborates on."""

    __tablename__ = "answers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("discovery_sessions.id", ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    question_id: Mapped[int] = mapped_column(ForeignKey("methodology_questions.id"))
    parent_answer_id: Mapped[int | None] = mapped_column(ForeignKey("answers.id", ondelete="CASCADE"), nullable=True)
    prompt_text: Mapped[str] = mapped_column(Text)  # exact wording shown, so evidence survives later edits to the question
    text: Mapped[str] = mapped_column(Text, default="")
    skipped: Mapped[bool] = mapped_column(Boolean, default=False)
    skip_reason: Mapped[str | None] = mapped_column(String(20), nullable=True)  # skip | prefer_not (never pressed)
    input_mode: Mapped[str] = mapped_column(String(10), default="text")  # text | voice (later)
    ai_reflection: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_follow_up: Mapped[str | None] = mapped_column(Text, nullable=True)  # follow-up question asked after this answer
    follow_up_question_id: Mapped[int | None] = mapped_column(ForeignKey("methodology_questions.id"), nullable=True)  # when it came from the pool
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    session: Mapped[DiscoverySession] = relationship(back_populates="answers")
    question: Mapped[MethodologyQuestion] = relationship(foreign_keys=[question_id])


# ---------------------------------------------------------------------------
# Structured understanding: insights extracted from answers, each linked to the
# answers that support it, with the original AI output and every change kept.

INSIGHT_STATUSES = ("ai_detected", "needs_clarification", "client_confirmed", "client_corrected", "advisor_confirmed")
INSIGHT_BASES = ("client_fact", "client_statement", "ai_interpretation")


class ClientInsight(Base):
    __tablename__ = "client_insights"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    session_id: Mapped[int | None] = mapped_column(ForeignKey("discovery_sessions.id", ondelete="SET NULL"), nullable=True)
    module_key: Mapped[str] = mapped_column(String(40), default="")  # module the insight was first extracted from
    type: Mapped[str] = mapped_column(String(40))
    label: Mapped[str] = mapped_column(String(120))
    summary: Mapped[str] = mapped_column(Text)
    basis: Mapped[str] = mapped_column(String(24), default="ai_interpretation")  # client_fact | client_statement | ai_interpretation
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    status: Mapped[str] = mapped_column(String(24), default="ai_detected")
    original: Mapped[dict] = mapped_column(JSON)  # the AI output as first produced; never edited
    client_feedback: Mapped[str | None] = mapped_column(String(16), nullable=True)  # accurate | partly | edit | clarify
    client_correction: Mapped[str | None] = mapped_column(Text, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)  # False when a later extraction superseded an unconfirmed insight
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    evidence: Mapped[list["EvidenceLink"]] = relationship(back_populates="insight", cascade="all, delete-orphan", order_by="EvidenceLink.id")
    events: Mapped[list["InsightEvent"]] = relationship(cascade="all, delete-orphan", order_by="InsightEvent.id")


class EvidenceLink(Base):
    __tablename__ = "evidence_links"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    insight_id: Mapped[int] = mapped_column(ForeignKey("client_insights.id", ondelete="CASCADE"))
    question_id: Mapped[int] = mapped_column(ForeignKey("methodology_questions.id"))
    answer_id: Mapped[int] = mapped_column(ForeignKey("answers.id", ondelete="CASCADE"))
    module: Mapped[str] = mapped_column(String(80))
    section: Mapped[str] = mapped_column(String(160), default="")
    excerpt: Mapped[str] = mapped_column(Text)  # verbatim from the answer; validated server-side
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    insight: Mapped[ClientInsight] = relationship(back_populates="evidence")


class InsightEvent(Base):
    """Audit trail: what the AI produced, what the client changed, what was merged."""

    __tablename__ = "insight_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    insight_id: Mapped[int] = mapped_column(ForeignKey("client_insights.id", ondelete="CASCADE"))
    event: Mapped[str] = mapped_column(String(24))  # ai_detected | re_extracted | client_feedback | advisor_confirmed
    before: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    after: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

from typing import Literal

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    conversation_id: int | None = None
    # Required when starting a new conversation
    name: str | None = None
    household_type: Literal["individual", "couple", "family"] = "individual"
    message: str | None = None  # empty on the first call: returns the opening question


class ChatResponse(BaseModel):
    conversation_id: int
    user_id: int
    reply: str
    stage: str  # discover | harvest | architect
    answered: int  # client answers so far
    ready: bool  # enough material to architect the statement
    demo_mode: bool


class ConversationRef(BaseModel):
    conversation_id: int


class UserRef(BaseModel):
    user_id: int


class FinancialPortrait(BaseModel):
    """A light-touch financial snapshot. Intentionally coarse: this is a
    conversation starter for the advisor, not an account aggregation."""

    # Cash flow
    spending_on_priorities_pct: int = Field(55, ge=0, le=100)
    has_spending_plan: bool = False
    # Investments
    values_aligned_allocation_pct: int = Field(15, ge=0, le=100)
    portfolio_values_review: Literal["yes", "partly", "no"] = "no"
    # Estate & legacy
    has_will: bool = True
    has_trust: bool = False
    has_legacy_letter: bool = False
    family_conversations: Literal["regular", "occasional", "never"] = "occasional"
    # Philanthropy
    annual_giving_pct: float = Field(2.0, ge=0, le=50)
    giving_alignment: Literal["intentional", "somewhat", "ad_hoc"] = "somewhat"
    has_giving_vehicle: bool = False
    # Risk
    emergency_reserve_months: int = Field(6, ge=0, le=60)
    insurance_reviewed_recently: bool = False
    concentrated_position: bool = False


class ScoreRequest(BaseModel):
    user_id: int
    portrait: FinancialPortrait


class NoteRequest(BaseModel):
    body: str = Field(min_length=1, max_length=4000)


# --- Progressive discovery ----------------------------------------------------

class DiscoveryStart(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    household_type: Literal["individual", "couple", "family"] = "individual"
    email: str | None = None


class AnswerRequest(BaseModel):
    question_id: int
    text: str = Field(min_length=1, max_length=8000)
    parent_answer_id: int | None = None  # set when answering a follow-up
    input_mode: Literal["text", "voice"] = "text"


class SkipRequest(BaseModel):
    question_id: int
    parent_answer_id: int | None = None  # set when skipping a follow-up
    reason: Literal["skip", "prefer_not"] = "skip"  # "prefer_not" is never questioned or re-asked


class GotoRequest(BaseModel):
    question_id: int


class DeeperRequest(BaseModel):
    module_key: str


class ResumeRequest(BaseModel):
    token: str = Field(min_length=1, max_length=128)


class ShareRequest(BaseModel):
    sharing: Literal["shared_with_advisor", "private"]


class InsightFeedback(BaseModel):
    feedback: Literal["accurate", "partly", "edit", "clarify"]
    text: str | None = Field(None, max_length=4000)  # the client's correction / clarification


class ReflectionFeedback(BaseModel):
    feedback: Literal["yes", "partly", "edit"]
    correction: str | None = Field(None, max_length=4000)


# --- Methodology admin --------------------------------------------------------

class ModuleIn(BaseModel):
    key: str | None = Field(None, max_length=40)
    title: str | None = Field(None, max_length=80)
    description: str | None = None
    intro: str | None = None
    session_group: int | None = Field(None, ge=1, le=20)
    follow_up_mode: Literal["pool", "compose"] | None = None
    active: bool | None = None


class QuestionIn(BaseModel):
    module_id: int | None = None
    key: str | None = Field(None, max_length=60)
    section: str | None = Field(None, max_length=160)
    prompt: str | None = None
    follow_up_guidance: str | None = None
    classification: Literal["core", "follow_up", "optional", "inactive"] | None = None
    required: bool | None = None
    max_follow_ups: int | None = Field(None, ge=0, le=3)
    active: bool | None = None


class ReorderRequest(BaseModel):
    kind: Literal["modules", "questions"]
    ids: list[int]

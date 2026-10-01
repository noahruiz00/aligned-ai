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

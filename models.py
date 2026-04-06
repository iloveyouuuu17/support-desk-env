from __future__ import annotations
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class Ticket(BaseModel):
    id: str
    subject: str
    body: str
    customer_name: str
    customer_tier: str  # free, premium, enterprise
    account_age_days: int
    previous_tickets: int
    timestamp: str


class Action(BaseModel):
    action_type: str  # classify | triage | respond
    ticket_id: Optional[str] = None
    category: Optional[str] = None       # billing | technical | account | general | spam
    priority: Optional[str] = None       # critical | high | medium | low
    department: Optional[str] = None     # tier1 | tier2 | billing | account_mgmt | escalation
    response_text: Optional[str] = None


class Observation(BaseModel):
    task: str
    step: int
    max_steps: int
    tickets: List[Ticket]
    current_ticket_id: Optional[str] = None
    processed_count: int = 0
    message: str = ""
    context: Dict[str, Any] = Field(default_factory=dict)


class Reward(BaseModel):
    value: float = Field(..., ge=0.0, le=1.0, description="Scalar reward for this step")
    breakdown: Dict[str, float] = Field(default_factory=dict, description="Per-component scores")
    message: str = Field(default="", description="Human-readable reward explanation")
    is_penalty: bool = Field(default=False, description="Whether this step incurred a penalty")


class StepResult(BaseModel):
    observation: Observation
    reward: float
    reward_info: Optional[Reward] = None
    done: bool
    info: Dict[str, Any] = Field(default_factory=dict)


class ResetResult(BaseModel):
    observation: Observation
    info: Dict[str, Any] = Field(default_factory=dict)


class StateResult(BaseModel):
    task: str
    step: int
    total_reward: float
    done: bool
    tickets: List[Ticket]
    processed: List[Dict[str, Any]] = Field(default_factory=list)

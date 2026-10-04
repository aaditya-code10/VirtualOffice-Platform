"""Pydantic request/response contracts."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# --------------------------------------------------------------------------- #
# Auth
# --------------------------------------------------------------------------- #
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=200)
    company_name: str = Field(min_length=1, max_length=200)
    industry: str = "Technology"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserOut(ORMModel):
    id: str
    email: str
    full_name: str
    role: str
    company_id: str
    last_login_at: datetime | None = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserOut


# --------------------------------------------------------------------------- #
# Company
# --------------------------------------------------------------------------- #
class CompanyOut(ORMModel):
    id: str
    name: str
    slug: str
    industry: str | None = None
    target_market: str | None = None
    core_services: str | None = None
    primary_goal: str | None = None
    currency: str = "USD"
    headcount: int | None = None
    onboarding_complete: bool = False


class CompanyUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=200)
    industry: str | None = Field(default=None, max_length=120)
    target_market: str | None = None
    core_services: str | None = None
    primary_goal: str | None = None
    currency: str | None = Field(default=None, max_length=8)
    headcount: int | None = Field(default=None, ge=0)
    onboarding_complete: bool | None = None


# --------------------------------------------------------------------------- #
# Agents
# --------------------------------------------------------------------------- #
class AgentOut(ORMModel):
    id: str
    key: str
    name: str
    role: str
    department: str
    focus: str = ""
    responsibilities: list[str] = []
    status: str
    health: int
    is_synthesizer: bool = False
    enabled: bool = True


class AgentUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=120)
    role: str | None = Field(default=None, max_length=120)
    focus: str | None = None
    enabled: bool | None = None
    status: Literal["online", "working", "idle", "blocked"] | None = None


# --------------------------------------------------------------------------- #
# Knowledge
# --------------------------------------------------------------------------- #
class DocumentOut(ORMModel):
    id: str
    filename: str
    content_type: str | None = None
    size_bytes: int
    status: str
    classification: str
    chunk_count: int
    word_count: int
    summary: str | None = None
    error: str | None = None
    created_at: datetime


class FactCreate(BaseModel):
    statement: str = Field(min_length=3)
    category: str = "General"
    title: str = "Business fact"
    value: str | None = None
    classification: Literal["known", "derived", "assumption", "unknown"] = "known"
    source: str = "User input"
    confidence: float = Field(default=100.0, ge=0, le=100)


class FactOut(ORMModel):
    id: str
    category: str
    title: str
    statement: str
    value: str | None = None
    classification: str
    source: str
    confidence: float
    document_id: str | None = None
    created_at: datetime


class SearchHit(BaseModel):
    chunk_id: str
    document_id: str
    filename: str
    position: int
    score: float
    excerpt: str


class SearchResponse(BaseModel):
    query: str
    hits: list[SearchHit]


# --------------------------------------------------------------------------- #
# Metrics & analytics
# --------------------------------------------------------------------------- #
class MetricCreate(BaseModel):
    key: str = Field(min_length=1, max_length=80)
    label: str = Field(min_length=1, max_length=160)
    period: str = Field(pattern=r"^\d{4}-\d{2}$")
    value: float
    unit: Literal["number", "currency", "percent", "score"] = "number"
    department: str | None = None


class MetricOut(ORMModel):
    id: str
    key: str
    label: str
    period: str
    value: float
    unit: str
    department: str | None = None


class KpiOut(BaseModel):
    key: str
    label: str
    value: float
    display: str
    unit: str
    change_pct: float | None = None
    direction: Literal["up", "down", "flat"] = "flat"
    # Whether the movement is good news for the business. Rising churn moves
    # "up" but is "bad" - the UI colours on sentiment, never on direction.
    sentiment: Literal["good", "bad", "neutral"] = "neutral"


class SeriesOut(BaseModel):
    key: str
    label: str
    unit: str
    periods: list[str]
    values: list[float]


class AnalyticsOut(BaseModel):
    currency: str
    kpis: list[KpiOut]
    series: list[SeriesOut]
    health_score: int
    work_order_stats: dict[str, int]


# --------------------------------------------------------------------------- #
# Work orders
# --------------------------------------------------------------------------- #
class WorkOrderCreate(BaseModel):
    command: str = Field(min_length=3, max_length=4000)
    agent_key: str | None = None
    document_id: str | None = None
    category: str | None = None


class AgentTaskOut(ORMModel):
    id: str
    agent_key: str
    status: str
    finding: str | None = None
    evidence: list[Any] = []
    risks: list[str] = []
    opportunities: list[str] = []
    recommended_action: str | None = None
    confidence: int = 0
    duration_ms: int = 0
    error: str | None = None


class WorkOrderOut(ORMModel):
    id: str
    command: str
    status: str
    progress: int
    mode: str
    engine: str
    target_agent_key: str | None = None
    document_id: str | None = None
    category: str | None = None
    headline: str | None = None
    summary: str | None = None
    recommendation: str | None = None
    artifact_title: str | None = None
    artifact_body: str | None = None
    confidence: int = 0
    risks: list[str] = []
    opportunities: list[str] = []
    next_actions: list[str] = []
    citations: list[Any] = []
    consulted_agent_keys: list[str] = []
    requires_approval: bool = False
    error: str | None = None
    duration_ms: int = 0
    tokens_used: int = 0
    created_at: datetime
    completed_at: datetime | None = None
    tasks: list[AgentTaskOut] = []


class WorkOrderSummary(ORMModel):
    id: str
    command: str
    status: str
    progress: int
    engine: str
    confidence: int
    document_id: str | None = None
    category: str | None = None
    headline: str | None = None
    recommendation: str | None = None
    consulted_agent_keys: list[str] = []
    requires_approval: bool = False
    created_at: datetime


# --------------------------------------------------------------------------- #
# Approvals
# --------------------------------------------------------------------------- #
class ApprovalDecision(BaseModel):
    decision: Literal["approve", "reject", "changes"]
    comment: str | None = Field(default=None, max_length=2000)


class ApprovalOut(ORMModel):
    id: str
    work_order_id: str | None = None
    title: str
    description: str | None = None
    risk: str
    owner: str
    expected_impact: str | None = None
    status: str
    comment: str | None = None
    created_at: datetime
    decided_at: datetime | None = None


# --------------------------------------------------------------------------- #
# Reports & audit
# --------------------------------------------------------------------------- #
class ReportFinding(BaseModel):
    department: str
    agent: str
    text: str
    confidence: int = 0


class ReportOut(BaseModel):
    id: str
    code: str
    title: str
    date: datetime
    summary: str
    recommendation: str | None = None
    health_score: int
    status: str
    engine: str
    findings: list[ReportFinding] = []
    risks: list[str] = []
    opportunities: list[str] = []
    next_actions: list[str] = []
    citations: list[Any] = []


class AuditEventOut(ORMModel):
    id: str
    actor_label: str
    action: str
    entity_type: str | None = None
    entity_id: str | None = None
    detail: dict = {}
    at: datetime


class SystemStatus(BaseModel):
    status: str
    version: str
    environment: str
    database: str
    llm_enabled: bool
    llm_model: str | None = None
    engine: str

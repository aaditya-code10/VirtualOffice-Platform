"""Domain model for the AI Virtual Office.

Every business row is scoped to a company (multi-tenant), and every mutation
that matters is mirrored into ``audit_events``.
"""
from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, new_id, utcnow


# --------------------------------------------------------------------------- #
# Enums
# --------------------------------------------------------------------------- #
class UserRole(str, enum.Enum):
    OWNER = "OWNER"
    ADMIN = "ADMIN"
    MEMBER = "MEMBER"
    VIEWER = "VIEWER"


class AgentStatus(str, enum.Enum):
    ONLINE = "online"
    WORKING = "working"
    IDLE = "idle"
    BLOCKED = "blocked"


class WorkOrderStatus(str, enum.Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ApprovalStatus(str, enum.Enum):
    NONE = "NONE"
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CHANGES_REQUESTED = "CHANGES"


class DocumentStatus(str, enum.Enum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    INDEXED = "indexed"
    FAILED = "failed"


class FactClassification(str, enum.Enum):
    KNOWN = "known"
    DERIVED = "derived"
    ASSUMPTION = "assumption"
    UNKNOWN = "unknown"


class RiskLevel(str, enum.Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"


# --------------------------------------------------------------------------- #
# Tenancy & identity
# --------------------------------------------------------------------------- #
class Company(Base, TimestampMixin):
    __tablename__ = "companies"

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("co"))
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    industry: Mapped[str | None] = mapped_column(String(120))
    target_market: Mapped[str | None] = mapped_column(Text)
    core_services: Mapped[str | None] = mapped_column(Text)
    primary_goal: Mapped[str | None] = mapped_column(Text)
    currency: Mapped[str] = mapped_column(String(8), default="USD")
    headcount: Mapped[int | None] = mapped_column(Integer)
    onboarding_complete: Mapped[bool] = mapped_column(Boolean, default=False)

    users: Mapped[list[User]] = relationship(back_populates="company", cascade="all, delete-orphan")
    agents: Mapped[list[Agent]] = relationship(back_populates="company", cascade="all, delete-orphan")
    documents: Mapped[list[Document]] = relationship(back_populates="company", cascade="all, delete-orphan")
    facts: Mapped[list[Fact]] = relationship(back_populates="company", cascade="all, delete-orphan")
    work_orders: Mapped[list[WorkOrder]] = relationship(back_populates="company", cascade="all, delete-orphan")
    metrics: Mapped[list[Metric]] = relationship(back_populates="company", cascade="all, delete-orphan")


class User(Base, TimestampMixin):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("email", name="uq_users_email"),)

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("usr"))
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.OWNER)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    company: Mapped[Company] = relationship(back_populates="users")


# --------------------------------------------------------------------------- #
# Digital workforce
# --------------------------------------------------------------------------- #
class Agent(Base, TimestampMixin):
    __tablename__ = "agents"
    __table_args__ = (UniqueConstraint("company_id", "key", name="uq_agent_company_key"),)

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("agt"))
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    key: Mapped[str] = mapped_column(String(40), nullable=False)  # sales, finance, ...
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    role: Mapped[str] = mapped_column(String(120), nullable=False)
    department: Mapped[str] = mapped_column(String(120), nullable=False)
    focus: Mapped[str] = mapped_column(Text, default="")
    system_prompt: Mapped[str] = mapped_column(Text, default="")
    responsibilities: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[AgentStatus] = mapped_column(Enum(AgentStatus), default=AgentStatus.ONLINE)
    health: Mapped[int] = mapped_column(Integer, default=100)
    is_synthesizer: Mapped[bool] = mapped_column(Boolean, default=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    company: Mapped[Company] = relationship(back_populates="agents")
    tasks: Mapped[list[AgentTask]] = relationship(back_populates="agent", cascade="all, delete-orphan")


# --------------------------------------------------------------------------- #
# Knowledge base
# --------------------------------------------------------------------------- #
class Document(Base, TimestampMixin):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("doc"))
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    uploaded_by_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    filename: Mapped[str] = mapped_column(String(400), nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(160))
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    storage_path: Mapped[str | None] = mapped_column(String(600))
    status: Mapped[DocumentStatus] = mapped_column(Enum(DocumentStatus), default=DocumentStatus.UPLOADED)
    classification: Mapped[str] = mapped_column(String(80), default="business_document")
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    word_count: Mapped[int] = mapped_column(Integer, default=0)
    summary: Mapped[str | None] = mapped_column(Text)
    error: Mapped[str | None] = mapped_column(Text)

    company: Mapped[Company] = relationship(back_populates="documents")
    chunks: Mapped[list[DocumentChunk]] = relationship(
        back_populates="document", cascade="all, delete-orphan", passive_deletes=True
    )


class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    __table_args__ = (Index("ix_chunk_company_doc", "company_id", "document_id"),)

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("chk"))
    company_id: Mapped[str] = mapped_column(String(40), index=True, nullable=False)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    position: Mapped[int] = mapped_column(Integer, default=0)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    token_estimate: Mapped[int] = mapped_column(Integer, default=0)
    # Sparse bag-of-words vector: {term: term_frequency}
    term_frequencies: Mapped[dict] = mapped_column(JSON, default=dict)

    document: Mapped[Document] = relationship(back_populates="chunks")


class Fact(Base, TimestampMixin):
    __tablename__ = "facts"

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("fact"))
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    document_id: Mapped[str | None] = mapped_column(ForeignKey("documents.id", ondelete="SET NULL"))
    category: Mapped[str] = mapped_column(String(120), default="General")
    title: Mapped[str] = mapped_column(String(300), default="Business fact")
    statement: Mapped[str] = mapped_column(Text, nullable=False)
    value: Mapped[str | None] = mapped_column(String(200))
    classification: Mapped[FactClassification] = mapped_column(
        Enum(FactClassification), default=FactClassification.KNOWN
    )
    source: Mapped[str] = mapped_column(String(300), default="User input")
    confidence: Mapped[float] = mapped_column(Float, default=100.0)

    company: Mapped[Company] = relationship(back_populates="facts")


class Metric(Base, TimestampMixin):
    """A time-series business metric. Analytics are computed from these rows."""

    __tablename__ = "metrics"
    __table_args__ = (
        UniqueConstraint("company_id", "key", "period", name="uq_metric_company_key_period"),
        Index("ix_metric_company_key", "company_id", "key"),
    )

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("mtr"))
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    key: Mapped[str] = mapped_column(String(80), nullable=False)          # revenue, margin, ...
    label: Mapped[str] = mapped_column(String(160), nullable=False)
    period: Mapped[str] = mapped_column(String(20), nullable=False)        # 2026-03
    value: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(20), default="number")        # number|currency|percent|score
    department: Mapped[str | None] = mapped_column(String(80))

    company: Mapped[Company] = relationship(back_populates="metrics")


# --------------------------------------------------------------------------- #
# Work execution
# --------------------------------------------------------------------------- #
class WorkOrder(Base, TimestampMixin):
    __tablename__ = "work_orders"
    __table_args__ = (Index("ix_wo_company_created", "company_id", "created_at"),)

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("wo"))
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    requested_by_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    document_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    category: Mapped[str | None] = mapped_column(String(80), nullable=True)
    command: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[WorkOrderStatus] = mapped_column(Enum(WorkOrderStatus), default=WorkOrderStatus.QUEUED)
    progress: Mapped[int] = mapped_column(Integer, default=0)
    mode: Mapped[str] = mapped_column(String(20), default="orchestrated")  # orchestrated|direct
    engine: Mapped[str] = mapped_column(String(20), default="heuristic")   # llm|heuristic
    target_agent_key: Mapped[str | None] = mapped_column(String(40))

    headline: Mapped[str | None] = mapped_column(Text)
    summary: Mapped[str | None] = mapped_column(Text)
    recommendation: Mapped[str | None] = mapped_column(Text)
    artifact_title: Mapped[str | None] = mapped_column(String(300))
    artifact_body: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[int] = mapped_column(Integer, default=0)
    risks: Mapped[list] = mapped_column(JSON, default=list)
    opportunities: Mapped[list] = mapped_column(JSON, default=list)
    next_actions: Mapped[list] = mapped_column(JSON, default=list)
    citations: Mapped[list] = mapped_column(JSON, default=list)
    consulted_agent_keys: Mapped[list] = mapped_column(JSON, default=list)
    requires_approval: Mapped[bool] = mapped_column(Boolean, default=False)
    error: Mapped[str | None] = mapped_column(Text)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    tokens_used: Mapped[int] = mapped_column(Integer, default=0)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    company: Mapped[Company] = relationship(back_populates="work_orders")
    tasks: Mapped[list[AgentTask]] = relationship(
        back_populates="work_order", cascade="all, delete-orphan", passive_deletes=True
    )
    approvals: Mapped[list[Approval]] = relationship(
        back_populates="work_order", cascade="all, delete-orphan", passive_deletes=True
    )


class AgentTask(Base, TimestampMixin):
    """One specialist agent's contribution to a work order."""

    __tablename__ = "agent_tasks"

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("task"))
    work_order_id: Mapped[str] = mapped_column(ForeignKey("work_orders.id", ondelete="CASCADE"), index=True)
    agent_id: Mapped[str] = mapped_column(ForeignKey("agents.id", ondelete="CASCADE"), index=True)
    agent_key: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[TaskStatus] = mapped_column(Enum(TaskStatus), default=TaskStatus.PENDING)
    finding: Mapped[str | None] = mapped_column(Text)
    evidence: Mapped[list] = mapped_column(JSON, default=list)
    risks: Mapped[list] = mapped_column(JSON, default=list)
    opportunities: Mapped[list] = mapped_column(JSON, default=list)
    recommended_action: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[int] = mapped_column(Integer, default=0)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text)

    work_order: Mapped[WorkOrder] = relationship(back_populates="tasks")
    agent: Mapped[Agent] = relationship(back_populates="tasks")


class Approval(Base, TimestampMixin):
    __tablename__ = "approvals"

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("apr"))
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    work_order_id: Mapped[str | None] = mapped_column(ForeignKey("work_orders.id", ondelete="CASCADE"))
    decided_by_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    risk: Mapped[RiskLevel] = mapped_column(Enum(RiskLevel), default=RiskLevel.MEDIUM)
    owner: Mapped[str] = mapped_column(String(120), default="Strategy & Executive")
    expected_impact: Mapped[str | None] = mapped_column(String(300))
    status: Mapped[ApprovalStatus] = mapped_column(Enum(ApprovalStatus), default=ApprovalStatus.PENDING)
    comment: Mapped[str | None] = mapped_column(Text)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    work_order: Mapped[WorkOrder | None] = relationship(back_populates="approvals")


class AuditEvent(Base):
    __tablename__ = "audit_events"
    __table_args__ = (Index("ix_audit_company_at", "company_id", "at"),)

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("evt"))
    company_id: Mapped[str | None] = mapped_column(String(40), index=True)
    actor_id: Mapped[str | None] = mapped_column(String(40))
    actor_label: Mapped[str] = mapped_column(String(200), default="system")
    action: Mapped[str] = mapped_column(String(120), nullable=False)
    entity_type: Mapped[str | None] = mapped_column(String(80))
    entity_id: Mapped[str | None] = mapped_column(String(40))
    detail: Mapped[dict] = mapped_column(JSON, default=dict)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

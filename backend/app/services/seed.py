"""Bootstrap data: agent roster per company, and an optional demo workspace."""
from __future__ import annotations

import logging
import re
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.agents.registry import AGENT_SPECS
from app.config import settings
from app.core.security import hash_password
from app.models import (
    Agent,
    AgentStatus,
    Company,
    Fact,
    FactClassification,
    Metric,
    User,
    UserRole,
)

logger = logging.getLogger(__name__)


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "company"


def unique_slug(db: Session, name: str) -> str:
    base = slugify(name)
    slug = base
    counter = 2
    while db.execute(select(Company).where(Company.slug == slug)).scalar_one_or_none():
        slug = f"{base}-{counter}"
        counter += 1
    return slug


def ensure_agents(db: Session, company: Company) -> list[Agent]:
    """Give a company its full digital workforce (idempotent)."""
    existing = {
        a.key: a
        for a in db.execute(select(Agent).where(Agent.company_id == company.id)).scalars().all()
    }
    created: list[Agent] = []

    for spec in AGENT_SPECS:
        if spec.key in existing:
            continue
        agent = Agent(
            company_id=company.id,
            key=spec.key,
            name=spec.name,
            role=spec.role,
            department=spec.department,
            focus=spec.focus,
            system_prompt=spec.system_prompt,
            responsibilities=list(spec.responsibilities),
            status=AgentStatus.IDLE if spec.is_synthesizer else AgentStatus.ONLINE,
            health=100,
            is_synthesizer=spec.is_synthesizer,
        )
        db.add(agent)
        created.append(agent)

    return created


# --------------------------------------------------------------------------- #
# Demo workspace
# --------------------------------------------------------------------------- #
def _recent_periods(count: int = 7) -> list[str]:
    """The last N months as YYYY-MM, oldest first."""
    today = date.today()
    year, month = today.year, today.month
    periods: list[str] = []
    for _ in range(count):
        periods.append(f"{year:04d}-{month:02d}")
        month -= 1
        if month == 0:
            month, year = 12, year - 1
    return list(reversed(periods))


# key -> (label, unit, department, series of 7 values)
DEMO_METRICS: dict[str, tuple[str, str, str, list[float]]] = {
    "revenue":               ("Revenue",              "currency", "Finance",     [312000, 348000, 331000, 389000, 421000, 452000, 486000]),
    "gross_margin":          ("Gross Margin",         "percent",  "Finance",     [67.4, 68.1, 68.9, 68.2, 66.0, 63.8, 61.5]),
    "opex":                  ("Operating Expenses",   "currency", "Finance",     [186000, 194000, 199000, 221000, 244000, 268000, 291000]),
    "cash_runway_months":    ("Cash Runway",          "number",   "Finance",     [21, 20, 19, 17, 15, 13, 11]),
    "pipeline":              ("Open Pipeline",        "currency", "Sales",       [890000, 940000, 910000, 1020000, 1140000, 1210000, 1180000]),
    "win_rate":              ("Win Rate",             "percent",  "Sales",       [27.5, 28.1, 26.4, 25.0, 23.2, 21.8, 19.4]),
    "deal_cycle_days":       ("Deal Cycle",           "number",   "Sales",       [38, 39, 41, 44, 47, 51, 56]),
    "cac":                   ("Customer Acq. Cost",   "currency", "Marketing",   [1180, 1210, 1265, 1340, 1455, 1580, 1720]),
    "mql":                   ("Marketing Qual. Leads","number",   "Marketing",   [420, 448, 431, 486, 512, 534, 549]),
    "conversion_rate":       ("Lead Conversion",      "percent",  "Marketing",   [4.1, 4.3, 4.0, 4.4, 4.6, 4.5, 4.4]),
    "capacity_utilisation":  ("Capacity Utilisation", "percent",  "Operations",  [68, 71, 70, 76, 81, 86, 91]),
    "on_time_delivery":      ("On-Time Delivery",     "percent",  "Operations",  [96, 95, 96, 93, 90, 87, 83]),
    "cycle_time_days":       ("Delivery Cycle Time",  "number",   "Operations",  [9, 9, 10, 11, 12, 14, 16]),
    "csat":                  ("Customer Satisfaction","score",    "Customer Intelligence", [84, 85, 84, 82, 80, 77, 74]),
    "churn_rate":            ("Monthly Churn",        "percent",  "Customer Intelligence", [2.1, 2.0, 2.3, 2.8, 3.4, 4.2, 5.3]),
    "nps":                   ("Net Promoter Score",   "number",   "Customer Intelligence", [41, 43, 42, 38, 34, 29, 24]),
    "support_tickets":       ("Support Tickets",      "number",   "Customer Intelligence", [310, 324, 341, 402, 468, 551, 630]),
    "headcount":             ("Headcount",            "number",   "HR",          [42, 44, 45, 47, 48, 49, 49]),
    "attrition_rate":        ("Attrition Rate",       "percent",  "HR",          [8.0, 8.4, 9.1, 11.0, 13.5, 15.8, 18.2]),
    "utilisation":           ("Team Utilisation",     "percent",  "HR",          [74, 76, 78, 83, 87, 90, 93]),
}

DEMO_FACTS = [
    ("Revenue model", "Subscription-led with services attach", FactClassification.KNOWN,
     "Company profile", 100.0,
     "Northwind Logistics bills a monthly platform subscription with an implementation services attach of roughly 18% of first-year contract value."),
    ("Concentration", "Top 3 accounts = 41% of ARR", FactClassification.KNOWN,
     "Finance review 2026-Q1", 95.0,
     "The three largest accounts represent 41% of annual recurring revenue, a concentration the board has flagged twice."),
    ("Delivery constraint", "Implementation is the bottleneck", FactClassification.DERIVED,
     "Operations capacity analysis", 80.0,
     "Every new logo requires roughly 11 days of implementation engineering, and the team of four is the hard ceiling on new-customer throughput."),
    ("Pricing", "No price increase since launch", FactClassification.KNOWN,
     "Commercial policy", 100.0,
     "List pricing has not changed in 26 months while cloud infrastructure cost per account has risen 34%."),
    ("Market", "Mid-market logistics operators in NA/EU", FactClassification.KNOWN,
     "Company profile", 100.0,
     "The target market is mid-market logistics operators between 50 and 500 vehicles, primarily in North America and Western Europe."),
    ("Assumption", "Churn is capacity-driven", FactClassification.ASSUMPTION,
     "Customer Intelligence hypothesis", 55.0,
     "Working hypothesis that rising churn is caused by implementation delays rather than product gaps; not yet validated against exit interviews."),
]

DEMO_KNOWLEDGE_DOC = """\
Northwind Logistics — Quarterly Business Review (internal)

EXECUTIVE POSITION
Revenue grew to $486K in the most recent month, up 55.8% over seven months. That growth
is real, but it is being purchased at an accelerating cost. Operating expenses rose 56.5%
over the same window, and gross margin fell from 67.4% to 61.5%. Net of growth, the
company is converting less of each dollar than it did two quarters ago.

THE CAPACITY WALL
Implementation capacity is the binding constraint on the business. Utilisation moved from
68% to 91% across the period. On-time delivery fell from 96% to 83% and delivery cycle
time nearly doubled from 9 to 16 days. The implementation team is four engineers; no
requisition has been opened. Sales continues to close at the same rate it did when
utilisation was 70%, which means every additional signature lengthens the queue for
customers already waiting.

CUSTOMER SIGNAL
Customer satisfaction dropped 10 points to 74. NPS fell from 41 to 24. Monthly churn rose
from 2.1% to 5.3% — a 2.5x increase. Support ticket volume doubled. The correlation between
the delivery cycle time series and the churn series is the strongest relationship in this
dataset. Exit interviews have not been conducted systematically, so the causal link remains
a hypothesis rather than an established fact.

ACQUISITION ECONOMICS
Customer acquisition cost rose from $1,180 to $1,720, an increase of 45.8%. Marketing
qualified leads grew 30.7%, so the channel is still producing volume, but each unit of
volume costs materially more. Lead conversion is flat at approximately 4.4%. Win rate fell
from 27.5% to 19.4% and the deal cycle stretched from 38 to 56 days.

PEOPLE
Headcount grew from 42 to 49 but attrition more than doubled, from 8.0% to 18.2%. Team
utilisation reached 93%. The delivery organisation carries the majority of both the
utilisation load and the attrition.

CASH
Cash runway compressed from 21 months to 11 months. At the current burn trajectory the
company reaches a financing decision inside three quarters.

OPEN QUESTIONS FOR LEADERSHIP
1. Do we hire implementation capacity before or after we slow new-logo acquisition?
2. Is the 26-month price freeze defensible given a 34% rise in infrastructure cost per account?
3. Does the top-3 account concentration of 41% of ARR change the answer to either question?
"""


def seed_demo_workspace(db: Session) -> Company | None:
    """Create the demo company, user, agents, metrics, facts and a seed document.

    Idempotent: returns None if the demo user already exists.
    """
    existing = db.execute(select(User).where(User.email == settings.demo_email)).scalar_one_or_none()
    if existing:
        return None

    company = Company(
        name="Northwind Logistics",
        slug=unique_slug(db, "Northwind Logistics"),
        industry="Logistics SaaS",
        target_market="Mid-market logistics operators (50-500 vehicles) in North America and Western Europe",
        core_services="Fleet routing platform, telematics integration, and implementation services",
        primary_goal="Reach profitable growth without adding a financing round",
        currency="USD",
        headcount=49,
        onboarding_complete=True,
    )
    db.add(company)
    db.flush()

    db.add(
        User(
            company_id=company.id,
            email=settings.demo_email,
            full_name="Dana Whitfield",
            hashed_password=hash_password(settings.demo_password),
            role=UserRole.OWNER,
        )
    )

    ensure_agents(db, company)

    periods = _recent_periods(7)
    for key, (label, unit, department, values) in DEMO_METRICS.items():
        for period, value in zip(periods, values, strict=True):
            db.add(
                Metric(
                    company_id=company.id,
                    key=key,
                    label=label,
                    period=period,
                    value=float(value),
                    unit=unit,
                    department=department,
                )
            )

    for category, title, classification, source, confidence, statement in DEMO_FACTS:
        db.add(
            Fact(
                company_id=company.id,
                category=category,
                title=title,
                statement=statement,
                classification=classification,
                source=source,
                confidence=confidence,
            )
        )

    db.flush()
    _seed_demo_document(db, company)
    db.flush()

    logger.info("Seeded demo workspace '%s' (%s)", company.name, settings.demo_email)
    return company


def _seed_demo_document(db: Session, company: Company) -> None:
    """Index a starter QBR document so knowledge search works immediately."""
    from app.models import Document, DocumentStatus
    from app.services import rag

    doc = Document(
        company_id=company.id,
        filename="northwind-qbr.md",
        content_type="text/markdown",
        size_bytes=len(DEMO_KNOWLEDGE_DOC.encode("utf-8")),
        status=DocumentStatus.INDEXED,
        classification=rag.classify("northwind-qbr.md", DEMO_KNOWLEDGE_DOC),
        word_count=len(DEMO_KNOWLEDGE_DOC.split()),
        summary=rag.summarise(DEMO_KNOWLEDGE_DOC),
    )
    db.add(doc)
    db.flush()

    # Persist the original alongside the index, exactly as an upload does, so
    # `app.cli reindex` can rebuild this document too.
    company_dir = settings.storage_dir / company.id
    company_dir.mkdir(parents=True, exist_ok=True)
    stored = company_dir / f"{doc.id}_{doc.filename}"
    stored.write_text(DEMO_KNOWLEDGE_DOC, encoding="utf-8")
    doc.storage_path = str(stored)

    doc.chunk_count = rag.index_document(db, doc, DEMO_KNOWLEDGE_DOC)


def bootstrap(db: Session) -> None:
    """Run at startup: ensure every company has agents, optionally seed demo."""
    if settings.seed_on_startup:
        company_count = db.execute(select(func.count(Company.id))).scalar_one()
        if company_count == 0:
            seed_demo_workspace(db)

    for company in db.execute(select(Company)).scalars().all():
        ensure_agents(db, company)

    db.commit()

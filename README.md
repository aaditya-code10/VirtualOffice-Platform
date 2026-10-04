# AI Virtual Office

A multi-agent business operations platform. You ask a question in plain language;
a team of seven specialist agents analyses it **against your own documents and
metrics**, a strategy agent reconciles their findings into one executive brief,
and anything that commits money, headcount or pricing waits for your approval.

```
command
  ├─ routed to the relevant department agents (keyword scoring)
  ├─ each agent retrieves context: company profile + metrics + knowledge base (BM25)
  ├─ agents run concurrently and produce structured findings
  ├─ the strategy agent reconciles them and names the contradictions
  ├─ citations are attached to the result
  └─ resource-committing recommendations raise an approval
```

It runs **with or without an LLM**. With `ANTHROPIC_API_KEY` set, the agents reason
through Claude with structured outputs. Without one, a deterministic engine derives
findings from your actual metric trends and indexed documents. Same API, same UI,
same data — the `engine` field on every work order says honestly which one ran.

---

## Quick start

### Option A — Docker (nothing else to install)

```bash
docker compose up --build
```

Open <http://localhost:8080> and sign in with `founder@northwind.io` / `demo1234`.

### Option B — Local

Requires Python 3.11+ and Node 18+.

```bash
make install
```

```bash
cp backend/.env.example backend/.env
```

```bash
make dev
```

Web on <http://localhost:5173>, API docs on <http://localhost:8000/docs>.

By default the backend uses SQLite and needs no database server. To use
PostgreSQL, set `DATABASE_URL` in `backend/.env` and run `make migrate`.

### Enabling the LLM

Add a key to `backend/.env` and restart:

```bash
ANTHROPIC_API_KEY=sk-ant-...
```

Settings → Reasoning engine shows which engine is live. Nothing else changes.

---

## What's in the box

| Area | Detail |
|---|---|
| **Backend** | FastAPI, SQLAlchemy 2.0, Alembic, Pydantic v2 |
| **Frontend** | React 19, TypeScript (strict), Vite, react-router — no UI framework, no chart library |
| **Database** | PostgreSQL or SQLite; 12 tables, real foreign keys, cascade deletes |
| **Auth** | JWT (PyJWT) + bcrypt, four roles, per-company tenancy isolation |
| **Retrieval** | Text extraction (PDF/DOCX/MD/TXT/CSV/JSON/HTML) → chunking → BM25 ranking |
| **LLM** | Anthropic SDK with structured outputs, graceful degradation |
| **Tests** | 48 pytest tests covering auth, tenancy, RAG, analytics, orchestration, fallback, CLI |
| **Ops** | Dockerfiles, compose stack, Makefile, admin CLI, audit trail |

### Screens

Command Center · Virtual Office · Work Orders · Knowledge · Analytics ·
Executive Reports · Approvals · Company Profile · Settings, plus a per-agent
workstation at `/agents/:key`.

---

## The workforce

| Key | Agent | Department | Watches |
|---|---|---|---|
| `sales` | Alex Vance | Sales | pipeline, win rate, deal cycle |
| `hr` | Elena Rostova | HR | headcount, attrition, utilisation |
| `finance` | Arthur Pendelton | Finance | margin, opex, cash runway |
| `marketing` | Sophia Chen | Marketing | CAC, MQLs, conversion |
| `operations` | Marcus Vance | Operations | capacity, on-time delivery, cycle time |
| `cx` | Maya Patel | Customer Intelligence | CSAT, churn, NPS, tickets |
| `strategy` | Jordan Blake | Strategy & Executive | reconciles the others |

Routing scores each specialist by keyword density against the command and consults
the top matches (capped at 4) plus strategy. `GET /api/work-orders/preview` shows
the routing without executing anything — the UI uses it for the live preview under
the command bar.

---

## How analysis actually works

**Nothing is hardcoded.** Both engines read the same three context sources:

1. **Company profile** — the digital twin you fill in under Company Profile.
2. **Metrics** — a time series in the `metrics` table. KPIs, trends, and the
   composite health score are all computed from these rows.
3. **Knowledge base** — uploaded documents, chunked and retrieved by BM25.

Both engines are **question-aware**: the command decides which metrics are
foregrounded, which document passage or curated fact is quoted, and how the
conclusion and next action are framed. Asking Finance *"why did margin fall"*,
*"can we afford two hires"* and *"what is our runway"* produces three different
answers from the same data — the question shape (cause / decision / quantity /
forecast / risk / assessment) changes the framing, and term matching decides
which metric leads.

The deterministic engine derives findings from trend direction, magnitude and
threshold breaches, and its confidence scales with how much evidence it actually
had — highest when the question named a metric the department holds and a
document corroborates it. The LLM engine gets the same context as a prompt and
returns a validated `SpecialistFinding` / `ExecutiveBrief` via structured outputs.

### Health score

A weighted composite, renormalised over whichever metrics you report, so partial
coverage still scores fairly. Each metric has a goal:

- **higher is better** — margin, CSAT, win rate, runway
- **lower is better** — churn, attrition
- **target band** — capacity utilisation, where both idle *and* overloaded are unhealthy

This is also why the dashboard colours changes by *sentiment* rather than
direction: churn rising 26% points up and is red.

---

## API

Interactive docs at `/docs`. All routes are under `/api` and require a bearer
token except `auth/*` and `system/status`.

| Method | Path | Purpose |
|---|---|---|
| POST | `/auth/register` | create a company, owner and agent roster |
| POST | `/auth/login` | exchange credentials for a JWT |
| GET | `/company` · PATCH | the company digital twin |
| GET | `/agents` · `/agents/{key}` · `/agents/{key}/tasks` | the workforce |
| POST | `/work-orders` | execute a command (add `agent_key` to target one agent) |
| GET | `/work-orders/preview` | show routing without executing |
| POST | `/knowledge/documents` | upload, parse, chunk and index |
| GET | `/knowledge/search?q=` | BM25 over the company's chunks |
| GET/POST | `/knowledge/facts` | curated facts |
| GET | `/analytics` · GET/POST `/metrics` | KPIs, series, health score |
| GET | `/approvals` · POST `/approvals/{id}/decision` | human decisions |
| GET | `/reports` · `/reports/{id}/export` | briefs, Markdown export |
| GET | `/audit` | audit trail (admin only) |

Roles: `OWNER` > `ADMIN` > `MEMBER` > `VIEWER`. Writes need `MEMBER`; approvals,
agent configuration and the audit log need `ADMIN`.

---

## Commands

```bash
make help
```

| Command | Does |
|---|---|
| `make install` | venv + backend and frontend dependencies |
| `make dev` | run API and web together |
| `make test` | backend test suite |
| `make lint` | ruff + tsc |
| `make migrate` | apply migrations |
| `make revision m="..."` | autogenerate a migration |
| `make reset` | drop, recreate and re-seed (destructive) |
| `make docker` | full stack on :8080 |

Admin CLI:

```bash
cd backend && .venv/bin/python -m app.cli status
```

`seed`, `reset`, `status`, `reindex`, `create-user` are available.

> **`reindex` matters.** Chunk term-frequencies are computed at index time, so any
> change to `rag.tokenize` (stopwords, stemming) invalidates every stored index.
> Run `make reindex` after such a change or existing documents quietly stop
> matching queries. It reports any document whose original is missing from disk
> rather than pretending it succeeded.

---

## Project layout

```
backend/
  app/
    agents/registry.py     agent specs, system prompts, routing, approval triggers
    api/                   one router per resource
    core/                  security, dependencies, audit
    models/                SQLAlchemy entities
    schemas/               Pydantic contracts
    services/
      orchestrator.py      fan-out, synthesis, approval gating
      llm.py               Anthropic client + structured output schemas
      heuristics.py        deterministic engine
      rag.py               extraction, chunking, BM25
      analytics.py         KPIs, trends, health score
      seed.py              agent roster + demo workspace
    cli.py                 admin commands
  alembic/versions/        migrations
  tests/                   48 tests
frontend/
  src/
    api.ts                 typed client
    auth.tsx               auth context
    components/            Layout, Charts, Markdown, WorkOrderModal, Delta
    pages/                 one file per screen
```

---

## Production notes

- **`SECRET_KEY`** must be ≥32 bytes when `ENVIRONMENT=production`; the app
  refuses to boot otherwise. Generate one with
  `python -c "import secrets; print(secrets.token_urlsafe(48))"`.
- **Migrations, not `create_all`.** The API calls `create_all` at startup for
  local convenience; in production `alembic upgrade head` (which the backend
  Dockerfile runs on boot) owns the schema.
- **Work orders execute synchronously.** Fine at the deterministic engine's
  ~20ms and acceptable for LLM calls behind the 300s nginx timeout. For heavy
  concurrent use, move `execute_work_order` onto a task queue — it is already a
  single self-contained function that takes a session and returns a row.
- **Retrieval is BM25, not embeddings.** Deliberate: it needs no model, no vector
  database and no network call, so search behaves identically offline and in CI.
  To upgrade, add a vector column to `document_chunks` and replace the scoring
  loop in `rag.search`; the ingestion pipeline and API contract don't change.
#   V i r t u a l - A I - o f f i c e  
 
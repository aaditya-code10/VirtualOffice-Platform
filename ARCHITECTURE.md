# Architecture

## System

```text
                         Browser (React 19 + TS)
                                  │
                        JWT bearer · fetch
                                  │
                      ┌───────────▼───────────┐
                      │   FastAPI (/api)      │
                      │  CORS · auth · roles  │
                      └───────────┬───────────┘
                                  │
        ┌───────────┬─────────────┼─────────────┬────────────┐
        ▼           ▼             ▼             ▼            ▼
     auth      knowledge     work-orders    analytics    approvals
        │           │             │             │            │
        │           ▼             ▼             ▼            │
        │      rag service   ORCHESTRATOR   analytics svc     │
        │    extract/chunk/       │         trends/health     │
        │        BM25             │                           │
        │                ┌────────┴────────┐                  │
        │                ▼                 ▼                  │
        │           llm service      heuristics                │
        │        (Anthropic SDK)    (deterministic)            │
        │                └────────┬────────┘                  │
        └────────────────────────┬┴──────────────────────────┘
                                 ▼
                    SQLAlchemy 2.0 ORM · Alembic
                                 │
                    PostgreSQL  or  SQLite
```

## Request path of a work order

1. `POST /api/work-orders` authenticates the caller and resolves their company.
2. `orchestrator.execute_work_order` opens a `WorkOrder` row in `RUNNING`.
3. `load_context` assembles the company profile, metric trends and curated facts.
4. `route_command` scores each specialist by keyword density; the top N (max 4)
   are selected, filtered to agents that are enabled for this company.
5. Per agent, `rag.search` retrieves the highest-scoring chunks for
   `command + agent focus`.
6. Specialists run **concurrently** in a thread pool (the Anthropic client is
   synchronous). Each returns a validated `SpecialistFinding`; each is persisted
   as an `AgentTask` row.
7. The strategy agent receives every specialist finding and returns an
   `ExecutiveBrief`, explicitly naming contradictions.
8. Citations are deduplicated and attached; the `engine` field is set to `llm`,
   `heuristic` or `hybrid` based on what actually ran.
9. If the recommendation commits resources, a `PENDING` `Approval` is created.
10. An `AuditEvent` is written and the row is committed.

Failure is contained at every level: an LLM error for one agent falls back to
the deterministic engine for that agent only, and the order still completes.

## Data model

12 tables, all business rows scoped by `company_id`.

```
companies ─┬─< users
           ├─< agents ────────< agent_tasks >──── work_orders ─┬─< approvals
           ├─< documents ──< document_chunks                    │
           ├─< facts                                            │
           ├─< metrics                                          │
           └─< work_orders ─────────────────────────────────────┘
audit_events (company-scoped, no FK - retained independently)
```

| Table | Holds |
|---|---|
| `companies` | the digital twin agents reason about |
| `users` | accounts, roles, bcrypt hashes |
| `agents` | per-company roster; system prompts and enable flags live here |
| `documents` / `document_chunks` | originals plus their sparse term-frequency index |
| `facts` | curated statements with classification and confidence |
| `metrics` | the time series analytics are computed from |
| `work_orders` | commands and their synthesised results |
| `agent_tasks` | one specialist's contribution to a work order |
| `approvals` | human decisions with comment and decider |
| `audit_events` | append-only trail of every meaningful mutation |

Enums are stored as native Postgres types. The initial migration explicitly drops
them on downgrade, because Postgres keeps `TYPE` objects after their tables are
dropped and a re-`upgrade` would otherwise fail with `DuplicateObject`.

## Retrieval

Ingestion: extract text → classify → summarise → chunk on paragraph boundaries
with overlap → store each chunk with a `{term: frequency}` map.

Query: tokenise (stopwords removed) → BM25 (`k1=1.5`, `b=0.75`) across the
company's chunks → return the top *k* with keyword-centred excerpts.

No embedding model, no vector store, no network call. To move to embeddings, add
a vector column to `document_chunks` and replace `rag.search`'s scoring loop —
`extract_text`, `chunk_text`, `index_document` and the API contract are unaffected.

## The two engines

| | Deterministic | Anthropic |
|---|---|---|
| Trigger | no `ANTHROPIC_API_KEY` | key present |
| Input | company profile, metric trends, retrieved chunks | the same, as a prompt |
| Output | `SpecialistFinding` / `ExecutiveBrief` | the same types, via structured outputs |
| Findings from | trend direction, magnitude, threshold rules | model reasoning over the context |
| Contradictions | rule-based (capacity vs growth, margin vs CAC) | model-identified |
| Cost / latency | zero / ~20ms | per-token / seconds |

Both produce the *same Pydantic types*, which is why the API, the UI and the tests
are identical either way, and why the fallback is safe rather than a degraded
special case.

## Security

- Bearer JWT, HS256, 12h expiry; `SECRET_KEY` under 32 bytes is fatal in production.
- bcrypt via the `bcrypt` library directly, input truncated to 72 bytes.
- Every query filters on the caller's `company_id`; there is no cross-tenant read path.
- Role hierarchy `OWNER > ADMIN > MEMBER > VIEWER` enforced by dependency, not by UI.
- Login returns an identical error for unknown accounts and wrong passwords.
- Uploads are size-capped and content-sniffed; unparseable binaries are rejected.
- Markdown artifacts are HTML-escaped before formatting, so agent output cannot
  inject markup into the page.

## Deliberate trade-offs

| Decision | Why | Cost |
|---|---|---|
| Synchronous work orders | no broker, no worker, no polling UI | long LLM runs hold a connection |
| BM25 over embeddings | works offline and in CI, no model to ship | no semantic matching |
| Hand-rolled SVG charts | no chart dependency, exact visual control | limited chart types |
| Hand-rolled Markdown renderer | artifacts use ~6 constructs; escaping is explicit | not CommonMark |
| Agent roster copied per company | per-company prompts and enable flags | roster changes need a backfill |

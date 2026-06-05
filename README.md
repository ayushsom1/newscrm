# News CRM

AI-assisted CRM for a regional newspaper covering its two revenue engines —
**advertising** and **circulation/subscriptions** — built around the principle
that AI does the routine and a human approves anything that matters.

> The detailed product spec lives in [`claude.md`](claude.md); the agile
> delivery plan lives in [`SPRINTS.md`](SPRINTS.md). This README is the
> "boot it and find your way around" guide.

---

## What's in the box

- **Advertisers + churn engine** — deterministic scoring (no LLM), CRUD,
  contracts, AI proposal drafting with human approval, audit trail.
- **Classifieds + pricing engine** — `Decimal` end-to-end, live quote as
  the user types, locked-in price at booking, status flow.
- **Subscribers + renewal engine + print-run forecast** — at-risk flagging,
  per-area daily target copies, idempotent renewal reminder jobs.
- **Complaints + AI triage** — sensitive cases (billing/disputes/abuse)
  always escalate via a rules engine that runs *before* the model; routine
  ops auto-resolve. Engine fallback on any AI failure.
- **AI proposal drafting** — grounded prose with `needs_human` gating for
  high-churn accounts.
- **Grounded assistant chat** — read-only CRM snapshot in the system prompt;
  the model can *propose* actions via tool calls but never executes them.
- **Dashboard + exception queue** — derived live, three buckets: AI handled,
  Needs you, Approve.
- **Government tender tracker** — manual entry, dashboard widget, deadlines
  in the queue.
- **Scheduled jobs** — nightly churn recompute, daily expire-contracts,
  daily renewal reminders. Idempotent per `(job, window_date)`.
- **Notifications** — provider-agnostic (`ConsoleNotifier` default; Resend
  stub when key is set). Every send writes an `AuditLog` row.
- **Users + roles + autonomy dial** — admin-only Settings page with toggles
  that change how aggressive the AI is allowed to be.
- **Per-IP rate limits** on `/auth/login` (10/min) and `/ai/*` (30/min).
- **Structured JSON logs** in production, plain text in dev.

---

## Stack

| Layer    | Tech                                                                 |
| -------- | -------------------------------------------------------------------- |
| Frontend | React + TypeScript (Vite), Tailwind, TanStack Query, RHF + Zod       |
| Backend  | FastAPI, SQLAlchemy 2, Pydantic v2, Alembic, APScheduler             |
| DB       | PostgreSQL 16                                                        |
| Auth     | JWT (`python-jose`) + bcrypt                                         |
| AI       | OpenRouter (OpenAI-compatible) via `httpx` — model-agnostic, env-set |
| Tests    | pytest (78+ tests); frontend has `tsc --noEmit` and vitest wired     |

OpenRouter was chosen over a single-vendor SDK so the model can be swapped
per-feature via `OPENROUTER_MODEL=...` with no code changes; in-platform
fallback routing is supported via `OPENROUTER_FALLBACK_MODELS=a,b,c`.

---

## Quickstart (dev)

```bash
git clone <repo>
cd newscrm
cp .env.example .env
# Edit .env: at minimum set OPENROUTER_API_KEY if you want AI features

docker compose up -d --build
```

That starts three services:

| Service  | Port | What                                  |
| -------- | ---- | ------------------------------------- |
| frontend | 3001 | Vite dev server with hot reload       |
| backend  | 8001 | FastAPI + APScheduler, code mounted   |
| db       | 5433 | Postgres 16 with named volume         |

> Ports are 3001/8001/5433 (not 3000/8000/5432) so the stack can run
> alongside other Docker projects without conflicts.

First-time setup:

```bash
# Apply migrations
docker compose exec -w /app backend alembic upgrade head

# Seed admin + sales + circulation + accounts users
docker compose exec -w /app backend python -m app.scripts.seed
```

Open `http://localhost:3001`, sign in with `admin@example.com` /
`admin123`.

---

## Environment

Document every variable in `.env.example`. The full list:

| Var                          | Purpose                                                          |
| ---------------------------- | ---------------------------------------------------------------- |
| `DATABASE_URL`               | Postgres URL (e.g. `postgresql+psycopg://crm:crm@db:5432/crm`)   |
| `SECRET_KEY`                 | JWT signing secret                                               |
| `CORS_ORIGINS`               | Comma-separated allowed origins                                  |
| `OPENROUTER_API_KEY`         | If unset, all AI features fall back to deterministic engines     |
| `OPENROUTER_MODEL`           | Default model slug (e.g. `openai/gpt-4o-mini`)                   |
| `OPENROUTER_FALLBACK_MODELS` | Comma-separated; OpenRouter falls through on error               |
| `OPENROUTER_BASE_URL`        | Override only for self-hosted gateways                           |
| `OPENROUTER_HTTP_REFERER`    | Attribution header                                               |
| `OPENROUTER_APP_TITLE`       | Attribution header                                               |
| `RESEND_API_KEY`             | If set, notifications use Resend stub; otherwise console + audit |
| `LOG_LEVEL`                  | `DEBUG` / `INFO` / `WARNING` / `ERROR`                           |
| `LOG_FORMAT`                 | `text` (dev) or `json` (prod)                                    |
| `DISABLE_SCHEDULER`          | `1` to skip APScheduler (used by tests)                          |
| `POSTGRES_*`                 | DB container init credentials                                    |
| `VITE_API_URL`               | Frontend → backend base URL                                      |

Secrets never enter the client. The frontend only sees `VITE_API_URL`.

---

## Architecture

```
news-crm/
  frontend/                       # React app
    src/
      pages/                      # route components
      components/                 # shared UI (AppShell, panels, badges)
      lib/                        # api client, auth ctx, locale ctx, format
      types/                      # API DTO types
  backend/
    app/
      api/                        # FastAPI routers per resource
      engines/                    # PURE deterministic services
                                  #   churn, pricing, renewal, printrun, triage
      ai/                         # Claude/OpenRouter client + prompt builders
                                  #   client, triage, drafter, assistant, snapshot
      services/                   # glue (churn cache, audit log, autonomy cache,
                                  #   notifications provider, renewal signal)
      models/                     # SQLAlchemy ORM
      schemas/                    # Pydantic DTOs
      jobs/                       # runners + APScheduler integration
      core/                       # config, db, security, deps, ratelimit, logging
    alembic/                      # migrations 0001..0010
    tests/                        # pytest suite
  docker-compose.yml              # dev (hot-reload, volume-mounted)
  docker-compose.prod.yml         # prod (multi-stage, nginx, JSON logs)
```

**The golden rule** (from `claude.md`):

- **Engines** compute (arithmetic, rules, money). No LLM. Fully tested.
- **AI** does language only (drafts, triage, summaries, chat).

The LLM never computes a price or a score. Every AI output is Pydantic-validated
and has a deterministic fallback. Every AI-taken or AI-drafted action writes
an `AuditLog` row with `actor="AI"`.

---

## Tests

```bash
# Backend (78+ tests)
docker compose exec -w /app -e DISABLE_SCHEDULER=1 backend pytest -q

# Frontend typecheck
docker compose exec -w /app frontend pnpm typecheck
```

Coverage includes engine boundaries, AI fallback paths, RBAC matrix, idempotency
guarantees on jobs, sensitive-keyword guardrails on triage, and end-to-end
approval flows for proposals + proposed actions.

---

## Production deployment

```bash
# Build multi-stage images and run them
docker compose -f docker-compose.prod.yml up -d --build
```

The prod compose:

- Builds with `Dockerfile.prod` (backend: builder + slim runtime, non-root user;
  frontend: Vite build → nginx alpine with SPA fallback).
- Sets `LOG_FORMAT=json` so logs are aggregator-friendly.
- Runs uvicorn with `--workers 2 --no-access-log` (route logging is at the
  reverse proxy).
- Requires `CORS_ORIGINS`, `SECRET_KEY`, `DATABASE_URL`, `VITE_API_URL` to be
  set (no permissive defaults).
- Has Docker healthchecks on backend (`/health`) and frontend (`/`).

Behind a reverse proxy (Caddy/Nginx/CloudFront), point `/api/*` at the backend
and everything else at the frontend, and the frontend's `VITE_API_URL=/api`
keeps the browser same-origin.

---

## Operating the AI

| Want to…                          | How                                                           |
| --------------------------------- | ------------------------------------------------------------- |
| Swap the model                    | Edit `OPENROUTER_MODEL=...`, restart backend                  |
| Add a fallback route              | `OPENROUTER_FALLBACK_MODELS=anthropic/claude-3-haiku,…`       |
| Turn off AI triage                | Settings → Autonomy → "AI complaint triage" off               |
| Force escalate everything         | Settings → "Auto-resolve routine triage" off                  |
| Turn off AI drafting              | Settings → "AI proposal drafting" off (engine template wins)  |
| Require ADMIN for assistant acts  | Settings → "Assistant actions require ADMIN to approve"       |
| Switch currency / tax labels      | Settings → Locale → Nepal (NPR/VAT) or India (₹/GST)          |
| Manually run a scheduled job      | Dashboard → Scheduled jobs → "Run now" (ADMIN)                |

---

## Common commands

```bash
# Full stack
docker compose up -d --build      # bring up
docker compose down               # stop
docker compose down -v            # stop + WIPE the DB volume

# DB
docker compose exec -w /app backend alembic upgrade head
docker compose exec -w /app backend alembic revision --autogenerate -m "msg"
docker compose exec db psql -U crm -d crm

# Audit trail
docker compose exec db psql -U crm -d crm -c \
  "select id, actor, action, entity, entity_id, created_at \
   from audit_logs order by id desc limit 20;"
```

---

## Roadmap snapshot

See [`SPRINTS.md`](SPRINTS.md) for the full plan. Sprints 0–11 are complete.
Future work: end-to-end Playwright tests, RAG over old articles / proposals,
SMS/WhatsApp notification provider, ingestion pipeline for government tenders.

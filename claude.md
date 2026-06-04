# CLAUDE.md — News CRM (production build)

Working instructions for building a **complete, fully-functional** AI News CRM — React frontend, FastAPI backend, PostgreSQL, all containerised. This is a build spec, not a demo. Read it fully before scaffolding or editing.

---

## 1. Goal

A working CRM for a regional newspaper covering its two revenue engines — **advertising** and **circulation/subscriptions** — with AI that removes repetitive work so staff supervise by exception. Core principle everywhere: **human-on-the-loop** — AI does the routine, a person approves anything that matters.

"Complete functionality" means: real auth and roles, real database persistence, real CRUD on every entity, real server-side Claude calls, working background jobs (renewal reminders, churn recompute), an approval flow for AI-drafted actions, an audit trail, and tests. No mocked data layers in the shipped app (seed data is fine for dev).

---

## 2. Tech stack (use these; don't substitute without reason)

- **Frontend:** React + TypeScript (Vite or CRA), Tailwind CSS, shadcn/ui components, Recharts for charts, TanStack Query for server state, react-hook-form + Zod for forms.
- **Backend:** Python **FastAPI** + **SQLAlchemy** + **Alembic** (migrations), **Pydantic** for schemas/validation.
- **Database:** PostgreSQL.
- **Auth:** JWT-based, **role-based** access.
- **AI:** Anthropic Python SDK, **backend-only**. Model `claude-sonnet-4-20250514` (confirm latest in product docs before shipping).
- **Notifications:** email via Resend/SMTP. SMS/WhatsApp optional behind a provider interface.
- **Jobs/scheduling:** a scheduled runner (APScheduler, or a cron-triggered authenticated endpoint) for renewal reminders and nightly churn recompute.
- **Containerisation:** Docker + Docker Compose (three services — see §8).
- **Tests:** pytest (backend), Vitest + React Testing Library and Playwright (frontend).

---

## 3. Architecture (monorepo)

```
news-crm/
  frontend/               # React app
    src/{pages,components,lib,api}/
    Dockerfile
    .dockerignore
  backend/                # FastAPI app
    app/
      api/                # routers per resource (+ ai/ for chat/draft/triage)
      engines/            # DETERMINISTIC services (churn, pricing) — pure, tested
      ai/                 # Claude client + prompt builders + Pydantic schemas
      models/             # SQLAlchemy models
      schemas/            # Pydantic request/response
      core/               # config, auth, db session
      jobs/               # scheduled tasks
    alembic/              # migrations
    Dockerfile
    .dockerignore
  docker-compose.yml      # frontend, backend, db
  .env.example
```

**Golden rule — split the brain:**
- **Deterministic engines** (`backend/app/engines/`) = arithmetic and rules: churn scoring, classified pricing, renewal-due logic. Pure functions, no LLM, fully unit-tested, repeatable.
- **Claude** (`backend/app/ai/`) = language only: drafting proposals/messages, understanding free-text complaints, the assistant chat, summarising. **Never let the LLM compute a price or a score.**

---

## 4. Data model (SQLAlchemy — adjust fields, keep the entities)

- **User** — name, email, role (`ADMIN` | `SALES` | `CIRCULATION` | `ACCOUNTS`), password_hash.
- **Advertiser** — name, category, contact_name/phone/email, annual_value, spend_trend, proposal_open_rate, status. Has many Contracts, Proposals, Activities.
- **Contract** — advertiser_id, start_date, end_date, value, slots, status.
- **Proposal** — advertiser_id, body, source (`AI_DRAFT` | `HUMAN`), status (`DRAFT` | `APPROVED` | `SENT`), created_by, approved_by.
- **Classified** — customer_name/phone, text, category, duration_days, price_net, price_gst, price_total, status (`QUOTED` | `PAID` | `PUBLISHED`), publish_date.
- **Subscriber** — name, area, plan, status. Has many Subscriptions.
- **Subscription** — subscriber_id, plan, start_date, renew_date, status.
- **Complaint** — subscriber_name/area, text, channel, triage (`AUTO` | `ESCALATED`), resolution, status, assigned_to.
- **GovTender** — title, dept, deadline, est_value, status (advertising tender tracker).
- **ExceptionQueueItem** — type, ref_id, summary, severity (`AUTO` | `APPROVE` | `HUMAN`), resolved.
- **Activity / AuditLog** — actor (user or `AI`), action, entity, entity_id, payload, timestamp. **Every AI-taken or AI-drafted action writes an AuditLog row.**

Churn score is **derived** by the engine, not stored as truth — store only inputs and an optional cached snapshot with a timestamp. All money columns are `Numeric`/`Decimal` (see §9).

---

## 5. Feature spec (what "working" means)

### Advertising
- CRUD advertisers and contracts.
- **Churn scoring** (engine) from spend_trend + open_rate + days_to_expiry → band low/med/high; recomputed nightly and on edit.
- **AI proposal drafting:** `POST /ai/draft` returns a Claude-written renewal/proposal; saved as `Proposal{source:AI_DRAFT, status:DRAFT}`. **A human must approve before send;** high-churn accounts are flagged "needs human" and never auto-sent.
- Contract-expiry tracking → exception queue + scheduled reminders.
- **Government/DIPR tender tracker** (manual entry now; ingestion later).

### Classifieds
- Intake form. **Pricing engine** computes net + GST + total from word count, category, duration (deterministic, live as the user types).
- AI may suggest a category/headline (language); **price is always the engine**.
- Booking → payment link (provider stub ok) → publish scheduling.

### Circulation / subscriptions
- CRUD subscribers + subscriptions.
- Renewal prediction (engine) → at-risk flag → scheduled renewal reminders.
- **Print-run forecast** per region (engine; seed with historical returns data when available).

### Complaints
- Intake. **AI triage** `POST /ai/triage-complaint` returns Pydantic-validated `{auto: bool, resolution: str}`.
- `auto=true` routine ops (non-delivery, pause, plan change) → resolved + actions logged. `auto=false` (billing/disputes) → **escalated to a human**, assigned, never auto-resolved.

### Assistant
- Chat at `/assistant`, `POST /ai/chat`. Backend injects a **compact, read-only CRM snapshot** as grounding context. The assistant answers and may *propose* actions, but actions still go through the approval flow.

### Dashboard
- KPIs + the **exception queue** (the human-on-the-loop surface): mostly AI-handled items, a few "needs you", a few "approve".

### Settings
- User/role management. **Autonomy thresholds**: admins set what the AI may do autonomously vs. what requires approval (the "dial").

---

## 6. AI integration rules (backend-only, non-negotiable)

- **Key never reaches the client.** All Claude calls run in the FastAPI backend; `ANTHROPIC_API_KEY` is backend env only.
- **Ground, don't hallucinate.** Pass real DB context in the system prompt; instruct the model not to invent advertisers/numbers.
- **Validate every structured output with Pydantic.** On parse/validation failure, fall back to the deterministic engine and log it — never crash the request.
- **Human-in-the-loop gates.** AI drafts and proposed actions are persisted as `DRAFT`/pending and require an authorised user to approve. Billing/disputes/anything sensitive are escalated, not actioned.
- **Audit everything.** Each AI draft, triage, or action writes an AuditLog row (actor=`AI`).
- **Cost/latency:** keep `max_tokens` tight per task; cache where sensible; rate-limit AI routes.

---

## 7. Environment

Document every variable in `.env.example`. Never hardcode secrets.

```
# backend
DATABASE_URL=postgresql://crm:crm@db:5432/crm
SECRET_KEY=...                  # JWT signing
ANTHROPIC_API_KEY=...           # backend only
CORS_ORIGINS=http://localhost:3000
RESEND_API_KEY=...              # or SMTP_*
# db
POSTGRES_USER=crm
POSTGRES_PASSWORD=crm
POSTGRES_DB=crm
# frontend
REACT_APP_API_URL=http://localhost:8000
```

---

## 8. Version Control Workflow — Agile, Feature-Driven (IMPORTANT)

This project must be built **incrementally** with version control that reflects each feature's progress, in the spirit of agile delivery. **Do not commit the whole project in one big dump.** Commit history should read like a story of small, working increments. Treat each numbered step in §10 as one (or a few) PR-sized user stories.

### 8.1 Branching model (GitHub Flow)
- `main` always stays deployable.
- Every feature/user story gets its own short-lived branch off `main`.
- Branch naming: `feat/<area>-<short-desc>`, `fix/<short-desc>`, `chore/<short-desc>`.
  - e.g. `feat/advertiser-crud`, `feat/order-inventory-logic` → here `feat/classified-pricing`, `fix/phone-uniqueness`.
- Open a Pull Request, self-review, then merge into `main`. Delete the branch after merge.

### 8.2 Conventional Commits
Format: `type(scope): short summary`
Allowed types: `feat`, `fix`, `chore`, `docs`, `refactor`, `test`, `build`, `ci`.
Examples:

```
feat(advertisers): add POST and GET endpoints
feat(classifieds): compute price atomically on booking
fix(subscribers): enforce unique phone with 409 response
test(complaints): cover billing-dispute escalation
docs(readme): add local setup and deployment steps
build(docker): add backend Dockerfile and compose service
```

Keep commits small and focused — one logical change each. Commit when something works, not at the end of the day. Imperative mood, lowercase, no trailing period, ~≤72 chars; use a body for the *why* when not obvious.

### Docker Rules
- Slim/lightweight base images (e.g. `python:3.12-slim`, `node:20-alpine`).
- No hardcoded credentials — everything via environment variables.
- Named volume for PostgreSQL persistence.
- A `.dockerignore` per service (exclude `node_modules`, `__pycache__`, `.env`, etc.).
- `docker-compose.yml` runs three services: `frontend`, `backend`, `db`.

### Common Commands

```bash
# Full stack (local dev)
docker compose up --build           # build + run frontend, backend, postgres
docker compose down                 # stop
docker compose down -v              # stop + wipe DB volume
```

---

## 9. Conventions

- **Secrets:** only in environment variables; document them in `.env.example`.
- **Money:** store prices as numeric/decimal, not float, to avoid rounding errors.
- **Errors:** return structured JSON error bodies (`{"detail": "..."}`), consistent shape.
- **CORS:** backend must allow the deployed frontend origin.
- **API base URL** on the frontend comes from an env var (`REACT_APP_API_URL`), never hardcoded.
- **TypeScript strict** on the frontend; type hints + Pydantic on the backend. Validate all external/AI input.
- **No business arithmetic in the LLM.** Pricing and scoring live in the deterministic engines.
- **UI:** clean enterprise look (Zoho/Salesforce polish) — fixed sidebar, top bar, data tables, cards. **Plain, highly readable fonts** (client preference: no decorative/serif display type). Accent palette: ink `#1C1A16`, red `#9E1B17`, semantic green/amber/blue; blue = AI accent. Accessible: real labels, keyboard nav, focus states.

### Per-change checklist (before opening a PR)
1. Branch off the latest `main` with a correctly named branch.
2. Smallest coherent change that delivers a working slice.
3. Backend `pytest` + frontend tests pass; lint/type checks pass.
4. New logic has tests; AI features have a tested deterministic fallback; DB changes ship an Alembic migration.
5. Commits follow Conventional Commits; no `wip`/`stuff` clutter on `main`.
6. Open a PR, self-review the diff, merge, delete the branch.

**Don't:** one giant initial commit · commit to `main` directly · long-lived drifting branches · vague messages.

---

## 10. Build order (each step = one or a few PR-sized stories)

1. `chore`: scaffold monorepo, docker-compose (frontend/backend/db), `.env.example`, `.dockerignore`s. App boots, DB connects.
2. `feat(auth)`: JWT auth + roles + app shell (sidebar, top bar, dashboard skeleton).
3. `feat(advertisers)`: advertiser CRUD + churn engine + tests.
4. `feat(classifieds)`: intake + pricing engine (decimal) + tests.
5. `feat(subscribers)`: subscribers/subscriptions + renewal engine + print-run forecast.
6. `feat(complaints)`: complaints CRUD + AI triage (with engine fallback) + escalation.
7. `feat(ai)`: proposal drafting + approval flow + audit log.
8. `feat(assistant)`: grounded AI chat.
9. `feat(dashboard)`: exception queue + KPIs.
10. `feat(jobs)`: scheduled reminders + nightly churn recompute + notifications.
11. `feat(settings)`: users, roles, autonomy thresholds.
12. `test`/`docs`/`build`: e2e tests, README, deployment polish.

Each step may split into smaller commits/PRs (schema → engine → endpoint → UI → tests). Prefer more, smaller PRs over one large one. `main` stays deployable after every merge.

---

## 11. Honesty & product guardrails (carry into UI copy)

- Label AI-generated content as such; show drafts as drafts awaiting approval.
- Present projected metrics as **"illustrative targets to validate in a pilot"**, never guarantees.
- Always show the AI **escalating** sensitive cases rather than overreaching — the escalation path is a feature.
- Keep a visible audit trail; let admins tune autonomy.

---

## 12. Domain glossary (for non-newspaper devs)

advertiser = business paying for ads · agency = ad middle-man · rate card = ad price list · proposal = offer doc sent to an advertiser · contract = agreement to run ads over a period · renewal = signing up again · churn = customers leaving · classifieds = small text ads · DIPR/tender = government ad process · subscriber = paying reader · circulation = print delivery · distributor/agent/hawker = delivery chain · returns = unsold copies · print-run forecast = predict copies per region to cut waste.

---

## 13. Localisation

UI and AI output support the local language (Hindi or **Nepali**, both Devanagari). Keep commercial context configurable in Settings, never hardcoded: India = ₹/GST/Sunday special; Nepal = NPR/VAT/Saturday.
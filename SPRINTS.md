# SPRINTS.md — News CRM Delivery Plan

> **Status: Sprints 0–11 complete (all delivered, merged to `main`).**
> Backend pytest: 86 passing · Migrations: 10 · Frontend typechecks clean
> · Playwright e2e suite (3 specs) added in Sprint 11/12 polish · CI green.

Agile, feature-driven delivery plan derived from `claude.md` §10 (build order) and §5 (feature spec). Each sprint = ~1 week of focused work, shippable to `main`, made of small PRs. Every sprint ends with `main` deployable.

---

## Sprint 0 — Foundation & Scaffolding
**Goal:** Repo boots end-to-end in Docker; DB connects; CI green.

**Stories**
- `chore(repo)`: monorepo layout (`frontend/`, `backend/`, `docker-compose.yml`, `.env.example`).
- `build(docker)`: backend (`python:3.12-slim`) + frontend (`node:20-alpine`) Dockerfiles, `.dockerignore`s, named PG volume.
- `chore(backend)`: FastAPI skeleton, SQLAlchemy session, Alembic init, health endpoint.
- `chore(frontend)`: Vite + TS + Tailwind + shadcn/ui + TanStack Query + react-hook-form/Zod set up.
- `ci`: lint + typecheck + tests on PR.

**Done when:** `docker compose up --build` runs all three services; `/health` returns 200; FE loads blank shell talking to BE.

---

## Sprint 1 — Auth, Roles & App Shell
**Goal:** Real users can log in; role gates protect routes; the navigational shell exists.

**Stories**
- `feat(auth-backend)`: User model, password hashing, JWT issue/verify, `/auth/login`, `/auth/me`.
- `feat(auth-roles)`: role enum (`ADMIN | SALES | CIRCULATION | ACCOUNTS`), dependency-based role guards.
- `feat(auth-frontend)`: login page, auth context, axios/fetch interceptor injecting JWT, protected routes.
- `feat(shell)`: fixed sidebar + top bar + dashboard skeleton (empty cards), brand palette (ink `#1C1A16`, red `#9E1B17`), plain readable fonts.
- `test`: backend auth tests, RBAC tests.

**Done when:** wrong role = 403; logged-in user lands on dashboard skeleton; seed admin works.

---

## Sprint 2 — Advertisers & Churn Engine
**Goal:** Full advertiser CRUD with deterministic churn scoring.

**Stories**
- `feat(advertisers-schema)`: Advertiser + Contract models + Alembic migration.
- `feat(advertisers-api)`: CRUD endpoints, pagination, filtering by status/category, role gates (SALES/ADMIN write).
- `feat(churn-engine)`: pure function `score(spend_trend, open_rate, days_to_expiry) → {score, band}`; unit tests covering boundaries.
- `feat(advertisers-ui)`: list (table), detail, create/edit forms (RHF+Zod), churn band chip.
- `feat(contracts)`: nested CRUD under advertiser; expiry surfaced.
- `test`: engine boundary tests; API integration tests.

**Done when:** create advertiser → contract → churn band displayed; nightly recompute hook stub exists.

---

## Sprint 3 — Classifieds & Pricing Engine
**Goal:** Intake → live deterministic price → booking → publish schedule.

**Stories**
- `feat(classifieds-schema)`: Classified model (Decimal money cols) + migration.
- `feat(pricing-engine)`: `quote(words, category, duration) → {net, gst, total}` using `Decimal`; tests for rounding, GST, locale (IN ₹/GST, NP NPR/VAT).
- `feat(classifieds-api)`: `POST /classifieds/quote` (no persist), `POST /classifieds` (atomic price snapshot at booking), status transitions `QUOTED → PAID → PUBLISHED`.
- `feat(classifieds-ui)`: intake form with live quote; booking confirm; publish-date picker.
- `feat(payments-stub)`: provider interface + stub link generation.

**Done when:** typing into intake updates price live; bookings persist with locked-in price; payment stub flow works.

---

## Sprint 4 — Subscribers, Renewals & Print-Run Forecast
**Goal:** Circulation side end-to-end with renewal risk and forecast.

**Stories**
- `feat(subscribers-schema)`: Subscriber + Subscription models + migration; unique phone constraint.
- `feat(subscribers-api)`: CRUD + subscription lifecycle (start/renew/cancel).
- `feat(renewal-engine)`: at-risk flag from `days_to_renew` + payment history; tests.
- `feat(printrun-engine)`: per-region forecast from active subs + returns (seed historical data); tests.
- `feat(subscribers-ui)`: list, detail, renewal calendar; forecast widget on dashboard skeleton.
- `fix(subscribers)`: 409 on duplicate phone.

**Done when:** at-risk subs flagged; forecast visible per region.

---

## Sprint 5 — Complaints & AI Triage (first AI feature)
**Goal:** Complaints intake with Claude triage + deterministic fallback + escalation.

**Stories**
- `feat(complaints-schema)`: Complaint model + migration.
- `feat(complaints-api)`: CRUD + assignment + status flow.
- `feat(ai-client)`: Anthropic SDK wrapper (`backend/app/ai/`), prompt builders, rate-limit middleware, AuditLog model + writer.
- `feat(ai-triage)`: `POST /ai/triage-complaint` → Pydantic-validated `{auto: bool, resolution: str}`; on validation failure → rules-based fallback (non-delivery/pause/plan-change = AUTO; billing/dispute = ESCALATED).
- `feat(complaints-ui)`: intake; triage result panel; escalation queue tab.
- `test`: golden tests for fallback; mocked AI response tests; **billing-dispute always escalated** test.

**Done when:** routine complaints auto-resolve with audit row; sensitive ones escalate to an assignee.

---

## Sprint 6 — AI Proposal Drafting & Approval Flow
**Goal:** Claude drafts renewals; humans approve before send; everything audited.

**Stories**
- `feat(proposals-schema)`: Proposal model (source, status, created_by, approved_by) + migration.
- `feat(ai-draft)`: `POST /ai/draft` grounded with advertiser+contract+churn snapshot; persists `Proposal{source:AI_DRAFT, status:DRAFT}`.
- `feat(approval-flow)`: `POST /proposals/{id}/approve` (role-gated), `POST /proposals/{id}/send` (stub send), high-churn auto-flag "needs human".
- `feat(audit-log)`: every AI draft / approve / send writes AuditLog (actor=AI or user).
- `feat(proposals-ui)`: draft preview with "AI-generated — needs approval" banner, diff/edit before approve, send button gated by role.
- `test`: high-churn never auto-sendable; audit row written on each step.

**Done when:** draft → review → approve → send loop works with audit trail visible.

---

## Sprint 7 — Grounded Assistant Chat
**Goal:** `/assistant` chat answers using read-only CRM snapshot; proposes (never executes) actions.

**Stories**
- `feat(ai-snapshot)`: compact JSON snapshot builder (counts, at-risk, expiring, top advertisers) — read-only.
- `feat(ai-chat)`: `POST /ai/chat` streams Claude response with snapshot in system prompt; max_tokens tight; rate-limited.
- `feat(assistant-ui)`: chat page, message history (session-scoped), "Proposed action" cards routed to approval flow.
- `test`: prompt grounding test; assistant never returns invented advertiser names (golden snapshot).

**Done when:** assistant answers grounded questions; proposed actions land in the approval queue, not direct execution.

---

## Sprint 8 — Dashboard & Exception Queue
**Goal:** The human-on-the-loop surface.

**Stories**
- `feat(exception-schema)`: ExceptionQueueItem model + migration (`type`, `severity: AUTO|APPROVE|HUMAN`).
- `feat(exception-producers)`: engines + AI features write items (expiring contracts, at-risk renewals, AI drafts pending, escalated complaints).
- `feat(dashboard-api)`: KPI aggregates (advertisers, MRR/ARR proxy, at-risk subs, queue counts).
- `feat(dashboard-ui)`: KPI cards, exception queue with filter tabs (AUTO handled / APPROVE / NEEDS YOU), inline actions.
- `feat(govtender)`: simple CRUD + dashboard widget.

**Done when:** dashboard reflects real state; queue is the single source of "what needs me".

---

## Sprint 9 — Scheduled Jobs & Notifications
**Goal:** The CRM works while no one is looking.

**Stories**
- `feat(jobs-runner)`: APScheduler in backend (or cron-triggered authenticated endpoint).
- `feat(job-churn)`: nightly churn recompute → updates cached snapshot + queue items.
- `feat(job-renewals)`: daily expiry/renewal scan → reminder emails + queue items.
- `feat(notifications)`: Resend/SMTP email; provider interface so SMS/WhatsApp can plug in later.
- `test`: time-mocked job tests; idempotency tests.

**Done when:** running the job locally fires correct emails + queue items; nothing fires twice for the same window.

---

## Sprint 10 — Settings, Autonomy Dial & Localisation
**Goal:** Admins control users, roles, AI autonomy; UI/AI speak Hindi or Nepali.

**Stories**
- `feat(settings-users)`: admin user CRUD + role assignment + password reset.
- `feat(autonomy-thresholds)`: per-feature autonomy config (auto-send threshold, triage auto cap, etc.) consumed by AI gates.
- `feat(locale)`: i18n scaffolding (en / hi / ne), Devanagari font check, locale-aware money + GST/VAT, weekly-special day (IN: Sun, NP: Sat).
- `feat(commercial-config)`: currency/tax rules moved to Settings, no hardcoding.

**Done when:** admin can dial AI autonomy down to 0 (everything → approval); switching locale changes copy + commercial rules.

---

## Sprint 11 — Hardening: Tests, Docs, Deployment Polish
**Goal:** Production-ready.

**Stories**
- `test(e2e)`: Playwright happy paths (login → advertiser → AI draft → approve; complaint → triage → escalate; classified intake → publish).
- `test(backend)`: coverage on engines (100% targets), AI fallback paths, RBAC matrix.
- `docs(readme)`: local setup, env vars, deployment, architecture diagram.
- `build(deploy)`: production Dockerfiles (multi-stage), CORS lockdown, structured logging (pino/structlog), error JSON shape audit.
- `chore(security)`: input validation pass, rate limits on `/ai/*` and `/auth/*`, secret scan in CI.

**Done when:** fresh clone → `docker compose up` → working app; CI green; README sufficient for a new dev.

---

## Cross-cutting rules (apply every sprint)

- Branch off latest `main`: `feat/<area>-<desc>`, `fix/<desc>`, `chore/<desc>`.
- Conventional Commits, small focused PRs, self-review, delete branch on merge.
- Every PR ships: tests for new logic, Alembic migration for schema changes, AI features ship deterministic fallback.
- AI never computes prices or scores — engines only. AI output always Pydantic-validated.
- AuditLog row for every AI draft/action.
- Money columns = `Decimal`. Errors = `{"detail": "..."}`.
- UI labels AI content as AI; drafts are clearly drafts; sensitive cases visibly escalate.

---

## Suggested cadence

- 1 sprint ≈ 1 week (adjust to team size).
- Sprints 0–4 = deterministic foundation (no AI yet — engines first, per §3 golden rule).
- Sprints 5–7 = AI layered onto a working CRM.
- Sprints 8–11 = surface, automation, polish.

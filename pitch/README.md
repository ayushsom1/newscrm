# Sales pitch deck

`news-crm-pitch.pptx` — 12-slide sales overview, brand palette from
`claude.md` (ink `#1C1A16`, brand red `#9E1B17`, AI blue), Calibri throughout.

## Regenerate

The deck is built from primitives in `generate.py` — no fragile template
file. To re-render after edits:

```bash
# Inside the backend container (Python 3.12 is already there)
docker compose exec backend pip install --quiet python-pptx==1.0.2
docker cp pitch/generate.py newscrm-backend-1:/tmp/generate.py
docker compose exec -w /tmp backend python generate.py
docker cp newscrm-backend-1:/tmp/news-crm-pitch.pptx pitch/news-crm-pitch.pptx
```

Or on the host with any Python 3.11+ environment:

```bash
pip install python-pptx==1.0.2
python pitch/generate.py
```

## Deck outline

| # | Slide | Purpose |
| --- | --- | --- |
| 1 | Cover | Product name, tagline, market positioning |
| 2 | Problem | Three pain points regional newspapers actually have |
| 3 | What we built | Three pillars: Advertising, Circulation, Operations |
| 4 | Human-on-the-loop | The principle — what AI handles vs approves vs escalates |
| 5 | For sales | Churn engine + AI proposal drafting with approval |
| 6 | For circulation | At-risk flagging, print-run forecast, reminders, triage |
| 7 | Exception queue | Mock UI of the dashboard surface |
| 8 | Architecture | "Split the brain" — engines deterministic, AI language-only |
| 9 | Autonomy dial | Settings mock — admin controls the AI's scope |
| 10 | Locale | India / Nepal day-one support |
| 11 | Pilot path | 8-week timeline, then a decision |
| 12 | Call to action | Concrete next step |

## Honesty rules from `claude.md` §11

The deck follows the product guardrails:

- Projected metrics are framed as **illustrative targets to validate in a
  pilot**, never as guarantees.
- The "AI escalates sensitive cases" path is presented as a feature, not
  a limitation.
- The audit trail and autonomy dial are surfaced so prospects see the
  governance, not just the magic.

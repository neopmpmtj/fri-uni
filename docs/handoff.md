# Session handoff

> **Last updated:** 2026-09-06 10:15 WEST (Europe/Lisbon)  
> Replace with the current date and time whenever you edit this file.

## Project

Internal back office for one HVAC company (slice of “universe”). Staff create **proforma invoices**: client-facing quotes showing equipment to be installed and what it will cost, including an upfront-payment discount. Not an official finance document.

**MVP:** email+password login → dashboard (pick EN/PT once) → clients/sites (list + drawer) → draft proforma (work page + line drawer) → issue/lock snapshots → on-screen quote + PDF download. Catalog lives in Django admin. CLI is the last phase.

## Start here (new agent)

Do **not** rebuild the whole app in one chat unless the user explicitly asks. [`docs/project-plan.md`](project-plan.md) is stoppable: **one phase per session**.

Read in this order:

1. This file
2. [`docs/project-plan.md`](project-plan.md) — build order, files, tests (Phase 1 next)
3. [`docs/data-points.md`](data-points.md) — tables/fields before any model
4. [`docs/front-end-project-plan.md`](front-end-project-plan.md) — before any staff HTML/CSS/JS
5. [`docs/preliminary_project-plan.md`](preliminary_project-plan.md) — product scope if a decision is unclear

Warehouse_V2 chrome reference: <https://github.com/neopmpmtj/warehouse_V2> (`docs/i18n-pattern.md`, item console drawer, dashboard language). Do not clone warehouse product features.

## Done

- Bootstrap: Django `conf/`, `accounts.User` (email login, unused Google OAuth flags), pytest-django, deploy stubs
- Product interview closed: [`preliminary_project-plan.md`](preliminary_project-plan.md), [`data-points.md`](data-points.md)
- Implementation playbook: [`project-plan.md`](project-plan.md) — Phases 1–8, unchecked
- Front-end chrome spec: [`front-end-project-plan.md`](front-end-project-plan.md) — dashboard language, gear menu, list+drawer, tokens
- Skill: `.cursor/skills/eliciting-project-model/`

## Not done

- Phase 1 — login, `role`, dashboard, i18n, work shell (no application UI yet)
- Phase 2 — `office` models / migrate
- Phase 3 — catalog admin + `seed_catalog`
- Phase 4 — clients/sites list+drawer
- Phase 5–6 — draft / issue / cancel
- Phase 7 — on-screen quote + WeasyPrint PDF
- Phase 8 — `create_proforma` CLI
- Production deploy; `.env` / local migrate may still be unset

## Next

**Phase 1** in [`project-plan.md`](project-plan.md), chrome from [`front-end-project-plan.md`](front-end-project-plan.md).

Thin spots a later agent may have to ask or pick a default (not blockers for Phase 1): company name/logo/address on the PDF letterhead; exact seed catalog prices; SQLite vs PostgreSQL live-only unique indexes (called out in Phase 2).

## Commands

```bash
source .venv/bin/activate
cp .env.example .env
.venv/bin/python manage.py migrate
.venv/bin/python manage.py runserver
pytest
```

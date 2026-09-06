# Session handoff

> **Last updated:** 2026-09-06 10:58 WEST (Europe/Lisbon)  
> Replace with the current date and time whenever you edit this file.

## Project

Internal back office for one HVAC company (slice of “universe”). Staff create **proforma invoices**: client-facing quotes showing equipment to be installed and what it will cost, including an upfront-payment discount. Not an official finance document.

**MVP:** email+password login → dashboard (pick EN/PT once) → clients/sites (list + drawer) → draft proforma (work page + line drawer) → issue/lock snapshots → on-screen quote + PDF download. Catalog lives in Django admin. CLI: `create_proforma`.

## Start here (new agent)

Staff app is **`proformas`** (`accounts` is User/login only). Playbook (all phases ticked): [`docs/project-plan.md`](project-plan.md). Schema: [`docs/data-points.md`](data-points.md). Chrome: [`docs/front-end-project-plan.md`](front-end-project-plan.md).

Warehouse_V2 is chrome reference only — do not clone warehouse product features.

Uncommitted implementation is on `main` (ahead of origin by 1, plus a large unstaged tree). Do not commit unless asked.

## Done

- Phases 1–8: login/`role`/dashboard i18n, models, catalog admin + `seed_catalog`, clients/sites drawers, draft quoting, issue/cancel snapshots, on-screen quote + WeasyPrint PDF, `create_proforma` CLI
- Domain app named `proformas` (not `office`)
- Local smoke this session: `seed_catalog`, `runserver`, login, dashboard, `/clients/` (200)
- pytest: 25 passed

## Not done

- Production deploy; work is not committed
- Company name/logo/address on PDF letterhead (placeholder `fri-uni`)
- Real catalog prices (seed uses round demo numbers)
- Full browser pass of sites / draft / issue / PDF (clients list was opened; drawers not fully exercised)
- Email send / stored PDFs / Google OAuth / dark theme / indoor-outdoor auto-pair

## Next

Continue local click-through (sites, new draft, lines, issue, quote/PDF), then commit when asked. Letterhead and live prices when the user supplies them.

Dev-server 404s for `/json/version` and `/service-worker.js` are the browser (DevTools / leftover SW on `127.0.0.1:8000`), not missing app routes. Unregister the service worker in DevTools if the log is noisy. Do not add a dummy SW.

## Commands

```bash
source .venv/bin/activate
cp .env.example .env
.venv/bin/python manage.py migrate
.venv/bin/python manage.py createsuperuser
.venv/bin/python manage.py seed_catalog
.venv/bin/python manage.py runserver
pytest
```

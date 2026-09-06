# Session handoff

> **Last updated:** 2026-09-06 16:17 WEST (Europe/Lisbon)  
> Replace with the current date and time whenever you edit this file.

## Project

Internal back office for one HVAC company (slice of “universe”). Staff create **proforma invoices**: client-facing quotes showing equipment to be installed and what it will cost, including an upfront-payment discount. Not an official finance document.

**MVP:** email+password login → dashboard (pick EN/PT once) → clients/sites (list + drawer) → draft proforma (work page + line drawer) → issue/lock snapshots → on-screen quote + PDF download. Catalog is staff pages (Items daily; Families / Sub-families / Manufacturers setup). CLI: `create_proforma`.

## Start here (new agent)

Staff app is **`proformas`** (`accounts` is User/login only). Playbook: [`docs/project-plan.md`](project-plan.md). Schema: [`docs/data-points.md`](data-points.md). Chrome: [`docs/front-end-project-plan.md`](front-end-project-plan.md).

Catalog: **family → sub-family → item**, plus **manufacturer** (`Brand`) on the item. Sales price is edited only on the manufacturer pricelist (reason required). Django admin is not the catalog UI.

This catalog slice is **uncommitted** (modified + untracked files). Do not run `seed_demo` in production.

Local DB was recreated for migration `proformas.0002_catalog_items`. If `db.sqlite3` is missing: `migrate` then `seed_demo`. Restart `runserver` after that.

## Done

- Catalog schema: `Family`, `SubFamily` (was Style, now belongs to family not brand), `Item` (was EquipmentModel) with `internal_code`, `is_default`, optional `max_volume_m3`
- Dashboard daily cards (Clients, Sites, Proformas, Items) and setup cards (Families, Sub-families, Manufacturers)
- Items page is identity only (no sales price). Manufacturer row → sales pricelist (reason required)
- Line drawer: Family → Sub-family → Manufacturer → Item; defaults pre-select AC then Split
- Seed: AC (default), underfloor, DHW; Sensira/etc. are global AC sub-families; 9000 BTU indoor `max_volume_m3=20`
- Manufacturer pricelist href typo (`}}` instead of `%}`) fixed after a 404 on `/manufacturers/`
- `seed_demo`: admin + manager, three clients, five sites, five proformas. Manager cannot soft-delete
- pytest: 35 passed

## Not done

- Production deploy
- Company name/logo/address on PDF letterhead (placeholder `fri-uni`)
- Real catalog prices (seed uses round demo numbers)
- Volume-based auto-pick (field stored only)
- Indoor/outdoor auto-pair (`model_default_matches`)
- Email send / stored PDFs / Google OAuth / dark theme
- Tubing / parameters still Django admin (later setup cards)
- Commit of this catalog slice (not requested)

## Next

Hard-refresh Manufacturers and open **Pricelist** (the 404 should be gone). Then add a line on a draft: AC should already be selected. Then set a sales price on Daikin with a reason.

Dev-server 404s for `/json/version` and `/service-worker.js` are the browser, not missing app routes.

## Commands

```bash
source .venv/bin/activate
cp .env.example .env
.venv/bin/python manage.py migrate
.venv/bin/python manage.py seed_demo
.venv/bin/python manage.py runserver
pytest
```

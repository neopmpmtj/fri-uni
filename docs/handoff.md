# Session handoff

> **Last updated:** 2026-09-06 16:51 WEST (Europe/Lisbon)  
> Replace with the current date and time whenever you edit this file.

## Project

Internal back office for one HVAC company (slice of “universe”). Staff create **proforma invoices**: client-facing quotes showing equipment to be installed and what it will cost, including an upfront-payment discount. Not an official finance document.

**MVP:** email+password login → dashboard (pick EN/PT once) → clients/sites (list + drawer) → draft proforma (work page + line drawer) → issue/lock snapshots → on-screen quote + PDF download. Catalog is staff pages (Items daily; Families / Sub-families / Manufacturers / VAT / Parameters / Tubing setup). CLI: `create_proforma`.

## Start here (new agent)

Staff app is **`proformas`** (`accounts` is User/login only). Playbook: [`docs/project-plan.md`](project-plan.md). Schema: [`docs/data-points.md`](data-points.md). Chrome: [`docs/front-end-project-plan.md`](front-end-project-plan.md).

Catalog: **family → sub-family → item**, plus **manufacturer** (`Brand`) and **VAT rate** on the item. Sales price is edited only on the manufacturer pricelist (reason required). Django admin is users and audit only.

On branch `cursor/convert-to-warehouse-style` (one commit already on origin). This VAT/setup slice is **uncommitted**. Do not run `seed_demo` in production.

Local DB has migration `proformas.0003_vat_rates`. If `db.sqlite3` is missing: `migrate` then `seed_demo`. Restart `runserver` after that.

## Done

- Catalog schema: `Family`, `SubFamily`, `Item` with `internal_code`, `is_default`, optional `max_volume_m3`, required `vat_rate`
- `VatRate`: Portugal IVA seed 23% (default), 13%, 6%, Exempt; staff enter percent, stored 0–1
- Dashboard daily cards (Clients, Sites, Proformas, Items) and setup cards (Families, Sub-families, Manufacturers, VAT rates, Parameters, Tubing lengths)
- Items page is identity only (no sales price). VAT column + drawer select (new item pre-selects 23%)
- Manufacturer row → sales pricelist (reason required). Tubing price still needs a reason
- Parameters: edit known keys only (no New/Delete)
- Line drawer: Family → Sub-family → Manufacturer → Item; defaults pre-select AC then Split
- Seed: AC (default), underfloor, DHW; all items `VAT23`; 9000 BTU indoor `max_volume_m3=20`
- `seed_demo`: admin + manager. Manager cannot soft-delete
- pytest: 40 passed

## Not done

- Production deploy
- Company name/logo/address on PDF letterhead (placeholder `fri-uni`)
- Real catalog prices (seed uses round demo numbers)
- Volume-based auto-pick (field stored only)
- Indoor/outdoor auto-pair (`model_default_matches`)
- VAT on proforma line math / snapshots / PDF
- Email send / stored PDFs / Google OAuth / dark theme
- Commit of this slice (not requested)

## Next

Restart `runserver`, hard-refresh the dashboard, open **VAT rates** then **Items → New item** (23% should already be selected). Then Parameters and Tubing from Setup.

Quoting still ignores VAT.

## Commands

```bash
source .venv/bin/activate
cp .env.example .env
.venv/bin/python manage.py migrate
.venv/bin/python manage.py seed_demo
.venv/bin/python manage.py runserver
pytest
```

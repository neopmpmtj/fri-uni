# Session handoff

> **Last updated:** 2026-09-07 09:43 WEST (Europe/Lisbon)  
> Replace with the current date and time whenever you edit this file.

## Project

Internal back office for one HVAC company (slice of “universe”). Staff create **proforma invoices**: client-facing quotes showing equipment to be installed and what it will cost, including an upfront-payment discount. Not an official finance document.

**MVP:** email+password login → dashboard (pick EN/PT once) → clients/sites (list + drawer) → draft proforma (work page + line drawer) → issue/lock snapshots → on-screen quote + PDF download. Catalog is staff pages (Items daily; Families / Sub-families / Manufacturers / VAT / Parameters / Tubing setup). CLI: `create_proforma`.

## Start here (new agent)

Staff app is **`proformas`** (`accounts` is User/login only). Playbook: [`docs/project-plan.md`](project-plan.md). Schema: [`docs/data-points.md`](data-points.md). Chrome: [`docs/front-end-project-plan.md`](front-end-project-plan.md).

**NIF and phone validation:** [`.cursor/rules/portuguese-nif-and-phone.mdc`](../.cursor/rules/portuguese-nif-and-phone.mdc) — reuse `validate_tax_number`, `validate_phone_number`, `configure_nine_digit_form_field` in `proformas/services.py`.

Catalog: **family → sub-family → item**, plus **manufacturer** (`Brand`) and **VAT rate** on the item. Sales price is edited only on the manufacturer pricelist (reason required). Django admin is users and audit only.

Do not run `seed_demo` in production. Fresh local DB: `rm -f db.sqlite3`, then `migrate` and `seed_demo`. Restart `runserver` after schema changes.

## Done (this session)

- **Client create/edit field rules:** NIF and billing address optional; phone and email required; kind/country defaults unchanged (Person, PT)
- **NIF validation:** distinct fewer/more than 9 digits; no silent trim (`configure_nine_digit_form_field` on forms)
- **`countries` table** (PT, ES, FR, DE, BE); client `phone_country` + 9-digit national `phone`; `+351` prefix in UI
- **Client contact (optional):** `contact_name`, `contact_position` (CEO, CFO, Manager, Director, Other)
- **Site contact block:** `phone_country`, `phone`, `email` (required), optional `contact_name` / `contact_position`; site form mirrors client phone UI
- **HQ site:** on new client, `save_client` copies address + phone/email/contact from client to headquarters site
- **Migrations:** `0008`–`0011` (client field requirements, country/phone, client contact, site contact)
- **Cursor rule:** merged [`.cursor/rules/portuguese-nif-and-phone.mdc`](../.cursor/rules/portuguese-nif-and-phone.mdc) (replaces separate NIF/phone rules)
- **Tests:** 95 passing (`pytest`)

## Done (earlier)

- Phases 1–8, catalog slice, VAT on items, setup cards, line cascade, `seed_demo`, review remediations (see prior handoff bullets in git history)

## Not done

- Production deploy
- Company letterhead on PDF
- Real catalog prices
- Volume auto-pick; indoor/outdoor auto-pair
- VAT on proforma line math / snapshots / PDF
- Proforma snapshot fields for site/client contact on issued PDFs
- Email send / stored PDFs / Google OAuth / dark theme
- Enable non-PT phone countries in UI (table seeded; PT only disabled selector)

## Next

1. **Manual UI:** New client (minimal: name + phone + email only); NIF blank and 10-digit error; New site with phone/email/contact; confirm HQ inherits client contact on create
2. Run `seed_demo` if demo data needed after fresh migrate
3. Quoting still ignores VAT — unchanged backlog item

## Commands

```bash
source .venv/bin/activate
cp .env.example .env
rm -f db.sqlite3   # only when resetting local dev DB
.venv/bin/python manage.py migrate
.venv/bin/python manage.py seed_demo
.venv/bin/python manage.py runserver
pytest
```

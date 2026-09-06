# Project plan

## Purpose

Internal back office for one HVAC company (this slice of “universe”). Staff create a **proforma invoice** the client can read: equipment to be installed and what it will cost, including a discount if they pay upfront. It is not an official finance document.

Working for the first slice means: staff sign in with email, complete that quoting workflow in the browser, and persist the data. Back-end first, then front-end.

## Users

- **staff** — prepare drafts, issue/lock, download the PDF
- **admin** — users, catalog, parameters, and anything staff must not do
- **clients** — do not log in; they receive the document outside the app

## Apps

### Staff web app

- Purpose: the only product surface in the first slice. Browser app where staff quote HVAC installs.
- Users: staff and admin (email login, admin-provisioned accounts). Django admin is superuser plumbing only.
- Owns (writes): users, clients, sites, equipment catalog (brand → style → model), tubing length prices, parameters, proformas and lines, audit/activity
- Reads: everything it owns
- Out of bounds: client login, payments, official invoices, email send, stock, supplier POs, install calendar

### CLI (later slice)

- Purpose: after the website path works, one Django management command that creates a proforma in a single invocation (mandatory and optional flags).
- Users: staff/operators on the machine; not a public interface
- Owns (writes): the same proforma workflow as the web app (same database)
- Reads: same as the web app
- Out of bounds: a second product, a second store, or a substitute for the web MVP

## Sharing

One shared database. The staff web app is source of truth for all writes in the first slice. The CLI later writes the same tables. No separate stores.

## In scope

- Email login (`accounts.User`); admin creates accounts; no public signup
- Clients as domain records; a client has many sites
- Site aliases: four generic columns (`alias_1` … `alias_4`), not a list
- Catalog: brand → style → model (start with Mitsubishi, LG, Nippon; models such as 9k / 12k / 18k BTU)
- Proforma belongs to exactly one site (and that site’s client)
- One proforma may have many equipment lines (e.g. five AC units for a house)
- Draft, then issue: snapshot and lock all values; catalog price changes never flow into issued proformas
- Company default upfront-payment discount (parameters); overridable on the draft
- Extra tubing **per line**: boolean; if needed, a length from a priced list (some units on the same invoice need it, some do not)
- Extra labour field (handy now; history for a possible later install follow-up)
- Observations: one text field on the proforma, on top of tubing/labour/lines
- PDF generated on download; not stored as files in the first slice
- Soft delete; non-admin must not see admin functions

## Out of scope

- Official tax invoices, payments, accounting export, finance-system duplication
- Client portal, mobile app, public marketing site, shared API
- Email send / mailer / background worker in the first slice
- Stock, supplier purchase orders, install scheduling (labour/tubing on the quote are not a jobs module)
- Unlocking or revising a locked proforma (create a new one)
- Storing generated PDFs
- Client login identities

## Decisions

- One organization, one Django staff app, one database
- Admin is a role inside that app, not a second product
- Clients are records, not users
- Issued proforma is a frozen snapshot; corrections = new proforma
- Extra tubing is per line, not per invoice
- Four site aliases are four columns, not a joined list
- Web MVP first; CLI is the next slice in this project, same database
- Default upfront % lives in parameters; changing it does not rewrite locked proformas
- Creating the first draft does not need a reason; locked values are not edited

## Open questions

None. See update below.

## Update 2026-09-06

Closed all remaining wrinkles so later slices do not require disruptive schema patches on a working app.

### What changed

- **Indoor/outdoor:** two catalog items; one machine per line when quoting. Default indoor+outdoor matching is **deferred** (later migration adds `model_default_matches`; not in MVP schema).
- **Currency:** one company currency in `parameters` (`currency`, e.g. EUR). All money fields use it.
- **Extra labour:** one money field on the **proforma** header, not per line.
- **Tubing list:** catalog-wide `tubing_lengths` table, not per model. Which lengths exist is operational data.
- **Proforma number:** format `PF-YYYY-NNNN` (`YYYY` = create year, `NNNN` = 4-digit per-year sequence). Assigned on create. Unique among live rows.
- **Client contact:** `phone` and `email` on `clients` (optional). No `contacts` table.
- **Site location:** `street`, `postal_code`, `city` on `sites` (optional). Aliases stay four columns. No `addresses` table.
- **Snapshot at issue:** issued PDFs must not change if client, site, or catalog rows are renamed or repriced. Copy client name, phone, email, site aliases, notes, address, and frozen money onto the proforma; copy brand, style, kind, btu, and line money onto each line. Keep FKs for navigation.
- **Tubing unit:** `tubing_lengths.length` is in **metres**. Parameter `tubing_length_unit` = `m`.
- **Line total:** extra tubing charged per machine: `line_total = quantity × (unit_price + tubing_amount)`. Equipment subtotal = sum of `quantity × unit_price`. Tubing total = sum of `quantity × tubing_amount`. Discount applies to equipment only.
- **CLI contract (documented now, implemented later):** same tables. Mandatory: `--user` (email), `--site` (id), at least one `--line` (`model_id:qty` or `model_id:qty:tubing_length_id`). Optional: `--discount-percent`, `--extra-labour`, `--observations`, `--issue`. `created_by` = `--user`. Intended for LLM agent invocation, not manual terminal use.

### Apps added/removed

None.

### Decisions

- Snapshot-at-issue is required for PDF stability.
- `model_default_matches` is explicitly deferred, not an open question.

### Open questions still open

None.

## Update 2026-09-06 — implementation surfaces

Decisions for how the staff app is built (not schema). Implementation order is [`project-plan.md`](project-plan.md).

### What changed

- **Admin vs custom UI:** Django contrib admin for catalog, parameters, users, and audit. Custom templates for clients, sites, and the proforma draft → issue → on-screen quote → PDF workflow. Staff (`role=staff`) must not use `/admin/`. Django admin UI stays English.
- **Login:** email + password only. Google OAuth fields on `accounts.User` stay unused.
- **i18n:** two languages, one app (`en` | `pt`). Copy CentCompras / [warehouse_V2](https://github.com/neopmpmtj/warehouse_V2) [`docs/i18n-pattern.md`](https://github.com/neopmpmtj/warehouse_V2/blob/main/docs/i18n-pattern.md): English fallback in HTML, vanilla JS dictionaries, `data-i18n*` attributes, preference in `localStorage` (`fu-lang`). No Django gettext `.po` files, no `LocaleMiddleware` UI switching, no `User.language` column. Dark/light theme from warehouse is not in this slice.
- **PDF / visualization:** MVP shows the issued quote on screen. Also generate a real PDF on download (`build_proforma_pdf` → bytes) so a later email feature can attach it. Do not store PDF files. Do not send email in this slice (Gmail vs local mail is a future enhancement).
- **PDF language:** WeasyPrint cannot read `localStorage`. Language JS also writes a `fu-lang` cookie; quote HTML/PDF uses a small server-side EN/PT dict. Switch the UI to English before download for a UK client.
- **Seed:** optional idempotent `seed_catalog` management command (demo brands/models/tubing/parameters). Not run automatically in production.
- **CLI:** last implementation phase; same services as the web; flag contract unchanged in data-points.

### Apps added/removed

None.

### Decisions

- UI translation is client-side JS (warehouse_V2), not gettext.
- Email send is out of scope; PDF bytes are the attachment seam.
- Catalog maintenance is Django admin; quoting is custom UI.

### Open questions still open

None.

## Update 2026-09-06 — staff UI chrome

Visual/chrome spec: [`front-end-project-plan.md`](front-end-project-plan.md). Copied from warehouse_V2; not a second product.

### What changed

- **Two layouts:** dashboard (card grid) and work page (topbar + table). Language `<select>` **only on the dashboard**; work pages read `fu-lang` and do not offer a switcher.
- **Gear (Settings):** top right on dashboard and work pages. Shows signed-in email and Sign out. No Help manuals, no “sign out other devices”, no dark theme.
- **List + drawer:** clients, sites, and proforma **lines** create/edit in a right-hand drawer (warehouse Items pattern). Sites stay a first-class list page (not nested under clients like warehouse Suppliers).
- **Proforma:** work page with header fields on the page and a lines table; not a Django form wizard.
- **Catalog console:** do not copy warehouse manager catalog; Django admin remains.

### Apps added/removed

None.

### Decisions

- Server-rendered tables + JS drawer; no warehouse `/api/manage/` clone for MVP.
- To issue an English PDF, staff switch language on the dashboard first, then download.

### Open questions still open

None.

## Update 2026-09-06 — Django domain app name

The staff domain app is **`proformas`**, not `office`. `accounts` remains the User/login app. Implementation order is unchanged ([`project-plan.md`](project-plan.md)).

### What changed

- **App package:** `proformas` (`INSTALLED_APPS`, services, models, admin, management commands, staff templates).

### Apps added/removed

- Named: `proformas`.
- Rejected name: `office`.

### Decisions

- Django-style plural of the main entity.

### Open questions still open

None.

## Update 2026-09-06 — Daikin catalog seed

Demo `seed_catalog` now includes **Daikin** in addition to Mitsubishi, LG, and Nippon.

### What changed

- **Daikin styles** come from the Portugal air-to-air heat-pump page (bombas de calor ar-ar): Sensira, Comfora, Perfera, Perfera Floor, Stylish, Emura, Ururu Sarara. Each style still gets indoor/outdoor 9k/12k/18k BTU with round demo prices.
- **Not seeded as styles:** Multi / Multi+ / pair (system layouts, not named indoor ranges). Ducted/concealed ceiling is listed as a form factor on that page but has no named consumer series there, so it is omitted until a real range name is supplied.
- Prices remain placeholders, not live Daikin list prices.

### Apps added/removed

None.

### Decisions

- Seed styles follow Daikin PT named ranges, not generic “Split”.

### Open questions still open

None.

## Update 2026-09-06 — Demo seed and manager delete

Local/demo `seed_demo` fills a clickable suite. `seed_catalog` stays catalog-only.

### What changed

- **Users:** `proforma-admin@fribila.dev` (`admin`, Django admin, may soft-delete) and `proforma-manager@fribila.dev` (`staff`, quoting UI, may not delete). Shared demo password documented in README. Manager maps to existing `staff` role; no third role.
- **Delete:** only `admin` may soft-delete clients and sites. Staff/manager do not see Delete in the drawer; POST delete is 403. Removing a line from a **draft** quote is still allowed (editing, not retiring a client/site). Cancel is not delete.
- **Demo records:** three clients, five sites, five proformas (two issued, two drafts, one cancelled). Idempotent. Not for production.

### Apps added/removed

None.

### Decisions

- Demo manager is `role=staff`. Only admin deletes clients/sites.

### Open questions still open

None.

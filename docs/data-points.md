# Data points

Conceptual model only. Not SQL, not ORM, not seeds.

## Conventions

Always-on columns on every entity table: `created_at`, `updated_at`, `created_by`, `updated_by`, `deleted_at` (null = live), `deleted_by`.

Unique keys apply to live rows only.

Audit defaults: `change_logs` (field-level), `activity_logs` (actions). Per-entity history and entity-specific activity only where listed below.

`created_by` / `updated_by` may be null for `actor_type = system`. The LLM/CLI path is not anonymous: the command takes a **mandatory user**; that user is `created_by` and `actor_type = user`.

Draft proformas may be edited. **Issued** proformas are frozen: no value updates, including when catalog cost prices change later. Corrections = a new proforma. `cancelled` retires a locked one without unlocking.

At **issue**, snapshot client, site, and catalog display fields onto the proforma and lines so issued PDFs do not change if live rows are renamed or repriced. FKs remain for navigation; PDF and locked values read the snapshots.

## Apps this model serves

Shared core in one database.

- **Staff web app** (MVP) writes all tables below.
- **CLI** (later slice) writes the same proforma workflow so an LLM agent can create a proforma in one shot. Not a separate store.

### CLI contract (later slice; no extra schema)

Mandatory flags:

- `--user` — staff email; becomes `created_by`
- `--site` — site id
- at least one `--line` — `model_id:qty` or `model_id:qty:tubing_length_id`

Optional flags:

- `--discount-percent`
- `--extra-labour`
- `--observations`
- `--issue` — issue immediately after create

Same validation and snapshot rules as the web app. Intended for LLM agent invocation, not manual terminal use.

## Tables

### users

- Purpose: login identities for staff and admin
- Written by (apps): staff web app (admin)
- Fields (plus always-on):
  - `email` — text, required
  - `first_name` — text, optional
  - `last_name` — text, optional
  - `role` — enum `staff` | `admin`, required
  - `is_active` — boolean, required
- Uniqueness: live `email`
- Notes: maps to existing `accounts.User` (email login). Admin-provisioned; no public signup. Clients are not users.
- Extra history table: no
- Extra activity table: no

### change_logs

- Purpose: field-level old/new
- Fields: entity type, entity id, field, old value, new value, actor, actor type (`user` | `system`), time, reason (required only for reason-required fields)
- Reason-required fields elsewhere:
  - `models.list_price`
  - `tubing_lengths.price`
- Notes: issued proforma money fields are not edited, so they are not reason-required (the edit is forbidden). Creating a draft does not need a reason.

### activity_logs

- Purpose: actions that are not a single field write
- Fields: actor, actor type, action, object type, object id, time, details
- Typical actions: issue proforma, download PDF, create proforma via agent/CLI

### parameters

- Purpose: settings editable without a deploy
- Written by (apps): staff web app (admin)
- Fields (plus always-on):
  - `key` — text, required
  - `value` — text, required
- Known keys:
  - `currency` — company currency (e.g. EUR); all money fields use this
  - `default_upfront_discount_percent` — number as text; default for new drafts; changing it does not rewrite locked proformas
  - `tubing_length_unit` — `m` (metres); documents the unit for `tubing_lengths.length`
- Uniqueness: live `key`
- Reason-required: no
- Extra history table: no
- Extra activity table: no

### clients

- Purpose: customer organization (e.g. a construction company)
- Written by (apps): staff web app
- Fields (plus always-on):
  - `name` — text, required
  - `phone` — text, optional
  - `email` — text, optional
- Relationships: has many `sites`
- Uniqueness: live `name`
- Reason-required fields: none
- Extra history table: no
- Extra activity table: no
- Notes: not a login. No contacts table, no addresses table.

### sites

- Purpose: a work location of a client
- Written by (apps): staff web app
- Fields (plus always-on):
  - `client` — fk → `clients`, required
  - `alias_1` — text, required
  - `alias_2` — text, optional
  - `alias_3` — text, optional
  - `alias_4` — text, optional
  - `street` — text, optional
  - `postal_code` — text, optional
  - `city` — text, optional
  - `notes` — text, optional
- Relationships: belongs to one `client`; has many `proformas`
- Uniqueness: none beyond always-on (aliases are not a joined list; four columns)
- Reason-required fields: none
- Extra history table: no
- Extra activity table: no

### brands

- Purpose: manufacturer (start: Mitsubishi, LG, Nippon)
- Written by (apps): staff web app (admin)
- Fields (plus always-on):
  - `name` — text, required
- Relationships: has many `styles`
- Uniqueness: live `name`
- Reason-required fields: none
- Extra history table: no
- Extra activity table: no

### styles

- Purpose: named range under a brand
- Written by (apps): staff web app (admin)
- Fields (plus always-on):
  - `brand` — fk → `brands`, required
  - `name` — text, required
- Relationships: belongs to one `brand`; has many `models`
- Uniqueness: live `name` per `brand`
- Reason-required fields: none
- Extra history table: no
- Extra activity table: no

### models

- Purpose: one machine in the catalog (indoor or outdoor); one machine per proforma line
- Written by (apps): staff web app (admin)
- Fields (plus always-on):
  - `style` — fk → `styles`, required
  - `kind` — enum `indoor` | `outdoor`, required
  - `btu` — number, required
  - `list_price` — money, required (current catalog price)
- Relationships: belongs to one `style` (and thus a brand); referenced by `proforma_lines`
- Uniqueness: live combination of `style` + `kind` + `btu`
- Reason-required fields: `list_price`
- Extra history table: no (locked lines hold the snapshot; no catalog price-history screen)
- Extra activity table: no
- Notes: default indoor+outdoor matching is deferred (`model_default_matches` in a later slice). MVP quoting picks each machine on its own line.

### tubing_lengths

- Purpose: priced extra-tubing options when indoor and outdoor are far apart
- Written by (apps): staff web app (admin)
- Fields (plus always-on):
  - `length` — number, required (metres; see `parameters.tubing_length_unit`)
  - `price` — money, required
- Relationships: referenced by `proforma_lines` when extra tubing is needed
- Uniqueness: live `length`
- Reason-required fields: `price`
- Extra history table: no
- Extra activity table: no
- Notes: catalog-wide list, not per model. Which lengths exist is operational data.

### proformas

- Purpose: client-facing quote for **one site**; not an official finance document
- Written by (apps): staff web app; later CLI (mandatory `--user`)
- Fields (plus always-on):
  - `site` — fk → `sites`, required (client is that site’s client)
  - `number` — text, required; format `PF-YYYY-NNNN` (`YYYY` = create year, `NNNN` = 4-digit per-year sequence); assigned on create
  - `status` — enum `draft` | `issued` | `cancelled`, required
  - `upfront_discount_percent` — number, required (copied from parameters on create; overridable while draft)
  - `extra_labour` — money, required, default 0
  - `observations` — text, optional
  - `equipment_subtotal` — money, optional until issue, then required frozen
  - `tubing_total` — money, optional until issue, then required frozen
  - `discount_amount` — money, optional until issue, then required frozen (equipment only)
  - `grand_total` — money, optional until issue, then required frozen
  - Snapshot fields (filled at issue; read by PDF):
    - `client_name` — text
    - `client_phone` — text, optional
    - `client_email` — text, optional
    - `site_alias_1` … `site_alias_4` — text
    - `site_street` — text, optional
    - `site_postal_code` — text, optional
    - `site_city` — text, optional
    - `site_notes` — text, optional
- Relationships: belongs to one `site`; has many `proforma_lines`
- Uniqueness: live `number`
- Reason-required fields: none (issued rows are not edited)
- Extra history table: no
- Extra activity table: no
- Notes:
  - Only `draft` is editable. Explicit **issue** snapshots totals, client/site display fields, and locks. PDF is for issued documents. Draft preview PDF (if added later) must not lock.
  - Upfront discount applies to **equipment line totals only**, not tubing, not extra labour.
  - `extra_labour` is on the header, not on lines.
  - `cancelled` retires a locked proforma. Do not unlock. Soft-delete still hides mistakes from live lists.
  - Totals at issue:
    - `equipment_subtotal` = sum over lines of `quantity × unit_price`
    - `tubing_total` = sum over lines of `quantity × tubing_amount`
    - `discount_amount` = `equipment_subtotal × upfront_discount_percent / 100`
    - `grand_total` = `equipment_subtotal - discount_amount + tubing_total + extra_labour`

### proforma_lines

- Purpose: one machine on a proforma (e.g. five AC units for a house = five lines)
- Written by (apps): staff web app; later CLI
- Fields (plus always-on):
  - `proforma` — fk → `proformas`, required
  - `model` — fk → `models`, required
  - `quantity` — number, required, default 1
  - `extra_tubing` — boolean, required, default false
  - `tubing_length` — fk → `tubing_lengths`, optional (required when `extra_tubing` is true)
  - `unit_price` — money, required (snapshot of model list price at save/issue)
  - `tubing_amount` — money, required, default 0 (snapshot of tubing length price; 0 when no extra tubing)
  - `line_total` — money, required
  - Snapshot fields (filled at issue; read by PDF):
    - `brand_name` — text
    - `style_name` — text
    - `kind` — enum `indoor` | `outdoor`
    - `btu` — number
    - `tubing_length_value` — number, optional (metres; 0 or null when no extra tubing)
- Relationships: belongs to one `proforma`; points at one `model`; optional `tubing_length`
- Uniqueness: none (same model may appear on more than one line)
- Reason-required fields: none
- Extra history table: no
- Extra activity table: no
- Notes:
  - Extra tubing is **per line** and charged **per machine**: `line_total = quantity × (unit_price + tubing_amount)`.
  - On one invoice, some lines may need extra tubing and some may not.
  - After issue, money and snapshot fields do not change if catalog prices or names change.

## Rejected

- `contacts`, `addresses` tables
- Stock, supplier POs, jobs / install calendar tables
- Stored PDF / file table
- `model_default_matches` in MVP (deferred to later slice; explicit migration when quoting auto-pair is built)
- `item_price_history`, `proforma_activities`, or any collapse of the four audit kinds into one “audit” table
- Client-login / portal tables
- Mailer / worker / job-queue tables in this slice
- Per-app copies of shared entities
- Official invoice / payment / tax tables
- Unlock or revision-chain tables for locked proformas

## Open questions

None.

# Front-end project plan

How the staff UI should look and behave. Product scope: [`preliminary_project-plan.md`](preliminary_project-plan.md). Schema: [`data-points.md`](data-points.md). Build order: [`project-plan.md`](project-plan.md).

Copy chrome from [warehouse_V2](https://github.com/neopmpmtj/warehouse_V2) (CentCompras). i18n mechanics: warehouse [`docs/i18n-pattern.md`](https://github.com/neopmpmtj/warehouse_V2/blob/main/docs/i18n-pattern.md). **Do not clone warehouse product screens** (items catalog API, Company Voice, branches).

A later agent implements UI only after the matching implementation phase. Checkboxes below are the visual backlog; tick them on session-handoff when that chrome exists.

## How to use

1. Read this file **before any staff HTML/CSS/JS**.
2. Two layouts only: **dashboard** and **work page**. Do not invent a third shell.
3. **Server-rendered tables + JS drawer.** Do not add a `/api/manage/` clone unless a later phase truly needs it. Warehouse items load rows via JSON APIs; fri-uni does not.
4. Catalog (brands, styles, models, tubing, parameters) stays **Django contrib admin**. Do not build a warehouse-style catalog console.

## Visual tokens (light only)

From warehouse `products/static/products/css/console.css`. No dark theme.

| Token | Value |
| ----- | ----- |
| `--bg` | `#f4f6f8` |
| `--surface` | `#ffffff` |
| `--surface-2` | `#eef2f5` |
| `--text` | `#1c2430` |
| `--muted` | `#5b6776` |
| `--border` | `#d5dde6` |
| `--accent` | `#0f766e` |
| `--accent-text` | `#ffffff` |
| `--shadow` | `0 12px 32px rgba(16, 24, 40, 0.12)` |
| Font | `system-ui, -apple-system, "Segoe UI", Roboto, sans-serif` |
| Radius | 6px controls, 8px cards/popover/drawer |

Primary buttons: accent fill, white text. Ghost/default: surface, 1px border. Body background `--bg`.

---

## Chrome rules (always)

### Two layouts

Warehouse does not use one `base.html` for everything. Match that:

- **Dashboard layout** — language + gear in a top `page-account-bar`; main is a card grid. Reference: warehouse `products/templates/products/dashboard.html`.
- **Work layout** — `header.topbar` + `main.page`. Reference: warehouse `products/templates/products/item_console.html`.

Shared includes: gear popover, i18n JS, CSS variables. Work pages include topbar nav. Dashboard does **not** include the work topbar nav.

### Dashboard layout

Top bar (`page-account-bar`), flex, space-between / end-aligned:

- Left (or start): language `<select>` (English / Português). **This is the only language control in the app.** Same idea as warehouse `preferences_bar.html` (`#pref-language`). No theme button.
- Right: gear Settings (see below).

Main (`dash-main`, max-width ~72rem):

- App title (e.g. company / “Proformas”).
- **Card grid** (`card-grid` / `dash-card`): Clients, Sites, Proformas.
- Extra card **Catalog (Django admin)** only if `user.role == "admin"` (link to `/admin/`).
- Cards: white surface, 8px radius, shadow; hover accent border. Title + one-line description. `data-i18n` on strings.

Language change writes `fu-lang` to **localStorage and cookie**, sets `document.documentElement.lang` to `en` or `pt-PT`, dispatches `fu-lang-changed` (warehouse uses `cc-lang-changed`). Work pages never show a language select; they only read the stored value.

To produce an English PDF for a UK client, staff return to the dashboard, switch to English, then open the issued quote / download.

### Work layout

`header.topbar` (surface, bottom border):

1. **Eyebrow** + page **`h1`** (warehouse `console_eyebrow.html` + title). Eyebrow can be the app name; `h1` is the screen name (Clients, Sites, …).
2. **Nav** — Home, Clients, Sites, Proformas. Active link styled (`is-active`). Home goes to the dashboard. **No language select here.**
3. **Actions (right)** — page-specific buttons if needed, then the **gear**. No warehouse “Master data” cluster. No Help `?`.

`main.page`: toolbar (filters + primary action), optional banner, `.table-wrap` > `table.grid`, optional pagination.

Early `<head>` script (anti-flash): read `fu-lang`, set `lang` on `<html>` before CSS paints. Default `en`.

### Gear / Settings (top right)

Warehouse calls this Settings (gear SVG), not “Definitions”. Copy the popover, not the extra warehouse actions.

- Button `#settings-toggle` (ghost, gear icon), `aria-haspopup`, `aria-controls="settings-popover"`.
- Popover: title “Settings”; **Sign out** (POST `{% url 'logout' %}`) in the head; line “Signed in as **{{ user.email }}**”.
- Click-outside and Escape close it; `hidden` when closed.
- **Skip:** Help launcher, user manuals, “Sign out other devices”, theme.

Reference: warehouse `products/templates/products/includes/account_settings.html`, `settings_menu.css`, `console_settings_menu.js` (menu open/close only).

### Drawer

Right-hand panel. Create and edit use the **same** drawer.

- `#drawer-backdrop.backdrop` + `#drawer.drawer`, both `hidden` when closed.
- Head: `h2` title + Close.
- Body: form, stacked labels (`span` + input/select). Actions row at the bottom (Save / soft-delete when editing).
- Close on Close button, backdrop click, Escape.
- Does not navigate to a separate form URL as the primary UX (query `?id=` or POST to the list URL is fine).

Reference: warehouse `item_console.html` (`#drawer`, `#drawer-backdrop`) and `.drawer*` rules in `console.css`.

### i18n

- English fallback text in HTML.
- `data-i18n`, `data-i18n-placeholder`, `data-i18n-aria` (and `data-i18n-col` on sortable headers if used).
- Shared `static/js/i18n.js`: `normalizeLang`, `t()`, `applyStaticI18n()`, `safeGet`/`safeSet`. `pt*` → `pt`; dicts may key `"pt-PT"` with a `pt` alias.
- No `.po` files, no `{% trans %}`, no `User.language`.

---

## Screens

### Login

Centered card on `--bg`. Email + password. English fallback + i18n. After login → dashboard.

### Dashboard

Only place to set language. Cards as above. Implementation: Phase 1.

### Clients (list + drawer)

Analog of warehouse **Items**, not of nested Suppliers.

- Toolbar: search (name), **New client**.
- `.grid`: name, phone, email, actions.
- Row or Edit opens the drawer: `name` required; `phone`, `email` optional. Soft-delete in the drawer (live lists hide deleted rows).
- Implementation: Phase 4.

### Sites (list + drawer)

First-class page. **Do not** nest sites inside the client drawer the way warehouse nests Suppliers under Items. A proforma belongs to a site.

- Toolbar: search, **filter by client**, **New site**.
- `.grid`: client name, `alias_1` (and maybe city), actions.
- Drawer fields from data-points: `client` required; `alias_1` required; `alias_2`–`alias_4` optional; `street`, `postal_code`, `city`, `notes` optional.
- Implementation: Phase 4.

### Proforma list

- Toolbar: search/filter by status (`draft` / `issued` / `cancelled`), **New draft** (must pick a site).
- `.grid`: number, site/client, status, grand total (if present), updated.
- Row opens the **proforma work page** (not a drawer for the whole quote).
- Implementation: Phase 5.

### Proforma work page

Analog of a warehouse **console**, not a Django form wizard.

- Header **on the page** (not in a drawer): upfront discount %, extra labour, observations; live totals; **Issue** / **Cancel** when allowed (Phase 6).
- Lines: `.grid` (model snapshot or live catalog name while draft, qty, tubing, line total).
- **Add line / Edit line = drawer:** model, quantity, extra tubing boolean, tubing length when needed.
- Draft: editable. Issued: read-only header and lines; buttons **View quote** and **Download PDF** (Phase 7). Cancelled: read-only, no unlock.
- Implementation: Phases 5–6 (PDF buttons Phase 7).

### Issued quote view

Document-like page for the client-facing quote (snapshots, line table, totals, observations). Still uses the **work topbar**. Print/PDF stylesheet. Language from `fu-lang` cookie on the server for PDF. Implementation: Phase 7.

---

## What not to copy from warehouse_V2

- Dark theme / `cc-theme`
- Help `?` and user-manual PDFs
- “Sign out other devices”
- JSON item/supplier APIs and client-rendered table bodies (unless a later phase adds an API for a good reason)
- “Master data” button cluster (Families / Sub-families / Suppliers)
- Manager catalog console (`catalog.html`) — Django admin instead
- Company Voice, branch cards, cost-trends, POs, goods receipts
- Nested supplier-style drawers for sites

---

## Tie-in to [`project-plan.md`](project-plan.md)

| Phase | Front-end delivers |
| ----- | ------------------ |
| 1 | Login, dashboard (language + cards + gear), work-page shell (topbar, empty home-quality chrome), i18n JS |
| 4 | Clients and sites list + drawer |
| 5 | Proforma list + work page + line drawer (draft) |
| 6 | Issue/cancel on the work page; issued read-only |
| 7 | Issued quote view + PDF download |
| 3, 8 | No extra staff chrome (admin / CLI) |

---

## Checkboxes

- [x] Front-end: CSS tokens + dashboard and work layouts (completed 2026-09-06)
- [x] Front-end: gear Settings popover (email + sign out) (completed 2026-09-06)
- [x] Front-end: language select on dashboard only (`fu-lang`) (completed 2026-09-06)
- [x] Front-end: shared drawer (backdrop, Escape, create/edit) (completed 2026-09-06)
- [x] Front-end: Clients list + drawer (completed 2026-09-06)
- [x] Front-end: Sites list + drawer (completed 2026-09-06)
- [x] Front-end: Proforma list + work page + line drawer (completed 2026-09-06)
- [x] Front-end: issued quote view chrome (completed 2026-09-06)

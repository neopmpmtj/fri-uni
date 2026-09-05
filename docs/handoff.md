# Session handoff

> **Last updated:** 2026-09-05 09:47 WEST (Europe/Lisbon)  
> Replace with the current date and time whenever you edit this file.

## Project

Brief description of what this project does.

Durable backlog: [`docs/project-plan.md`](project-plan.md) — **living file** (pending work across sessions; status updated on session-handoff).

## Done

- Bootstrap scaffold: Django `conf/` package, `.cursor/` rules, `AGENTS.md`
- Auth mode: email

## Not done

- First Django app
- `migrate` / `createsuperuser`
- Production deployment

## Next

1. `cp .env.example .env` and set `SECRET_KEY`
2. `.venv/bin/python manage.py migrate`
3. Add your first app with `manage.py startapp`

## Commands

```bash
source .venv/bin/activate
cp .env.example .env
.venv/bin/python manage.py migrate
.venv/bin/python manage.py runserver
pytest
```

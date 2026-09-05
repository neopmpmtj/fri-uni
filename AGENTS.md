# fri-uni — Agent instructions

Django project with settings in `conf/`. No apps scaffolded yet.

**Read [`docs/handoff.md`](docs/handoff.md) first** — session snapshot (done / not done / next).  
**Read [`docs/project-plan.md`](docs/project-plan.md)** — durable backlog of pending work across chats.

## Architecture

```text
views / management commands  →  services.py  →  models.py
```

- Business logic in `services.py`, not views or templates
- Plain Django templates + plain JavaScript — no React/Vue unless requested
- Minimize scope — focused diffs; match existing patterns

## Do

- Read `docs/handoff.md`, `docs/project-plan.md`, and `README.md` before large changes
- When you notice new plans, features, or follow-ups not yet in the plan, **ask**: "Should I add this to `docs/project-plan.md`?"
- When the user says **"put this in the plan"** (or similar), append to `docs/project-plan.md` immediately — do not rely on chat memory
- Use `.venv/bin/python` for `manage.py` and tests (or activate the venv first)
- Put secrets in root `.env` only; use `.env.example` as the committed template
- End substantive sessions with `/session-handoff` or skill `session-handoff`

## Do not

- Commit `.env`, API keys, `db.sqlite3`, or `media/`
- Over-engineer: no extra abstractions, queues, or auth unless requested
- Edit `.cursor/plans/` unless the user asks
- Use emoji in logs or prints

## Commands

```bash
source .venv/bin/activate
cp .env.example .env
.venv/bin/python manage.py migrate
.venv/bin/python manage.py runserver
pytest
```

## Documentation conventions

**Living documents** (updated throughout the project, not one-off archives):

| File | Role | How it changes |
|------|------|----------------|
| [`docs/handoff.md`](docs/handoff.md) | Session snapshot | Rewritten each session-handoff — done / not done / next |
| [`docs/project-plan.md`](docs/project-plan.md) | Durable backlog | Appended when you ask; checkboxes updated on session-handoff |

**Project plan format** when appending:

```markdown
- [ ] Short description (added YYYY-MM-DD)
```

Mark complete during session-handoff: `- [x] ... (completed YYYY-MM-DD)`

- **Reviews:** in-progress audits under [`docs/reviews/`](docs/reviews/); move concluded docs to [`docs/archive/`](docs/archive/)
- **Deploy:** see [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) and [`scripts/deploy.sh`](scripts/deploy.sh)
- Review/audit filenames: `topic-YYYY-MM-DD-HHMM.md` when adding docs under `docs/`

## Cursor project config

| Path | Use |
|------|-----|
| [`.cursor/rules/`](.cursor/rules/) | Project rules (`.mdc`) |
| [`.cursor/skills/`](.cursor/skills/) | Project skills |
| [`.cursor/agents/`](.cursor/agents/) | Custom subagents |
| [`.cursor/commands/`](.cursor/commands/) | Slash commands |
| [`.cursor/hooks/`](.cursor/hooks/) | Hook scripts + `hooks.json` |

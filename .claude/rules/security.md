# Security

## Secrets and credentials
- No real API keys, tokens, passwords, DB credentials, or SSH keys in `app.py`,
  routes, templates, services, `config.py`, the README, tests, or screenshots.
- Config reads them only via `os.environ.get(...)`.
- `.env` must be in `.gitignore`. Also ignore `*.pem`, `cikeys*`, `.ssh/`, `.venv/`,
  `__pycache__/`, `instance/`.
- `.env.example` documents every variable with fake placeholder values only.
- If asked to "just hardcode it for now", use an env var instead and say so.

## Database credentials (A3)
- DB settings come from env vars: `DB_USERNAME`, `DB_PASSWORD`, `DB_HOST`,
  `DB_PORT`, `DB_NAME`. Build the SQLAlchemy URL in `config.py` (e.g. with
  `sqlalchemy.engine.URL.create`) so special characters in passwords are safe.
- Never print the DB URL or password in logs, error pages, or the README.
- The SSH private key (`~/.ssh/cikeys`) is Brennen's. Never read, copy, paste, or
  commit it. Never put his cPanel username or server host in committed files.

## Before any commit or push
Check the diff for: real keys or credentials, `.env`, `.venv/`, SSH keys,
`migrations` files containing credentials (they should not).

## Input handling
- Treat query params, form fields, JSON store data, scraped HTML, and API
  responses as untrusted. Missing keys or bad values must not cause a 500;
  show a sensible message instead.
- Never show a raw traceback to users. Return friendly error pages/messages and
  log details server-side.
- Use the ORM or bound parameters only. Never build SQL by string formatting.
- Jinja autoescaping stays on. Never mark user-supplied text `|safe`.
- Wrap every external call in try/except with a fallback (`live: True/False`).
- State-changing actions (create/update/delete) must be POST (not GET).
  CSRF protection is a known gap unless Flask-WTF is added; list it in the
  README's Known Limitations if not implemented.

## Search (A4)
- Search input is untrusted: normalize, cap length, escape LIKE wildcards,
  whitelist `sort` and filter values, use ORM expressions only.
- Telemetry stores no PII; `session_id` is a random UUID in the session cookie.
- Recording a result click on a GET is a documented exception to "state changes
  are POST": telemetry only, and only for an event owned by the same session.

## Survey / user-submitted data (when built)
- Validate types and ranges server-side before storing.
- No PII: no names, emails, or precise user location beyond the break.
- Flag rate limiting / anti-flooding as a known gap if not implemented.

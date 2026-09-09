# Security

## Secrets
- Real API keys, tokens, and passwords **never** go in `app.py`, routes,
  templates, services, or `config.py` itself — only referenced via
  `os.environ.get("SOME_KEY")`.
- If a `.env` file is used, it must be listed in `.gitignore`. Never commit
  it.
- Never commit `.venv/` to GitHub.

## Before any commit or push
Check that the diff doesn't include:
- a real API key or credential
- a `.env` file
- the `.venv/` folder

If Claude is asked to "just make it work" with a hardcoded key, use an
environment variable instead and say so — don't hardcode it "temporarily."

## Input handling
- Data coming from the JSON store or query params (e.g. the filter feature)
  should be handled defensively: missing keys, empty filters, or unexpected
  values shouldn't crash the route with a 500 — handle it and show a
  sensible empty state instead.
- When calling any external API (later modules), wrap the call in a
  try/except and provide a fallback, matching the course pattern:
  `catalog_live = True/False` style flags so the page still renders if the
  external service is down.

## Survey / user-submitted data
Survey reports are open user input, not trusted data — treat them like any
external input:
- Validate ranges before storing (e.g. wave height, wind speed) — don't
  trust the client to send sane values.
- No PII in survey submissions. Don't collect names, emails, or precise
  user location beyond the break they're reporting on.
- Rate-limit or otherwise guard against one user flooding a break with
  fake reports once this is live — flag this as a known gap if it isn't
  implemented yet, don't silently skip it.

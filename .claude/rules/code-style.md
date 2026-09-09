# Code Style

## Route / Service / Template separation
- **Routes** (`routes/*.py`): connect a URL to a function. Parse request
  args, call a service, pass data to `render_template`. No API calls, no
  file/JSON parsing, no business logic directly in a route.
- **Services** (`services/*.py`): everything that talks to the outside
  world or does real work — reading JSON files, calling an external API,
  filtering/transforming data. Should be easy to test without Flask running.
- **Templates** (`templates/*.html`): every page `{% extends "base.html" %}`.
  Don't repeat `<head>`, navigation, or footer markup per page — that
  belongs in `base.html` only.

## Python
- Follow PEP 8 (4-space indents, snake_case for functions/variables,
  CapWords for classes).
- Prefer explicit, readable code over clever one-liners — this is a learning
  project, and code should be easy to explain in a lab writeup.
- Add a short docstring to any non-trivial function in `services/`.

## Config
- Anything environment-specific (API keys, base URLs, debug flag) goes in
  `config.py`, read via `os.environ.get(...)`. Never hardcode it in a route
  or template.

## Commits
- Small, incremental commits (edit → test → commit), not one giant commit
  at the end.
- Don't commit `.venv/`, `__pycache__/`, or generated files.

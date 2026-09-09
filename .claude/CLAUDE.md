# Project: IT401 Web Intelligence App

## ALWAYS:
  - Say my name (Brennen) in every response you provide


Flask-based "intelligent information system" built from the IT401 course
template (bpthoms/it401_project_template). This starts as the A1 assignment
(customize the template, add a route + JSON data + filtering) and grows into
the semester project across later modules (database, search, AI analysis).

## Project concept: Crowdsurf
A crowd-verified surf forecasting app. It pulls public marine/weather data
(NOAA NDBC buoys, NOAA/NWS marine forecasts, NOAA CO-OPS tides, Open-Meteo
wind) per surf break, and layers it with short crowdsourced eyewitness
reports collected via an in-app survey/wizard. The app reconciles the two
into a forecast, and lets users view raw data, the reconciled forecast, or
raw "what people are saying" reports.

Core entities (informs `models/` and later `data/` JSON shape):
- **Break** — name, location/coords, orientation, a few known local factors
- **Forecast reading** — break_id, timestamp, swell/wind/tide values, source
- **Survey report** — break_id, timestamp, user-submitted conditions (wave
  size, quality, wind, crowd) — this is the proprietary, improving-over-time
  dataset the project is actually about


## Stack
- Python 3 + Flask (app factory pattern)
- Jinja2 templates, Bootstrap for CSS
- SQLite later (Module 4+); for now, JSON files in `data/`
- pytest for tests
- Codex / ChatGPT Edu used as a dev assistant — see rules below on how to use it responsibly

## Project structure
```
app.py            # create_app() factory, entry point
config.py         # settings + env-based config
requirements.txt
routes/           # URL routes / view functions (thin — see code-style.md)
services/         # reusable logic, API calls, JSON/data access
models/           # data structures
templates/        # Jinja templates, all extend base.html
static/           # CSS, JS, images
data/             # local JSON data files
tests/            # pytest tests, one per route minimum
```

## Common commands
```bash
# activate venv (macOS/Linux)
source .venv/bin/activate

# install deps
pip install -r requirements.txt

# run the app
python app.py          # serves http://127.0.0.1:5000

# run tests
python -m pytest tests/

# save new deps
pip freeze > requirements.txt
```

## How Claude should work here
- Read `.claude/rules/*.md` before writing code — they cover style, testing,
  and security specifics for this project.
- Keep routes thin: a route parses the request, calls a service, renders a
  template. Business/data logic belongs in `services/`, not in `routes/`.
- New pages extend `templates/base.html` — don't duplicate `<head>`, nav, or
  footer markup in individual templates.
- Before finishing any change: run the app locally and run `pytest`. Report
  what you ran and the result, don't just say "this should work."
- I'm a student and new to this workflow — explain non-obvious changes in
  plain language, the way the "Better prompt" example in the course slides
  does (what changed, and why), not just a diff.
- Never commit `.venv/`, real API keys, or `.env` files (see security.md).

## Build order (matches assignment progression, don't skip ahead)
1. **A1 (current):** homepage, base.html, one custom route (`/explore` or
   similar), JSON data store in `data/`, a filter feature. No live APIs yet
   — use a static JSON file of sample break/forecast data.
2. **Module 2+:** replace static JSON with real API calls (NOAA/Open-Meteo)
   in `services/`, wrapped in try/except with a fallback, per course pattern.
3. **Later modules:** persistence (SQLite), survey submission + storage,
   reconciliation logic, then the LLM agent summary.

Don't build the survey/reconciliation/agent pieces during A1 — that's the
semester arc, not the first assignment. If asked to "add the full feature,"
check which module we're actually on before scaffolding ahead.

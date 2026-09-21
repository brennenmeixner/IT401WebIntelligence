# Project: IT401 Web Intelligence App

## ALWAYS:
  - Say my name (Brennen) in every response you provide


Flask-based "intelligent information system" built from the IT401 course
template (bpthoms/it401_project_template). A1 customized the template
(homepage, one route, static JSON data, filtering). A2 replaced the static
data with live external API calls + one scraped webpage. It grows into the
semester project across later modules (database, search, AI analysis).

## Project concept: Crowdsurf
A crowd-verified surf forecasting app. As of A2 it pulls live public
marine/weather data per surf break — Open-Meteo (marine + weather), NOAA
NWS (forecast + active alerts), NOAA CO-OPS (tides), NOAA SPC (convective
outlook), RainViewer (radar imagery) — and scrapes a real observed reading
from a NOAA NDBC buoy station page for comparison against the forecast.
Later modules add short crowdsourced eyewitness reports collected via an
in-app survey/wizard, and reconcile the two into a forecast, letting users
view raw data, the reconciled forecast, or raw "what people are saying"
reports.

Core entities (see `data/breaks.json` and `services/forecast_service.py`):
- **Break** — name, location/coords, orientation, known local factors,
  plus (A2) `latitude`/`longitude` and per-break NWS/NDBC/CO-OPS station
  IDs — all local, student-curated reference data, not live-fetched.
- **Forecast reading** — as of A2, fetched live per request from five
  external APIs via `services/forecast_service.build_break_panel()`, never
  persisted; each source returns a uniform `{live, source, data,
  fetched_at, error}` shape (see `services/external_common.py`).
- **Survey report** — break_id, timestamp, user-submitted conditions (wave
  size, quality, wind, crowd) — still planned, not built. This is the
  proprietary, improving-over-time dataset the project is actually about.


## Stack
- Python 3 + Flask (app factory pattern)
- Jinja2 templates, Foundation CSS (via CDN) for layout/components, brand
  styling layered on top in `static/style.css`
- Chart.js (via CDN) for the break-detail dashboard's charts
- `requests` + BeautifulSoup for the NDBC scrape
- `python-dotenv` — `.env` is loaded in `app.py` before `config.py` is
  imported (ordering matters: `Config`'s `os.environ.get(...)` class
  attributes evaluate at import time)
- SQLite later (Module 4+); for now, JSON files in `data/`
- pytest for tests
- Codex / ChatGPT Edu used as a dev assistant — see rules below on how to use it responsibly

## Project structure
```
app.py            # create_app() factory; load_dotenv() runs before config import
config.py         # settings + env-based config
requirements.txt
.env.example      # documents required env vars, no real values
routes/           # URL routes / view functions (thin — see code-style.md)
services/         # reusable logic: one file per external source, plus
                   # forecast_service.py as the orchestrator that fans out
                   # to all of them and never lets one source's failure
                   # break the others
models/           # data structures
templates/        # Jinja templates, all extend base.html
static/           # CSS (Foundation + brand overrides), JS via CDN, images
data/             # local JSON reference data (breaks.json)
tests/            # pytest tests: routes, one file per service, fixtures/
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
1. **A1 (done):** homepage, base.html, `/explore`, JSON data store in
   `data/`, a filter feature — static sample data, no live APIs.
2. **A2 (current):** live external data acquisition. `/break/<id>` calls
   five free/keyless APIs (Open-Meteo marine + weather, NOAA NWS, NOAA
   CO-OPS, NOAA SPC) plus a NOAA NDBC scrape, each wrapped in try/except
   with a `live: True/False` result shape so the page still renders if a
   source is down. Full UI overhaul onto Foundation CSS + Chart.js.
3. **A3 (next):** SQLite persistence, caching external responses instead
   of re-fetching live every request, a dynamic nearest-station lookup.
4. **Later modules:** survey submission + storage, reconciliation logic
   blending live data with survey reports, then the LLM agent summary.

Don't build the survey/reconciliation/agent pieces yet — that's a later
module, not A2. If asked to "add the full feature," check which module
we're actually on before scaffolding ahead.

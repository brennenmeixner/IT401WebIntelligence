# Project: IT401 Web Intelligence App (Crowdsurf)

## ALWAYS:
  - Say my name (Brennen) in every response you provide

Flask "intelligent information system" built from the IT401 course template
(bpthoms/it401_project_template). It grows across the semester:
A1 foundation, A2 external acquisition, A3 persistence, **A4 search (current)**,
A5 intelligence, A6 decision support, then the final project.

## Project concept: Crowdsurf
A crowd-verified surf forecast and session planner for Ventura and Santa Barbara
county breaks. It combines live marine/weather data with short eyewitness
reports from surfers, checks the forecast against what people actually see, and
helps the user decide whether to surf a break (Go / Wait / Skip or switch).

Live sources (A2, all keyless): Open-Meteo (marine + weather), NOAA NWS,
NOAA CO-OPS, NOAA SPC (via Iowa Mesonet), RainViewer, and a scraped NOAA NDBC
buoy page. Planned: one RapidAPI surf-spot source (API not chosen yet).

Core entities:
- **Break**: curated reference data in `data/breaks.json` (coords + station IDs).
- **Reading / record** (A3): acquired forecast or buoy data, persisted in MySQL
  with provenance (source, source URL, retrieved date). The A3 required fields
  are: primary key, title/name, description, source, source URL, retrieved date,
  created date. Extra fields must be justified in the README.
- **Survey report** (later in A3 or A4): break_id, timestamp, wave size, quality,
  wind, crowd. Open user input. Validate everything, collect no PII.

## Stack
- Python 3 + Flask (app factory), Jinja2, Foundation CSS (CDN), Chart.js (CDN)
- `requests` + BeautifulSoup for the NDBC scrape
- **Flask-SQLAlchemy + Flask-Migrate + PyMySQL + cloud MySQL (CI-Keys)**
- `python-dotenv` (`.env` loaded in `app.py` before `config.py` is imported)
- pytest. Tests use an in-memory SQLite `TestConfig`, never the live MySQL.

## Project structure (as of A4)
```
app.py              # create_app() factory
config.py           # Config + TestConfig (builds the DB URL from env vars)
extensions.py       # db = SQLAlchemy(); migrate = Migrate()
models/             # reading.py, search_event.py (A4 telemetry)
routes/             # main.py, readings.py (CRUD), search.py (A4: /search, /search/history)
services/           # one file per external source, reading_service (persistence),
                    # search_service (A4: query processing, filters, ranking, telemetry)
scripts/            # run_search_eval.py (A4 evaluation; real DB, never in pytest)
migrations/         # Flask-Migrate output, committed
templates/ static/ data/ tests/ docs/
```

## Common commands
```bash
source .venv/bin/activate
pip install -r requirements.txt
python app.py                         # http://127.0.0.1:5000
python -m pytest tests/
flask acquire-all                     # save a snapshot of every break (needs the tunnel)
flask db init                         # once per project
flask db migrate -m "message"         # generate a migration, then REVIEW it
flask db upgrade                      # apply it
```
The CI-Keys MySQL server is only reachable through an SSH tunnel that Brennen
opens on his own machine (see `.claude/rules/database.md`). Never try to read
his SSH key or open the tunnel yourself.

## How Claude should work here
- Read `.claude/rules/*.md` before writing code. Course material is in
  `.claude/course-material.md`: read the relevant module section on demand.
- Keep routes thin: parse request, call a service, render a template.
- New pages extend `templates/base.html`.
- Before finishing any change: run the app and run `pytest`. Report exactly what
  you ran and the result.
- Brennen is a student: explain non-obvious changes in plain language (what
  changed and why). He must be able to explain every line in a lab write-up.
  Use the course's Codex pattern: explain the goal, inspect first, make a plan,
  implement, test, review the diff, then commit.
- Never commit `.venv/`, `.env`, API keys, DB credentials, or SSH keys.
- Small commits on the assignment branch (`brennenmeixner-it401-a4`).
- Keep a short list of what AI helped with, in case an AI-usage reflection is required.

## Build order (match assignments; do not skip ahead)
1. **A1 (done):** homepage, base layout, `/explore`, JSON store, filter.
2. **A2 (done):** live APIs + NDBC scrape on `/break/<id>`, `live: True/False` shape.
3. **A3 (done):** MySQL via Flask-SQLAlchemy, `Reading` model, CRUD, validation,
   duplicate handling, README per the A3 spec.
4. **A4 (current):** `/search` over stored readings only (never external calls):
   Retrieve → Filter → Rank → Paginate → Display in one SQL query. Keyword search
   (AND across tokens, OR across title/description/break name), filters (break,
   source, kind, date range), sort + SQL relevance score, 10 per page, four page
   states, `SearchEvent` telemetry + `/search/history`, error handling, and a
   precision/recall evaluation on real data (Brennen picks the relevant records).
   Survey reports still come after this.
5. **A5:** grounded intelligent summary (capability still tentative).
6. **A6:** decision support (Go / Wait / Skip, evidence, uncertainty, feedback).
7. **Final project:** integration, evaluation, README, recorded presentation.

If asked to build something from a later step, say which step it belongs to and
confirm with Brennen first.

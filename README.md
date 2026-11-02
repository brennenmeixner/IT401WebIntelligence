# Crowdsurf

**Application:** Crowdsurf, a crowd-verified surf forecast for Ventura and Santa Barbara county breaks
**Student:** Brennen Meixner
**Course:** IT401 Web Intelligence, Assignment 3 (A3): Expanding the Web Intelligence Application with Information Persistence
**Branch:** `brennenmeixner-it401-a3`

Started from the `bpthoms/it401_project_template` Flask template. A1 built the homepage and the
Explore filter on static data. A2 added live acquisition from APIs plus one scraped page. A3 makes
the app persistent: acquired information is stored in MySQL, managed through a web CRUD interface,
validated before it is saved, and reused when a live source is down.

## Project Overview

Surf forecasts are model output. What a surfer actually finds at the beach often differs. Crowdsurf
puts live forecasts, real buoy observations and (later) short reports from surfers side by side, so
a surfer can judge whether a forecast is holding up before deciding whether to paddle out.

**Purpose of the A3 version:** in A2, every value existed only for one page load. A3 stores the
acquired information so it survives restarts, can be browsed and corrected, can stand in for a source
that's down, and becomes the base for search (A4) and intelligence (A5).

**Intended users**
- **Local regular surfer** (primary): checks one or two home breaks and wants to know whether the
  forecast matches what the buoys see.
- **Newer surfer:** wants plain-language context (tide, daylight, water quality) next to the numbers.
- **Contributor:** any surfer who records what they saw at a break as a manual reading.

## Information Persistence

**Stored permanently (MySQL, `readings` table)**
- **Acquired snapshots:** "Save this snapshot" on a break page stores one reading per live source
  (13 sources: forecasts, buoy observations, tides, alerts, daylight, water-quality advisories), each
  with provenance (source, exact source URL, retrieved time) and the structured data returned.
- **Manual readings:** forecasts, observations or notes entered through the "Add a reading" form.
- **AI summaries:** a Claude-generated summary of a break's saved readings, stored with the model
  name, prompt version, the ids of the readings it used, token counts and a grounding check result.

**Why:** stored readings (1) survive restarts, (2) give the app a history to compare forecasts against
observations, (3) let the break page fall back to the last saved copy when a live source fails, and
(4) are the searchable collection A4 needs.

**What stays temporary**
- Every page view still fetches live data. Only an explicit "Save this snapshot" writes to the database,
  so the table doesn't grow on every page view.
- Radar tiles (RainViewer) are images that go stale within minutes, so they're never stored.
- The list of breaks stays in `data/breaks.json`. It's small, hand-curated reference data (coordinates
  and station ids) that changes only when I edit it. See Design Decisions.

## Database Schema

One table, `readings` (created by migration `migrations/versions/0cab449f5d49_create_readings_table.py`).

| Column | Type | Null? | Purpose |
|---|---|---|---|
| `id` | Integer, **PK** | no | Internal primary key |
| `title` | String(200) | no | Name of the reading, e.g. "Rincon: NOAA NDBC Realtime Feed, 2026-11-02 01:00 UTC" |
| `description` | Text | yes | One readable sentence of what the source said (or the user's note / AI summary text) |
| `source` | String(64), indexed | no | Short stable source id, e.g. `noaa-ndbc-realtime`, `crowdsurf-user`, `anthropic-claude` |
| `source_url` | String(500) | yes | Exact endpoint or page the data came from |
| `retrieved_at` | DateTime (UTC) | no | When the app fetched the data, or when the user observed it |
| `created_at` | DateTime (UTC) | no | When the row was inserted, set by the app |
| `external_id` | String(120) | no | Identifier for the external item (see duplicate handling) |
| `break_id` | String(50), indexed | no | Which surf break (an id from `data/breaks.json`) |
| `kind` | String(20) | no | `forecast`, `observation`, `note` or `summary` |
| `data_json` | JSON | yes | The structured values (hourly series, tide table, buoy rows, AI metadata, manual measurements) |
| `updated_at` | DateTime (UTC) | yes | Last time the row was edited or refreshed |

**Constraints:** `UNIQUE (source, external_id)` named `uq_reading_source_external_id`.

**Relationships:** none inside the database yet. `break_id` refers to a break in `data/breaks.json`
and is validated against that file before saving. Moving breaks into their own table (with a real
foreign key) is planned; see Future Work.

**Why the extra fields (beyond the seven required)**
- `external_id`: the course pattern for duplicate prevention. Together with `source` it identifies
  one external item, so saving it again updates it instead of copying it.
- `break_id`: every reading belongs to a surf break. Without it, readings can't be shown on the right
  break page or filtered by break.
- `kind`: forecasts and observations have to be told apart to compare them ("forecast said 4 ft, buoy
  saw 6 ft"), and AI summaries must be kept out of the AI's own input.
- `data_json`: each source returns a different shape (hourly arrays, tide lists, buoy rows). Storing
  the cleaned result as JSON keeps the real numbers without one table per source, and it's what the
  "show saved copy" fallback renders.
- `updated_at`: refreshing a snapshot or editing a reading changes it. This records when, separately
  from `created_at`.

## Application Architecture

```
Browser
  │  HTTP (GET pages, POST forms with CSRF token)
  ▼
Flask app (app.py: create_app factory)
  ├── routes/main.py        /, /explore, /rewards, /break/<id>, /break/<id>/save, /break/<id>/summarize
  ├── routes/readings.py    /readings, /readings/<id>, /readings/new, /readings/<id>/edit, /readings/<id>/delete
  │        (routes only parse the request, call a service, render a template)
  ▼
services/ (all real work)
  ├── forecast_service.py   fans out to 14 source calls in parallel, never raises
  │     ├── openmeteo_service, nws_service, coops_service, spc_service, radar_service   (APIs, keyless)
  │     ├── rapidapi_marine_service   (RapidAPI, keyed)
  │     ├── ndbc_realtime_service, usno_service, beach_quality_service              (APIs, keyless)
  │     └── buoy_scraper_service      (BeautifulSoup scrape)
  ├── reading_service.py    validation, duplicate checks, CRUD, snapshot saving, stored fallbacks
  ├── ai_service.py         grounded summary via the Claude API (anthropic SDK)
  └── source_registry.py    one table describing every persistable source (slug, label, URL, kind)
  ▼
models/reading.py  (SQLAlchemy model)  ──►  Flask-SQLAlchemy session  ──►  PyMySQL  ──►  MySQL (CI-Keys, via SSH tunnel)
  ▲                                                                  schema managed by Flask-Migrate (migrations/)
  │
templates/ (Jinja2, all extend base.html; Foundation CSS + Chart.js from CDN)
```

**Major components:** Flask (web layer, routing, sessions), Flask-SQLAlchemy (ORM and models),
Flask-Migrate/Alembic (versioned schema changes), PyMySQL (MySQL driver), MySQL on CI-Keys (storage),
Flask-WTF (CSRF protection), Jinja2 templates (presentation), `requests` + BeautifulSoup (acquisition),
`anthropic` (Claude API client).

## Information Flow

**Saving acquired information**

```
User clicks "Save this snapshot" (POST /break/rincon/save, CSRF token checked)
  → forecast_service fetches all sources in parallel (API calls + NDBC scrape)
  → reading_service.save_panel_snapshot():
       skip sources that are down
       → normalize: title, one-line description, source slug, exact source URL, retrieved_at
       → duplicate check: same (source, external_id = break:source:hour) already stored?
            yes → update that row      no → insert a new Reading
  → one transaction: commit, or roll back everything on error
  → redirect with a message ("Saved 12 new reading(s)… Skipped (unavailable): …")
```

**Manual create / edit**

```
User submits form → validate_reading_form() (required, lengths, ranges, URL scheme, date, allowed kind, known break)
  → errors? re-show the form with messages, HTTP 400, nothing written
  → duplicate? (same break + title + minute) → message, HTTP 409, nothing written
  → db.session.add / change fields → commit → redirect to the reading's page
```

**Reading back (and reuse when a source is down)**

```
GET /break/<id> → fetch live sources → any source failed?
  → stored_fallbacks(): newest saved reading for that break + source → render it with a
    "Live source is down. Showing the saved copy from <time>" label
```

**AI summary**

```
POST /break/<id>/summarize → latest saved readings for the break (newest per source + up to 5 notes)
  → none? stop: "No saved readings…"   (no data, no summary)
  → Claude API (bounded text context, instructions to use only these readings)
  → grounding check: every number in the answer must appear in the context
  → saved as a Reading (kind=summary) with model / prompt version / input ids / token usage
```

## Current Features

- **Homepage** (`/`) and shared layout. The nav shows a live count of stored readings.
- **API integration:** 13 external calls per break: Open-Meteo marine and weather, NOAA NWS forecast and
  alerts, NOAA CO-OPS tides (3 products), NOAA SPC outlook, RainViewer radar, **RapidAPI WeatherAPI.com**
  (second-opinion forecast: marine swell and tides on a paid plan, wind/gusts/rain/conditions on the
  free plan), **NOAA NDBC realtime feed** (24-report observed trend),
  **USNO** (first light, sunrise, sunset, moon phase), **CA Water Boards Beach Watch** (bacteria advisories
  near the break). New in A3 in bold.
- **Web scraping:** the NOAA NDBC buoy station page (BeautifulSoup), compared against the forecast.
- **MySQL persistence:** Flask-SQLAlchemy model, Flask-Migrate migration, CI-Keys MySQL through env vars.
- **CRUD through the web interface:**
  - **Create:** "Save this snapshot" (acquired data) and "Add a reading" (manual form)
  - **Read:** `/readings` list (newest first, 20 per page) and `/readings/<id>` detail with full provenance and stored data
  - **Update:** `/readings/<id>/edit`
  - **Delete:** a button on the detail page (POST, with a confirm prompt)
- **Filtering:** `/readings` filters by break, source and kind. `/explore` filters breaks by name, region and wind.
- **Data validation:** server-side checks before any write (see Error Handling). Duplicates are handled.
- **Stored-copy fallback:** if a live source is down, the break page shows the last saved copy, labeled as such.
- **AI summary (early A5 preview):** a grounded Claude summary built only from saved readings, with a number check.
- **CSRF protection** on every form (Flask-WTF).

## Project Structure

```
IT401WebIntelligence/
├── app.py                     # create_app(): config, db/migrate/csrf init, routes, error pages
├── config.py                  # Config / DevelopmentConfig / TestConfig; builds the DB URL from env vars
├── extensions.py              # db = SQLAlchemy(), migrate = Migrate(), csrf = CSRFProtect()
├── requirements.txt
├── .env.example               # every env var, placeholder values only
├── migrations/                # Flask-Migrate (Alembic) scripts, committed
│   └── versions/0cab449f5d49_create_readings_table.py
├── models/
│   └── reading.py             # Reading model + UniqueConstraint(source, external_id)
├── routes/
│   ├── main.py                # home, explore, rewards, break page, save snapshot, summarize
│   └── readings.py            # readings CRUD pages
├── services/
│   ├── forecast_service.py    # parallel fan-out to every source; never raises
│   ├── reading_service.py     # validation, duplicates, CRUD, snapshot saving, stored fallbacks
│   ├── ai_service.py          # grounded Claude summary + grounding check
│   ├── source_registry.py     # slug/label/URL/kind for every persistable source
│   ├── rapidapi_marine_service.py, ndbc_realtime_service.py, usno_service.py, beach_quality_service.py   # new in A3
│   ├── openmeteo_service.py, nws_service.py, coops_service.py, spc_service.py, radar_service.py         # A2
│   ├── buoy_scraper_service.py   # NDBC scrape (A2)
│   ├── external_common.py     # shared {live, source, data, fetched_at, error} result shape
│   └── breaks_service.py, rewards_service.py   # A1
├── templates/
│   ├── base.html              # head, nav (with stored-readings count), flash messages, footer
│   ├── break_detail.html      # dashboard: 9 tabs + save / summarize bar + AI summary
│   ├── readings/list.html, detail.html, form.html
│   └── error.html, index.html, explore.html, rewards.html
├── static/style.css
├── data/breaks.json           # curated break reference data (coords + station ids)
├── docs/screenshots/
└── tests/                     # pytest; in-memory SQLite, no network
    ├── conftest.py            # app/client/db fixtures, fake break panel
    ├── test_reading_model.py, test_reading_service.py, test_readings_routes.py
    ├── test_ai_service.py, test_new_sources.py
    └── test_app.py + one test file per A2 source
```

## Installation Instructions

**Prerequisites:** Python 3.10+, Git, a CI-Keys MySQL database and SSH key (see the course "CI Keys SSH
Workaround" handout).

1. **Clone**
   ```bash
   git clone <repository-url>
   cd IT401WebIntelligence
   git checkout brennenmeixner-it401-a3
   ```
2. **Create a virtual environment**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate          # Windows: .venv\Scripts\activate
   ```
3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```
4. **Configure `.env`**
   ```bash
   cp .env.example .env
   # fill in DB_USERNAME, DB_PASSWORD, DB_NAME (DB_HOST=127.0.0.1, DB_PORT=3307 for the tunnel),
   # NWS_USER_AGENT, and optionally RAPIDAPI_KEY and ANTHROPIC_API_KEY
   ```
5. **Open the SSH tunnel to CI-Keys MySQL** (leave this terminal open):
   ```bash
   ssh -N -o IdentitiesOnly=yes -o ExitOnForwardFailure=yes \
       -L 127.0.0.1:3307:127.0.0.1:3306 -i ~/.ssh/cikeys -p 22 \
       <CPANEL_USERNAME>@<CIKEYS_SERVER>
   ```
   `-N` means "forward the port only, don't open a shell". CI-Keys accounts don't have shell access, so
   without `-N` the server replies "Shell access is not enabled on your account!" and closes the
   connection (and the tunnel with it). With `-N` the terminal just sits there, which means it's working.
   Check it from another terminal with `nc -zv 127.0.0.1 3307`.
6. **Initialize the database** (creates the `readings` table from the committed migration):
   ```bash
   export FLASK_APP=app.py            # Windows: set FLASK_APP=app.py
   flask db upgrade
   ```
7. **Run**
   ```bash
   python app.py                      # http://127.0.0.1:5000
   ```
8. **Test**
   ```bash
   python -m pytest tests/            # 107 tests, no network or MySQL needed
   ```

If the `DB_*` variables are not set, the app logs a warning and uses a local SQLite file
(`instance/crowdsurf-dev.db`) so it can still start for development. The submitted app is meant to
run on MySQL.

## Environment Variables

All are read in `config.py` with `os.environ.get(...)`. Real values go only in `.env`, which is gitignored.

| Variable | Required? | Purpose |
|---|---|---|
| `DB_USERNAME` | yes (MySQL) | CI-Keys MySQL user |
| `DB_PASSWORD` | yes (MySQL) | CI-Keys MySQL password |
| `DB_HOST` | yes (MySQL) | `127.0.0.1` when using the SSH tunnel |
| `DB_PORT` | no (default 3306) | `3307` with the tunnel above |
| `DB_NAME` | yes (MySQL) | database name |
| `SECRET_KEY` | yes in practice | signs the session cookie and CSRF tokens |
| `RAPIDAPI_KEY` | optional | RapidAPI key subscribed to WeatherAPI.com (the free Basic plan works). Without it, only the Second Opinion tab is unavailable. |
| `ANTHROPIC_API_KEY` | optional | Claude API key for AI summaries. Without it, the Summarize button shows a message instead. |
| `ANTHROPIC_MODEL` | no (default `claude-opus-5-5`) | Claude model id |
| `NWS_USER_AGENT` | recommended | contact string required by the NWS API usage policy |
| `EXTERNAL_API_TIMEOUT` | no (default 10) | seconds before any external call gives up |
| `FLASK_ENV` | no (default `development`) | selects the config class |

The database URL is built with `sqlalchemy.engine.URL.create(...)`, so special characters in the
password are escaped safely. It is never printed or logged.

## Error Handling

- **Invalid input:** every form is checked on the server before anything is written. Required fields
  (title, break), maximum lengths, allowed `kind` values, URLs must start with `http://` or `https://`,
  dates must parse and can't be in the future, and numbers must be numeric and in range (waves 0–60 ft,
  period 0–30 s, wind 0–100 kt, water 32–95 °F). On failure the form is shown again with every problem
  listed, HTTP 400, and nothing is saved. Unknown reading ids return a friendly 404 page.
  Create/update/delete only accept POST (a GET to `/delete` returns 405), and every POST needs a valid
  CSRF token (missing token → 400).
- **Missing API key:** `RAPIDAPI_KEY` missing → the Second Opinion tab says so and no request is
  sent. **Key without access to an endpoint:** RapidAPI's free plan answers the marine endpoint with
  HTTP 401 ("This endpoint is disabled for your subscription"). The service treats a 401/403 from that
  endpoint as "not on this plan" and switches to WeatherAPI.com's forecast endpoint (wind, gusts, rain,
  conditions), and the tab explains the switch. A 401 on both endpoints means the key itself is wrong,
  and the tab says to check the key and plan. `ANTHROPIC_API_KEY` missing → the Summarize button shows "AI summaries are off". Everything
  else keeps working.
- **API failures:** every source returns `{live, source, data, fetched_at, error}` and never raises.
  A failed source shows the last saved copy, clearly labeled, or an "unavailable" message if none
  is stored. Saving a snapshot skips sources that are down and lists them. RapidAPI HTTP errors report
  only the status code, so request details aren't echoed back. Claude API errors (bad key, rate limit,
  server error, no connection, refusal) each produce a friendly message and save nothing.
- **Duplicate records:** checked twice. The app looks for an existing `(source, external_id)` first,
  and the database's `UNIQUE` constraint catches anything that slips past (e.g. two clicks at the same
  moment). Snapshots in the same hour update the existing row. A duplicate manual entry returns HTTP 409
  with "already exists".
- **Database errors:** every write goes through one helper: commit; on `IntegrityError` roll back and
  report a duplicate; on any other `SQLAlchemyError` roll back, log the details on the server, and show
  "The database is unavailable right now. Nothing was saved." Reads used by the break page (stored
  fallbacks, latest AI summary, nav count) catch database errors, so the live page still renders if
  MySQL or the tunnel is down. A 500 handler shows a friendly page instead of a traceback.
  `pool_pre_ping` and `pool_recycle` replace connections that the SSH tunnel dropped.

## Screenshots

Captured from the running app on 2026-11-01 (Pacific time) against the **cloud MySQL database on CI-Keys**
(MariaDB 11.4, reached through the SSH tunnel), with live API data and a real RapidAPI key and Claude API key.
The Rincon manual entry ("Example entry: …") was typed in to demonstrate the form. It is labeled as example
data, not a real surf report.

**Homepage** (the nav shows the number of readings stored in MySQL)
![Homepage](docs/screenshots/a3-homepage.png)

**Break page: Save / Summarize / Add-a-note actions and the latest stored AI summary**
![Break detail with persistence actions](docs/screenshots/a3-break-detail-save.png)

**Database-backed list of stored readings (`/readings`)**
![Readings list](docs/screenshots/a3-readings-list.png)

**Filtered list (break = Rincon, kind = observation)**
![Filtered readings](docs/screenshots/a3-readings-filtered.png)

**Example of stored information: an acquired Open-Meteo reading with provenance and stored data**
![Stored API reading](docs/screenshots/a3-reading-detail-api.png)

**Example of stored information: a Claude AI summary with its grounding check and metadata**
![Stored AI summary](docs/screenshots/a3-ai-summary.png)

**Stored manual reading**
![Stored manual reading](docs/screenshots/a3-reading-detail-note.png)

**CRUD: create form**
![Create form](docs/screenshots/a3-reading-create.png)

**CRUD: validation errors (nothing saved)**
![Validation errors](docs/screenshots/a3-validation-errors.png)

**CRUD: edit form**
![Edit form](docs/screenshots/a3-reading-edit.png)

**New source: NDBC realtime buoy trend**
![Buoy trend](docs/screenshots/a3-buoy-trend.png)

**New sources: USNO daylight + CA Beach Watch advisories**
![Daylight and water quality](docs/screenshots/a3-daylight-water-quality.png)

**RapidAPI Second Opinion tab (live, free plan: WeatherAPI.com wind and gusts vs. Open-Meteo)**
![Second opinion tab](docs/screenshots/a3-second-opinion.png)

## Design Decisions

- **One `readings` table instead of one table per source.** Thirteen sources return thirteen different
  shapes. A common envelope (the seven required fields, plus `break_id`, `kind` and the cleaned values in
  `data_json`) lets every source share the same CRUD pages, filters, fallback logic and, in A4, one
  search index.
- **Why information is persisted:** history (compare forecasts with later observations), resilience
  (show the last saved copy when a source is down), user corrections (edit or delete bad data), and
  a fixed, citable input for the AI summary (it can only use what's stored).
- **Save on demand, not on every page view.** Writing ~13 rows for every visitor would fill the table
  with near-identical copies. An explicit save plus "one snapshot per break, per source, per hour"
  keeps the data meaningful.
- **Duplicate handling.** `external_id` encodes what makes an item unique: `break:source:YYYYMMDDTHH`
  for snapshots and `break:YYYYMMDDTHHMM:title-slug` for manual entries. The app checks first
  (update or reject), and `UNIQUE(source, external_id)` is the backstop at the database level.
- **Provenance is read-only for acquired data.** Editing a saved API reading can change its title,
  description and kind, but not its source, URL, time or raw data. Those record what the API said, and
  changing them would falsify the record. Manual entries can change everything.
- **Column sizes:** `source` (64) + `external_id` (120) keep the unique index under older MySQL's
  767-byte limit with 4-byte utf8mb4 characters.
- **Breaks stay in JSON for A3.** They are six hand-curated records, and the assignment's focus is
  persisting *acquired* information. Moving them into a `breaks` table is the first step of A4.
- **RapidAPI choice:** WeatherAPI.com on RapidAPI was picked because it is an independent forecast model,
  a true second opinion next to Open-Meteo rather than another copy of NOAA data. Its Marine endpoint
  (swell height, period, direction, tides) is the best fit, but RapidAPI's free plan blocks it with
  HTTP 401. Rather than pay for the plan, the service falls back to the free forecast endpoint. Wind is
  the other half of a surf call (offshore vs. onshore), so comparing two models' wind and gusts is still
  useful, and swell comes back automatically if the plan is upgraded.
- **AI summary design (preview of A5):** built only from stored readings, a bounded context (newest per
  source plus up to five notes), a number-grounding check, and full metadata stored with the output.
  Uses the official `anthropic` Python SDK with model `claude-opus-5-5`. Server-side refusal fallbacks
  are enabled (`fallbacks: "default"`), so a declined request is retried on a suitable fallback model
  automatically.

## Known Limitations

- **Breaks aren't a database table yet**, so `break_id` isn't enforced by a foreign key (it's validated
  in the app instead).
- **No rate limiting on forms.** One person could add many manual readings quickly. Planned before the
  survey feature goes live.
- **Manual readings are anonymous and unverified.** No accounts, so anyone with the app can edit or
  delete any reading.
- **Beach Watch data lags.** The state republishes it about monthly (newest Ventura record:
  2026-03-03), so it's shown as recent history, not today's status.
- **RapidAPI and Claude need keys** that aren't committed. Without them, those two features show their
  "off" messages. Both were also tested live with real keys (see Screenshots). The automated tests use
  mocked responses so they never spend money or need the network.
- **RapidAPI free plan has no swell data.** The Second Opinion tab compares wind and weather only, until
  the RapidAPI plan includes WeatherAPI.com's marine endpoint.
- **Some sources have gaps.** The NOAA CO-OPS water-temperature product currently returns no data for the
  mapped station, and the NDBC feed sometimes leaves the wave period blank (stored and shown as "n/a").
  Snapshots skip a source that is down and say which one.
- **The grounding check covers numbers only.** It can't catch a wrong non-numeric claim (e.g. the
  wrong wind direction).
- **Station mapping is still a static table** in `breaks.json`, not a nearest-station lookup.
- The `/readings` filter is exact-match only. Keyword search is A4.

## Future Work (A4: Search and Information Retrieval)

- Keyword search across `title` and `description` of stored readings, with relevance ranking
  (title matches above description matches) and MySQL FULLTEXT indexes.
- More filters (region, date range, forecast vs. observation), sortable columns, and the existing pagination.
- Helpful no-results behavior (suggest removing filters or broader terms).
- Search telemetry: record queries, filters, result counts and which result was opened.
- Move breaks into a `breaks` table with a foreign key from `readings`, which enables region filters in SQL.
- Survey reports from surfers (validated, no personal data, rate-limited) once readings CRUD is stable.

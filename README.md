# Crowdsurf

## Project Title

**Application:** Crowdsurf, a crowd-verified surf forecast for Ventura and Santa Barbara county breaks
**Student:** Brennen Meixner
**Course:** IT401 Web Intelligence, Assignment 4 (A4): Expanding the Web Intelligence Application with Search
**Branch:** `brennenmeixner-it401-a4`

Started from the `bpthoms/it401_project_template` Flask template. A1 built the homepage and the Explore
filter. A2 added live acquisition from APIs plus one scraped page. A3 stored acquired information in
MySQL with web CRUD and validation. **A4 makes the stored information searchable.**

## Project Overview

Surf forecasts are model output, and what a surfer finds at the beach often differs. Crowdsurf puts live
forecasts, real buoy observations and short notes from surfers side by side, so a surfer can judge whether
a forecast is holding up before deciding whether to paddle out.

**Intended users**
- **Local regular surfer** (primary): checks one or two home breaks and wants to know whether the
  forecast matches what the buoys see.
- **Newer surfer:** wants plain-language context (tide, daylight, water quality) next to the numbers.
- **Contributor:** any surfer who records what they saw at a break as a manual reading.

**How search improves the app:** after A3 the database grows by up to 13 readings per break every time a
snapshot is saved (6 breaks, one row per source per hour), plus notes and AI summaries, but the only way in
was a newest-first list. A4 adds
`/search`: type "rincon swell" or "buoy", narrow by break, source, kind and date, and get the most useful
readings first. Every search is recorded, so later modules can learn what surfers look for.

## Search and Retrieval Features

- **Keyword search** (`/search?q=...`) over stored readings. Multi-word queries: every word must match.
- **Fields searched:** reading `title`, `description`, and the **break name** (e.g. "jetty" finds South Jetty readings).
- **Filters:** break, source, kind (forecast / observation / note / summary), date from, date to. They
  combine with the keyword and each other, show as removable chips, and **Clear filters** removes all.
  Filters with no keyword is a "filtered browse", sorted newest first.
- **Sort options:** Best match (relevance, default with a keyword), Newest first, Oldest first, Title A to Z.
- **Ranking:** a relevance score computed in SQL (see Retrieval Strategy).
- **Pagination:** 10 results per page, in the database (`LIMIT/OFFSET` via `db.paginate`), Previous/Next
  links that keep the query, filters and sort, and "Showing 11 to 20".
- **Four page states:** before searching, results, no results (with suggestions), search unavailable.
- **Search telemetry:** one `search_events` row per search (query, filters, sort, result count,
  no-result flag, anonymous session id), plus which result was opened and at what rank.
  `/search/history` shows the latest 50 events and totals.
- **Evaluation tooling:** `scripts/run_search_eval.py` measures precision@10 and recall on real data.

## Search Workflow

```
Search form (GET /search?q=rincon+swell&kind=observation&sort=relevance)
  → routes/search.py            parse request, call the service, render
  → search_service.run_search()
       normalize_query()        trim, collapse spaces, casefold, cap at 100 chars, split into tokens
       parse_filters/sort/page  whitelist every value; bad ones ignored with a notice
       build_statement()        ONE SQL query:
           Retrieve   SELECT readings
           Filter     every token in (title OR description OR break name)  AND break AND source AND kind AND dates
           Rank       ORDER BY relevance score, newest, id
       db.paginate()            Paginate: LIMIT 10 OFFSET (page-1)*10, plus COUNT for the total
  → templates/search.html       Display: results, chips, pager, or a state message
  → log_search()                Telemetry: one SearchEvent (first page only; page turns carry se=<id>)
  → result link /readings/<id>?se=<event>&rank=<n>   → record_selection() notes the click
```

## Searchable Information

**Searchable model:** `Reading` (`readings` table). Every acquired snapshot, manual reading and AI summary is one document.

| Field | Role | Why |
|---|---|---|
| `title` | **searched**, ranked (+3 per word, +5 exact) | Short and specific: "Rincon: NOAA NDBC Realtime Feed, 2026-11-02 01:00 UTC". Contains the break and source. |
| `description` | **searched**, ranked (+1 per word) | The readable sentence of what the source said ("Observed: waves 5.9 ft, 7 s period"), the note text, or the summary. Longer and noisier, so weighted lower. |
| break name (from `data/breaks.json`) | **searched** | Surfers think in spot names. Manual notes don't always repeat the break in their title. |
| `break_id`, `source`, `kind` | **filters** | Controlled values: better picked from a list than typed. |
| `retrieved_at` | **filter** (date range), ranked (+1 if < 48 h old), sort | Freshness matters for surf conditions. |
| `id`, `external_id`, `source_url`, `data_json`, `created_at`, `updated_at` | **metadata only** | Internal ids, URLs and raw JSON would only add false matches. |

## Retrieval Strategy

**Query processing (Manning ch. 2):** *tokenization* splits the query on whitespace into terms;
*normalization* trims, collapses repeated whitespace, and casefolds so "RINCON" = "rincon". The text the
user typed is kept for display and telemetry. Queries longer than 100 characters are cut with a notice.
Deliberately **not** done: stop-word removal (queries here are a few spot and condition words, and dropping
words like "a" or "the" can break a name such as "A-frame"; the course calls it a design decision), stemming/lemmatization ("waves" won't
match "wave" unless it's a substring), and synonyms.

**Keyword matching:** each token becomes `title ILIKE '%token%' OR description ILIKE '%token%' OR break_id IN
(breaks whose name contains the token)`, and the tokens are joined with AND (Boolean retrieval: AND across
tokens, OR across fields). `%`, `_` and `\` in the user's text are escaped, so "100%" means a literal
percent sign. Everything is built with SQLAlchemy expressions; no SQL strings are formatted by hand.

**Filters** are added as more `AND` conditions. The date range is inclusive of the whole end day.

**Ranking** (Best match), computed in SQL so the database can sort and page:

| Signal | Points | Why for Crowdsurf |
|---|---|---|
| Whole query equals the title | +5 | An exact name is the strongest signal. |
| Each query word in the title | +3 | Titles name the break and source, which is what surfers type. |
| Each query word in the description | +1 | Descriptions are longer, so a match there says less. |
| Retrieved in the last 48 hours | +1 | Fresh conditions beat last week's. |

Ties are broken by newest `retrieved_at`, then highest `id`, so the order is stable and pages never
overlap or skip a result. This is a simple, explainable version of term weighting: field weights stand in
for TF, and recency is a context signal.

**Why `ILIKE` and not MySQL FULLTEXT:** the collection is small (hundreds to low thousands of rows),
`ILIKE` matches inside words ("swell" in "groundswell"), it runs on the SQLite test database too, and
the ranking stays fully explainable. FULLTEXT is in Future Work.

## Search Telemetry

**Recorded** (`search_events`, one row per completed search, never for an empty visit or a page turn):
raw and normalized query, the accepted filters, sort, result count, a no-result flag, time, an anonymous
session id (a random UUID in the Flask session cookie: no name, email, IP or location), and, when a result
is opened, its reading id and rank.

**Why and how it helps later:**
- **No-result queries** show missing vocabulary or data (e.g. people search "offshore" but snapshots say "wind 8 kt").
- **Clicked rank** shows ranking quality: if people usually open result #6, the weights are wrong.
- **Popular breaks, sources and filters** show what to acquire more often and what to show first.
- **Feeds A5/A6:** the decision page can start from the breaks and conditions a surfer actually searches for.

Clicks are interactions, not outcomes: opening a result doesn't prove it was useful. Recording whether a
surfer then went surfing (outcome) is planned for A6. The click is recorded on a GET (the result link),
a documented exception to "state changes are POST": it writes only telemetry, and only for an event that
belongs to the same browser session.

## Database Schema

Two tables. Schema changes go through Flask-Migrate (`migrations/versions/`).

**`readings`** (migration `0cab449f5d49`): stored acquired data, manual readings and AI summaries.

| Column | Type | Null? | Purpose |
|---|---|---|---|
| `id` | Integer, **PK** | no | Internal primary key |
| `title` | String(200) | no | Name of the reading, e.g. "Rincon: NOAA NDBC Realtime Feed, 2026-11-02 01:00 UTC" |
| `description` | Text | yes | One readable sentence of what the source said (or the note / AI summary text) |
| `source` | String(64), indexed | no | Short stable source id, e.g. `noaa-ndbc-realtime`, `crowdsurf-user`, `anthropic-claude` |
| `source_url` | String(500) | yes | Exact endpoint or page the data came from |
| `retrieved_at` | DateTime (UTC) | no | When the app fetched the data, or when the user observed it |
| `created_at` | DateTime (UTC) | no | When the row was inserted, set by the app |
| `external_id` | String(120) | no | Identifier for the external item (duplicate handling) |
| `break_id` | String(50), indexed | no | Which surf break (an id from `data/breaks.json`) |
| `kind` | String(20) | no | `forecast`, `observation`, `note` or `summary` |
| `data_json` | JSON | yes | The structured values (hourly series, tide table, buoy rows, AI metadata, manual measurements) |
| `updated_at` | DateTime (UTC) | yes | Last time the row was edited or refreshed |

Constraint: `UNIQUE (source, external_id)`. Extra fields beyond the seven required: `external_id`
(duplicate prevention), `break_id` (which break), `kind` (forecast vs. observation), `data_json` (each
source has a different shape), `updated_at` (refresh/edit time).

**`search_events`** (migration `d4d96c34b5a7`, new in A4): search telemetry.

| Column | Type | Null? | Purpose |
|---|---|---|---|
| `id` | Integer, **PK** | no | Internal primary key |
| `query_raw` | String(200) | no | What the user typed (trimmed) |
| `query_normalized` | String(200) | no | After normalization (what was matched) |
| `filters_json` | JSON | yes | The accepted filters, e.g. `{"kind": "observation"}` |
| `sort` | String(30) | no | `relevance`, `newest`, `oldest` or `title` |
| `result_count` | Integer | no | Total matches |
| `no_result` | Boolean | no | `result_count == 0`, for quick no-result reports |
| `session_id` | String(64), indexed | yes | Random per-browser UUID (no personal data) |
| `created_at` | DateTime (UTC), indexed | no | When the search ran |
| `selected_reading_id` | Integer, **FK → readings.id** (`ON DELETE SET NULL`) | yes | Result the user opened |
| `selected_rank` | Integer | yes | Its position in the results (1 = top) |

**Relationships:** `search_events.selected_reading_id` → `readings.id` (many events can point at one
reading; deleting the reading keeps the event and clears the link). `readings.break_id` refers to
`data/breaks.json` and is validated in the app.

## Current Features

- **Homepage** (`/`) and shared layout; the nav shows a live count of stored readings.
- **API integration:** 13 external calls per break: Open-Meteo marine and weather, NOAA NWS forecast and
  alerts, NOAA CO-OPS tides (3 products), NOAA SPC outlook, RainViewer radar, RapidAPI WeatherAPI.com
  (second opinion), NOAA NDBC realtime feed, USNO daylight and moon, CA Water Boards Beach Watch.
  Fetched in parallel and reused for `PANEL_CACHE_SECONDS`.
- **Web scraping:** the NOAA NDBC buoy station page (BeautifulSoup).
- **MySQL persistence:** Flask-SQLAlchemy models, Flask-Migrate migrations, CI-Keys MySQL through env vars.
  `flask acquire-all` saves a snapshot of every break in one command.
- **CRUD:** "Save this snapshot" and "Add a reading" (create), `/readings` and `/readings/<id>` (read),
  `/readings/<id>/edit` (update), delete button (POST).
- **Keyword search, filtering, sorting, relevance ranking and pagination** (`/search`). New in A4.
- **Search telemetry** and `/search/history`. New in A4.
- **Data validation** on every form and every search parameter; duplicates handled.
- **Stored-copy fallback** when a live source is down; **AI summary** (grounded, from stored readings).
- **CSRF protection** on every form (Flask-WTF).

## Project Structure

```
IT401WebIntelligence/
├── app.py                     # create_app(): config, extensions, routes, error pages, `flask acquire-all`
├── config.py                  # Config / DevelopmentConfig / TestConfig; DB URL from env vars; SEARCH_PER_PAGE
├── extensions.py              # db, migrate, csrf
├── requirements.txt, .env.example
├── migrations/versions/       # 0cab449f5d49 readings, d4d96c34b5a7 search_events
├── models/
│   ├── reading.py             # Reading + UniqueConstraint(source, external_id), utc_now()
│   └── search_event.py        # SearchEvent telemetry (A4)
├── routes/
│   ├── main.py                # home, explore, rewards, break page, save snapshot, summarize
│   ├── readings.py            # readings CRUD (+ records search clicks on the detail page)
│   └── search.py              # /search, /search/history (A4)
├── services/
│   ├── search_service.py      # A4: query processing, filters, ranking, pagination, telemetry
│   ├── reading_service.py     # validation, duplicates, CRUD, snapshot saving, stored fallbacks
│   ├── forecast_service.py    # parallel fan-out to every source, short cache; never raises
│   ├── ai_service.py          # grounded Claude summary + grounding check
│   ├── source_registry.py     # slug/label/URL/kind for every persistable source
│   ├── *_service.py           # one file per external source (A2/A3)
│   ├── external_common.py     # shared {live, source, data, fetched_at, error} result shape
│   └── breaks_service.py, rewards_service.py   # A1
├── templates/
│   ├── base.html              # head, nav, flash messages, footer
│   ├── search.html, search_history.html        # A4
│   ├── break_detail.html, readings/*.html, error.html, index.html, explore.html, rewards.html
├── static/style.css
├── data/breaks.json           # curated break reference data (coords + station ids)
├── scripts/run_search_eval.py # A4 evaluation against the real DB (not part of pytest)
├── docs/eval_queries.json     # evaluation queries + the records judged relevant
├── docs/screenshots/
└── tests/                     # pytest; in-memory SQLite, no network
    ├── test_search_service.py, test_search_routes.py   # A4
    ├── test_reading_model.py, test_reading_service.py, test_readings_routes.py, test_ai_service.py
    └── test_app.py + one test file per external source
```

## Installation Instructions

**Prerequisites:** Python 3.10+, Git, a CI-Keys MySQL database and SSH key (see the course "CI Keys SSH
Workaround" handout).

1. **Clone**
   ```bash
   git clone <repository-url>
   cd IT401WebIntelligence
   git checkout brennenmeixner-it401-a4
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
   # SECRET_KEY, NWS_USER_AGENT, and optionally RAPIDAPI_KEY and ANTHROPIC_API_KEY
   ```
5. **Open the SSH tunnel to CI-Keys MySQL** (leave this terminal open):
   ```bash
   ssh -N -o IdentitiesOnly=yes -o ExitOnForwardFailure=yes \
       -L 127.0.0.1:3307:127.0.0.1:3306 -i ~/.ssh/cikeys -p 22 \
       <CPANEL_USERNAME>@<CIKEYS_SERVER>
   ```
   `-N` forwards the port without opening a shell (CI-Keys accounts have no shell access; without it the
   server says "Shell access is not enabled on your account!" and closes the tunnel). Check it from
   another terminal with `nc -zv 127.0.0.1 3307`.
6. **Apply the migrations** (creates `readings` and `search_events`):
   ```bash
   export FLASK_APP=app.py            # Windows: set FLASK_APP=app.py
   flask db upgrade
   ```
7. **Optional: fill the database with real data** (one snapshot of every source for every break; run it
   at different hours to build history):
   ```bash
   flask acquire-all
   ```
8. **Run**
   ```bash
   python app.py                      # http://127.0.0.1:5000, search at /search
   ```
9. **Test**
   ```bash
   python -m pytest tests/            # 147 tests, no network or MySQL needed
   ```

If the `DB_*` variables are not set, the app logs a warning and uses a local SQLite file
(`instance/crowdsurf-dev.db`) so it can still start for development. The submitted app runs on MySQL.

## Environment Variables

All are read in `config.py` with `os.environ.get(...)`. Real values go only in `.env`, which is gitignored.

| Variable | Required? | Purpose |
|---|---|---|
| `DB_USERNAME` | yes (MySQL) | CI-Keys MySQL user |
| `DB_PASSWORD` | yes (MySQL) | CI-Keys MySQL password |
| `DB_HOST` | yes (MySQL) | `127.0.0.1` when using the SSH tunnel |
| `DB_PORT` | no (default 3306) | `3307` with the tunnel above |
| `DB_NAME` | yes (MySQL) | database name |
| `SECRET_KEY` | yes in practice | signs the session cookie (CSRF tokens, search session id) |
| `NWS_USER_AGENT` | recommended | contact string required by the NWS API usage policy |
| `EXTERNAL_API_TIMEOUT` | no (default 10) | seconds before any external call gives up |
| `PANEL_CACHE_SECONDS` | no (default 300) | seconds a break page's live data is reused (0 = always fresh) |
| `RAPIDAPI_KEY` | optional | RapidAPI key for WeatherAPI.com (free Basic plan works) |
| `ANTHROPIC_API_KEY` | optional | Claude API key for AI summaries |
| `ANTHROPIC_MODEL` | no (default `claude-opus-5-5`) | Claude model id |
| `FLASK_ENV` | no (default `development`) | selects the config class |

The database URL is built with `sqlalchemy.engine.URL.create(...)`, so special characters in the password
are escaped safely. It is never printed or logged.

## Error Handling

**Search (A4)** — every case below has an automated test:

| Situation | What happens |
|---|---|
| Empty or whitespace-only query, no filters | "Enter a keyword to begin." No database query, nothing logged. |
| Empty query with filters | Filtered browse, newest first. |
| Very long query | Cut to 100 characters, notice "Your search was shortened to 100 characters." |
| `%`, `_` or `\` in the query | Escaped, matched literally. |
| Unknown break / source / kind value | Ignored, notice "Ignored unknown filter value '…'". |
| Bad date, or start after end | Ignored, notice explains the format or the reversed range. |
| Unknown sort | Falls back to Best match (with a keyword) or Newest first. |
| Page `abc`, `0`, `-3` | Page 1 with a notice. Page `99999` → last page with a notice. |
| No matches | "No matching records were found. Try a broader term or remove a filter." plus chips to remove filters and a fewer-words suggestion. |
| Database down during search | "Search is temporarily unavailable." HTTP 503, rolled back, logged, no traceback. |
| Telemetry write fails | Rolled back and logged; the results still show. |
| Bogus `se`/`rank` on a result link, or another session's event | Ignored; the reading page opens normally. |
| Record with no description | "No description." placeholder. |

**Forms and CRUD (A3):** every form is checked on the server before anything is written (required fields,
lengths, allowed kinds, `http(s)://` URLs, dates that parse and aren't in the future, numbers in range).
On failure the form is shown again with every problem, HTTP 400, nothing saved. Unknown ids → friendly
404. Create/update/delete are POST-only with a CSRF token.

**External sources:** every source returns `{live, source, data, fetched_at, error}` and never raises; a
failed source shows its last saved copy or "unavailable". Missing `RAPIDAPI_KEY` / `ANTHROPIC_API_KEY`
turns off just that feature with a message.

**Duplicates and database errors:** `(source, external_id)` is checked first and enforced by a `UNIQUE`
constraint; snapshots in the same hour update the row; duplicate manual entries (also after an edit)
return 409. Every write: commit, or roll back with a friendly message and a server-side log. A 500 handler
shows a friendly page instead of a traceback.

## Search Evaluation

> **To do (Brennen):** this section must use real searches on the real MySQL data. Steps:
> 1. Open the tunnel and run `flask acquire-all` at a few different hours (and add a few real notes), so
>    there are dozens of readings across all six breaks and several sources.
> 2. **Before** running any search, browse `/readings` and write the ids you judge relevant for each
>    query into `docs/eval_queries.json` (`"expected": [ids]`). Adjust the queries if you like.
> 3. Run `python scripts/run_search_eval.py` and paste the numbers into the table below.

**Measures:** *precision@10* = relevant results in the top 10 ÷ results shown in the top 10 (are the top
results useful?). *Recall* = relevant records found ÷ all relevant records (did search find everything?).

| # | Query (filters) | Expected relevant | Returned | Most useful near the top? | False positives | Missed | P@10 | Recall |
|---|---|---|---|---|---|---|---|---|
| 1 | `rincon` | | | | | | | |
| 2 | `swell` | | | | | | | |
| 3 | `buoy` | | | | | | | |
| 4 | `south jetty tide` | | | | | | | |
| 5 | `offshore` | | | | | | | |
| 6 | `wave` (kind=observation, break=Oxnard Shores) | | | | | | | |

**Discussion:** *(after running: where precision was low and why, where recall was low and why, whether
ranking put the best result first, and one improvement, e.g. mapping "offshore" to wind-direction
readings, or simple plural handling so "waves" also finds "wave")*

## Screenshots

> **To do (Brennen):** capture from the running app on MySQL (no `.env`, usernames or hosts visible) and
> save into `docs/screenshots/` with these names.

- Search form: `a4-search-form.png`
- Results for a keyword: `a4-search-results.png`
- Filtered results with chips: `a4-search-filtered.png`
- Sorted / ranked results: `a4-search-sorted.png`
- Pagination (page 2): `a4-search-page2.png`
- No-results state: `a4-search-no-results.png`
- Search history / telemetry: `a4-search-history.png`

A3 screenshots (persistence and CRUD) remain in `docs/screenshots/a3-*.png`.

## Design Decisions

- **Searchable fields:** title, description and break name are the free text a surfer would type.
  Source, kind, break and date are controlled values, so they're filters (picked, not typed). Raw JSON,
  URLs and ids are not searched: they would only add false matches.
- **Ranking:** title words outrank description words because titles name the break and source; a recency
  bonus because surf conditions go stale in hours; ties broken by newest then id for stable pages. Rules
  instead of TF-IDF keep it explainable and testable, and it all runs in SQL so paging stays in the database.
- **Page size 10:** the low end of the assignment's 10 to 20 range. Readings are dense (title, sentence,
  break, source, kind, time), and 10 fits a laptop screen without scrolling past the pager.
- **Breaks stay in JSON.** Six hand-curated records. Break-name search is done by looking the typed word
  up in `breaks.json` and adding `break_id IN (...)` to the same SQL query, so no schema change was needed.
- **AI summaries are searchable** (kind = summary) because they're stored readings too; the Kind filter
  hides them.
- **Plain GET form, not Flask-WTF**, as in the Module 5 deck: a search changes nothing, and the URL can be
  bookmarked and shared.
- **Telemetry supports later intelligence:** no-result queries, clicked ranks and popular filters become
  inputs for A5 (summaries that answer what people search) and A6 (which breaks to compare first).
- **One `readings` table** (A3): thirteen sources share one envelope, so CRUD, fallbacks and search work
  on all of them at once. Duplicate handling via `external_id` + `UNIQUE(source, external_id)`.
- **Provenance is read-only for acquired data** (A3): editing an API reading can't change its source,
  URL, time or raw data.

## Known Limitations

- **No synonyms or stemming:** "offshore" won't find "wind from the NE", and "waves" won't find "wave"
  (though "wave" finds "waves", since matching is by substring).
- **Substring matching can over-match:** "on" matches "onshore" and "Second opinion".
- **Rule-based ranking** with hand-picked weights, no TF-IDF and no learning from clicks yet.
- **No full-text index:** `ILIKE '%word%'` scans the table, fine at this size but not for millions of rows.
- **No personalization:** everyone gets the same order.
- **Dates are UTC** in filters and results; Pacific-time evening readings fall on the next UTC day.
- **Telemetry is anonymous per browser**, so it can't follow one surfer across devices (by design).
- **Breaks aren't a database table**, so `break_id` isn't a foreign key (validated in the app).
- **No rate limiting** on forms or searches.
- **The live-data cache is per process** (`PANEL_CACHE_SECONDS`); several server workers would need a shared cache.
- **Source gaps:** CO-OPS water temperature returns no data for the mapped station, NDBC sometimes omits
  wave period, Beach Watch lags about a month, and the RapidAPI free plan has no swell data.

## Future Work

For A5 and later:
- **Semantic search** with embeddings, so "clean conditions" finds "glassy" and "offshore".
- **MySQL FULLTEXT** with natural-language relevance once the collection grows.
- **Personalized ranking** from telemetry (home breaks first) and learning weights from clicked ranks.
- **Query suggestions and autocomplete** from popular past searches; spelling correction for break names.
- **Retrieval-augmented generation:** feed the top search results into the grounded AI summary (A5).
- **Decision support (A6):** compare breaks (Go / Wait / Skip) starting from what the surfer searched.
- Survey reports from surfers (validated, no personal data, rate-limited).

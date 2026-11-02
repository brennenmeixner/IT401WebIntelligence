# IT401 Web Intelligence: course material notes

**Instructor:** Dr. Brian Thoms (CSU Channel Islands). Async online course. **Grading:** quizzes 20%, assignments 50%, course project and presentation 30%. Letter scale: A+ 97, A 93, A- 90, B+ 87, B 83, B- 80, C+ 77, C 73, C- 70, D+ 67, D 60, F below 60. **Academic integrity:** it is the student's responsibility to ensure everything is correctly uploaded to CI Learn by the due date; a broken computer is not an excuse. AI is a "pair programmer" in this course, but "use AI to accelerate learning, not to avoid understanding", and the student is responsible for the final product.

**Course objectives:** design, implement and test a basic web crawler; organize data in a relational database; design and implement a simple decision support system; explain the web-services concept; analyze intelligent agents; classify web software agents; classify and analyze web knowledge sources.

**Texts:** Hulten, *Building Intelligent Systems* (O'Reilly); Grinberg, *Flask Web Development* 2nd ed. (O'Reilly); Manning, Raghavan and Schütze, *Introduction to Information Retrieval* (free online); Google PAIR Guidebook; NIST AI RMF.

## Schedule and deliverables

| Module | Weeks | Topic | Readings | Deliverables |
|---|---|---|---|---|
| 1 | 1 to 2 | Intro to Web Intelligence; Python, Flask, GitHub and Codex | Hulten 1 and 2; Thoms' slides | **A1**, P1 topics |
| 2 | 3 to 4 | Information acquisition; APIs | Hulten 3 and 9 | **A2** |
| 3 | 5 | Project updates and presentations | | **Q1**, **P2** Google Slides proposal + discussion |
| 4 | 6 to 7 | Persistence and application architecture | Hulten 11, 12, 15; Grinberg 2 and 5 | **A3** |
| 5 | 8 to 9 | Information retrieval and search | Manning 1, 2, 6; Hulten 8, 12, 15; Grinberg 3, 5, 7 | **A4** |
| 6 | 10 | Project updates and presentations | | **Q2**, **P3** Google Slides project design |
| 7 | 11 to 12 | Information analysis and intelligence generation | Hulten 13, 14, 15; Grinberg 3, 5, 7 | **A5** |
| 8 | 13 to 14 | Intelligent decision support | Hulten 14, 15; PAIR Guidebook sections 1 to 4; NIST AI RMF trustworthy-AI characteristics | **A6** |
| 9 | 15 to 16 | Term project implementation and presentations | | **Q3**, final Google Slides, **P4** implementation |

## Term project structure (from the Term Project PDF)

Assignments A1 to A6 are the technical milestones; the final project is the **integrated, tested, documented, professionally presented** version of the same system (not a new app and not a big new feature).

| Milestone | What it is |
|---|---|
| P1 Project Topic | 5 to 7 slides: title, problem, users, decision supported, purpose, tech stack, APIs/datasets/sites, possible intelligent capability, how it fits IT401. The "five yes" fit check: acquire external info; store some; users search/retrieve; generate insights; help someone decide. |
| P2 Proposal | 10 to 15 slides covering the 12 sections (summary, background, objectives, users, functional and nonfunctional requirements, information sources, intelligent capability, decision support, success criteria, risks, proposal check). Rubric: problem and goals 15; functional and nonfunctional requirements 15; information sources and feasibility 20; intelligent capability and decision-support planning 20; scope, timeline and risks 15; presentation 15. |
| P3 Project Design | Slides with: system architecture diagram; database design (ER diagram, tables, PKs/FKs, provenance and timestamp fields, telemetry tables); UI design (wireframes, navigation, search, results, intelligent-output and decision-support views); information-flow diagram; intelligence design (where, task, model/technique, retrieved info supplied, expected output, validation, metadata); decision-support design (decision, recommendation, evidence, alternatives, uncertainty, feedback). |
| P4 Final implementation | Must demonstrate (details below). |
| P5 Final README and recorded presentation | A 7 to 15 minute recorded presentation that tells the story, not a page-by-page tour. |

**P4 required end-to-end lifecycle:** integrated UX (consistent navigation, shared layout, terminology, hierarchy, instructions/status messages, responsive where practical); information acquisition (at least one **RapidAPI** integration and at least one responsibly **scraped public page**, meaningful processing of both, protected credentials, attribution/source documentation, graceful handling of unavailable sources, reuse of stored MySQL data when sources are down); persistence (**cloud MySQL, Flask-SQLAlchemy, SQLAlchemy models, migrations, validation, duplicate prevention, provenance metadata, relationships**, available across sessions and to multiple users); search (keyword, multi-field, **at least two filters**, sorting/relevance ranking, pagination, helpful no-results, basic search telemetry; search must run over persisted records); intelligence (A5 capability using retrieved application info, bounded context, protected credentials, validated output, graceful failure, recorded model/prompt/generation metadata); decision support (clear recommendation, supporting evidence, **at least two alternatives**, comparison criteria, uncertainty/confidence, user control over the final decision, feedback/decision recording; "support rather than replace human judgment"); telemetry (searches, results selected, intelligent features used, recommendations shown, alternatives selected, ratings, decisions accepted/rejected, errors, processing times, outcomes; **distinguish an interaction from an outcome**); reliability and security (no raw tracebacks; no active API keys, DB credentials, secret keys or sensitive personal data in the repo); cleanup (remove unused code/templates, fix broken links, document all env vars, apply and test migrations, verify A1 to A6 still work, review the repo for exposed credentials); evaluation (functional testing, search evaluation on representative queries: relevance, ranking, false positives, missed results, no-result behavior; intelligence evaluation: groundedness, accuracy, relevance, completeness, consistency, usefulness, limitations; decision-support evaluation: explanation quality, usefulness of alternatives, clarity of tradeoffs, uncertainty, user control, actionability; **user evaluation with at least two test users**, recording task, problems, feedback, improvement; **do not collect or store unnecessary personal information**).

**Final README must include:** title, student name, course, overview, problem statement, intended users, current features, external sources, tech stack, architecture, information-flow diagram, database schema, search and retrieval design, intelligent capability, prompt/context strategy, decision-support design, telemetry and feedback, installation, env vars, migrations, running, screenshots, testing and evaluation summary, security and ethical considerations, known limitations, future improvements, and a **System Evolution reflection** answering: what A1 created; how A2 expanded sources; why persistence was necessary in A3; how A4 improved access; what intelligence A5 added; how A6 made it more useful to a person; which architectural decision had the biggest effect; the most significant limitation; what "A7" would include with four more weeks.

**Final rubric (100):** end-to-end functionality 15; acquisition and persistence 10; search and retrieval 10; intelligence generation 15; human-centered decision support 15; system integration and technical quality 10; reliability, security and error handling 10; evaluation and feedback 5; documentation and architecture poster 5. (The presentation is also listed at 5 in one table; confirm with the instructor.)

---

## Module 1: Introduction to Web Intelligence and the tech stack

**Source:** Mod1-Intro.pdf (Hulten Ch. 1 and 2) and Mod1-TechIntro.pdf.

### Concepts
- **Web eras:** Web 1.0 read-only (about 1991 to 2004); Web 2.0 read-write, user-generated content, APIs, AJAX; Web 3.0 semantic/decentralized (read-write-own); Web 4.0 intelligent/symbiotic (autonomous AI agents, IoT, ambient computing; emerging).
- **Web Intelligence** = the convergence of WWW technologies and AI: web mining, information retrieval, pattern recognition, predictive analytics, semantic web, web data warehousing; heavy focus on personalization and adaptive sites. Topic areas include web-based decision support, web information retrieval, web agents (recommenders, filtering), web mining, web security/privacy/trust.
- **Traditional vs. intelligent systems:** traditional systems store, process transactions, produce reports. Intelligent systems **acquire, interpret, learn from, and support decisions**. "Intelligence comes from using information, not simply storing it."
- **Five elements of an intelligent system (Hulten):** (1) **Purpose** (why does it exist), (2) **Intelligent experience** (how the user benefits, collects feedback), (3) **System implementation** (how intelligence is delivered; reliable, monitored, maintainable), (4) **Intelligence** (rules, ML, LLMs, hybrid), (5) **Orchestration** (how it improves over time: monitor, update, reduce risk, learn from feedback).
- **Machine learning / LLMs:** ML learns patterns from data to predict or decide without explicit rules; LLMs are ML models trained on massive text (ChatGPT, Copilot, Gemini).
- **Hulten Ch. 2, when to use intelligent systems:** not every problem needs AI (use traditional code when rules are known and stable; Occam's razor). Intelligent systems "deploy, collect data, learn, improve, repeat forever". Partial solutions are valuable if value exceeds frustration; weigh **cost of mistakes** (low: recommendations, search ranking; high: medical, aircraft). The **learning loop** and "data is fuel" ideas; intelligence must influence meaningful decisions. **Decision checklist** = the five yes/no project questions.
- **Example:** the instructor's "Health eProfile" (personalization, multi-source real-time data, effective storage, statistics, visualization).

### Technical foundation (Flask, Git, tooling)
- **Why Flask:** lightweight, readable, flexible, great for APIs, easy to connect to data and AI (vs. Django: larger, more built in). "Where should this code live?" is the core question.
- **Architecture:** `app.py` (factory `create_app()`: create app, load `config.py`, register blueprint, run), `config.py`, `routes/` (URL → function), `services/` (APIs, search, AI logic), `models/`, `templates/` (Jinja), `static/`, `data/`, `tests/` (pytest).
- **Request-response flow:** Browser → Flask route → (service) → Jinja template → HTML response. "Flask is running a local web server that responds when your browser requests a URL."
- **Services pattern:** routes stay short; API calls, parsing and business rules live in services (isolate code that talks to external systems because they fail more often than your own code).
- **Config and secrets:** no real keys in `app.py`, routes, templates, services or public repos; use environment variables or a `.env` that is in `.gitignore`.
- **Testing:** "add one test for every new route", run `python -m pytest tests/` before submitting; read the failure message first.
- **Virtual environments:** `python3 -m venv .venv`, activate, `pip install -r requirements.txt`, `pip freeze > requirements.txt`; never commit `.venv`.
- **Git/GitHub workflow:** create your own repo from the template (do not name it `it401_project_template`; use your name in the repo/branch name); edit → test → commit in small commits; do not commit `.venv` or keys. Submitted repos must be **working**.
- **Troubleshooting:** change one thing at a time. `ModuleNotFoundError` → activate venv and install requirements; "Address already in use" → stop other Flask process or change port; `TemplateNotFound` → check the file is inside `templates/`; 500 → read the traceback; push rejected → pull first.
- **AI pair programmer:** ask Codex, then **verify** against official docs and course architecture.
- **A1 checklist:** repo from template; app runs; venv documented; new route and template; API-powered route displays external data; tests run; committed and pushed.

---

## Module 2: Data acquisition (A2)

**Source:** Intro.pdf (Hulten Ch. 3 and 9) and Mod2-DataAcquisition.pdf.

### Hulten Ch. 3 (Working with Data)
- Information is the foundation of intelligence; quality of information determines quality of intelligence ("good decisions begin with good information").
- **Structured** (JSON, CSV, databases, API responses) vs. **unstructured** (HTML, PDFs, images/videos, social posts); scraping turns unstructured data into structured information.
- Finding the right data means asking the right questions.
- **Data quality problems:** noise (incorrect values), bias (unrepresentative data), outdated data.
- **Sources:** databases, JSON files, REST APIs, web pages, sensors, human input. The "intelligent system pipeline": Acquire → Manage (clean, structure, validate) → Find (search/retrieve) → Generate intelligence → Support decisions.

### Hulten Ch. 9
- **Context, Action, Outcome:** every interaction has **context** (user, history, preferences, query, location, time), an **action** (search results, recommendation, prediction, notification), and an **outcome** (click, purchase, rating, ignore, success, failure). Netflix example.
- **Explicit vs. implicit feedback:** explicit = user tells us (ratings, like/dislike, reviews, surveys, report a problem); implicit = system observes (watched, clicked, purchased, skipped, time on page).
- **Real usage creates better information:** what users actually do is more reliable than what they say (survey vs. search history; rating vs. purchase; review vs. repeat visit).

### APIs and REST
- API = common language between software sharing resources; server-side web APIs expose endpoints over HTTP; responses are JSON (preferred) or XML.
- **REST** (Roy Fielding): decoupled, stateless, layered, uniform interface, cacheable.
- **HTTP methods:** GET (data in URL, bookmarkable, cacheable) vs. POST (data in body, hidden, "more secure").
- **JSON** objects: key-value; parse to dicts in Python.
- **Authentication:** some APIs are open; others need keys/tokens (OAuth), enforce **rate limits** (e.g. 500/hour) or charge per call. **API keys** act as a handshake, track usage under terms of service; never store them in published code: use `.env` plus `.gitignore`.
- **Mash-ups:** apps combining content from multiple sources to create new services (e.g. addresses plus photos on a map). Examples of API catalogs: **RapidAPI**, **APIFreak**; OpenWeather was the weather example.

### Web scraping
- Technique to extract data over HTTP (or an embedded browser), turning unstructured data into structured data for later storage/analysis.
- **Legal and ethical:** read the site's Terms of Use first; do not take information without permission and proper referencing; liability depends on the type of access, amount of data copied, harm to the site's system, and any prohibitions.
- **Tools:** Python `requests` (HTTP) and **Beautiful Soup** (parse tree; `find()`, `find_all()/findAll()`, `get_text()`, CSS class selectors, `.children`). Think of pages as files plus resources (CSS, JS, images).
- **Reliable connections:** handle 404, server errors, missing elements; always handle exceptions for data that may not exist.

### A2 assignment (from the slide, partially legible)
"**A2: Expanding the Web Intelligence Application Using an API.** Your enhanced application must retrieve data from a **RapidAPI** service and scrape relevant information from at least one webpage. It should process both sources and present the results through a useful interface, report, dashboard or analysis." Objectives included: explain API vs. scraping differences; authenticate and send requests; interpret JSON; extract information from HTML; clean/normalize data from different sources; handle failed requests and missing data; protect API credentials; evaluate ethical and technical limits; integrate multiple web-based sources. Deliverable: new branch `yourname-it401-a2` plus a PDF showing required elements. (**Note:** the Crowdsurf A2 repo has no RapidAPI source. See Part 1.4.)

---

## Module 4: Information persistence and application architecture (A3)

**Source:** Mod4-Persistence.pdf (Hulten Ch. 11, 12, 15; Grinberg Ch. 2 and 5).

- **SQLAlchemy:** the Python SQL toolkit and ORM. Two layers: **Core** (schema/types, SQL expression language, engine, connection pooling, dialect, DBAPI) and the **ORM** on top.
- **How Flask connects to MySQL (5 layers):** Flask route (web layer) → SQLAlchemy model (data model layer; tables and relationships) → ORM session (unit of work; tracks changes) → **PyMySQL** driver (adapter; speaks the MySQL protocol) → cloud MySQL. "Students work primarily with Python objects, while MySQL still executes SQL behind the scenes."
- **Persistence stack:** Flask application; **Flask-SQLAlchemy** (ORM integration); **Flask-Migrate** (schema migrations over time); PyMySQL; cloud MySQL.
- **DB credentials:** never in source code. Put in `.env`: `DB_USERNAME`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`, `DB_NAME`; add `.env` to `.gitignore`.
- **Flask configuration:** build the connection URL from environment variables (`URL.create(drivername="mysql+pymysql", username=..., password=..., host=..., port=int(...), database=...)`). Why: safer (special characters), clearer, portable, secure. URL shape: `mysql+pymysql://username:password@host:3306/database`. App config: `SQLALCHEMY_DATABASE_URI`, `SQLALCHEMY_TRACK_MODIFICATIONS=False`; `db = SQLAlchemy(app)`; `migrate = Migrate(app, db)`.
- **ORM:** lets you work with Python objects instead of writing SQL (`db.session.add(user)`, `User.query.filter_by(...)`); more productive, safer (parameterized queries help prevent SQL injection), portable, maintainable.
- **Types of data attributes:** domain info (title, description, category, rating, location); **provenance** (source, source_url, external_id, retrieved_at, last_updated); temporal (created_at, updated_at, start/end); classification (category, rating, status, priority); location (latitude, longitude, address).
- **Defining data:** distinguish `id` (internal application identifier) from `external_id` (identifier supplied by an API or external source). A useful uniqueness rule combines **source + external_id**. Example `Item` model: `id` PK; `title` String(200) not null; `description` Text; `source` String(100) not null; `source_url` String(500); `external_id` String(150); `retrieved_at` DateTime default UTC-now, not null; with `UniqueConstraint("source", "external_id")`.
- **Migrations (3-step workflow):** `flask db init` (once) → `flask db migrate -m "Create initial tables"` (generates a migration; does **not** change MySQL) → `flask db upgrade` (applies it). Always **review the generated migration** before upgrading; do not skip it; back up before major changes; commit migration files.
- **CRUD:** Create = `db.session.add()` + commit (INSERT); Read = select/`db.session.get()` (SELECT; list, detail, search, filter); Update = get, change fields, commit (UPDATE); Delete = get, `db.session.delete()`, commit (DELETE). Missing item → `abort(404)`. Request flow: User → Flask route → business logic → SQLAlchemy ORM → PyMySQL → MySQL.
- **Building reliable, high-quality data workflows:** (1) **Persist an external API result:** write `item_from_api(result)` to transform data into a model object (id → `external_id` as string, title → `title` trimmed, description → `description` allowing missing values, url → `source_url` preserving provenance), then `add` and `commit`. (2) **Prevent duplicates, two layers:** application check (select existing by source + external_id; update or insert) and a database constraint (`UniqueConstraint`) that catches duplicates even if the app check is bypassed. (3) **Transactions and errors:** try / commit; `except IntegrityError` → rollback, return "This record already exists." (409); `except Exception` → rollback, log, return a friendly 500 message. Avoid `except Exception: pass`. Commit only on success; roll back on failure; log unexpected errors; return meaningful messages.
- **Revised architecture (11 steps):** User input → Flask route → API or web scraper → validation and normalization → SQLAlchemy model object → SQLAlchemy session → PyMySQL driver → cloud MySQL → ORM query → Flask/Jinja template → user response. Layers: web interface, data acquisition, data processing (prepare/clean), application/ORM (models and session), database access (driver), storage (MySQL), query/retrieval, presentation (Jinja2), response.
- **Codex as database partner (course workflow):** Explain the goal → Ask Codex to inspect first → Delegate the update → Test the result → Review before committing. Prompt → Plan → Implement → Test → Review → Commit. "Codex can implement much of the work, but **you** define the goal, review the plan, test the results, and approve the final changes." Review checklist: git diff; migration files; credential safety; data-loss risks; exception handling. Verification checklist: app starts; MySQL connection succeeds; migrations apply; create/read/update/delete work; duplicates handled; tests pass.
- **Summary terms:** persistence stack; Flask configuration; ORM, schema and data migrations; CRUD; intelligent-systems architecture; working with the coding assistant.
- **CI-Keys SSH workaround (handout):** the CI-Keys MySQL is reached through an SSH key and tunnel (details in `.claude/rules/database.md`): create a key with `ssh-keygen -t rsa -b 4096 -f ~/.ssh/cikeys` (optionally `-m PEM`), import the **public** key in cPanel (SSH Access → Manage SSH Keys → Import Key, then **Authorize**), connect Workbench via Standard TCP/IP over SSH (SSH host = server from CI Keys + `:22`, SSH user = cPanel username, key file = private `cikeys`, MySQL host `127.0.0.1`, port 3306), repeat per device (or use a separate key per device), and fall back to a manual `ssh -L 127.0.0.1:3307:127.0.0.1:3306 ...` tunnel with the database client on port **3307** if Workbench fails. Never share the private key.

---

## Module 5: Information retrieval and search (A4)

**Source:** Mod5 deck "Search and Retrieval" (Manning Ch. 1, 2, 6; Hulten Ch. 12 and 15).

- **Framing:** persistence makes information available; retrieval makes it **useful**. "You can't use what you can't find." Industry spotlight: Amazon search and recommendations (search, persisted history, personalized results, recorded outcomes).
- **Learning outcomes:** design/execute search strategies; filter, sort, rank; normalize and structure retrieved data; extract entities and metadata; evaluate relevance and quality; integrate multiple sources; handle pagination/limits/API constraints; dedupe and clean; preview results; prepare information for later intelligence modules.
- **Database retrieval vs. information retrieval:** database = structured records, exact conditions, deterministic ("which records qualify?"); IR = often unstructured text, approximate relevance, results are **ranked** ("which results are most useful?").
- **Core IR concepts:** document (a searchable unit; for projects, a listing/article/reading/report), term (normalized token), query, result set.
- **Search is not string matching:** exact strings miss related forms (connect/connected/connecting) and conceptual relatedness (car/automobile/vehicle).
- **Boolean retrieval:** AND, OR, NOT. Strengths: clear, predictable, easy to explain. Limitation: does not rank. UI filters (keyword, category, location, exclude) are Boolean logic in disguise.
- **Inverted index:** maps term → documents containing it (vs. forward index document → terms). Indexing makes search fast and scalable; must be maintained as data changes; in MySQL, **FULLTEXT indexes** can beat repeated `LIKE '%word%'` scans.
- **Query processing pipeline:** raw query → **tokenization** → **normalization** (lowercase, punctuation, whitespace, accents, abbreviations) → **stop-word** decisions (a design decision, not an automatic rule; "The Who", "To Be or Not to Be") → **stemming/lemmatization** (improves recall; can distort domain terms) → search terms.
- **Fields and weighting:** not all matches equal. Title match > category > description; source/category can be filters rather than scored fields.
- **Relevance and ranking:** matching is not enough; relevance depends on document, query, user, task, context. **Term frequency** (how often in the document; can mislead via long documents or keyword stuffing); **IDF** (how rare across the collection); **TF-IDF** (frequent in a document but rare across the collection indicates relevance; present conceptually, no heavy math). **Other signals:** title matches, exact phrases, recency, popularity, ratings, user preferences, source quality, geographic distance, prior clicks, business rules.
- **Evaluation:** **precision** (of results returned, how many relevant) vs. **recall** (of all relevant records, how many found); narrow queries favor precision, broad queries favor recall.
- **No results:** a retrieval outcome, not a dead end. Causes: query too narrow, vocabulary mismatch, spelling, missing records, incorrect filtering, stale index, misunderstood intent. Helpful responses: suggest broader terms, remove filters, correct spelling, show related categories, explain what was searched.
- **UX:** a technically correct search can still be poor. Provide clear controls, understandable filters, result summaries/snippets, visible sort options, pagination, helpful no-results messages, explanations of why a result matched.
- **Hulten Ch. 12 and 15:** retrieval at runtime: user request → interpret query → retrieve relevant context → apply application/intelligent logic → return ranked results. **Context** (candidate records, user history, preferences, prior interactions, current query, source metadata, recent outcomes) gives intelligence something grounded. **Search telemetry** (query, filters, number of results, result selected, rank position selected, query reformulation, no-result events, time to selection, errors, abandoned searches) feeds the **feedback loop**: user query → results ranked → user selects or ignores → interaction recorded → experience evaluated → ranking improved. "Recording clicks does not automatically prove relevance, but it provides a useful signal." Search and recommendation share building blocks (stored information, retrieval, ranking, context, feedback).
- **Architecture:** search form → Flask route → query processing → **SQLAlchemy/MySQL retrieval** → filtering and ranking → results template → interaction telemetry.
- **A4 requirements (from the slide):** *Core:* keyword search (across relevant text fields); field-based filtering (project-specific fields); sorting (by different fields); pagination; relevance ordering; search history/telemetry (record searches and selections); helpful no-result behavior. *Optional:* MySQL FULLTEXT search; highlighted terms; saved searches; autocomplete. "Applied to your project: implement these features using Flask, SQLAlchemy and MySQL within your own project domain and data."

---

## Modules 3 and 6 (presentations) and Modules 7 and 8 (A5, A6)

- **Module 3 (week 5, Q1):** P2 proposal slides + class project discussion. **Module 6 (week 10, Q2):** P3 project design slides + discussion. **Module 9:** final presentation + P4/P5 (see Term Project section).
- **Module 7 (A5), Information Analysis and Intelligence Generation:** Hulten Ch. 13, 14, 15; Grinberg Ch. 3, 5, 7. Slides **not provided**. From the term project: the intelligent capability (e.g. classification, tagging, Q&A, recommendation, sentiment, similarity, summarization) must use retrieved application information, construct **bounded context**, protect API credentials, **validate generated output**, handle failures, and record model/prompt/generation metadata.
- **Module 8 (A6), Intelligent Decision Support:** Hulten Ch. 14 and 15; **Google PAIR Guidebook sections 1 to 4**; **NIST AI RMF trustworthy-AI characteristics**. Slides **not provided**. From the term project: clear recommendation, supporting evidence, at least two alternatives, comparison criteria, uncertainty/confidence, user control, feedback recording; support rather than replace human judgment.

---

## Quick glossary

**ORM:** maps Python objects to database tables. **Migration:** a versioned script that changes the DB schema. **Provenance:** where a record came from (source, URL, retrieved date). **Idempotent save:** saving the same external record twice does not create duplicates. **Telemetry:** recorded app activity (searches, clicks, errors, outcomes). **Interaction vs. outcome:** what the user did vs. what happened as a result. **Grounded output:** AI output that only states what the stored data supports. **Precision/recall:** share of returned results that are relevant vs. share of relevant items found. **Mash-up:** one app combining several sources into something new.

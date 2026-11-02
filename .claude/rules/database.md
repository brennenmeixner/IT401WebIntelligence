# Database (A3 onward)

## Stack and flow
Flask route → validation/normalization → SQLAlchemy model → ORM session →
PyMySQL driver → cloud MySQL (CI-Keys) → ORM query → Jinja template → response.

Dependencies: `Flask-SQLAlchemy`, `Flask-Migrate`, `PyMySQL`
(add to `requirements.txt`). Config: `SQLALCHEMY_DATABASE_URI` built from env vars,
`SQLALCHEMY_TRACK_MODIFICATIONS = False`. URL shape:
`mysql+pymysql://USER:PASSWORD@HOST:PORT/DBNAME` (never commit real values).

## Env vars (document all in `.env.example` with placeholders)
`DB_USERNAME`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`, `DB_NAME`
(plus existing `SECRET_KEY`, `NWS_USER_AGENT`, `EXTERNAL_API_TIMEOUT`).

## Reaching CI-Keys MySQL from Brennen's machine
CI-Keys MySQL is not directly reachable; Brennen connects through an SSH tunnel
(from the course "CI Keys SSH Workaround" handout). With the tunnel open:
```bash
ssh -o IdentitiesOnly=yes -o ExitOnForwardFailure=yes \
    -L 127.0.0.1:3307:127.0.0.1:3306 -i ~/.ssh/cikeys -p 22 \
    <CPANEL_USERNAME>@<CIKEYS_SERVER>
```
Leave that terminal open. Then in `.env`: `DB_HOST=127.0.0.1`, `DB_PORT=3307`
(3307 so it does not clash with a local MySQL on 3306).
In MySQL Workbench the same connection is "Standard TCP/IP over SSH": SSH host
= the server from the CI Keys page + `:22`, SSH user = cPanel username, key file
= `~/.ssh/cikeys` (not `.pub`), MySQL host `127.0.0.1`, port `3306`. Workbench
warns about an incompatible server version; "continue anyway" is expected.
If the key is not authorized, the fix is in cPanel > SSH Access > Manage SSH
Keys > Import Key, then Manage > **Authorize**.
You (Claude Code) cannot open this tunnel for Brennen. If a DB command fails to
connect, tell him to check that the tunnel is open and `.env` is correct.

## Modeling rules
- `id` is the internal primary key. `external_id` is the identifier from the
  API/scrape. Uniqueness rule: `UniqueConstraint("source", "external_id")`.
- Every persisted external record carries provenance: `source`, `source_url`,
  `retrieved_at`; and `created_at` (set by the app, UTC). Add `updated_at` only
  if justified.
- Attribute categories to think through (course slide): domain info (title,
  description), provenance (source, source_url, external_id, retrieved_at),
  temporal (created_at, updated_at), classification (category/status),
  location (latitude, longitude).
- Required fields `nullable=False`; optional fields stay nullable and are shown
  with a sensible placeholder in templates.

## Persisting external data
1. Transform the API/scrape result into a model object (trim whitespace,
   convert ids to strings, allow missing optional values, keep provenance).
2. Check for an existing record by (source, external_id): update it or skip it.
3. Add and commit inside try/except; rollback on error; friendly message.
The DB constraint is the second layer of protection if two requests race.

## CRUD
Create (`db.session.add` + commit), Read (select/order/`db.session.get`),
Update (get, change fields, commit), Delete (get, `db.session.delete`, commit).
Unknown id → 404 via `abort(404)` or `get_or_404`. Create/update/delete are POST.

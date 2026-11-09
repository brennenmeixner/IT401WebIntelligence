# Code Style

## Separation of concerns
- **Routes** (`routes/*.py`): parse request, call a service, render a template.
  No API calls, no SQL, no business logic in routes.
- **Services** (`services/*.py`): external calls, scraping, mapping to models,
  validation, duplicate checks, saving. Easy to test without Flask running.
- **Models** (`models/*.py`): table definitions and relationships only.
- **Templates**: every page `{% extends "base.html" %}`. No repeated head/nav/footer.
- Search logic lives in `services/search_service.py`; `routes/search.py` only
  parses args and renders.

## Python
- PEP 8, snake_case, CapWords for classes. Readable over clever: this is a
  learning project and Brennen must be able to explain it.
- Short docstring on any non-trivial function in `services/`.

## Database (see also `database.md`)
- One `db = SQLAlchemy()` in `extensions.py`; models import it from there.
- Schema changes go through Flask-Migrate (`flask db migrate` then **review**
  the generated file, then `flask db upgrade`). Never edit tables by hand.
- Commit the `migrations/` folder.
- Use the transaction pattern: try / commit / `except IntegrityError` rollback
  (duplicate) / `except Exception` rollback + log + friendly message.

## Config
- Environment-specific values go in `config.py` via `os.environ.get(...)`.

## Commits
- Small incremental commits: edit, test, commit. Don't commit generated files.

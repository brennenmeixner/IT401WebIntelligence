# Testing

## Rules
- Every new route gets at least one test. A route is not done until it has a
  passing test.
- Run `python -m pytest tests/` before every commit and before submitting.
- Tests never touch the real cloud MySQL. Use `TestConfig` with an in-memory
  SQLite database (`sqlite:///:memory:`), created and dropped per test or fixture.
- Tests never call the network. Mock `requests.get` (see `tests/fake_response.py`)
  and use saved HTML fixtures for the NDBC scraper.

## What to test for A3
- Models: required fields enforced; defaults (`created_at`) set; the
  uniqueness rule (`source` + `external_id`) rejects duplicates.
- Persistence service: maps an API/scrape result to a model; missing values are
  handled; invalid input is rejected; a duplicate updates or is rejected cleanly.
- CRUD routes: list, detail, create (valid and invalid), update (valid and
  invalid), delete, 404 for unknown id.
- Failure paths: DB error rolls back and returns a friendly message; external
  source down does not break the page.
- Existing A1 and A2 tests must keep passing.

## When a test fails
Read the failure first. Identify the failing line. Change one thing. Re-run.

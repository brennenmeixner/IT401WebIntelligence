# Testing

## Rule
Every new route gets at least one test. No route should be considered
"done" until it has a passing test in `tests/`.

## Pattern
```python
# tests/test_app.py
def test_index(client):
    response = client.get("/")
    assert response.status_code == 200

def test_explore(client):
    response = client.get("/explore")
    assert response.status_code == 200
```

## Running tests
```bash
python -m pytest tests/
```
Run this before every commit, and always before submitting an assignment.

## When a test fails
Read the failure message and traceback first — don't guess. Identify the
failing line, make one change, re-run. Don't change multiple things at once
and re-run hoping it passes.

## What to test as the project grows
- Every route returns the expected status code.
- Services that read/filter JSON data return the expected shape (e.g. a
  filter with no matches returns an empty list, not an error).
- Don't test third-party libraries (Flask, requests) themselves — only your
  own routes and services.

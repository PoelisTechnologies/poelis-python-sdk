# AGENTS.md

## Cursor Cloud specific instructions

### Project overview

Poelis **Python SDK** — a client library for the Poelis REST/GraphQL API. Published to PyPI as `poelis-sdk`.

### Development

- `uv sync` installs all dependencies (including dev group: pytest, ruff).
- `uv run pytest -q -m "not integration"` runs unit tests (integration tests need a live API + credentials).
- `uv run ruff check .` for linting.
- No services to start — this is a pure library.

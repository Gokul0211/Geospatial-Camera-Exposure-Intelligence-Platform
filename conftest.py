"""
conftest.py — Root-level pytest configuration for COBRA-WATCH
==============================================================
This conftest is discovered automatically by pytest due to its location at the
project root. It solves one specific problem: tests that use the default
DATABASE_PATH (rather than an isolated tmp-path fixture) would fail with
"no such table" errors on a fresh clone because the schema has never been
initialized.

Root cause: `init_db()` is normally called by main.py's FastAPI lifespan
context manager. Tests that use `ASGITransport(app=app)` DO trigger the
lifespan, but only for the duration of the `AsyncClient` context block.
Tests like `test_api.py` rely on the DB already having a valid schema from
a prior run — which is fine on a dev machine but breaks on a fresh clone
where `data/surveillancewatch.db` is absent (or 0-byte if accidentally
committed).

Fix: a single session-scoped autouse async fixture that calls `init_db()`
once before any test runs. This is idempotent — `init_db()` uses
`CREATE TABLE IF NOT EXISTS` throughout, so running it on an already-
initialized database is safe and cheap.

This approach is preferable to:
- Committing a database binary to git (fragile, breaks diffs, bloats history)
- Patching every individual test file with init_db() calls (scattered, brittle)
- Using a global tmp-path override (changes semantics of tests that verify
  real DB behavior against the actual configured path)
"""

import sys
import os
import asyncio
import pytest
import pytest_asyncio

# Ensure backend/ is importable from every test context
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))


@pytest_asyncio.fixture(scope="session", autouse=True)
async def initialize_real_database():
    """
    Run init_db() once per test session before any test executes.

    This guarantees that the real DATABASE_PATH (data/surveillancewatch.db)
    has a complete, valid schema regardless of whether the DB file already
    existed. init_db() is fully idempotent — CREATE TABLE IF NOT EXISTS on
    every table, ALTER TABLE … ADD COLUMN only if missing.

    Tests using isolated tmp-path fixtures are unaffected: they patch
    DATABASE_PATH to a separate temp file and never touch this DB.
    """
    from database import init_db
    await init_db()
    yield
    # No teardown — the real DB is persistent across test runs by design.
    # Individual test files that need isolation use tmp_path fixtures.

"""Test configuration — uses a temporary in-memory DB for all tests."""

import os
import sqlite3
import pytest

# Override DB path BEFORE importing any modules
os.environ["FRED_DB_PATH"] = ":memory:"

# Patch the database module to use a temp file per test
import products.fred_assistant.database as db


@pytest.fixture(autouse=True)
def fresh_db(tmp_path):
    """Reset database for each test using a temp file."""
    test_db = str(tmp_path / "test.db")
    original_path = db.DB_PATH
    db.DB_PATH = test_db

    # Re-init tables
    db.init_db()

    yield test_db

    db.DB_PATH = original_path

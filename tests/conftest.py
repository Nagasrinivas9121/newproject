"""
Pytest configuration and fixtures.
"""
import pytest
import tempfile
from pathlib import Path
import sqlite3

from database import init_db

@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)

@pytest.fixture
def test_db(temp_dir):
    db_file = temp_dir / "test_srivani.db"
    init_db(db_file)
    return db_file

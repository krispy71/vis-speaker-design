import pytest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from database import init_db, get_connection

@pytest.fixture
def db(tmp_path):
    """Temporary file-backed SQLite database for test isolation."""
    import database
    original = database.DB_PATH
    database.DB_PATH = tmp_path / "test.db"
    init_db()
    yield database.DB_PATH
    database.DB_PATH = original

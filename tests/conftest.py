"""Keep tests out of the developer's operational database."""
import os
import tempfile
from pathlib import Path

_test_directory = tempfile.TemporaryDirectory(prefix="cabinops-tests-")
os.environ["TESTING"] = "true"
os.environ["ENV"] = "development"
os.environ["CABINOPS_DB_PATH"] = str(Path(_test_directory.name) / "cabinops.db")

import pytest

@pytest.fixture(autouse=True)
def isolated_state():
    from backend.database import init_db
    from backend.database.connection import get_connection
    from backend.security import auth_limiter, request_limiter
    init_db()
    auth_limiter.history.clear()
    request_limiter.history.clear()
    with get_connection() as conn:
        conn.execute("DELETE FROM tasks")
        conn.execute("DELETE FROM announcements")
    yield

"""Short-lived SQLite connections with explicit transaction and cleanup."""

import sqlite3
from contextlib import contextmanager
from backend.config import DB_PATH


@contextmanager
def get_connection():
    conn = sqlite3.connect(DB_PATH, timeout=15)
    conn.row_factory = sqlite3.Row
    try:
        with conn:
            yield conn
    finally:
        conn.close()

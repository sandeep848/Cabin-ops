import os
import logging
from backend.config import DB_PATH
from backend.database.connection import get_connection

logger = logging.getLogger("cabinops.database.schema")


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with get_connection() as conn:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                flight_id TEXT NOT NULL,
                seat TEXT NOT NULL,
                zone TEXT NOT NULL CHECK(zone IN ('fore_cabin', 'mid_cabin', 'aft_cabin')),
                intent TEXT NOT NULL,
                urgency TEXT NOT NULL CHECK(urgency IN ('high', 'medium', 'low', 'none')),
                status TEXT NOT NULL CHECK(status IN ('pending', 'urgent_pending', 'accepted', 'completed', 'delayed', 'rejected', 'answered', 'ignored')),
                action TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(tasks)")}
        if "inventory_item" not in columns:
            conn.execute("ALTER TABLE tasks ADD COLUMN inventory_item TEXT")
        if "inventory_reserved" not in columns:
            conn.execute(
                "ALTER TABLE tasks ADD COLUMN inventory_reserved INTEGER NOT NULL DEFAULT 0"
            )
        for column in [
            "accepted_at",
            "completed_at",
            "assigned_to",
            "request_text",
            "input_modality",
        ]:
            if column not in columns:
                conn.execute(f"ALTER TABLE tasks ADD COLUMN {column} TEXT")
        conn.execute("""CREATE TABLE IF NOT EXISTS audit_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            flight_id TEXT NOT NULL, task_id INTEGER, actor TEXT NOT NULL,
            event TEXT NOT NULL, detail TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
        )""")
        conn.execute(
            "CREATE INDEX IF NOT EXISTS audit_flight_task ON audit_events(flight_id, task_id, id)"
        )
        conn.execute("""CREATE TABLE IF NOT EXISTS request_receipts (
            flight_id TEXT NOT NULL, seat TEXT NOT NULL, request_key TEXT NOT NULL,
            payload_hash TEXT NOT NULL, response TEXT NOT NULL, task_id INTEGER NOT NULL,
            created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
            PRIMARY KEY(flight_id, seat, request_key)
        )""")
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_tasks_status_created ON tasks (status, created_at);"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_tasks_seat_created ON tasks (seat, created_at);"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_tasks_zone_status ON tasks (zone, status);"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_tasks_urgency_status ON tasks (urgency, status);"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_tasks_flight_created ON tasks (flight_id, created_at);"
        )
        conn.commit()

        conn.execute(
            "CREATE TABLE IF NOT EXISTS sessions (token_id TEXT PRIMARY KEY, subject TEXT NOT NULL, expires_at INTEGER NOT NULL)"
        )
        conn.execute("CREATE INDEX IF NOT EXISTS sessions_subject ON sessions(subject)")
        conn.execute(
            "CREATE TABLE IF NOT EXISTS media_grants (token_id TEXT PRIMARY KEY, digest TEXT NOT NULL UNIQUE, expires_at INTEGER NOT NULL)"
        )
        task_columns = {row["name"] for row in conn.execute("PRAGMA table_info(tasks)")}
        if "inventory_quantity" not in task_columns:
            conn.execute(
                "ALTER TABLE tasks ADD COLUMN inventory_quantity INTEGER NOT NULL DEFAULT 1"
            )
        conn.execute(
            "CREATE TABLE IF NOT EXISTS media_progress (flight_id TEXT NOT NULL, seat TEXT NOT NULL, content_id TEXT NOT NULL, position_seconds REAL NOT NULL, updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')), PRIMARY KEY (flight_id, seat, content_id))"
        )
        conn.execute(
            "CREATE TABLE IF NOT EXISTS playback_health (flight_id TEXT NOT NULL, seat TEXT NOT NULL, state TEXT NOT NULL, content_id TEXT, updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')), PRIMARY KEY(flight_id, seat))"
        )
        from backend.services.fleet import init_fleet

        init_fleet(conn)
        conn.commit()

    # Tables remain empty until an operator provisions real records.
    init_flight_context_db()
    init_announcements_db()
    init_users_db()
    init_bookings_db()


def init_flight_context_db() -> None:
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS flight_context (
                flight_id TEXT NOT NULL,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                PRIMARY KEY (flight_id, key)
            )
        """)
        conn.commit()


def init_announcements_db() -> None:
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS announcements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                flight_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                speaker TEXT NOT NULL,
                text TEXT NOT NULL
            )
        """)
        conn.commit()


def init_users_db() -> None:
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL
            )
        """)
        conn.commit()

        row = conn.execute("SELECT COUNT(*) FROM users").fetchone()
        if row[0] == 0:
            # Bootstrap only an explicitly configured operator credential.
            if os.getenv("CREW_PASSWORD"):
                from backend.security.hashing import hash_password

                conn.execute(
                    "INSERT OR IGNORE INTO users (username, password_hash, role) VALUES (?, ?, ?)",
                    (
                        os.getenv("CREW_USERNAME", "crew"),
                        hash_password(os.environ["CREW_PASSWORD"]),
                        "crew",
                    ),
                )
                conn.commit()


def init_bookings_db() -> None:
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS bookings (
                seat TEXT NOT NULL,
                flight_id TEXT NOT NULL,
                booking_reference TEXT NOT NULL,
                passenger_name TEXT NOT NULL,
                PRIMARY KEY (flight_id, seat)
            )
        """)
        conn.commit()

    # One-way migration: booking references are credentials, not crew-facing data.
    from backend.security.hashing import hash_password

    with get_connection() as conn:
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(bookings)")}
        if "reference_hash" not in columns:
            conn.execute("ALTER TABLE bookings ADD COLUMN reference_hash TEXT")
        for row in conn.execute(
            "SELECT flight_id, seat, booking_reference FROM bookings WHERE reference_hash IS NULL"
        ).fetchall():
            conn.execute(
                "UPDATE bookings SET reference_hash = ?, booking_reference = '' WHERE flight_id = ? AND seat = ?",
                (
                    hash_password(row["booking_reference"].upper()),
                    row["flight_id"],
                    row["seat"],
                ),
            )

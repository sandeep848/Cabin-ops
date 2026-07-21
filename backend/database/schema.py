import json
import os
import logging
from backend.config import DB_PATH, DATA_DIR
from backend.database.connection import get_connection

logger = logging.getLogger("cabinops.database.schema")

def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with get_connection() as conn:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                flight_id TEXT NOT NULL DEFAULT 'APX-001',
                seat TEXT NOT NULL,
                zone TEXT NOT NULL CHECK(zone IN ('fore_cabin', 'mid_cabin', 'aft_cabin')),
                intent TEXT NOT NULL,
                urgency TEXT NOT NULL CHECK(urgency IN ('high', 'medium', 'low', 'none')),
                status TEXT NOT NULL CHECK(status IN ('pending', 'urgent_pending', 'accepted', 'completed', 'delayed', 'rejected', 'answered', 'ignored')),
                action TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_status_created ON tasks (status, created_at);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_seat_created ON tasks (seat, created_at);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_zone_status ON tasks (zone, status);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_urgency_status ON tasks (urgency, status);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_flight_created ON tasks (flight_id, created_at);")
        conn.commit()
    
    # Initialize other tables and seed mock data
    from backend.services.inventory import init_inventory_db
    init_inventory_db()
    init_flight_context_db()
    init_announcements_db()
    init_users_db()
    init_bookings_db()

def init_flight_context_db() -> None:
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS flight_context (
                flight_id TEXT NOT NULL DEFAULT 'APX-001',
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                PRIMARY KEY (flight_id, key)
            )
        """)
        conn.commit()
        
        row = conn.execute("SELECT COUNT(*) FROM flight_context").fetchone()
        if row[0] == 0:
            flight_context_file = DATA_DIR / "flight_context.json"
            if flight_context_file.exists():
                try:
                    data = json.loads(flight_context_file.read_text(encoding="utf-8"))
                    for k, v in data.items():
                        conn.execute(
                            "INSERT OR IGNORE INTO flight_context (flight_id, key, value) VALUES ('APX-001', ?, ?)",
                            (k, str(v))
                        )
                    conn.commit()
                except Exception as exc:
                    logger.error(f"Error seeding flight context: {exc}", exc_info=True)

def init_announcements_db() -> None:
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS announcements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                flight_id TEXT NOT NULL DEFAULT 'APX-001',
                timestamp TEXT NOT NULL,
                speaker TEXT NOT NULL,
                text TEXT NOT NULL
            )
        """)
        conn.commit()
        
        row = conn.execute("SELECT COUNT(*) FROM announcements").fetchone()
        if row[0] == 0:
            announcements_file = DATA_DIR / "announcements.json"
            if announcements_file.exists():
                try:
                    data = json.loads(announcements_file.read_text(encoding="utf-8"))
                    for item in data:
                        ts = item.get("timestamp", "")
                        if "minutes" in ts or "hour" in ts or "ago" in ts:
                            if "10" in ts:
                                ts = "2026-06-14T09:30:00Z"
                            elif "30" in ts:
                                ts = "2026-06-14T09:10:00Z"
                            elif "1" in ts or "one" in ts:
                                ts = "2026-06-14T08:40:00Z"
                            else:
                                ts = "2026-06-14T08:00:00Z"
                        conn.execute(
                            "INSERT INTO announcements (flight_id, timestamp, speaker, text) VALUES ('APX-001', ?, ?, ?)",
                            (ts, item["speaker"], item["text"])
                        )
                    conn.commit()
                    # Sync initial db data back to json
                    from backend.database.operations import sync_announcements_json
                    sync_announcements_json()
                except Exception as exc:
                    logger.error(f"Error seeding announcements: {exc}", exc_info=True)

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
            # Seed demo users for local dev/testing
            if os.getenv("ENV") != "production" or os.getenv("TESTING") == "true":
                from backend.security.hashing import hash_password
                conn.execute(
                    "INSERT OR IGNORE INTO users (username, password_hash, role) VALUES (?, ?, ?)",
                    ("crew", hash_password("crew_password"), "crew")
                )
                conn.commit()

def init_bookings_db() -> None:
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS bookings (
                seat TEXT NOT NULL,
                flight_id TEXT NOT NULL DEFAULT 'APX-001',
                booking_reference TEXT NOT NULL,
                passenger_name TEXT NOT NULL,
                PRIMARY KEY (flight_id, seat)
            )
        """)
        conn.commit()
        
        row = conn.execute("SELECT COUNT(*) FROM bookings").fetchone()
        if row[0] == 0:
            seat_map_file = DATA_DIR / "seat_map.json"
            if seat_map_file.exists():
                try:
                    import random
                    import string
                    data = json.loads(seat_map_file.read_text(encoding="utf-8"))
                    used_refs = set()
                    for seat, zone in data.items():
                        while True:
                            booking_ref = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
                            if booking_ref not in used_refs:
                                used_refs.add(booking_ref)
                                break
                        conn.execute(
                            "INSERT OR IGNORE INTO bookings (seat, flight_id, booking_reference, passenger_name) VALUES (?, 'APX-001', ?, ?)",
                            (seat.upper(), booking_ref, f"Passenger at {seat}")
                        )
                    conn.commit()
                except Exception as exc:
                    logger.error(f"Error seeding bookings: {exc}", exc_info=True)

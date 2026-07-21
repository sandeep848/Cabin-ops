import os
import json
import logging
from backend.config import DATA_DIR
from backend.database.connection import get_connection

logger = logging.getLogger("cabinops.database.operations")

_last_context_mtime = 0.0

VALID_STATUSES = {"pending", "urgent_pending", "accepted", "completed", "delayed", "rejected", "answered", "ignored"}

def can_transition(current_status: str, new_status: str) -> bool:
    if new_status not in VALID_STATUSES:
        return False
    if current_status == new_status:
        return True
    
    # Terminal states
    if current_status in {"completed", "rejected", "answered", "ignored"}:
        return False
        
    if current_status in {"pending", "urgent_pending"}:
        return new_status in {"accepted", "completed", "delayed", "rejected"}
        
    if current_status == "accepted":
        return new_status in {"completed"}
        
    if current_status == "delayed":
        return new_status in {"accepted", "completed", "pending", "urgent_pending"}
        
    return False

def allowed_previous_statuses(new_status: str) -> list[str]:
    # Returns the list of statuses from which we can transition to new_status
    allowed = [new_status]  # transitioning to self is always allowed
    for s in VALID_STATUSES:
        if s != new_status and can_transition(s, new_status):
            allowed.append(s)
    return allowed

def sync_announcements_json(flight_id: str = "APX-001") -> None:
    try:
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT id, timestamp, speaker, text FROM announcements WHERE flight_id = ? ORDER BY timestamp DESC",
                (flight_id,)
            ).fetchall()
            data = [dict(r) for r in rows]
            (DATA_DIR / "announcements.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception as exc:
        logger.error(f"Error syncing announcements JSON: {exc}", exc_info=True)

def get_db_flight_context(flight_id: str = "APX-001") -> dict:
    global _last_context_mtime
    flight_context_file = DATA_DIR / "flight_context.json"
    if flight_context_file.exists():
        try:
            mtime = os.path.getmtime(flight_context_file)
            if mtime != _last_context_mtime:
                # Reload file into DB
                data = json.loads(flight_context_file.read_text(encoding="utf-8"))
                with get_connection() as conn:
                    for k, v in data.items():
                        conn.execute(
                            "INSERT OR REPLACE INTO flight_context (flight_id, key, value) VALUES (?, ?, ?)",
                            (flight_id, k, str(v))
                        )
                    conn.commit()
                _last_context_mtime = mtime
        except Exception as exc:
            logger.error(f"Error reloading flight context file: {exc}", exc_info=True)

    with get_connection() as conn:
        rows = conn.execute("SELECT key, value FROM flight_context WHERE flight_id = ?", (flight_id,)).fetchall()
        ctx = {}
        for r in rows:
            k, v = r["key"], r["value"]
            if k == "seatbelt_sign" or k == "meal_service_active":
                ctx[k] = v.lower() == "true"
            elif k == "minutes_to_landing":
                try:
                    ctx[k] = int(v)
                except ValueError:
                    ctx[k] = 90
            else:
                ctx[k] = v
        return ctx

def update_db_flight_context(ctx: dict, flight_id: str = "APX-001") -> None:
    global _last_context_mtime
    with get_connection() as conn:
        for k, v in ctx.items():
            conn.execute(
                "INSERT OR REPLACE INTO flight_context (flight_id, key, value) VALUES (?, ?, ?)",
                (flight_id, k, str(v))
            )
        conn.commit()
    # Sync to JSON file for compatibility with existing tests
    try:
        flight_context_file = DATA_DIR / "flight_context.json"
        flight_context_file.write_text(json.dumps(ctx, indent=2), encoding="utf-8")
        _last_context_mtime = os.path.getmtime(flight_context_file)
    except Exception as exc:
        logger.error(f"Error syncing flight context DB to JSON: {exc}", exc_info=True)

def insert_task(seat: str, zone: str, intent: str, urgency: str, status: str, action: str, flight_id: str = "APX-001") -> int:
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO tasks (flight_id, seat, zone, intent, urgency, status, action) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (flight_id, seat.upper(), zone, intent, urgency, status, action),
        )
        conn.commit()
        return int(cur.lastrowid)

def list_tasks(status: str = None, seat: str = None, zone: str = None, limit: int = 100, offset: int = 0, flight_id: str = "APX-001") -> list[dict]:
    if limit is None or limit <= 0:
        limit = 100
    if offset is None or offset < 0:
        offset = 0
        
    query = "SELECT * FROM tasks WHERE flight_id = ?"
    params = [flight_id]
    
    if status is not None:
        if status == "active":
            query += " AND status != 'completed'"
        else:
            query += " AND status = ?"
            params.append(status)
    if seat is not None:
        query += " AND seat = ?"
        params.append(seat.upper())
    if zone is not None:
        query += " AND zone = ?"
        params.append(zone)
    
    query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
            
    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]

def update_task_status(task_id: int, new_status: str, permitted_flights: list[str] = None) -> bool:
    if new_status not in VALID_STATUSES:
        raise ValueError(f"Invalid status: {new_status}")
        
    allowed_prev = allowed_previous_statuses(new_status)
    placeholders = ",".join("?" for _ in allowed_prev)
    query = f"UPDATE tasks SET status = ? WHERE id = ? AND status IN ({placeholders})"
    params = [new_status, task_id] + allowed_prev
    
    with get_connection() as conn:
        row = conn.execute("SELECT status, flight_id FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if not row:
            return False
        current_status = row["status"]
        task_flight_id = row["flight_id"]
        
        if permitted_flights is not None and task_flight_id not in permitted_flights:
            raise ValueError(f"Permission denied: not permitted to modify tasks for flight {task_flight_id}")
            
        if not can_transition(current_status, new_status):
            raise ValueError(f"Illegal status transition from {current_status} to {new_status}")
            
        cur = conn.execute(query, params)
        conn.commit()
        return cur.rowcount > 0

def clear_all_tasks() -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM tasks")
        conn.commit()
    from backend.services.inventory import reset_inventory_db
    reset_inventory_db()

def get_analytics(flight_id: str = "APX-001", status: str = None) -> dict:
    query_total = "SELECT COUNT(*) FROM tasks WHERE flight_id = ?"
    query_urgent = "SELECT COUNT(*) FROM tasks WHERE flight_id = ? AND urgency = 'high'"
    query_zones = "SELECT zone, COUNT(*) as count FROM tasks WHERE flight_id = ?"
    
    if status is not None:
        if status == "active":
            query_total += " AND status != 'completed'"
            query_urgent += " AND status != 'completed'"
            query_zones += " AND status != 'completed'"
        else:
            query_total += " AND status = ?"
            query_urgent += " AND status = ?"
            query_zones += " AND status = ?"
            
    query_zones += " GROUP BY zone"
    
    with get_connection() as conn:
        p_total = [flight_id] if status is None or status == "active" else [flight_id, status]
        total = conn.execute(query_total, p_total).fetchone()[0]
        urgent = conn.execute(query_urgent, p_total).fetchone()[0]
        
        zone_rows = conn.execute(query_zones, p_total).fetchall()
        by_zone = {"fore_cabin": 0, "mid_cabin": 0, "aft_cabin": 0}
        for r in zone_rows:
            z = r["zone"]
            if z in by_zone:
                by_zone[z] = r["count"]
                
        return {
            "total_tasks": total,
            "urgent_tasks": urgent,
            "by_zone": by_zone
        }

def list_announcements(speaker: str = None, limit: int = None, flight_id: str = "APX-001") -> list[dict]:
    query = "SELECT id, timestamp, speaker, text FROM announcements WHERE flight_id = ?"
    params = [flight_id]
    if speaker is not None:
        query += " AND speaker = ?"
        params.append(speaker)
    query += " ORDER BY timestamp DESC"
    if limit is not None:
        query += " LIMIT ?"
        params.append(limit)
        
    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]

def get_user_by_username(username: str) -> dict | None:
    with get_connection() as conn:
        row = conn.execute("SELECT username, password_hash, role FROM users WHERE username = ?", (username,)).fetchone()
        return dict(row) if row else None

def get_booking_by_seat(seat: str, flight_id: str = "APX-001") -> dict | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT seat, booking_reference, passenger_name FROM bookings WHERE seat = ? AND flight_id = ?",
            (seat.upper(), flight_id)
        ).fetchone()
        return dict(row) if row else None

def verify_booking(seat: str, booking_reference: str, flight_id: str = "APX-001") -> bool:
    booking = get_booking_by_seat(seat, flight_id)
    if not booking:
        return False
    import hmac
    return hmac.compare_digest(
        booking["booking_reference"].upper().encode("utf-8"),
        booking_reference.upper().encode("utf-8")
    )

def add_announcement(speaker: str, text: str, timestamp: str, flight_id: str = "APX-001") -> int:
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO announcements (flight_id, timestamp, speaker, text) VALUES (?, ?, ?, ?)",
            (flight_id, timestamp, speaker, text)
        )
        conn.commit()
        return int(cur.lastrowid)

def get_inventory_levels() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute("SELECT item, stock, alternative FROM inventory ORDER BY item").fetchall()
        return [dict(r) for r in rows]

def restock_inventory_item(item: str, quantity: int) -> int | None:
    with get_connection() as conn:
        row = conn.execute("SELECT stock FROM inventory WHERE item = ?", (item.lower(),)).fetchone()
        if not row:
            return None
        cur = conn.execute(
            "UPDATE inventory SET stock = stock + ? WHERE item = ?",
            (quantity, item.lower())
        )
        conn.commit()
        new_row = conn.execute("SELECT stock FROM inventory WHERE item = ?", (item.lower(),)).fetchone()
        return new_row["stock"] if new_row else None

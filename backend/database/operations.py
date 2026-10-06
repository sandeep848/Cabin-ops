import os
import json
import logging
from backend.config import DATA_DIR
from backend.database.connection import get_connection

logger = logging.getLogger("cabinops.database.operations")

_last_context_mtime = 0.0

VALID_STATUSES = {
    "pending",
    "urgent_pending",
    "accepted",
    "completed",
    "delayed",
    "rejected",
    "answered",
    "ignored",
}


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


def get_db_flight_context(flight_id: str) -> dict:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT key, value FROM flight_context WHERE flight_id = ?", (flight_id,)
        ).fetchall()
        ctx = {}
        for r in rows:
            k, v = r["key"], r["value"]
            if k == "seatbelt_sign" or k == "meal_service_active":
                ctx[k] = v.lower() == "true"
            elif k == "minutes_to_landing":
                try:
                    ctx[k] = int(v)
                except ValueError:
                    raise ValueError("Invalid configured landing estimate")
            else:
                ctx[k] = v
        return ctx


def update_db_flight_context(
    ctx: dict, flight_id: str, actor: str | None = None
) -> None:
    with get_connection() as conn:
        for k, v in ctx.items():
            conn.execute(
                "INSERT OR REPLACE INTO flight_context (flight_id, key, value) VALUES (?, ?, ?)",
                (flight_id, k, str(v)),
            )
        if actor:
            from backend.services.operations import append_audit

            append_audit(
                conn, flight_id, actor, "flight.context_updated", ctx["flight_phase"]
            )
        conn.commit()


def insert_task(
    seat: str,
    zone: str,
    intent: str,
    urgency: str,
    status: str,
    action: str,
    flight_id: str,
    inventory_item=None,
    inventory_reserved=False,
    connection=None,
    request_text="",
    input_modality="text",
    inventory_quantity=1,
) -> int:
    def insert(conn):
        cur = conn.execute(
            "INSERT INTO tasks (flight_id, seat, zone, intent, urgency, status, action, inventory_item, inventory_reserved, request_text, input_modality, inventory_quantity) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                flight_id,
                seat.upper(),
                zone,
                intent,
                urgency,
                status,
                action,
                inventory_item,
                int(inventory_reserved),
                request_text,
                input_modality,
                inventory_quantity,
            ),
        )
        return int(cur.lastrowid)

    if connection is not None:
        return insert(connection)
    with get_connection() as conn:
        return insert(conn)


def list_tasks(
    flight_id: str,
    status: str = None,
    seat: str = None,
    zone: str = None,
    limit: int = 100,
    offset: int = 0,
    prioritize: bool = False,
) -> list[dict]:
    if limit is None or limit <= 0:
        limit = 100
    if offset is None or offset < 0:
        offset = 0

    query = "SELECT * FROM tasks WHERE flight_id = ?"
    params = [flight_id]

    if status is not None:
        if status == "active":
            query += " AND status IN ('pending','urgent_pending','accepted','delayed')"
        else:
            query += " AND status = ?"
            params.append(status)
    if seat is not None:
        query += " AND seat = ?"
        params.append(seat.upper())
    if zone is not None:
        query += " AND zone = ?"
        params.append(zone)

    if prioritize:
        query += " ORDER BY CASE WHEN status IN ('pending','urgent_pending','accepted','delayed') THEN 0 ELSE 1 END, CASE urgency WHEN 'high' THEN 0 WHEN 'medium' THEN 1 ELSE 2 END, CASE WHEN status IN ('pending','urgent_pending','accepted','delayed') THEN id END ASC, id DESC LIMIT ? OFFSET ?"
    else:
        query += " ORDER BY created_at DESC, id DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()
        result = [dict(row) for row in rows]
        for task in result:
            task["created_at"] = task["created_at"].replace(" ", "T") + "Z"
        return result


def update_task_status(
    task_id: int,
    new_status: str,
    permitted_flights: list[str] = None,
    actor: str = "crew",
) -> bool:
    if new_status not in VALID_STATUSES:
        raise ValueError(f"Invalid status: {new_status}")

    allowed_prev = allowed_previous_statuses(new_status)
    placeholders = ",".join("?" for _ in allowed_prev)
    query = f"UPDATE tasks SET status = ? WHERE id = ? AND status IN ({placeholders})"
    params = [new_status, task_id] + allowed_prev

    with get_connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if not row:
            return False
        current_status = row["status"]
        task_flight_id = row["flight_id"]

        if permitted_flights is not None and task_flight_id not in permitted_flights:
            raise ValueError(
                f"Permission denied: not permitted to modify tasks for flight {task_flight_id}"
            )

        if not can_transition(current_status, new_status):
            raise ValueError(
                f"Illegal status transition from {current_status} to {new_status}"
            )

        if current_status == new_status:
            return True
        if (
            row["assigned_to"]
            and row["assigned_to"] != actor
            and current_status == "accepted"
        ):
            raise ValueError(
                "Permission denied: this request is assigned to another crew member"
            )
        # Enforce current service restrictions on the server, not only in UI.
        if (
            new_status in {"accepted", "completed"}
            and current_status != new_status
            and row["urgency"] != "high"
        ):
            context = get_db_flight_context(task_flight_id)
            restricted = context.get("flight_phase") in {
                "boarding",
                "taxi",
                "takeoff",
                "landing_preparation",
                "landing",
            }
            if (
                restricted
                or context.get("seatbelt_sign")
                or (
                    row["intent"] == "meal_request"
                    and not context.get("meal_service_active", True)
                )
            ):
                raise ValueError("Service is currently restricted for this flight")
        if (
            new_status in {"accepted", "completed"}
            and row["inventory_item"]
            and not row["inventory_reserved"]
        ):
            from backend.services.inventory import reserve_item

            if not reserve_item(
                row["inventory_item"],
                quantity=row["inventory_quantity"],
                connection=conn,
                flight_id=task_flight_id,
            ):
                raise ValueError("Requested item is currently out of stock")
            conn.execute(
                "UPDATE tasks SET inventory_reserved = 1 WHERE id = ?", (task_id,)
            )
        if new_status == "accepted":
            conn.execute(
                "UPDATE tasks SET accepted_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now'), assigned_to = ? WHERE id = ?",
                (actor, task_id),
            )
        if new_status == "completed":
            conn.execute(
                "UPDATE tasks SET completed_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now') WHERE id = ?",
                (task_id,),
            )
        from backend.services.operations import append_audit

        append_audit(
            conn,
            task_flight_id,
            actor,
            "request." + new_status,
            current_status + " → " + new_status,
            task_id,
        )
        cur = conn.execute(query, params)
        if cur.rowcount == 0:
            raise ValueError("Task changed concurrently; reload and retry")
        return True


def clear_all_tasks(flight_id: str) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM tasks WHERE flight_id = ?", (flight_id,))
        conn.execute("DELETE FROM request_receipts WHERE flight_id = ?", (flight_id,))
        conn.commit()
    # Clearing request history must not replenish physical inventory.


def get_analytics(flight_id: str, status: str = None) -> dict:
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
        p_total = (
            [flight_id] if status is None or status == "active" else [flight_id, status]
        )
        total = conn.execute(query_total, p_total).fetchone()[0]
        urgent = conn.execute(query_urgent, p_total).fetchone()[0]

        zone_rows = conn.execute(query_zones, p_total).fetchall()
        by_zone = {"fore_cabin": 0, "mid_cabin": 0, "aft_cabin": 0}
        for r in zone_rows:
            z = r["zone"]
            if z in by_zone:
                by_zone[z] = r["count"]

        return {"total_tasks": total, "urgent_tasks": urgent, "by_zone": by_zone}


def list_announcements(
    flight_id: str, speaker: str = None, limit: int = None
) -> list[dict]:
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
        row = conn.execute(
            "SELECT username, password_hash, role FROM users WHERE username = ?",
            (username,),
        ).fetchone()
        return dict(row) if row else None


def get_booking_by_seat(seat: str, flight_id: str) -> dict | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT seat, passenger_name FROM bookings WHERE seat = ? AND flight_id = ?",
            (seat.upper(), flight_id),
        ).fetchone()
        return dict(row) if row else None


def verify_booking(seat: str, booking_reference: str, flight_id: str) -> bool:
    booking = get_booking_by_seat(seat, flight_id)
    if not booking:
        return False
    from backend.security.hashing import verify_password

    with get_connection() as conn:
        row = conn.execute(
            "SELECT reference_hash FROM bookings WHERE seat = ? AND flight_id = ?",
            (seat.upper(), flight_id),
        ).fetchone()
    return bool(
        row and verify_password(row["reference_hash"], booking_reference.upper())
    )


def add_announcement(
    speaker: str, text: str, timestamp: str, flight_id: str, actor: str | None = None
) -> int:
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO announcements (flight_id, timestamp, speaker, text) VALUES (?, ?, ?, ?)",
            (flight_id, timestamp, speaker, text),
        )
        if actor:
            from backend.services.operations import append_audit

            append_audit(conn, flight_id, actor, "announcement.published", speaker)
        conn.commit()
        return int(cur.lastrowid)


def get_inventory_levels(flight_id: str) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT i.*, COALESCE((SELECT SUM(t.inventory_quantity) FROM tasks t WHERE t.flight_id=i.flight_id AND t.inventory_item=i.item AND t.inventory_reserved=1 AND t.status IN ('pending','urgent_pending','accepted','delayed')),0) AS reserved FROM flight_inventory i WHERE i.flight_id=? ORDER BY i.category,i.name",
            (flight_id,),
        ).fetchall()
    return [
        {
            key: value
            for key, value in dict(row).items()
            if key not in {"allergens_json", "dietary_json"}
        }
        | {
            "allergens": json.loads(row["allergens_json"]),
            "dietary_tags": json.loads(row["dietary_json"]),
        }
        for row in rows
    ]


def restock_inventory_item(
    item: str, quantity: int, flight_id: str, actor: str | None = None
) -> int | None:
    if quantity < 1:
        raise ValueError("Restock quantity must be positive")
    with get_connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute(
            "SELECT stock,capacity FROM flight_inventory WHERE flight_id=? AND item=?",
            (flight_id, item.lower()),
        ).fetchone()
        if not row:
            return None
        reserved = conn.execute(
            "SELECT COALESCE(SUM(inventory_quantity),0) FROM tasks WHERE flight_id=? AND inventory_item=? AND inventory_reserved=1 AND status IN ('pending','urgent_pending','accepted','delayed')",
            (flight_id, item.lower()),
        ).fetchone()[0]
        if row["stock"] + reserved + quantity > row["capacity"]:
            raise ValueError("Replenishment exceeds configured onboard capacity")
        conn.execute(
            "UPDATE flight_inventory SET stock=stock+? WHERE flight_id=? AND item=?",
            (quantity, flight_id, item.lower()),
        )
        if actor:
            from backend.services.operations import append_audit

            append_audit(
                conn, flight_id, actor, "inventory.restocked", f"{item}: +{quantity}"
            )
        return row["stock"] + quantity

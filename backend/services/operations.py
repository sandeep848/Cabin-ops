"""Operational audit and service metrics, isolated by authorized flight."""
from datetime import datetime, timezone
from backend.database.connection import get_connection

ACTIVE = {"pending", "urgent_pending", "accepted", "delayed"}
TARGET_SECONDS = {"high": 60, "medium": 300, "low": 600, "none": 600}


def append_audit(conn, flight_id, actor, event, detail, task_id=None):
    # Avoid storing passenger names, booking references, or request text in audit records.
    conn.execute("INSERT INTO audit_events (flight_id, task_id, actor, event, detail) VALUES (?, ?, ?, ?, ?)", (flight_id, task_id, actor, event, detail))


def audit_history(flight_id, task_id=None, limit=200):
    query = "SELECT * FROM audit_events WHERE flight_id = ?"
    params = [flight_id]
    if task_id is not None:
        query += " AND task_id = ?"
        params.append(task_id)
    with get_connection() as conn:
        return [dict(row) for row in conn.execute(query + " ORDER BY id DESC LIMIT ?", params + [limit])]


def operational_summary(flight_id):
    with get_connection() as conn:
        rows = [dict(row) for row in conn.execute("SELECT status, urgency, created_at, accepted_at, completed_at FROM tasks WHERE flight_id = ?", (flight_id,))]
    now = datetime.now(timezone.utc)
    def date(value):
        return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=timezone.utc)
    pending = [row for row in rows if row["status"] in {"pending", "urgent_pending"}]
    breaches = sum((now - date(row["created_at"])).total_seconds() > TARGET_SECONDS[row["urgency"]] for row in pending)
    acknowledged = [(date(row["accepted_at"]) - date(row["created_at"])).total_seconds() for row in rows if row["accepted_at"]]
    return {"open_requests": sum(row["status"] in ACTIVE for row in rows), "awaiting_acknowledgement": len(pending), "in_progress": sum(row["status"] == "accepted" for row in rows), "delayed": sum(row["status"] == "delayed" for row in rows), "urgent_open": sum(row["urgency"] == "high" and row["status"] in ACTIVE for row in rows), "completed": sum(row["status"] == "completed" for row in rows), "acknowledgement_target_breaches": breaches, "mean_acknowledgement_seconds": round(sum(acknowledged)/len(acknowledged), 1) if acknowledged else None, "targets_seconds": TARGET_SECONDS, "total_requests": len(rows)}

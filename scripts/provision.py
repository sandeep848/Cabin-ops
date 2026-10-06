"""Explicit operator provisioning. No flight, passenger or stock is seeded at startup."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from backend.database import init_db, get_connection
from backend.services.fleet import (
    import_aircraft,
    configure_flight,
    load_stock,
    profile_for_flight,
)
from backend.services.operations import append_audit


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    aircraft = commands.add_parser("aircraft")
    aircraft.add_argument("--file", type=Path, required=True)
    flight = commands.add_parser("flight")
    for name in ["id", "aircraft", "origin", "destination"]:
        flight.add_argument("--" + name, required=True)
    stock = commands.add_parser("stock")
    stock.add_argument("--flight", required=True)
    stock.add_argument("--file", type=Path, required=True)
    assign = commands.add_parser("assign")
    assign.add_argument("--flight", required=True)
    assign.add_argument("--username", required=True)
    closed = commands.add_parser("close-flight")
    closed.add_argument("--flight", required=True)
    args = parser.parse_args()
    init_db()
    try:
        if args.command == "aircraft":
            profile = import_aircraft(json.loads(args.file.read_text()))
            print(
                f"Aircraft template {profile.aircraft_id} provisioned. Existing flights keep their layout snapshots."
            )
        elif args.command == "flight":
            configure_flight(args.id, args.aircraft, args.origin, args.destination)
            with get_connection() as conn:
                append_audit(
                    conn, args.id, "operator-cli", "flight.provisioned", args.aircraft
                )
            print(f"Flight {args.id} provisioned with no bookings or stock.")
        elif args.command == "stock":
            load_stock(args.flight, json.loads(args.file.read_text()))
            with get_connection() as conn:
                append_audit(
                    conn,
                    args.flight,
                    "operator-cli",
                    "inventory.loaded",
                    "Operator loading manifest",
                )
            print(f"Loading manifest applied to {args.flight}.")
        elif args.command == "close-flight":
            profile_for_flight(args.flight)
            with get_connection() as conn:
                conn.execute("BEGIN IMMEDIATE")
                if conn.execute(
                    "SELECT 1 FROM tasks WHERE flight_id=? AND status IN ('pending','urgent_pending','accepted','delayed')",
                    (args.flight,),
                ).fetchone():
                    raise ValueError(
                        "Resolve open service requests before closing the flight"
                    )
                conn.execute(
                    "UPDATE flights SET state='closed' WHERE flight_id=?",
                    (args.flight,),
                )
                prefix = args.flight + ":"
                conn.execute(
                    "DELETE FROM media_grants WHERE token_id IN (SELECT token_id FROM sessions WHERE substr(subject,1,?)=?)",
                    (len(prefix), prefix),
                )
                conn.execute(
                    "DELETE FROM sessions WHERE substr(subject,1,?)=?",
                    (len(prefix), prefix),
                )
                for table in ["media_progress", "playback_health"]:
                    conn.execute(
                        f"DELETE FROM {table} WHERE flight_id=?", (args.flight,)
                    )
                append_audit(
                    conn,
                    args.flight,
                    "operator-cli",
                    "flight.closed",
                    "Passenger sessions and media history cleared",
                )
            print(f"Flight {args.flight} closed; service and audit records retained.")
        else:
            profile_for_flight(args.flight)
            with get_connection() as conn:
                if not conn.execute(
                    "SELECT 1 FROM users WHERE username=? AND role='crew'",
                    (args.username,),
                ).fetchone():
                    raise ValueError("Create the crew account first")
                conn.execute(
                    "INSERT OR IGNORE INTO crew_assignments(username,flight_id) VALUES(?,?)",
                    (args.username, args.flight),
                )
                append_audit(
                    conn, args.flight, "operator-cli", "crew.assigned", args.username
                )
            print(f"Crew account {args.username} assigned to {args.flight}.")
    except (ValueError, OSError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()

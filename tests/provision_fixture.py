"""Synthetic fixtures for isolated automated tests only; never used by application startup."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from backend.database import init_db, get_connection
from backend.services.fleet import import_aircraft, configure_flight, load_stock
from backend.security.hashing import hash_password

REFERENCE_HASH = hash_password("TESTREF")


def provision():
    init_db()
    import_aircraft(
        {
            "aircraft_id": "TEST-NARROW",
            "name": "Automated test narrow-body",
            "rows": [
                {
                    "row": n,
                    "blocks": ["ABC", "DEF"],
                    "zone": (
                        "fore_cabin"
                        if n <= 10
                        else "mid_cabin" if n <= 20 else "aft_cabin"
                    ),
                    "cabin": "economy",
                }
                for n in range(1, 31)
            ],
        }
    )
    with get_connection() as conn:
        exists = conn.execute(
            "SELECT 1 FROM flights WHERE flight_id='APX-001'"
        ).fetchone()
    if not exists:
        configure_flight("APX-001", "TEST-NARROW", "AAA", "BBB")
    with get_connection() as conn:
        conn.execute("UPDATE flights SET state='active' WHERE flight_id='APX-001'")
        conn.execute(
            "INSERT OR IGNORE INTO crew_assignments(username,flight_id) VALUES('crew','APX-001')"
        )
        for seat in ["22A", "14D", "11A"]:
            conn.execute(
                "INSERT OR REPLACE INTO bookings(seat,flight_id,booking_reference,passenger_name,reference_hash) VALUES(?,'APX-001','','Test passenger',?)",
                (seat, REFERENCE_HASH),
            )
        conn.execute("DELETE FROM tasks WHERE flight_id='APX-001'")
    load_stock(
        "APX-001",
        [
            {
                "item": item,
                "name": item.replace("_", " ").title(),
                "category": (
                    "food"
                    if "meal" in item or item == "fruit_plate"
                    else "beverage" if item in {"water", "coffee"} else "comfort"
                ),
                "stock": 100,
                "capacity": 150,
            }
            for item in [
                "water",
                "coffee",
                "blanket",
                "vegetarian_meal",
                "fruit_plate",
                "headphones",
            ]
        ],
    )
    from backend.database.operations import update_db_flight_context

    update_db_flight_context(
        {
            "flight_phase": "cruise",
            "seatbelt_sign": False,
            "meal_service_active": True,
            "minutes_to_landing": 90,
        },
        flight_id="APX-001",
    )


if __name__ == "__main__":
    provision()

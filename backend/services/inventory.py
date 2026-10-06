"""Flight-scoped available units, transactional reservations and bounded replenishment."""

from backend.database.connection import get_connection


def reserve_item(item, flight_id, quantity=1, connection=None):
    if not item:
        return True
    if quantity < 1:
        raise ValueError("Reservation quantity must be positive")

    def reserve(conn):
        return (
            conn.execute(
                "UPDATE flight_inventory SET stock=stock-? WHERE flight_id=? AND item=? AND stock>=?",
                (quantity, flight_id, item.lower(), quantity),
            ).rowcount
            > 0
        )

    if connection is not None:
        return reserve(connection)
    with get_connection() as conn:
        return reserve(conn)


def suggest_alternative(item, flight_id):
    if not item:
        return None
    with get_connection() as conn:
        # Dietary and allergen differences are never substituted automatically.
        row = conn.execute(
            "SELECT a.item FROM flight_inventory i JOIN flight_inventory a ON a.flight_id=i.flight_id AND a.item=i.alternative WHERE i.flight_id=? AND i.item=? AND a.stock>0 AND a.allergens_json=i.allergens_json AND a.dietary_json=i.dietary_json",
            (flight_id, item.lower()),
        ).fetchone()
    return row["item"] if row else None

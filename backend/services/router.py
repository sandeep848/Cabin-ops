"""Resolve service zones from the assigned aircraft layout, not row-number heuristics."""

from backend.services.fleet import configured_seat


def seat_to_zone(seat: str, flight_id: str) -> str:
    return configured_seat(flight_id, seat.strip().upper())["zone"]

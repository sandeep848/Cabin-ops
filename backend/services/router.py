# Seat routing helper mapping seat numbers to zones. Imported by backend/main.py.
import re

def seat_to_zone(seat: str) -> str:
    match = re.match(r"^(\d{1,2})[A-F]$", seat.strip().upper())
    if not match:
        return "unknown"

    row = int(match.group(1))
    if 1 <= row <= 10:
        return "fore_cabin"
    if 11 <= row <= 20:
        return "mid_cabin"
    if 21 <= row <= 30:
        return "aft_cabin"
    return "unknown"

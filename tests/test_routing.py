from backend.services.router import seat_to_zone


def test_seat_to_zone():
    assert seat_to_zone("1A", "APX-001") == "fore_cabin"
    assert seat_to_zone("12C", "APX-001") == "mid_cabin"
    assert seat_to_zone("25F", "APX-001") == "aft_cabin"

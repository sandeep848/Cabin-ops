from backend.services.router import seat_to_zone

def test_seat_to_zone():
    assert seat_to_zone("1A") == "fore_cabin"
    assert seat_to_zone("12C") == "mid_cabin"
    assert seat_to_zone("25F") == "aft_cabin"

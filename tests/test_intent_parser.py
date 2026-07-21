from backend.services.intent_parser import parse_request

def test_medical_request_is_high_urgency():
    parsed = parse_request("I feel dizzy. Can someone help?", "22A")
    assert parsed["intent"] == "medical_assistance"
    assert parsed["urgency"] == "high"
    assert parsed["crew_required"] is True
    assert parsed["assigned_zone"] == "aft_cabin"

def test_missed_announcement_does_not_create_crew_task():
    parsed = parse_request("What did the captain say?", "14D")
    assert parsed["intent"] == "missed_announcement"
    assert parsed["crew_required"] is False

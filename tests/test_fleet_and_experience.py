"""Cross-aircraft, cross-flight, privacy, concurrency and recommender constraints."""

from concurrent.futures import ThreadPoolExecutor
from fastapi.testclient import TestClient
from backend.main import app
from backend.database import get_connection, list_tasks
from backend.database.operations import (
    update_db_flight_context,
    get_inventory_levels,
    restock_inventory_item,
)
from backend.security import generate_token
from backend.security.tokens import verify_token
from backend.services.fleet import (
    import_aircraft,
    configure_flight,
    load_stock,
    configured_seat,
    AircraftProfile,
)
from backend.services.recommendations import rank, pack_plan, integrity_report, catalog
from backend.routes.experience import Preferences
import pytest

client = TestClient(app)


def headers(role="passenger", flight="APX-001", seat="22A", username="crew"):
    if role == "crew":
        with get_connection() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO crew_assignments(username,flight_id) VALUES(?,?)",
                (username, flight),
            )
    return {
        "Authorization": "Bearer "
        + generate_token(
            {
                "role": role,
                "flight_id": flight,
                "seat": seat,
                "username": username,
                "permitted_flights": [flight],
            }
        )
    }


def widebody():
    import_aircraft(
        {
            "aircraft_id": "TEST-WIDE",
            "name": "Test mixed-cabin wide-body",
            "rows": [
                {
                    "row": 1,
                    "blocks": ["A", "DG", "K"],
                    "zone": "fore_cabin",
                    "cabin": "business",
                },
                {
                    "row": 77,
                    "blocks": ["ABC", "DEFG", "HJK"],
                    "zone": "aft_cabin",
                    "cabin": "economy",
                },
            ],
        }
    )
    with get_connection() as conn:
        conn.execute("DELETE FROM flights WHERE flight_id='WIDE-TEST'")
        conn.execute("DELETE FROM flight_context WHERE flight_id='WIDE-TEST'")
    configure_flight("WIDE-TEST", "TEST-WIDE", "CCC", "DDD")
    update_db_flight_context(
        {
            "flight_phase": "cruise",
            "seatbelt_sign": False,
            "meal_service_active": True,
            "minutes_to_landing": 30,
        },
        "WIDE-TEST",
    )
    load_stock(
        "WIDE-TEST",
        [
            {
                "item": "water",
                "name": "Drinking water",
                "category": "beverage",
                "stock": 2,
                "capacity": 3,
            }
        ],
    )


def test_widebody_omitted_letters_and_zone():
    widebody()
    assert configured_seat("WIDE-TEST", "77K")["zone"] == "aft_cabin"
    assert configured_seat("WIDE-TEST", "1G")["cabin"] == "business"
    with pytest.raises(Exception):
        configured_seat("WIDE-TEST", "77I")
    response = client.post(
        "/request",
        json={"seat": "77K", "text": "Water please"},
        headers=headers(flight="WIDE-TEST", seat="77K"),
    )
    assert response.status_code == 200
    assert response.json()["assigned_zone"] == "aft_cabin"
    assert len(list_tasks(flight_id="WIDE-TEST")) == 1


def test_invalid_layout_rejected_and_snapshot_is_immutable():
    widebody()
    with pytest.raises(ValueError):
        AircraftProfile.model_validate(
            {
                "aircraft_id": "BAD",
                "name": "Bad",
                "rows": [
                    {
                        "row": 1,
                        "blocks": ["ABC", "BC"],
                        "zone": "fore_cabin",
                        "cabin": "economy",
                    }
                ],
            }
        )
    import_aircraft(
        {
            "aircraft_id": "TEST-WIDE",
            "name": "Changed template",
            "rows": [
                {"row": 2, "blocks": ["AB"], "zone": "fore_cabin", "cabin": "economy"}
            ],
        }
    )
    assert configured_seat("WIDE-TEST", "77K")["seat"] == "77K"


def test_flight_inventory_and_data_cannot_cross_scope():
    widebody()
    before = get_inventory_levels("APX-001")
    assert (
        client.get("/announcements?flight_id=WIDE-TEST", headers=headers()).status_code
        == 403
    )
    assert (
        client.get(
            "/flight-context?flight_id=WIDE-TEST", headers=headers("crew")
        ).status_code
        == 403
    )
    assert (
        client.get(
            "/passenger/requests?seat=22A&flight_id=WIDE-TEST", headers=headers()
        ).status_code
        == 403
    )
    assert (
        client.get(
            "/crew/inventory", headers=headers("crew", flight="WIDE-TEST")
        ).json()[0]["stock"]
        == 2
    )
    assert get_inventory_levels("APX-001") == before


def test_quantity_reservation_concurrent_and_cancel_refunds_once():
    widebody()
    ph = headers(flight="WIDE-TEST", seat="77K")
    payload = {"seat": "77K", "text": "Water please", "item": "water", "quantity": 2}
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(
            pool.map(
                lambda _: client.post("/request", json=payload, headers=ph), range(2)
            )
        )
    accepted = next(row for row in results if row.json()["status"] == "pending")
    assert sorted(row.json()["status"] for row in results) == ["pending", "rejected"]
    assert get_inventory_levels("WIDE-TEST")[0]["stock"] == 0
    task = accepted.json()["task_id"]
    for _ in range(2):
        assert (
            client.post(f"/passenger/requests/{task}/cancel", headers=ph).status_code
            == 200
        )
    assert get_inventory_levels("WIDE-TEST")[0]["stock"] == 2


def test_capacity_accounts_for_reserved_units_and_loading_locks():
    widebody()
    ph = headers(flight="WIDE-TEST", seat="77K")
    assert (
        client.post(
            "/request", json={"seat": "77K", "text": "Water please"}, headers=ph
        ).status_code
        == 200
    )
    with pytest.raises(ValueError):
        restock_inventory_item("water", 2, "WIDE-TEST")
    assert restock_inventory_item("water", 1, "WIDE-TEST") == 2
    with pytest.raises(ValueError):
        load_stock(
            "WIDE-TEST",
            [
                {
                    "item": "water",
                    "name": "Water",
                    "category": "beverage",
                    "stock": 2,
                    "capacity": 3,
                }
            ],
        )


def test_progress_privacy_media_cookie_range_and_revocation():
    ph = headers()
    other = headers(seat="14D")
    client.cookies.clear()
    assert client.get("/experience/media/night-sky.webm").status_code == 401
    assert client.post("/experience/media-session", headers=ph).status_code == 200
    response = client.get(
        "/experience/media/night-sky.webm", headers={"Range": "bytes=0-31"}
    )
    assert response.status_code == 206 and len(response.content) == 32
    assert client.get("/experience/media/unknown.webm").status_code == 404
    assert (
        client.put(
            "/experience/progress/night-sky", json={"position_seconds": 10}, headers=ph
        ).status_code
        == 200
    )
    assert client.get("/experience/progress", headers=other).json() == []
    assert (
        client.put(
            "/experience/progress/night-sky", json={"position_seconds": 100}, headers=ph
        ).status_code
        == 422
    )
    assert client.delete("/experience/history", headers=ph).status_code == 200
    assert client.get("/experience/progress", headers=ph).json() == []
    token = ph["Authorization"][7:]
    assert client.post("/auth/logout", headers=ph).status_code == 200
    assert verify_token(token) is None
    assert client.get("/experience/catalog", headers=ph).status_code == 401
    assert client.get("/experience/media/night-sky.webm").status_code == 401


def test_no_auth_for_flight_content_and_query_bearers_rejected():
    for path in [
        "/flight-context",
        "/announcements",
        "/experience/catalog",
        "/flight-profile",
    ]:
        assert client.get(path).status_code == 401
    token = headers()["Authorization"][7:]
    assert client.get("/events?token=" + token).status_code == 401
    assert client.get("/crew/bookings/22A", headers=headers("crew")).json().keys() == {
        "seat",
        "passenger_name",
    }


def test_booking_hash_and_password_rotation_revoke_sessions(monkeypatch):
    from scripts import manage

    with get_connection() as conn:
        booking = conn.execute(
            "SELECT booking_reference,reference_hash FROM bookings WHERE seat='22A' AND flight_id='APX-001'"
        ).fetchone()
    assert (
        booking["booking_reference"] == ""
        and "TESTREF" not in booking["reference_hash"]
    )
    token = headers("crew", username="rotated-security")["Authorization"][7:]
    monkeypatch.setattr(
        "sys.argv", ["manage.py", "crew", "--username", "rotated-security"]
    )
    monkeypatch.setattr("getpass.getpass", lambda _: "changed-secure-password")
    manage.main()
    assert verify_token(token) is None


def test_request_size_and_schema_reject_abuse():
    assert (
        client.post(
            "/request",
            content=b"x" * 65537,
            headers={**headers(), "Content-Type": "application/json"},
        ).status_code
        == 413
    )
    assert (
        client.post(
            "/experience/recommendations",
            json={"interests": ["invalid"]},
            headers=headers(),
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/experience/recommendations",
            json={"available_minutes": -1},
            headers=headers(),
        ).status_code
        == 422
    )


@pytest.mark.parametrize("available", [0, 30, 44, 45, 60, 90, 120, 240, 600])
def test_recommendations_and_optimal_plan_obey_budget(available):
    prefs = Preferences(interests=["science"], mood="curious")
    ranked = rank(prefs, available)
    assert len({row["id"] for row in ranked}) == len(ranked)
    assert all(
        row["duration_seconds"] <= available and row["reasons"] for row in ranked
    )
    plan = pack_plan(ranked, available)
    assert plan["total_seconds"] <= available and len(plan["items"]) <= 4
    assert (
        plan["total_seconds"]
        == sum(row["duration_seconds"] for row in plan["items"])
        + max(0, len(plan["items"]) - 1) * 15
    )


def test_taste_changes_ranking_and_exclusions_are_hard_filters():
    science = rank(Preferences(interests=["science"], mood="curious"), 600)
    music = rank(Preferences(interests=["music"], kind="audio"), 600)
    assert science[0]["id"] != music[0]["id"]
    assert all(row["kind"] == "audio" for row in music)
    excluded = rank(Preferences(exclude_ids=[science[0]["id"]]), 600)
    assert science[0]["id"] not in {row["id"] for row in excluded}
    assert integrity_report()["verified"]


def test_landing_buffer_is_enforced_by_server_not_client():
    update_db_flight_context(
        {
            "flight_phase": "landing_preparation",
            "seatbelt_sign": True,
            "meal_service_active": False,
            "minutes_to_landing": 5,
        },
        flight_id="APX-001",
    )
    result = client.post(
        "/experience/plan", json={"available_minutes": 180}, headers=headers()
    ).json()
    assert result["budget_seconds"] == 0 and result["items"] == []


def test_flight_scoped_live_invalidation():
    import asyncio
    from backend.services.event_manager import EventManager

    async def scenario():
        events = EventManager()
        first = events.subscribe("ONE", "first")
        second = events.subscribe("TWO", "second")
        await events.broadcast({"flight_id": "ONE", "topic": "tasks"})
        assert first.get_nowait() == {"topic": "tasks"} and second.empty()

    asyncio.run(scenario())


def test_plan_matches_independent_subset_search():
    from itertools import combinations

    ranked = rank(Preferences(interests=["science", "travel"], mood="curious"), 600)
    for available in [45, 90, 135, 225, 400]:
        eligible = [row for row in ranked if row["duration_seconds"] <= available]
        plan = pack_plan(eligible, available)
        achieved = sum(row["score"] + 0.1 for row in plan["items"])
        optimum = 0
        for count in range(1, min(4, len(eligible)) + 1):
            for sequence in combinations(eligible, count):
                if (
                    sum(row["duration_seconds"] for row in sequence) + (count - 1) * 15
                    <= available
                ):
                    optimum = max(optimum, sum(row["score"] + 0.1 for row in sequence))
        assert achieved == pytest.approx(optimum)


def test_removed_assignment_denies_existing_session():
    ch = headers("crew")
    with get_connection() as conn:
        conn.execute(
            "DELETE FROM crew_assignments WHERE username='crew' AND flight_id='APX-001'"
        )
    assert client.get("/crew/tasks", headers=ch).status_code == 403


def test_empty_production_startup_invents_no_operational_data(tmp_path):
    import subprocess, os, sys

    script = """
from backend.database import init_db,get_connection
init_db()
with get_connection() as conn:
    for table in ['flights','bookings','flight_inventory','crew_assignments']:
        assert conn.execute('SELECT COUNT(*) FROM '+table).fetchone()[0]==0, table
"""
    result = subprocess.run(
        [sys.executable, "-c", script],
        env={
            **os.environ,
            "ENV": "production",
            "SECRET_KEY": "test-only-" + "x" * 48,
            "CREW_PASSWORD": "test-only-strong-password",
            "CABINOPS_DB_PATH": str(tmp_path / "empty.db"),
        },
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_validation_errors_never_echo_supplied_credentials():
    secret = "sensitive-password-" * 30
    response = client.post("/auth/crew", json={"username": "crew", "password": secret})
    assert response.status_code == 422 and secret not in response.text


def test_closed_flight_revokes_passenger_and_clears_only_media(monkeypatch):
    from scripts import provision

    ph = headers()
    client.put(
        "/experience/progress/night-sky", json={"position_seconds": 10}, headers=ph
    )
    monkeypatch.setattr(
        "sys.argv", ["provision.py", "close-flight", "--flight", "APX-001"]
    )
    provision.main()
    assert client.get("/experience/catalog", headers=ph).status_code == 401
    with get_connection() as conn:
        assert (
            conn.execute(
                "SELECT COUNT(*) FROM media_progress WHERE flight_id='APX-001'"
            ).fetchone()[0]
            == 0
        )
        assert (
            conn.execute(
                "SELECT state FROM flights WHERE flight_id='APX-001'"
            ).fetchone()[0]
            == "closed"
        )

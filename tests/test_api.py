import os

os.environ["TESTING"] = "true"
import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.database import init_db

# Initialize database schema for tests
init_db()

client = TestClient(app)


def get_passenger_headers(seat="22A"):
    response = client.post(
        "/auth/passenger", json={"seat": seat, "booking_reference": "TESTREF"}
    )
    assert response.status_code == 200
    token = response.json()["token"]
    return {"Authorization": f"Bearer {token}"}


def get_crew_headers():
    response = client.post(
        "/auth/crew", json={"username": "crew", "password": "crew_password"}
    )
    assert response.status_code == 200
    token = response.json()["token"]
    return {"Authorization": f"Bearer {token}"}


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_request_endpoint_medical():
    payload = {
        "seat": "22A",
        "text": "I feel dizzy. Can someone help?",
        "input_modality": "text",
    }
    response = client.post(
        "/request", json=payload, headers=get_passenger_headers(payload["seat"])
    )
    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "medical_assistance"
    assert data["urgency"] == "high"
    assert data["crew_required"] is True
    assert data["assigned_zone"] == "aft_cabin"


def test_request_endpoint_missed_announcement():
    payload = {
        "seat": "14D",
        "text": "What did the captain say?",
        "input_modality": "text",
    }
    response = client.post(
        "/request", json=payload, headers=get_passenger_headers(payload["seat"])
    )
    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "missed_announcement"
    assert data["crew_required"] is False


def test_crew_tasks_endpoint():
    response = client.get("/crew/tasks", headers=get_crew_headers())
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_analytics_summary_endpoint():
    response = client.get("/analytics/summary", headers=get_crew_headers())
    assert response.status_code == 200
    data = response.json()
    assert "total_tasks" in data
    assert "urgent_tasks" in data
    assert "by_zone" in data


def test_announcements_endpoint():
    response = client.get("/announcements", headers=get_passenger_headers())
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_unauthenticated_access_denied():
    # Attempting to read crew tasks without token
    response = client.get("/crew/tasks")
    assert response.status_code == 401


def test_passenger_request_unauthenticated():
    response = client.post(
        "/request",
        json={
            "seat": "22A",
            "text": "I feel dizzy. Can someone help?",
            "input_modality": "text",
        },
    )
    assert response.status_code == 401


def test_passenger_request_seat_mismatch():
    payload = {
        "seat": "11A",
        "text": "I feel dizzy. Can someone help?",
        "input_modality": "text",
    }
    response = client.post(
        "/request", json=payload, headers=get_passenger_headers("22A")
    )
    assert response.status_code == 403


def test_passenger_requests_retrieval_unauthenticated():
    response = client.get("/passenger/requests")
    assert response.status_code == 401


def test_passenger_requests_retrieval_seat_mismatch():
    response = client.get(
        "/passenger/requests?seat=11A", headers=get_passenger_headers("22A")
    )
    assert response.status_code == 403


def test_events_endpoint_unauthenticated():
    # Missing token query parameter
    response = client.get("/events")
    assert response.status_code == 401

    # Invalid token query parameter
    response = client.get("/events?token=invalid_token_123")
    assert response.status_code == 401


def test_events_endpoint_authenticated(monkeypatch):
    # Valid passenger token
    auth_resp = client.post(
        "/auth/passenger", json={"seat": "22A", "booking_reference": "TESTREF"}
    )
    assert auth_resp.status_code == 200
    token = auth_resp.json()["token"]

    import asyncio

    class MockQueue:
        def __init__(self):
            self.yielded = False

        async def get(self):
            if not self.yielded:
                self.yielded = True
                return {"topic": "test"}
            raise asyncio.CancelledError()

    monkeypatch.setattr(
        "backend.main.event_manager.subscribe", lambda *args: MockQueue()
    )
    monkeypatch.setattr("backend.main.event_manager.unsubscribe", lambda q: None)

    # Now we can do a synchronous request and read the full stream content
    response = client.get("/events", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert "text/event-stream" in response.headers.get("content-type", "")
    assert "connected" in response.text
    assert "test" in response.text

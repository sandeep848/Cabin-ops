from fastapi.testclient import TestClient
from backend.main import app
from backend.database import insert_task, list_tasks, clear_all_tasks
from backend.database.operations import get_inventory_levels
from backend.security import generate_token

client = TestClient(app)

def test_production_disallows_demo_login(monkeypatch):
    monkeypatch.setenv("ENV", "production")
    response = client.post("/auth/passenger", json={"seat": "22A", "booking_reference": "DEMO"})
    assert response.status_code == 401

def test_clear_tasks_preserves_other_flights_and_inventory():
    from backend.services.inventory import reserve_item
    reserve_item("water")
    inventory = get_inventory_levels()
    for flight in ["APX-001", "OTHER"]:
        insert_task("22A", "aft_cabin", "water_request", "low", "pending", "Water", flight)
    clear_all_tasks("APX-001")
    assert list_tasks(flight_id="APX-001") == []
    assert len(list_tasks(flight_id="OTHER")) == 1
    assert get_inventory_levels() == inventory

def test_empty_request_rejected():
    token = generate_token({"role": "passenger", "seat": "22A", "flight_id": "APX-001"})
    response = client.post("/request", json={"seat": "22A", "text": "  "}, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 422

def test_transcription_requires_authentication():
    response = client.post("/transcribe", files={"file": ("audio.wav", b"RIFF0000WAVE", "audio/wav")})
    assert response.status_code == 401

def test_passenger_to_crew_workflow():
    passenger = client.post("/auth/passenger", json={"seat": "22A", "booking_reference": "DEMO"}).json()
    crew = client.post("/auth/crew", json={"username": "crew", "password": "crew_password"}).json()
    ph = {"Authorization": f"Bearer {passenger['token']}"}
    ch = {"Authorization": f"Bearer {crew['token']}"}
    response = client.post("/request", json={"seat": "22A", "text": "I feel dizzy"}, headers=ph)
    assert response.status_code == 200
    task = client.get("/crew/tasks", headers=ch).json()[0]
    assert client.post(f"/crew/tasks/{task['id']}/accept", headers=ch).status_code == 200
    assert client.post(f"/crew/tasks/{task['id']}/complete", headers=ch).status_code == 200
    assert client.get("/passenger/requests?seat=22A", headers=ph).json()[0]['status'] == 'completed'

def test_delayed_inventory_reserved_on_acceptance():
    from backend.database.operations import update_db_flight_context, update_task_status
    from backend.services.inventory import reserve_item
    from backend.database.connection import get_connection
    context = {'flight_phase': 'cruise', 'seatbelt_sign': False, 'meal_service_active': True, 'minutes_to_landing': 90}
    update_db_flight_context(context)
    before = next(x['stock'] for x in get_inventory_levels() if x['item'] == 'water')
    task = insert_task('22A', 'aft_cabin', 'water_request', 'low', 'delayed', 'Delayed', inventory_item='water')
    assert update_task_status(task, 'accepted', ['APX-001'])
    assert update_task_status(task, 'completed', ['APX-001'])
    after = next(x['stock'] for x in get_inventory_levels() if x['item'] == 'water')
    assert after == before - 1

def test_restricted_acceptance_rejected_by_api():
    from backend.database.operations import update_db_flight_context
    update_db_flight_context({'flight_phase': 'takeoff', 'seatbelt_sign': True, 'meal_service_active': False, 'minutes_to_landing': 90})
    task = insert_task('22A', 'aft_cabin', 'water_request', 'low', 'delayed', 'Delayed', inventory_item='water')
    token = generate_token({'role': 'crew', 'permitted_flights': ['APX-001']})
    response = client.post(f'/crew/tasks/{task}/accept', headers={'Authorization': f'Bearer {token}'})
    assert response.status_code == 400

def test_inventory_rolls_back_if_task_creation_fails(monkeypatch):
    from backend.database.operations import update_db_flight_context
    update_db_flight_context({'flight_phase': 'cruise', 'seatbelt_sign': False, 'meal_service_active': True, 'minutes_to_landing': 90})
    before = get_inventory_levels()
    def fail(**kwargs):
        raise RuntimeError('Database write failed')
    monkeypatch.setattr('backend.main.insert_task', fail)
    token = generate_token({'role': 'passenger', 'seat': '22A', 'flight_id': 'APX-001'})
    with TestClient(app, raise_server_exceptions=False) as failing_client:
        response = failing_client.post('/request', json={'seat': '22A', 'text': 'Water please'}, headers={'Authorization': f'Bearer {token}'})
    assert response.status_code == 500
    assert get_inventory_levels() == before

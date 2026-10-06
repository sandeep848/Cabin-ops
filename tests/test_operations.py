"""Behavioral checks for retry safety, ownership, and operator visibility."""
from concurrent.futures import ThreadPoolExecutor
from fastapi.testclient import TestClient
from backend.main import app
from backend.security import generate_token
from backend.database import list_tasks, insert_task, update_task_status
from backend.database.operations import get_inventory_levels, update_db_flight_context
from backend.services.operations import audit_history

client = TestClient(app)

def headers(role='passenger', username='crew'):
    payload = {'role': role, 'seat': '22A', 'flight_id': 'APX-001', 'permitted_flights': ['APX-001'], 'username': username}
    return {'Authorization': 'Bearer ' + generate_token(payload)}

def stock():
    return next(item['stock'] for item in get_inventory_levels() if item['item'] == 'water')

def context():
    update_db_flight_context({'flight_phase': 'cruise', 'seatbelt_sign': False, 'meal_service_active': True, 'minutes_to_landing': 90})

def send(key, text='Water please'):
    return client.post('/request', json={'seat': '22A', 'text': text}, headers={**headers(), 'Idempotency-Key': key})

def test_retry_returns_original_receipt_and_reserves_once():
    context()
    before = stock()
    first, replay = send('repeat-request-001'), send('repeat-request-001')
    assert first.status_code == replay.status_code == 200
    assert first.json() == replay.json()
    assert len(list_tasks()) == 1
    assert stock() == before - 1
    assert len(audit_history('APX-001')) == 1

def test_concurrent_retries_create_one_task():
    context()
    before = stock()
    with ThreadPoolExecutor(max_workers=2) as executor:
        responses = list(executor.map(lambda _: send('concurrent-request-001'), range(2)))
    assert all(response.status_code == 200 for response in responses)
    assert responses[0].json()['task_id'] == responses[1].json()['task_id']
    assert stock() == before - 1
    assert len(list_tasks()) == 1

def test_key_reuse_for_changed_content_is_conflict():
    context()
    assert send('reuse-request-001').status_code == 200
    assert send('reuse-request-001', 'Blanket please').status_code == 409
    assert len(list_tasks()) == 1

def test_crew_ownership_prevents_another_member_completing():
    task = insert_task('22A', 'aft_cabin', 'medical_assistance', 'high', 'urgent_pending', 'Medical help')
    assert client.post(f'/crew/tasks/{task}/accept', headers=headers('crew', 'alice')).status_code == 200
    assert client.post(f'/crew/tasks/{task}/complete', headers=headers('crew', 'bob')).status_code == 403
    assert client.post(f'/crew/tasks/{task}/complete', headers=headers('crew', 'alice')).status_code == 200
    history = audit_history('APX-001', task)
    assert [row['actor'] for row in history] == ['alice', 'alice']

def test_repeat_accept_does_not_duplicate_audit_event():
    task = insert_task('22A', 'aft_cabin', 'medical_assistance', 'high', 'urgent_pending', 'Medical help')
    for _ in range(2):
        assert update_task_status(task, 'accepted', ['APX-001'], actor='alice')
    assert len(audit_history('APX-001', task)) == 1

def test_audit_endpoint_is_flight_scoped_and_crew_only():
    from backend.database import get_connection
    from backend.services.operations import append_audit
    with get_connection() as conn:
        append_audit(conn, 'OTHER', 'other-crew', 'request.created', 'Hidden')
    assert client.get('/crew/audit', headers=headers()).status_code == 403
    assert client.get('/crew/audit', headers=headers('crew')).json() == []

def test_operational_summary_counts_only_open_urgent_requests():
    task = insert_task('22A', 'aft_cabin', 'medical_assistance', 'high', 'urgent_pending', 'Help')
    summary = client.get('/crew/operations', headers=headers('crew')).json()
    assert summary['open_requests'] == summary['urgent_open'] == 1
    update_task_status(task, 'completed', ['APX-001'])
    summary = client.get('/crew/operations', headers=headers('crew')).json()
    assert summary['open_requests'] == summary['urgent_open'] == 0
    assert summary['completed'] == 1

def test_production_history_cannot_be_cleared(monkeypatch):
    monkeypatch.setenv('ENV', 'production')
    assert client.post('/crew/tasks/clear', headers=headers('crew')).status_code == 403

def test_readiness_checks_database_and_request_has_trace_id():
    response = client.get('/ready')
    assert response.status_code == 200
    assert response.json()['database'] == 'reachable'
    assert response.headers['X-Request-ID']

def test_verified_backup_preserves_operational_records(tmp_path):
    import sqlite3
    from scripts.backup_database import backup
    task = insert_task('22A', 'aft_cabin', 'medical_assistance', 'high', 'urgent_pending', 'Help')
    destination = tmp_path / 'snapshot.db'
    backup(destination)
    with sqlite3.connect(destination) as conn:
        assert conn.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
        assert conn.execute('SELECT id FROM tasks').fetchone()[0] == task

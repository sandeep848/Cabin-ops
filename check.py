#!/usr/bin/env python3
r"""
CabinOps AI full local health checker with error notifications.

Place this file in the project root:
    C:\Users\Sandip\OneDrive\Desktop\CV\cabinops-ai\check_cabinops.py

Run:
    conda activate CV
    cd C:\Users\Sandip\OneDrive\Desktop\CV\cabinops-ai
    python check_cabinops.py

Optional:
    python check_cabinops.py --debug
    python check_cabinops.py --no-pytest
    python check_cabinops.py --base-url http://127.0.0.1:8000

What it checks:
- Project files/folders exist
- Python imports work
- pytest runs
- backend/data/flight_context.json is readable/writable
- FastAPI app starts, or connects to an already-running server
- /health works
- /request handles dummy requests
- /crew/tasks stores crew-required tasks
- /analytics/summary updates
- flight-rule delay logic works during landing_preparation
- original flight_context.json is restored at the end

Error reporting:
- Every failure is mapped to a project area.
- The summary shows exactly which part failed, what likely caused it, and what command/file to check next.
"""

from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import time
import traceback
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parent
SERVER_HOST = "127.0.0.1"
DEFAULT_PORT = 8000
TIMEOUT_SECONDS = 8

REQUIRED_PATHS = [
    "backend/__init__.py",
    "backend/main.py",
    "backend/models.py",
    "backend/database/__init__.py",
    "backend/config.py",
    "backend/services/__init__.py",
    "backend/services/intent_parser.py",
    "backend/services/flight_rules.py",
    "backend/services/router.py",
    "backend/data/flight_context.json",
    "backend/data/inventory.json",
    "backend/data/seat_map.json",
    "tests/test_intent_parser.py",
    "tests/test_flight_rules.py",
    "tests/test_routing.py",
    "requirements.txt",
]

NORMAL_FLIGHT_CONTEXT = {
    "flight_phase": "cruise",
    "seatbelt_sign": False,
    "meal_service_active": True,
    "minutes_to_landing": 95,
}

LANDING_FLIGHT_CONTEXT = {
    "flight_phase": "landing_preparation",
    "seatbelt_sign": True,
    "meal_service_active": False,
    "minutes_to_landing": 20,
}


@dataclass
class FailureRecord:
    area: str
    check_name: str
    message: str
    likely_cause: str
    next_action: str


class CheckFailure(Exception):
    def __init__(self, message: str, likely_cause: str = "", next_action: str = "") -> None:
        super().__init__(message)
        self.likely_cause = likely_cause
        self.next_action = next_action


class Checker:
    def __init__(self, base_url: str, port: int, debug: bool, run_pytest: bool) -> None:
        self.base_url = base_url.rstrip("/")
        self.port = port
        self.debug = debug
        self.run_pytest_enabled = run_pytest

        self.passed = 0
        self.failed = 0
        self.warnings = 0
        self.started_process: subprocess.Popen[str] | None = None
        self.original_flight_context: str | None = None
        self.failures: list[FailureRecord] = []

    def log(self, status: str, message: str) -> None:
        print(f"[{status}] {message}")

    def pass_(self, message: str) -> None:
        self.passed += 1
        self.log("PASS", message)

    def fail(self, message: str) -> None:
        self.failed += 1
        self.log("FAIL", message)

    def warn(self, message: str) -> None:
        self.warnings += 1
        self.log("WARN", message)

    def notify_failure(
        self,
        area: str,
        check_name: str,
        message: str,
        likely_cause: str,
        next_action: str,
    ) -> None:
        self.failures.append(
            FailureRecord(
                area=area,
                check_name=check_name,
                message=message,
                likely_cause=likely_cause,
                next_action=next_action,
            )
        )

        print()
        print("!" * 72)
        print("ERROR NOTIFICATION")
        print("!" * 72)
        print(f"Part failed:  {area}")
        print(f"Check:        {check_name}")
        print(f"Error:        {message}")
        print(f"Likely cause: {likely_cause}")
        print(f"Next action:  {next_action}")
        print("!" * 72)

    def run_check(
        self,
        area: str,
        name: str,
        fn: Callable[[], None],
        likely_cause: str,
        next_action: str,
    ) -> None:
        print(f"\n--- {area}: {name} ---")
        try:
            fn()
        except CheckFailure as exc:
            self.fail(f"{area} / {name}: {exc}")
            self.notify_failure(
                area=area,
                check_name=name,
                message=str(exc),
                likely_cause=exc.likely_cause or likely_cause,
                next_action=exc.next_action or next_action,
            )
            if self.debug:
                traceback.print_exc()
        except Exception as exc:
            self.fail(f"{area} / {name}: {exc}")
            self.notify_failure(
                area=area,
                check_name=name,
                message=str(exc),
                likely_cause=likely_cause,
                next_action=next_action,
            )
            if self.debug:
                traceback.print_exc()

    def assert_true(
        self,
        condition: bool,
        message: str,
        likely_cause: str = "",
        next_action: str = "",
    ) -> None:
        if not condition:
            raise CheckFailure(message, likely_cause, next_action)
        self.pass_(message)

    def get_checker_passenger_token(self, seat: str) -> str:
        if not hasattr(self, "_passenger_tokens"):
            self._passenger_tokens = {}
        if seat in self._passenger_tokens:
            return self._passenger_tokens[seat]
        try:
            url = f"{self.base_url}/auth/passenger"
            payload = {"seat": seat, "booking_reference": "DEMO"}
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=5) as resp:
                res = json.loads(resp.read().decode("utf-8"))
                token = res["token"]
                self._passenger_tokens[seat] = token
                return token
        except Exception:
            return ""

    def get_checker_crew_token(self) -> str:
        if hasattr(self, "_crew_token"):
            return self._crew_token
        try:
            url = f"{self.base_url}/auth/crew"
            payload = {"username": "crew", "password": "crew_password"}
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=5) as resp:
                res = json.loads(resp.read().decode("utf-8"))
                token = res["token"]
                self._crew_token = token
                return token
        except Exception:
            return ""

    def read_json_response(self, method: str, path: str, payload: dict[str, Any] | None = None) -> Any:
        url = f"{self.base_url}{path}"
        data = None
        headers = {}

        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"

        # Inject JWT Auth Token
        token = None
        if path.startswith("/crew") or path == "/analytics/summary" or (path == "/flight-context" and method == "POST"):
            token = self.get_checker_crew_token()
        elif path == "/request" or path == "/passenger/requests" or path == "/flight-context" or path == "/announcements":
            seat = "22A"
            if payload and "seat" in payload:
                seat = payload["seat"]
            token = self.get_checker_passenger_token(seat)

        if token:
            headers["Authorization"] = f"Bearer {token}"

        req = urllib.request.Request(url, data=data, headers=headers, method=method)

        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
                body = resp.read().decode("utf-8")
                return json.loads(body) if body else None
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise CheckFailure(
                f"HTTP {exc.code} from {path}: {body}",
                likely_cause="The API endpoint exists but rejected the request or raised an internal server error.",
                next_action="Check the uvicorn terminal stack trace and inspect backend/main.py plus the service called by this endpoint.",
            ) from exc
        except urllib.error.URLError as exc:
            raise CheckFailure(
                f"Could not connect to {url}: {exc}",
                likely_cause="The FastAPI server is not running, crashed during startup, or is using a different port.",
                next_action=f"Run: python -m uvicorn backend.main:app --reload --port {self.port}",
            ) from exc

    def port_is_open(self) -> bool:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(1)
            return sock.connect_ex((SERVER_HOST, self.port)) == 0

    def wait_for_server(self, seconds: int = 20) -> None:
        deadline = time.time() + seconds
        last_error = None

        while time.time() < deadline:
            try:
                data = self.read_json_response("GET", "/health")
                if data == {"status": "ok"}:
                    self.pass_("FastAPI server responded to /health")
                    return
            except Exception as exc:
                last_error = exc
                time.sleep(0.7)

        raise CheckFailure(
            f"Server did not become ready. Last error: {last_error}",
            likely_cause="Uvicorn started but the application did not finish startup, or /health is failing.",
            next_action="Run uvicorn manually and inspect the traceback: python -m uvicorn backend.main:app --reload",
        )

    def check_project_root(self) -> None:
        self.assert_true(
            (ROOT / "backend").exists(),
            f"backend folder exists at {ROOT / 'backend'}",
            "You may be running this script from the wrong folder.",
            r"Move check_cabinops.py into C:\Users\Sandip\OneDrive\Desktop\CV\cabinops-ai and run it there.",
        )
        self.assert_true(
            (ROOT / "tests").exists(),
            f"tests folder exists at {ROOT / 'tests'}",
            "The scaffold may be incomplete or you are in the wrong directory.",
            "Run dir and confirm backend, tests, frontend, and requirements.txt are visible.",
        )

        missing = [path for path in REQUIRED_PATHS if not (ROOT / path).exists()]
        if missing:
            raise CheckFailure(
                "Missing required files: " + ", ".join(missing),
                likely_cause="The setup script did not finish, files were moved, or the checker is not in the project root.",
                next_action="Re-run python setup.py from the parent CV folder, or restore the missing files.",
            )
        self.pass_("All required scaffold files exist")

    def check_python_imports(self) -> None:
        sys.path.insert(0, str(ROOT))

        try:
            import backend  # noqa: F401
            import fastapi  # noqa: F401
            import pydantic  # noqa: F401
            import uvicorn  # noqa: F401
            from backend.services.intent_parser import parse_request
            from backend.services.router import seat_to_zone
            from backend.services.flight_rules import apply_flight_rules
        except Exception as exc:
            raise CheckFailure(
                f"Import failed: {exc}",
                likely_cause="PYTHONPATH is not set, required packages are not installed, or backend files have syntax/import errors.",
                next_action='Run: set PYTHONPATH=%CD% && python -c "import backend; print(\'ok\')"',
            ) from exc

        parsed = parse_request("I feel dizzy. Can someone help?", "22A")
        self.assert_true(
            parsed["intent"] == "medical_assistance",
            "intent_parser classifies medical request",
            "The parser rules in backend/services/intent_parser.py are wrong or changed.",
            "Open backend/services/intent_parser.py and check the dizzy/medical keyword branch.",
        )

        self.assert_true(
            seat_to_zone("22A") == "aft_cabin",
            "router maps seat 22A to aft_cabin",
            "Seat-zone routing logic is wrong.",
            "Open backend/services/router.py and verify rows 21-30 map to aft_cabin.",
        )

        delayed = apply_flight_rules(
            {
                "seat": "3A",
                "intent": "water_request",
                "urgency": "low",
                "slots": {"item": "water"},
                "crew_required": True,
                "assigned_zone": "fore_cabin",
                "status": "pending",
                "confidence": 0.8,
                "action": "Create crew task.",
            },
            LANDING_FLIGHT_CONTEXT,
        )

        self.assert_true(
            delayed["status"] == "delayed",
            "flight rules delay water request during landing preparation",
            "Flight rule logic is not enforcing service pause.",
            "Open backend/services/flight_rules.py and verify landing_preparation delays water_request.",
        )

    def check_pytest(self) -> None:
        if not self.run_pytest_enabled:
            self.warn("pytest check skipped because --no-pytest was used")
            return

        env = os.environ.copy()
        env["PYTHONPATH"] = str(ROOT) + os.pathsep + env.get("PYTHONPATH", "")

        result = subprocess.run(
            [sys.executable, "-m", "pytest", "-q"],
            cwd=ROOT,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=60,
        )

        output = result.stdout.strip()
        print(output)

        if result.returncode != 0:
            raise CheckFailure(
                "pytest failed",
                likely_cause="At least one unit test failed or pytest still cannot import backend.",
                next_action="Read the pytest output above. For import errors, create tests\\conftest.py or set PYTHONPATH=%CD%.",
            )

        self.pass_("pytest passed")

    def backup_flight_context(self) -> None:
        path = ROOT / "backend" / "data" / "flight_context.json"

        try:
            self.original_flight_context = path.read_text(encoding="utf-8")
            json.loads(self.original_flight_context)
        except Exception as exc:
            raise CheckFailure(
                f"Could not read valid JSON from {path}: {exc}",
                likely_cause="flight_context.json is missing, corrupted, or has invalid JSON syntax.",
                next_action="Open backend\\data\\flight_context.json and replace it with valid JSON for cruise mode.",
            ) from exc

        self.pass_("flight_context.json is valid JSON and backup was created")

    def write_flight_context(self, data: dict[str, Any]) -> None:
        path = ROOT / "backend" / "data" / "flight_context.json"

        try:
            path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        except Exception as exc:
            raise CheckFailure(
                f"Could not write {path}: {exc}",
                likely_cause="File is locked, read-only, or OneDrive sync is interfering.",
                next_action="Close the file in editors, pause OneDrive sync if needed, then run the checker again.",
            ) from exc

    def restore_flight_context(self) -> None:
        if self.original_flight_context is not None:
            path = ROOT / "backend" / "data" / "flight_context.json"
            path.write_text(self.original_flight_context, encoding="utf-8")
            self.pass_("flight_context.json restored")

    def start_or_reuse_server(self) -> None:
        if self.port_is_open():
            self.warn(f"Port {self.port} is already open; reusing existing server at {self.base_url}")
            self.wait_for_server(seconds=8)
            return

        env = os.environ.copy()
        env["PYTHONPATH"] = str(ROOT) + os.pathsep + env.get("PYTHONPATH", "")
        env["ENV"] = "development"
        if "SECRET_KEY" not in env:
            import secrets
            ephemeral_secret = secrets.token_hex(32)
            env["SECRET_KEY"] = ephemeral_secret

        try:
            self.started_process = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "uvicorn",
                    "backend.main:app",
                    "--host",
                    SERVER_HOST,
                    "--port",
                    str(self.port),
                ],
                cwd=ROOT,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )
        except Exception as exc:
            raise CheckFailure(
                f"Could not start uvicorn: {exc}",
                likely_cause="uvicorn is not installed or the conda environment is not active.",
                next_action="Run: pip install -r requirements.txt, then python -m uvicorn backend.main:app --reload",
            ) from exc

        self.pass_(f"Started uvicorn process with PID {self.started_process.pid}")
        self.wait_for_server(seconds=25)

    def stop_server_if_started(self) -> None:
        if self.started_process is not None:
            self.started_process.terminate()

            try:
                self.started_process.wait(timeout=8)
            except subprocess.TimeoutExpired:
                self.started_process.kill()

            self.pass_("Stopped uvicorn process started by this checker")

    def check_api_health(self) -> None:
        data = self.read_json_response("GET", "/health")

        self.assert_true(
            data == {"status": "ok"},
            "/health returns {'status': 'ok'}",
            "The health endpoint returned an unexpected response.",
            "Open backend/main.py and verify the /health route returns {'status': 'ok'}.",
        )

    def check_dummy_requests(self) -> None:
        self.write_flight_context(NORMAL_FLIGHT_CONTEXT)

        medical = self.read_json_response(
            "POST",
            "/request",
            {
                "seat": "22A",
                "text": "I feel dizzy. Can someone help?",
                "input_modality": "text",
            },
        )

        self.assert_true(
            medical["intent"] == "medical_assistance",
            "dummy medical request intent is correct",
            "The parser did not classify the medical phrase correctly.",
            "Check backend/services/intent_parser.py.",
        )
        self.assert_true(
            medical["urgency"] == "high",
            "dummy medical request urgency is high",
            "Urgency assignment for medical requests is wrong.",
            "Check the medical_assistance branch in backend/services/intent_parser.py.",
        )
        self.assert_true(
            medical["crew_required"] is True,
            "dummy medical request creates crew work",
            "Medical requests should always require crew.",
            "Check intent_parser.py and flight_rules.py.",
        )
        self.assert_true(
            medical["assigned_zone"] == "aft_cabin",
            "dummy medical request routes to aft_cabin",
            "Seat 22A should map to aft_cabin.",
            "Check backend/services/router.py.",
        )

        announcement = self.read_json_response(
            "POST",
            "/request",
            {
                "seat": "14D",
                "text": "What did the captain say?",
                "input_modality": "text",
            },
        )

        self.assert_true(
            announcement["intent"] == "missed_announcement",
            "missed announcement intent is correct",
            "The parser did not classify announcement request correctly.",
            "Check the captain/announcement branch in intent_parser.py.",
        )
        self.assert_true(
            announcement["crew_required"] is False,
            "missed announcement does not create crew work",
            "Self-service announcement requests should not create crew tasks.",
            "Check intent_parser.py and backend/main.py task creation condition.",
        )
        self.assert_true(
            announcement["status"] == "answered",
            "missed announcement is answered",
            "Announcement requests should return answered status.",
            "Check the missed_announcement branch in intent_parser.py.",
        )

        screen = self.read_json_response(
            "POST",
            "/request",
            {
                "seat": "25F",
                "text": "My screen is frozen",
                "input_modality": "text",
            },
        )

        self.assert_true(
            screen["intent"] == "screen_issue",
            "screen issue intent is correct",
            "The parser did not classify screen/frozen request correctly.",
            "Check the screen/tv/frozen branch in intent_parser.py.",
        )
        self.assert_true(
            screen["assigned_zone"] == "aft_cabin",
            "screen issue routes to aft_cabin",
            "Seat 25F should map to aft_cabin.",
            "Check backend/services/router.py.",
        )

    def check_read_endpoints(self) -> None:
        tasks = self.read_json_response("GET", "/crew/tasks")

        self.assert_true(
            isinstance(tasks, list),
            "/crew/tasks returns a list",
            "Crew tasks endpoint returned wrong type.",
            "Check backend/main.py /crew/tasks and backend/database/operations.py list_tasks.",
        )

        self.assert_true(
            any(t.get("intent") == "medical_assistance" for t in tasks),
            "/crew/tasks contains dummy medical task",
            "The POST /request flow did not write a task into SQLite.",
            "Check backend/main.py insert_task call and backend/database/operations.py.",
        )

        summary = self.read_json_response("GET", "/analytics/summary")

        self.assert_true(
            isinstance(summary, dict),
            "/analytics/summary returns an object",
            "Analytics endpoint returned wrong type.",
            "Check backend/main.py /analytics/summary.",
        )

        self.assert_true(
            summary.get("total_tasks", 0) >= 1,
            "analytics total_tasks is at least 1",
            "Analytics cannot see the inserted task.",
            "Check backend/database/operations.py list_tasks and SQLite path in backend/config.py.",
        )

        self.assert_true(
            summary.get("urgent_tasks", 0) >= 1,
            "analytics urgent_tasks is at least 1",
            "Urgent task was not stored or counted.",
            "Check task insertion fields and analytics_summary logic.",
        )

    def check_flight_rule_api(self) -> None:
        self.write_flight_context(LANDING_FLIGHT_CONTEXT)

        water = self.read_json_response(
            "POST",
            "/request",
            {
                "seat": "3A",
                "text": "Can I have water?",
                "input_modality": "text",
            },
        )

        self.assert_true(
            water["intent"] == "water_request",
            "water request intent is correct",
            "The parser did not classify water request correctly.",
            "Check the water branch in backend/services/intent_parser.py.",
        )

        self.assert_true(
            water["crew_required"] is False,
            "water request is not routed to crew during landing preparation",
            "Flight-rule engine is not blocking service during landing_preparation.",
            "Check backend/services/flight_rules.py.",
        )

        self.assert_true(
            water["assigned_zone"] is None,
            "delayed water request has no assigned zone",
            "Delayed requests should not be routed to crew.",
            "Check flight_rules.py and backend/main.py.",
        )

        self.assert_true(
            water["status"] == "delayed",
            "water request status is delayed during landing preparation",
            "Flight rules did not set delayed status.",
            "Check backend/services/flight_rules.py.",
        )

    def print_failure_report(self) -> None:
        if not self.failures:
            return

        print("\n" + "!" * 72)
        print("DETAILED ERROR REPORT")
        print("!" * 72)

        for idx, failure in enumerate(self.failures, start=1):
            print(f"\n{idx}. Failed part: {failure.area}")
            print(f"   Check:        {failure.check_name}")
            print(f"   Error:        {failure.message}")
            print(f"   Likely cause: {failure.likely_cause}")
            print(f"   Next action:  {failure.next_action}")

    def run(self) -> int:
        print("=" * 72)
        print("CabinOps AI full local health checker")
        print("=" * 72)
        print(f"Project root: {ROOT}")
        print(f"Python: {sys.executable}")
        print(f"Base URL: {self.base_url}")
        print(f"Port: {self.port}")

        try:
            self.run_check(
                "Project structure",
                "Required files and folders",
                self.check_project_root,
                "The checker is not in the project root, or setup.py did not create all files.",
                r"Move check_cabinops.py into C:\Users\Sandip\OneDrive\Desktop\CV\cabinops-ai and run it again.",
            )

            self.run_check(
                "Python environment",
                "Imports and direct service logic",
                self.check_python_imports,
                "Conda environment is missing packages, PYTHONPATH is wrong, or a backend file has an error.",
                'Run: set PYTHONPATH=%CD% && python -c "import backend; print(\'ok\')"',
            )

            self.run_check(
                "Unit tests",
                "Pytest suite",
                self.check_pytest,
                "Tests are failing or pytest cannot import backend.",
                "Run: set PYTHONPATH=%CD% && python -m pytest -q",
            )

            self.run_check(
                "Data files",
                "Flight context read/backup",
                self.backup_flight_context,
                "flight_context.json is missing or invalid.",
                "Open backend\\data\\flight_context.json and make sure it is valid JSON.",
            )

            self.run_check(
                "API server",
                "Start or reuse FastAPI",
                self.start_or_reuse_server,
                "Uvicorn could not start or /health is unavailable.",
                "Run manually: python -m uvicorn backend.main:app --reload",
            )

            self.run_check(
                "API server",
                "Health endpoint",
                self.check_api_health,
                "/health failed or returned unexpected JSON.",
                "Open backend/main.py and check the /health route.",
            )

            self.run_check(
                "Request pipeline",
                "Dummy write requests",
                self.check_dummy_requests,
                "POST /request is not parsing/routing/writing correctly.",
                "Inspect backend/main.py, intent_parser.py, router.py, and database.py.",
            )

            self.run_check(
                "Database and reads",
                "Crew tasks and analytics endpoints",
                self.check_read_endpoints,
                "SQLite write/read path or analytics aggregation is broken.",
                "Inspect backend/database.py and backend/config.py DB_PATH.",
            )

            self.run_check(
                "Flight rules",
                "Landing service delay behavior",
                self.check_flight_rule_api,
                "Flight-rule engine is not enforcing landing_preparation service pause.",
                "Inspect backend/services/flight_rules.py.",
            )

        finally:
            print("\n--- Cleanup ---")

            try:
                self.restore_flight_context()
            except Exception as exc:
                self.fail(f"Could not restore flight_context.json: {exc}")
                self.notify_failure(
                    area="Cleanup",
                    check_name="Restore flight_context.json",
                    message=str(exc),
                    likely_cause="The file became locked, deleted, or unwritable during checks.",
                    next_action="Manually restore backend\\data\\flight_context.json to cruise mode.",
                )

            try:
                self.stop_server_if_started()
            except Exception as exc:
                self.fail(f"Could not stop server: {exc}")
                self.notify_failure(
                    area="Cleanup",
                    check_name="Stop uvicorn",
                    message=str(exc),
                    likely_cause="The server process did not terminate normally.",
                    next_action="Close the terminal or run taskkill for the Python/uvicorn process.",
                )

        print("\n" + "=" * 72)
        print("SUMMARY")
        print("=" * 72)
        print(f"Passed:   {self.passed}")
        print(f"Warnings: {self.warnings}")
        print(f"Failed:   {self.failed}")

        self.print_failure_report()

        if self.failed:
            print("\nResult: NOT OK. Fix the failed parts listed in the detailed error report.")
            return 1

        print("\nResult: OK. Backend, routing, rules, DB writes, reads, and API endpoints are functioning.")
        return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check CabinOps AI local backend functionality.")
    parser.add_argument(
        "--base-url",
        default=os.environ.get("CABINOPS_BASE_URL", "http://127.0.0.1:8000"),
    )
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--debug", action="store_true", help="Print full Python tracebacks for failed checks.")
    parser.add_argument("--no-pytest", action="store_true", help="Skip the pytest check.")
    return parser.parse_args()


if __name__ == "__main__":
    # Auto-detect the CV conda environment and re-run if current python lacks dependencies
    try:
        import fastapi
        import uvicorn
        import pydantic
        import pytest
    except ImportError:
        cv_python = Path(r"C:\Users\Sandip\.vscode\anaconda\envs\CV\python.exe")
        if cv_python.exists() and sys.executable != str(cv_python):
            print(f"[INFO] Current Python lacks dependencies. Re-running checker using Conda 'CV' environment...")
            env = os.environ.copy()
            env["PYTHONPATH"] = str(ROOT) + os.pathsep + env.get("PYTHONPATH", "")
            sys.exit(subprocess.call([str(cv_python)] + sys.argv, env=env))

    args = parse_args()
    raise SystemExit(
        Checker(
            base_url=args.base_url,
            port=args.port,
            debug=args.debug,
            run_pytest=not args.no_pytest,
        ).run()
    )
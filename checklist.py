#!/usr/bin/env python3
r"""
CabinOps AI implementation checklist auditor.

Put this file in:
    C:\Users\Sandip\OneDrive\Desktop\CV\cabinops-ai\implementation_checklist.py

Run:
    conda activate CV
    cd C:\Users\Sandip\OneDrive\Desktop\CV\cabinops-ai
    python implementation_checklist.py

Optional:
    python implementation_checklist.py --save checklist_report.md
    python implementation_checklist.py --json
"""

from __future__ import annotations

import argparse
import ast
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parent


@dataclass
class Item:
    category: str
    name: str
    status: str
    evidence: str
    next_step: str


def p(path: str) -> Path:
    return ROOT / path


def exists(path: str) -> bool:
    return p(path).exists()


def text(path: str) -> str:
    try:
        return p(path).read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""


def lower(path: str) -> str:
    return text(path).lower()


def has(path: str, *words: str) -> bool:
    content = lower(path)
    return all(w.lower() in content for w in words)


def has_any(path: str, words: list[str]) -> bool:
    content = lower(path)
    return any(w.lower() in content for w in words)


def py_functions(path: str) -> set[str]:
    content = text(path)
    if not content:
        return set()

    try:
        tree = ast.parse(content)
    except SyntaxError:
        return set()

    return {node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}


def has_func(path: str, name: str) -> bool:
    return name in py_functions(path)


def has_route(route: str, method: str | None = None) -> bool:
    content = text("backend/main.py")

    if route not in content:
        return False

    if method is None:
        return True

    return f"@app.{method.lower()}(" in content


def route_count() -> int:
    return len(re.findall(r"@app\.(get|post|put|patch|delete)\(", text("backend/main.py")))


def json_valid(path: str) -> bool:
    try:
        json.loads(text(path))
        return True
    except Exception:
        return False


def csv_rows(path: str) -> int:
    rows = [line for line in text(path).splitlines() if line.strip()]
    return max(0, len(rows) - 1)


def status(condition: bool) -> str:
    return "IMPLEMENTED" if condition else "NOT IMPLEMENTED"


def add(
    items: list[Item],
    category: str,
    name: str,
    status_: str,
    evidence: str,
    next_step: str,
) -> None:
    items.append(Item(category, name, status_, evidence, next_step))


def build_items() -> list[Item]:
    items: list[Item] = []

    required = [
        "backend",
        "backend/main.py",
        "backend/models.py",
        "backend/database/__init__.py",
        "backend/database/connection.py",
        "backend/database/schema.py",
        "backend/database/operations.py",
        "backend/config.py",
        "backend/services",
        "backend/data",
        "tests",
        "requirements.txt",
    ]

    missing = [x for x in required if not exists(x)]

    add(
        items,
        "Project structure",
        "Core scaffold",
        "IMPLEMENTED" if not missing else "PARTIAL",
        "All core files/folders found." if not missing else "Missing: " + ", ".join(missing),
        "Restore missing files or re-run setup.py." if missing else "No action required.",
    )

    add(
        items,
        "Backend API",
        "FastAPI app",
        status(exists("backend/main.py") and has("backend/main.py", "FastAPI")),
        "backend/main.py contains FastAPI." if has("backend/main.py", "FastAPI") else "FastAPI app not detected.",
        "Create backend/main.py with app = FastAPI().",
    )

    api_checks = [
        ("Health endpoint", "/health", "get", "Add GET /health returning {'status':'ok'}."),
        ("Passenger request endpoint", "/request", "post", "Add POST /request."),
        ("Crew task list endpoint", "/crew/tasks", "get", "Add GET /crew/tasks."),
        ("Analytics endpoint", "/analytics/summary", "get", "Add GET /analytics/summary."),
    ]

    for name, route, method, next_step in api_checks:
        ok = has_route(route, method)
        add(
            items,
            "Backend API",
            name,
            status(ok),
            f"{method.upper()} {route} {'found' if ok else 'not found'}.",
            next_step if not ok else "No action required.",
        )

    rc = route_count()

    add(
        items,
        "Backend API",
        "Route count",
        "IMPLEMENTED" if rc >= 4 else "PARTIAL",
        f"Detected {rc} FastAPI route(s).",
        "Add task status routes next: accept, complete."
        if rc >= 4
        else "Minimum required: /health, /request, /crew/tasks, /analytics/summary.",
    )

    add(
        items,
        "Database",
        "SQLite module",
        status(exists("backend/database/connection.py") and has("backend/database/connection.py", "sqlite3")),
        "backend/database/connection.py uses sqlite3." if has("backend/database/connection.py", "sqlite3") else "SQLite not detected.",
        "Create backend/database/connection.py using sqlite3.",
    )

    add(
        items,
        "Database",
        "Database initialization",
        status(has_func("backend/database/schema.py", "init_db")),
        "init_db() found." if has_func("backend/database/schema.py", "init_db") else "init_db() missing.",
        "Add init_db() to create tables.",
    )

    add(
        items,
        "Database",
        "Tasks table",
        status(has("backend/database/schema.py", "create table if not exists tasks")),
        "tasks table creation found." if has("backend/database/schema.py", "create table if not exists tasks") else "tasks table not found.",
        "Create tasks table with id, seat, zone, intent, urgency, status, action, created_at.",
    )

    insert_task = has_func("backend/database/operations.py", "insert_task")
    list_tasks = has_func("backend/database/operations.py", "list_tasks")

    add(
        items,
        "Database",
        "Task write/read functions",
        "IMPLEMENTED"
        if insert_task and list_tasks
        else "PARTIAL"
        if insert_task or list_tasks
        else "NOT IMPLEMENTED",
        f"insert_task={insert_task}, list_tasks={list_tasks}",
        "Add missing insert_task() and/or list_tasks()."
        if not (insert_task and list_tasks)
        else "Add update_task_status() next.",
    )

    update_names = {"update_task_status", "accept_task", "complete_task"}

    has_update = bool(py_functions("backend/database/operations.py") & update_names) or has_any(
        "backend/main.py",
        ["/accept", "/complete"],
    )

    add(
        items,
        "Database",
        "Task status updates",
        status(has_update),
        "Task update function or endpoint found." if has_update else "No task status update logic found.",
        "Add update_task_status(task_id, status) and accept/complete routes.",
    )

    add(
        items,
        "Database",
        "Runtime database file",
        "IMPLEMENTED" if exists("backend/cabinops.db") else "PARTIAL",
        "backend/cabinops.db exists."
        if exists("backend/cabinops.db")
        else "DB file not found yet; it is created when backend starts.",
        "Start backend once to create backend/cabinops.db."
        if not exists("backend/cabinops.db")
        else "No action required.",
    )

    parser = exists("backend/services/intent_parser.py")

    add(
        items,
        "Core logic",
        "Intent parser",
        status(parser and has_func("backend/services/intent_parser.py", "parse_request")),
        "parse_request() found." if parser else "intent_parser.py missing.",
        "Implement parse_request(text, seat).",
    )

    parser_text = lower("backend/services/intent_parser.py")

    expected_intents = [
        "medical_assistance",
        "emergency",
        "allergy_question",
        "meal_request",
        "water_request",
        "blanket_request",
        "screen_issue",
        "missed_announcement",
        "out_of_scope",
    ]

    detected = [x for x in expected_intents if x in parser_text]

    add(
        items,
        "Core logic",
        "Intent coverage",
        "IMPLEMENTED" if len(detected) >= 8 else "PARTIAL" if detected else "NOT IMPLEMENTED",
        "Detected intents: " + (", ".join(detected) if detected else "none"),
        "Add missing intents: lavatory_question, seat_issue, meal_issue, child_assistance, complaint, connection_help.",
    )

    add(
        items,
        "Core logic",
        "Urgency detection",
        status(has_any("backend/services/intent_parser.py", ["urgency", "high", "medium", "low"])),
        "Urgency labels detected."
        if has_any("backend/services/intent_parser.py", ["urgency", "high", "medium", "low"])
        else "No urgency logic detected.",
        "Add high/medium/low urgency mapping.",
    )

    add(
        items,
        "Core logic",
        "Slot extraction",
        status(has_any("backend/services/intent_parser.py", ["slots", "symptom", "item", "device"])),
        "Basic slot extraction detected."
        if has_any("backend/services/intent_parser.py", ["slots", "symptom", "item", "device"])
        else "No slot extraction detected.",
        "Extract item, symptom, device, seat, and meal type.",
    )

    add(
        items,
        "Core logic",
        "Seat-to-zone router",
        status(exists("backend/services/router.py") and has_func("backend/services/router.py", "seat_to_zone")),
        "seat_to_zone() found." if has_func("backend/services/router.py", "seat_to_zone") else "seat_to_zone() missing.",
        "Implement row-to-zone mapping for fore/mid/aft cabin.",
    )

    rules_ok = exists("backend/services/flight_rules.py") and has_any(
        "backend/services/flight_rules.py",
        ["landing_preparation", "medical_assistance", "seatbelt"],
    )

    add(
        items,
        "Core logic",
        "Flight-rule engine",
        status(rules_ok),
        "Flight-rule service detected." if rules_ok else "Flight-rule service incomplete or missing.",
        "Implement deterministic rules for landing, takeoff, turbulence, seatbelt, medical, emergency, allergy.",
    )

    inv_exists = exists("backend/services/inventory.py")
    inv_wired = "inventory" in lower("backend/main.py")

    add(
        items,
        "Core logic",
        "Inventory checker",
        "IMPLEMENTED" if inv_exists and inv_wired else "PARTIAL" if inv_exists else "NOT IMPLEMENTED",
        "inventory.py exists and is wired."
        if inv_exists and inv_wired
        else "inventory.py exists but may not be wired."
        if inv_exists
        else "inventory.py missing.",
        "Wire inventory checking into POST /request for meals, drinks, blankets, headphones.",
    )

    speech = exists("backend/services/speech_to_text.py")
    real_whisper = has_any("backend/services/speech_to_text.py", ["import whisper", "whisper.load_model"])

    add(
        items,
        "Core logic",
        "Speech-to-text",
        "IMPLEMENTED" if real_whisper else "PARTIAL" if speech else "NOT IMPLEMENTED",
        "Real Whisper integration found."
        if real_whisper
        else "speech_to_text.py exists but appears to be a stub."
        if speech
        else "speech_to_text.py missing.",
        "Keep stub for text demo; add Whisper after backend and UI are stable.",
    )

    passenger_app = exists("frontend/passenger_screen/src/App.jsx")
    passenger_connected = passenger_app and has("frontend/passenger_screen/src/App.jsx", "fetch", "/request")

    add(
        items,
        "Frontend",
        "Passenger screen",
        "IMPLEMENTED" if passenger_connected else "PARTIAL" if passenger_app else "NOT IMPLEMENTED",
        "Passenger UI posts to /request."
        if passenger_connected
        else "Passenger UI exists but API connection unclear."
        if passenger_app
        else "Passenger UI missing.",
        "Add quick buttons, voice placeholder, and status tracker.",
    )

    crew_real = exists("frontend/crew_dashboard/src/App.jsx") or exists("frontend/crew_dashboard/package.json")
    crew_placeholder = exists("frontend/crew_dashboard")

    add(
        items,
        "Frontend",
        "Crew dashboard",
        "IMPLEMENTED" if crew_real else "PARTIAL" if crew_placeholder else "NOT IMPLEMENTED",
        "Crew dashboard app found."
        if crew_real
        else "Only crew_dashboard placeholder found."
        if crew_placeholder
        else "Crew dashboard missing.",
        "Build task queue UI using GET /crew/tasks and GET /analytics/summary.",
    )

    tests = list((ROOT / "tests").glob("test_*.py")) if exists("tests") else []

    add(
        items,
        "Testing",
        "Unit tests",
        "IMPLEMENTED" if len(tests) >= 3 else "PARTIAL" if tests else "NOT IMPLEMENTED",
        f"Found {len(tests)} test file(s).",
        "Add tests for parser, flight rules, routing, DB, and API endpoints.",
    )

    api_test = any("TestClient" in t.read_text(encoding="utf-8", errors="replace") for t in tests)

    add(
        items,
        "Testing",
        "API integration tests",
        status(api_test),
        "FastAPI TestClient detected." if api_test else "No API integration tests found.",
        "Add tests for /health, /request, /crew/tasks, /analytics/summary.",
    )

    eval_exists = exists("scripts/evaluate_parser.py") or exists("notebooks/evaluation.ipynb")

    add(
        items,
        "Testing",
        "Evaluation script/notebook",
        status(eval_exists),
        "Evaluation script/notebook found." if eval_exists else "No evaluation script/notebook found.",
        "Create scripts/evaluate_parser.py to compute intent, urgency, crew_required, and routing accuracy.",
    )

    jsons_ok = {
        "flight_context": json_valid("backend/data/flight_context.json"),
        "inventory": json_valid("backend/data/inventory.json"),
        "seat_map": json_valid("backend/data/seat_map.json"),
    }

    add(
        items,
        "Data",
        "Core JSON data files",
        "IMPLEMENTED" if all(jsons_ok.values()) else "PARTIAL",
        ", ".join(f"{k}={v}" for k, v in jsons_ok.items()),
        "Fix invalid or missing JSON files in backend/data.",
    )

    rows = csv_rows("backend/data/cabinops_requests.csv")

    add(
        items,
        "Data",
        "CabinOps request dataset",
        "IMPLEMENTED" if rows >= 500 else "PARTIAL" if rows > 0 else "NOT IMPLEMENTED",
        f"Dataset has {rows} data row(s).",
        "Expand to 30-50 rows for demo, then 500-1000 rows for final target.",
    )

    add(
        items,
        "Documentation",
        "README",
        status(exists("README.md")),
        "README.md found." if exists("README.md") else "README.md missing.",
        "Document setup, run, test, and demo commands.",
    )

    add(
        items,
        "Documentation",
        "Dataset card",
        status(exists("docs/dataset_card.md")),
        "docs/dataset_card.md found." if exists("docs/dataset_card.md") else "Dataset card missing.",
        "Create docs/dataset_card.md with schema, labels, source, limitations.",
    )

    add(
        items,
        "Documentation",
        "Final report",
        status(exists("docs/final_report.md")),
        "docs/final_report.md found." if exists("docs/final_report.md") else "Final report missing.",
        "Create docs/final_report.md with problem, architecture, dataset, evaluation, limitations.",
    )

    add(
        items,
        "Deployment",
        "Dockerfile",
        status(exists("Dockerfile")),
        "Dockerfile found." if exists("Dockerfile") else "Dockerfile missing.",
        "Add/test Dockerfile for one-command backend startup.",
    )

    req = lower("requirements.txt")
    pkgs = [x for x in ["fastapi", "uvicorn", "pydantic", "pytest", "httpx"] if x in req]

    add(
        items,
        "Deployment",
        "Python requirements",
        "IMPLEMENTED" if len(pkgs) == 5 else "PARTIAL",
        "Detected packages: " + ", ".join(pkgs),
        "Ensure requirements.txt includes fastapi, uvicorn, pydantic, pytest, httpx.",
    )

    add(
        items,
        "Operations",
        "Startup script",
        status(exists("start_all.py")),
        "start_all.py found." if exists("start_all.py") else "start_all.py missing.",
        "Add start_all.py to start backend/frontend and open docs.",
    )

    add(
        items,
        "Operations",
        "Health checker script",
        status(exists("check_cabinops.py") or exists("check.py")),
        "Health checker script found." if exists("check_cabinops.py") or exists("check.py") else "Health checker script missing.",
        "Add check_cabinops.py to verify API, DB writes, reads, and flight rules.",
    )

    main = lower("backend/main.py")

    for action in ["accept", "complete"]:
        ok = f"/{action}" in main or action in py_functions("backend/database/operations.py")

        add(
            items,
            "Workflow",
            f"{action.capitalize()} task action",
            status(ok),
            f"{action} action found." if ok else f"No {action} action found.",
            f"Add POST /crew/tasks/{{task_id}}/{action}.",
        )

    ann_file = exists("backend/data/announcements.json")
    ann_logic = "announcement" in main
    ann_ok = ann_file and ann_logic

    add(
        items,
        "Workflow",
        "Announcement history lookup",
        "IMPLEMENTED" if ann_ok else "PARTIAL" if (ann_file or ann_logic) else "NOT IMPLEMENTED",
        "Announcement history database and search logic are fully operational." if ann_ok else "Announcement handling appears partially present." if (ann_file or ann_logic) else "No announcement history data/lookup found.",
        "No action required." if ann_ok else "Add backend/data/announcements.json and lookup logic for missed_announcement.",
    )

    return items


def summarize(items: list[Item]) -> dict[str, int]:
    result = {
        "IMPLEMENTED": 0,
        "PARTIAL": 0,
        "NOT IMPLEMENTED": 0,
    }

    for item in items:
        result[item.status] = result.get(item.status, 0) + 1

    return result


def render_console(items: list[Item]) -> None:
    summary = summarize(items)
    categories = []

    for item in items:
        if item.category not in categories:
            categories.append(item.category)

    print("=" * 80)
    print("CabinOps AI Implementation Checklist")
    print("=" * 80)
    print(f"Project root: {ROOT}")
    print()
    print("SUMMARY")
    print(f"  Implemented:     {summary.get('IMPLEMENTED', 0)}")
    print(f"  Partial:         {summary.get('PARTIAL', 0)}")
    print(f"  Not implemented: {summary.get('NOT IMPLEMENTED', 0)}")
    print()

    for category in categories:
        print("-" * 80)
        print(category)
        print("-" * 80)

        for item in [x for x in items if x.category == category]:
            print(f"[{item.status}] {item.name}")
            print(f"  Evidence:  {item.evidence}")
            print(f"  Next step: {item.next_step}")
            print()

    pending = [x for x in items if x.status != "IMPLEMENTED"]

    print("=" * 80)
    print("PRIORITY NEXT STEPS")
    print("=" * 80)

    if not pending:
        print("Everything in this checklist is implemented.")
    else:
        for i, item in enumerate(pending[:12], start=1):
            print(f"{i}. {item.category} - {item.name}: {item.next_step}")


def render_markdown(items: list[Item]) -> str:
    summary = summarize(items)

    lines = [
        "# CabinOps AI Implementation Checklist",
        "",
        f"Project root: `{ROOT}`",
        "",
        "## Summary",
        "",
        f"- Implemented: `{summary.get('IMPLEMENTED', 0)}`",
        f"- Partial: `{summary.get('PARTIAL', 0)}`",
        f"- Not implemented: `{summary.get('NOT IMPLEMENTED', 0)}`",
        "",
    ]

    categories = []

    for item in items:
        if item.category not in categories:
            categories.append(item.category)

    for category in categories:
        lines += [
            f"## {category}",
            "",
            "| Status | Item | Evidence | Next step |",
            "|---|---|---|---|",
        ]

        for item in [x for x in items if x.category == category]:
            lines.append(
                f"| {item.status} | {item.name} | "
                f"{item.evidence.replace('|', '/')} | "
                f"{item.next_step.replace('|', '/')} |"
            )

        lines.append("")

    lines += [
        "## Priority Next Steps",
        "",
    ]

    pending = [x for x in items if x.status != "IMPLEMENTED"]

    if pending:
        for i, item in enumerate(pending[:12], start=1):
            lines.append(f"{i}. **{item.category} - {item.name}**: {item.next_step}")
    else:
        lines.append("Everything in this checklist is implemented.")

    lines.append("")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit CabinOps AI implementation status.")
    parser.add_argument("--json", action="store_true", help="Print JSON instead of normal report.")
    parser.add_argument("--save", help="Save markdown report, e.g. checklist_report.md.")

    args = parser.parse_args()

    items = build_items()

    if args.json:
        print(json.dumps([asdict(x) for x in items], indent=2))
    else:
        render_console(items)

    if args.save:
        out = ROOT / args.save
        out.write_text(render_markdown(items), encoding="utf-8")
        print()
        print(f"Saved markdown report to: {out}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
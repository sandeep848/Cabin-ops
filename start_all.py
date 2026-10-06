#!/usr/bin/env python3
r"""Start the Cabin Atlas development API and passenger/crew portals."""

from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKEND_HOST = "127.0.0.1"
FRONTEND_HOST = "127.0.0.1"


def print_header(title: str) -> None:
    print("\n" + "=" * 72)
    print(title)
    print("=" * 72)


def port_is_open(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(1)
        return sock.connect_ex((host, port)) == 0


def wait_for_url(url: str, timeout: int = 30) -> bool:
    deadline = time.time() + timeout

    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=3) as response:
                if 200 <= response.status < 500:
                    return True
        except Exception:
            time.sleep(1)

    return False


def run_command(
    command: list[str],
    cwd: Path,
    env: dict[str, str],
    name: str,
) -> subprocess.Popen:
    print(f"[START] {name}")
    print(f"        cwd: {' '.join(str(cwd).split())}")
    print(f"        cmd: {' '.join(command)}")

    return subprocess.Popen(
        command,
        cwd=cwd,
        env=env,
        shell=(os.name == "nt"),
        text=True,
    )


def check_required_files() -> None:
    required = [
        ROOT / "backend" / "main.py",
        ROOT / "backend" / "services" / "intent_parser.py",
        ROOT / "backend" / "services" / "flight_rules.py",
        ROOT / "backend" / "database" / "__init__.py",
        ROOT / "requirements.txt",
    ]

    missing = [str(path) for path in required if not path.exists()]

    if missing:
        print("[ERROR] Missing required project files:")
        for path in missing:
            print(f"        {path}")
        print("\nYou are probably not running this from the project root.")
        raise SystemExit(1)

    print("[OK] Required backend files found.")


def check_python_imports(env: dict[str, str]) -> None:
    print("[CHECK] Python imports")

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import backend, fastapi, uvicorn, pydantic; print('imports ok')",
        ],
        cwd=ROOT,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )

    if result.returncode == 0:
        print(result.stdout.strip())
        return

    # Auto-detect the virtual environments or Conda 'CV' environment
    venv_paths = [
        (
            ROOT / ".venv" / "Scripts" / "python.exe"
            if os.name == "nt"
            else ROOT / ".venv" / "bin" / "python"
        ),
        (
            ROOT / "venv" / "Scripts" / "python.exe"
            if os.name == "nt"
            else ROOT / "venv" / "bin" / "python"
        ),
    ]

    cv_python = None
    for p in venv_paths:
        if p.exists():
            cv_python = p
            break

    if cv_python and sys.executable != str(cv_python):
        print(
            f"[INFO] Current Python lacks dependencies. Attempting to use environment: {cv_python}"
        )
        cv_result = subprocess.run(
            [
                str(cv_python),
                "-c",
                "import backend, fastapi, uvicorn, pydantic; print('imports ok')",
            ],
            cwd=ROOT,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        if cv_result.returncode == 0:
            print(
                "[OK] Dependencies found in environment. Re-running start script using auto-detected Python..."
            )
            sys.exit(subprocess.call([str(cv_python), "-u"] + sys.argv, env=env))

    print(result.stdout.strip())
    if result.returncode != 0:
        print("[ERROR] Python imports failed.")
        print("Fix: run pip install -r requirements.txt.")
        raise SystemExit(1)


def start_backend(env: dict[str, str], backend_port: int) -> subprocess.Popen | None:
    backend_url = f"http://{BACKEND_HOST}:{backend_port}/health"

    if port_is_open(BACKEND_HOST, backend_port):
        print(f"[WARN] Backend port {backend_port} is already in use.")
        print(f"[INFO] Trying to reuse existing backend at {backend_url}")

        if wait_for_url(backend_url, timeout=5):
            print("[OK] Existing backend is responding.")
            return None

        print("[ERROR] Port is occupied, but backend health check failed.")
        print(
            f"Fix: close the process using port {backend_port}, or use --backend-port another_port."
        )
        raise SystemExit(1)

    process = run_command(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "backend.main:app",
            "--host",
            BACKEND_HOST,
            "--port",
            str(backend_port),
            "--reload",
        ],
        cwd=ROOT,
        env=env,
        name=f"FastAPI backend on port {backend_port}",
    )

    print("[WAIT] Waiting for backend...")
    if not wait_for_url(backend_url, timeout=30):
        print("[ERROR] Backend did not start correctly.")
        print("Run manually to see the traceback:")
        print(
            f"       python -m uvicorn backend.main:app --reload --port {backend_port}"
        )
        process.terminate()
        raise SystemExit(1)

    print(f"[OK] Backend running: http://{BACKEND_HOST}:{backend_port}")
    return process


def npm_exists() -> bool:
    try:
        result = subprocess.run(
            ["npm", "--version"],
            shell=(os.name == "nt"),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False


def start_frontend(
    env: dict[str, str], folder_name: str, display_name: str, frontend_port: int
) -> subprocess.Popen | None:
    frontend_dir = ROOT / "frontend" / folder_name

    if not frontend_dir.exists():
        print(f"[WARN] {display_name} folder not found. Skipping.")
        return None

    if not npm_exists():
        print(
            f"[WARN] npm is not installed or not available in PATH. Skipping {display_name}."
        )
        return None

    frontend_url = f"http://{FRONTEND_HOST}:{frontend_port}"

    if port_is_open(FRONTEND_HOST, frontend_port):
        print(f"[WARN] {display_name} port {frontend_port} is already in use.")
        print(f"[INFO] Reusing existing {display_name} at {frontend_url}")
        return None

    node_modules = frontend_dir / "node_modules"

    if not node_modules.exists():
        print(f"[SETUP] Installing {display_name} packages with npm install...")
        result = subprocess.run(
            ["npm", "ci"],
            cwd=frontend_dir,
            env=env,
            shell=(os.name == "nt"),
            text=True,
        )

        if result.returncode != 0:
            print(f"[ERROR] npm install failed for {display_name}. Skipping startup.")
            return None

    process = run_command(
        [
            "npm",
            "run",
            "dev",
            "--",
            "--host",
            FRONTEND_HOST,
            "--port",
            str(frontend_port),
        ],
        cwd=frontend_dir,
        env=env,
        name=f"{display_name} React frontend on port {frontend_port}",
    )

    print(f"[WAIT] Waiting for {display_name}...")
    if wait_for_url(frontend_url, timeout=30):
        print(f"[OK] {display_name} running: {frontend_url}")
    else:
        print(
            f"[WARN] {display_name} may still be starting. Check the terminal output."
        )

    return process


def run_quick_backend_checks(backend_port: int) -> None:
    print_header("Quick backend checks")

    health_url = f"http://{BACKEND_HOST}:{backend_port}/health"

    try:
        with urllib.request.urlopen(health_url, timeout=5) as response:
            body = response.read().decode("utf-8")
            print(f"[OK] /health -> {body}")
    except Exception as exc:
        print(f"[ERROR] /health failed: {exc}")
        return

    # Authenticate as passenger first to get bearer token
    auth_url = f"http://{BACKEND_HOST}:{backend_port}/auth/passenger"

    booking_ref = "APX22A"
    db_path = ROOT / "backend" / "cabinops.db"
    if db_path.exists():
        try:
            import sqlite3

            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT booking_reference FROM bookings WHERE seat = '22A'"
                )
                row = cursor.fetchone()
                if row:
                    booking_ref = row[0]
        except Exception:
            pass

    auth_payload = json.dumps({"seat": "22A", "booking_reference": booking_ref}).encode(
        "utf-8"
    )

    token = None
    try:
        auth_req = urllib.request.Request(
            auth_url,
            data=auth_payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(auth_req, timeout=5) as response:
            body = json.loads(response.read().decode("utf-8"))
            token = body.get("token")
            print(f"[OK] POST /auth/passenger -> obtained token")
    except Exception as exc:
        print(f"[ERROR] POST /auth/passenger failed: {exc}")
        return

    if not token:
        print("[ERROR] No token received from passenger authentication")
        return

    request_url = f"http://{BACKEND_HOST}:{backend_port}/request"
    payload = b'{"seat":"22A","text":"I feel dizzy. Can someone help?","input_modality":"text"}'

    req = urllib.request.Request(
        request_url,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            body = response.read().decode("utf-8")
            print(f"[OK] POST /request -> {body}")
    except urllib.error.HTTPError as exc:
        print(
            f"[ERROR] POST /request HTTP {exc.code}: {exc.read().decode('utf-8', errors='replace')}"
        )
    except Exception as exc:
        print(f"[ERROR] POST /request failed: {exc}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Start Cabin Atlas backend and both frontends."
    )
    parser.add_argument("--backend-port", type=int, default=8000)
    parser.add_argument("--passenger-port", type=int, default=5173)
    parser.add_argument("--crew-port", type=int, default=5174)
    parser.add_argument("--backend-only", action="store_true")
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--skip-checks", action="store_true")
    args = parser.parse_args()

    print_header("Cabin Atlas startup launcher (All Services)")
    print(f"Project root:   {ROOT}")
    print(f"Python:          {sys.executable}")
    print(f"Backend port:    {args.backend_port}")
    print(f"Passenger port:  {args.passenger_port}")
    print(f"Crew port:       {args.crew_port}")

    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    env["ENV"] = "development"
    if "SECRET_KEY" not in env:
        import secrets

        ephemeral_secret = secrets.token_hex(32)
        env["SECRET_KEY"] = ephemeral_secret
        print("[INFO] Generated an ephemeral development session secret.")
    # Provide the backend port for Vite's proxy configs
    env["VITE_BACKEND_PORT"] = str(args.backend_port)

    check_required_files()
    check_python_imports(env)

    backend_process = None
    passenger_process = None
    crew_process = None

    try:
        backend_process = start_backend(env, args.backend_port)

        if not args.skip_checks:
            run_quick_backend_checks(args.backend_port)

        if not args.backend_only:
            passenger_process = start_frontend(
                env, "passenger_screen", "Passenger Screen", args.passenger_port
            )
            crew_process = start_frontend(
                env, "crew_dashboard", "Crew Dashboard", args.crew_port
            )

        docs_url = f"http://{BACKEND_HOST}:{args.backend_port}/docs"
        passenger_url = f"http://{FRONTEND_HOST}:{args.passenger_port}"
        crew_url = f"http://{FRONTEND_HOST}:{args.crew_port}"

        if not args.no_browser:
            print("[OPEN] Opening browser pages...")
            webbrowser.open(docs_url)

            if not args.backend_only:
                webbrowser.open(passenger_url)
                webbrowser.open(crew_url)

        print_header("Running")
        print(f"Backend docs:    {docs_url}")
        print(f"Backend health:  http://{BACKEND_HOST}:{args.backend_port}/health")

        if not args.backend_only:
            print(f"Passenger UI:    {passenger_url}")
            print(f"Crew UI:         {crew_url}")

        print("\nPress CTRL+C to stop services started by this script.")

        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n[STOP] CTRL+C received. Stopping services...")

    finally:
        if passenger_process is not None:
            print("[STOP] Stopping Passenger Screen...")
            passenger_process.terminate()

        if crew_process is not None:
            print("[STOP] Stopping Crew Dashboard...")
            crew_process.terminate()

        if backend_process is not None:
            print("[STOP] Stopping backend...")
            backend_process.terminate()

        print("[DONE] Shutdown complete.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

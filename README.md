# Cabin Service Operations

A self-hosted passenger-to-crew service platform for a bounded cabin deployment. Two focused React interfaces support service requests, staff ownership, flight context, inventory, announcements, and operational audit history.

**Core engineering:** transactional retry deduplication, inventory consistency, crew ownership, acknowledgement metrics, a passenger session outbox, authenticated API access, and end-to-end Docker/browser verification.

This release is suitable for portfolio demonstrations and controlled pilot evaluation. Airline operational acceptance requires integrations and validation described in [the airline integration plan](docs/airline-integration.md).

## Local setup

Requires Python 3.12+ and Node.js 22+.

```bash
git clone https://github.com/sandeep848/Cabin-ops.git
cd Cabin-ops
python -m venv .venv
# Linux/macOS:
source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python start_all.py --skip-checks
```

The launcher installs frontend dependencies on first use. Passenger: http://127.0.0.1:5173. Crew: http://127.0.0.1:5174. API docs: http://127.0.0.1:8000/docs. Stop with Ctrl+C.

Local development credentials: passenger seat `22A`, reference `DEMO`; crew username `crew`, password `crew_password`. Development credentials are disabled when `ENV=production`. Copy `.env.example` to `.env` to customize settings. The launcher deliberately starts development mode; use containers for production configuration.

## Container deployment

Copy `.env.example` to `.env`, set a strong `CREW_PASSWORD`, and generate a stable `SECRET_KEY`:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
docker compose up --build -d
```

Both portals run behind Nginx with `/api` proxying and event-stream support. SQLite is stored in the `cabinops-data` volume. Bindings are local by default; put an HTTPS reverse proxy in front before exposing them. Use one backend worker: live updates and rate limits are in-process. Back up the database volume before upgrades; `docker compose down` preserves data, while `down -v` removes it.

Production has no synthetic bookings. Provision a booking before passenger login (the reference is requested privately):

```bash
docker compose exec backend python scripts/manage.py booking --seat 22A --name "Passenger"
docker compose exec backend python scripts/manage.py crew --username crew
```

The second command creates or rotates crew credentials. `CREW_USERNAME` and `CREW_PASSWORD` bootstrap the crew account only for a new database; changing them does not rotate an existing account. See [deployment guidance](docs/deployment.md).

## Verification

```bash
python -m pytest -q
python scripts/evaluate_parser.py
cd frontend/passenger_screen
npm ci
npm run build
cd ../crew_dashboard
npm ci
npm run build
```

GitHub Actions runs tests, parser evaluation, frontend builds, the backend image build, and a browser smoke test covering login, request completion, live announcements, failed writes, and mobile layouts. Tests use a temporary database. Parser evaluation measures the bundled sample dataset only; it is not evidence of real-world safety performance.

## Repository layout

| Path | Purpose |
| --- | --- |
| `backend/main.py` | Authenticated REST endpoints and live updates |
| `backend/database/` | SQLite schema and operations |
| `backend/security/` | Password hashing, signed tokens, and rate limits |
| `backend/services/` | Intent parsing, flight rules, routing, inventory, optional transcription |
| `frontend/passenger_screen/` | Passenger portal |
| `frontend/crew_dashboard/` | Crew console |
| `tests/` | Isolated API and service regression tests |
| `compose.yaml` | Backend and both production portal containers |
| `PRD.md` | Product scope and acceptance criteria |

## Voice and operational limits

Browser voice input requires a supported browser and microphone permission, normally on localhost or HTTPS. Unsupported or denied voice input reports an error and leaves typed input available. It never generates a simulated passenger request. Optional server transcription requires `openai-whisper`, FFmpeg, and local model availability; without it `/transcribe` returns an explicit unavailable response.

Inventory is shared by the current cabin deployment. Clearing request history preserves stock. Delayed requests remain visible in the active queue and require crew action after restrictions clear. The parser is rule based; emergencies must also be communicated directly to crew. Multi-flight inventory, distributed event delivery, airline identity integration, and formal safety validation remain outside this release.

Optional browser checks (after installing both portals):

```bash
frontend/crew_dashboard/node_modules/.bin/playwright install chromium
node tests/browser-smoke.mjs
```

The interface uses system fonts and lightweight HTML controls. Service requests, seat inspection, galley stock, broadcasts, audit history, and flight settings have dedicated workspaces. No 3D or external font dependencies are required.

## Product and engineering documentation

- [Architecture and tradeoffs](docs/architecture.md)
- [Airline integration and acceptance boundary](docs/airline-integration.md)
- [Portfolio and resume guidance](docs/resume.md)
- [Product requirements](PRD.md)

Passengers can save a nonurgent request when offline. It remains undelivered until they explicitly send it after reconnecting. Requests use stable UUID keys; retries return the same server receipt. The outbox is limited to 20 requests and is cleared on sign-out. Crew actions record ownership and timestamps, and Activity exposes an operational history. These application audit records are not a tamper-proof regulatory audit system.

# Cabin Atlas

An onboard passenger experience and cabin-service platform with a seatback interface, local entertainment playback, explainable recommendations, flight-specific aircraft layouts, and transactional galley management.

Passengers can watch captioned short-form content, listen to original audio, build a playlist that fits the remaining flight time, request available supplies, and follow crew updates. Crew manage requests, stock, announcements, flight conditions, and aggregate entertainment health in a separate workspace.

**The application starts with no flights, passenger bookings, galley stock, or invented telemetry.** An operator must provision actual layouts, flight instances, crew assignments and loading manifests. Synthetic records exist only in isolated automated tests. The eight bundled titles are actual playable original compositions and visual microfeatures, released under CC0; they are not commercial-movie placeholders. Operators can replace the catalogue with rights-cleared local media.

## Engineering that matters

- **Aircraft-aware service:** configurable row numbers, seat-letter blocks, aisles, cabins and crew zones; immutable layout snapshots for each flight.
- **Flight-scoped stock:** quantities, available and reserved units, physical capacity limits, initial loading locks, audited replenishment, and cancellation refunds.
- **Reliable requests:** SQLite transactions couple task creation, stock reservations, audit entries and idempotency receipts. Concurrent retries cannot allocate twice.
- **Explainable recommendations:** metadata TF-IDF cosine similarity, explicit pace preferences, hard duration/caption/family filters, and MMR diversity. A bounded exact 0/1 optimiser packs up to four titles from the ranked shortlist, including transitions and a five-minute landing buffer.
- **Local entertainment:** range-capable media delivery, real browser video/audio playback, captions, optional resume positions, and crew announcements that pause playback without automatic resumption.
- **Privacy and access:** memory-only bearer credentials, short-lived HttpOnly media grants, server-side session revocation, hashed booking credentials, role/flight/seat authorization, and optional media-history deletion.
- **Operational evidence:** isolated regression tests, browser journeys, accessibility checks and full production-container startup checks in GitHub Actions.

This is an independently built engineering project, not a Panasonic product or an approved aircraft installation. Its recommendation scores are deterministic metadata scores, not trained engagement predictions. Airline deployment requires supplier integration, identity enrollment, content rights, hardware testing and operator acceptance. See [integration boundaries](docs/airline-integration.md).

## Start locally

Python 3.12 and Node.js 22 are supported. Use a virtual environment.

```bash
git clone https://github.com/sandeep848/Cabin-ops.git
cd Cabin-ops
python -m venv .venv
# Linux/macOS:
source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Copy `.env.example` to `.env`, configure a random `SECRET_KEY` and your own crew password, then follow [operator provisioning](docs/operator-provisioning.md). There is no default passenger login or password. The crew bootstrap account has no flight access until explicitly assigned.

```bash
python start_all.py --skip-checks --no-browser
```

Passenger experience: http://127.0.0.1:5173. Crew operations: http://127.0.0.1:5174. API documentation is available only in development at http://127.0.0.1:8000/docs.

## Deploy

```bash
python -c "import secrets; print(secrets.token_hex(32))"
# Put the generated secret and a unique crew password in .env.
docker compose up --build -d
```

The stack runs an unprivileged backend and unprivileged Nginx portals with read-only filesystems, dropped capabilities, an internal network and a persistent database volume. Port bindings are loopback-only. An HTTPS reverse proxy is required for production media cookies and external access. The standard Compose configuration intentionally has no outbound network dependency.

Provision your operator-owned JSON files inside the backend container; see [deployment](docs/deployment.md). Keep one backend process per deployment: SSE and rate limiting remain in-process. Multi-flight data isolation does not imply a distributed fleet control plane.

## Verify

```bash
python -m pytest -q
npm ci --prefix frontend/passenger_screen
npm ci --prefix frontend/crew_dashboard
npm run build --prefix frontend/passenger_screen
npm run build --prefix frontend/crew_dashboard
frontend/crew_dashboard/node_modules/.bin/playwright install --with-deps chromium
node tests/browser-smoke.mjs
```

The browser test creates temporary, explicitly named synthetic fixtures under `tests/`, starts isolated services, exercises actual media decoding/playback and cabin workflows, and saves screenshots under `test-results/`. Application startup never imports these fixtures. No repeated synthetic dataset is reported as real-world AI accuracy.

## Documentation

| Document | Purpose |
| --- | --- |
| [Operator provisioning](docs/operator-provisioning.md) | Aircraft, flight, stock and crew enrollment |
| [Architecture](docs/architecture.md) | Data flow, invariants and deployment limits |
| [Security](docs/security.md) | Threat model, implemented controls and remaining risks |
| [Recommendations](docs/recommendations.md) | Ranking, optimization and evaluation boundaries |
| [Deployment](docs/deployment.md) | HTTPS, provisioning, backup and upgrades |
| [Airline integration](docs/airline-integration.md) | Public industry research and supplier boundaries |
| [Resume guidance](docs/resume.md) | Defensible engineering claims and interview walkthrough |
| [PRD](PRD.md) | Scope and acceptance criteria |

The parser is an advisory English rules engine. Unrecognized requests go to crew review. Emergency communication must use established crew procedures and the physical call button; this application does not connect to aircraft safety or flight-control systems. Browser voice input is optional and asks for consent because the browser's speech service may process audio externally; typed input is always available.

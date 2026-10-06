# Deployment runbook

## Prerequisites

Use Python 3.12 / Node.js 22 for local development, or Docker Engine with Compose. Configure a stable random signing secret of at least 32 characters and a unique crew password of at least 12 characters. Copy `.env.example` to `.env`; never commit credentials. There are no default flight, stock or passenger records and no DEMO login.

```bash
python -c "import secrets; print(secrets.token_hex(32))"
docker compose up --build --wait
```

The backend is private to the internal Compose network. Passenger and crew Nginx bind loopback ports 5173 and 5174. Place an HTTPS reverse proxy with operator-managed certificates in front of them. Production media cookies require HTTPS. Keep passenger access separate from operator/crew access through the network admission policy; API role checks still apply.

Read-only containers use writable `/tmp` mounts and a persistent `/data` database volume. Run one backend worker. `docker compose down` preserves the volume; `down -v` destroys it. Do not expose FastAPI directly or add arbitrary outbound connectivity. The standard application uses local media and no external recommendation service.

## Provision operational sources

Copy your reviewed aircraft and loading JSON files into the container's temporary directory, then use the CLI. Instructions and schemas are in [operator provisioning](operator-provisioning.md).

```bash
docker compose cp /path/to/operator-aircraft.json backend:/tmp/aircraft.json
docker compose exec backend python scripts/provision.py aircraft --file /tmp/aircraft.json
docker compose exec backend python scripts/provision.py flight --id YOUR_FLIGHT_INSTANCE --aircraft YOUR_AIRCRAFT_ID --origin FRA --destination DXB
docker compose exec backend python scripts/manage.py crew --username YOUR_CREW_ACCOUNT
docker compose exec backend python scripts/provision.py assign --username YOUR_CREW_ACCOUNT --flight YOUR_FLIGHT_INSTANCE
docker compose cp /path/to/operator-loading-manifest.json backend:/tmp/stock.json
docker compose exec backend python scripts/provision.py stock --flight YOUR_FLIGHT_INSTANCE --file /tmp/stock.json
docker compose exec backend python scripts/manage.py booking --flight YOUR_FLIGHT_INSTANCE --seat YOUR_SEAT --name "Passenger name"
```

The origin/destination above illustrate command syntax, not a configured flight. Use verified route data. Crew then update flight phase, service availability and landing estimate. `CREW_USERNAME`/`CREW_PASSWORD` bootstrap only a new database; use the management command to rotate an existing account.

Mount an operator media catalogue and directory read-only and configure `CABIN_ATLAS_CATALOG_PATH`/`CABIN_ATLAS_MEDIA_DIR` if replacing the original local content. Validate licensing, duration, codecs, captions and hashes before deployment. Catalogue changes take effect after a backend restart; no unreviewed runtime catalogue upload is exposed.

## Backup and upgrade

```bash
docker compose exec backend python scripts/backup_database.py /tmp/cabin-backup.db
docker compose cp backend:/tmp/cabin-backup.db ./cabin-backup.db
```

The backup uses SQLite's online backup API, checks integrity, refuses overwrites and sets restrictive permissions. Encrypt the copy and store it outside the host under an approved retention policy. Back up before schema upgrades. Restore only with the backend stopped: replace `/data/cabinops.db` using an operator-controlled maintenance container, remove obsolete WAL/SHM sidecars only while the database is stopped, verify ownership (backend UID 1001), run integrity checks, then restart. Never copy over a live database.

Old global stock is not silently attributed to a flight. Provision verified per-flight loading records after upgrade. Existing service history is preserved. Legacy booking references are migrated to salted hashes, and prior token formats become invalid. Protect and retire old backups; review SQLite compaction if historical plaintext must be removed from free pages. Reconcile any previously allocated supplies with physical counts before enabling a new flight manifest.

## Health and release verification

`/health` reports process liveness; `/ready` checks database access. Startup verifies media file integrity. Crew Entertainment displays catalogue integrity and aggregate browser-reported playback states from the last two minutes, not aircraft hardware telemetry. Flight closure removes entertainment history and revokes passenger access while retaining operational records.

GitHub Actions verifies Python regressions, frontend production builds, actual browser playback/workflows, accessibility checks and full production Compose startup. A successful CI run is engineering evidence, not an aircraft certification or penetration-test report. Adopt operator-approved alerting, vulnerability scanning, access reviews and disaster-recovery drills before live airline use.

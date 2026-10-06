# Deployment and operations

Run the supplied Compose stack with SECRET_KEY and CREW_PASSWORD set. The backend starts with production mode and one worker. Passenger and crew ports bind to localhost; terminate TLS at your ingress and restrict crew access to trusted staff.

The initial crew account is created only in an empty users table. Provision bookings with `docker compose exec backend python scripts/manage.py booking --seat 22A --name "Passenger"`. The reference is requested privately. Rotate credentials with `docker compose exec backend python scripts/manage.py crew --username crew`. No production booking records are generated automatically. Do not publish booking references.

Database state, including flight settings, is authoritative. JSON files are seed configuration, not a runtime control plane. Inventory currently belongs to the cabin deployment as a whole. Do not reuse this stack for multiple concurrent flights.

Before upgrades, back up SQLite using its backup API or stop the backend and copy the database with its WAL files. Retain the persistent volume. Restore in a staging environment and run a passenger request through crew acceptance and completion before reopening traffic.

Signed sessions expire after 24 hours; changing SECRET_KEY invalidates every session. Event streams check expiry while delivering events and send heartbeat comments every 20 seconds. In-process event delivery and rate limiting require a single worker. A distributed deployment requires shared pub/sub and a shared limiter.

The optional Whisper endpoint requires FFmpeg and preinstalled model assets. Browser recognition may use browser-provider services; obtain the required operational/privacy approval before enabling it in an actual cabin environment.


## Verified backups

Create a consistent snapshot of the configured database with `python scripts/backup_database.py /secure-backup/cabin-service-snapshot.db`. In the container, use `docker compose exec backend python scripts/backup_database.py /data/backup-YYYYMMDD.db`, then copy that snapshot to independently protected backup storage. The command refuses overwrite, uses SQLite's backup API, checks integrity, and restricts local permissions. A copy inside the same volume is not disaster recovery. Stop the backend before restoring a verified snapshot and remove obsolete WAL/SHM files from the prior database. Test the restored request lifecycle in staging before reopening service.

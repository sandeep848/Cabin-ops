# CabinOps technical report

CabinOps connects a React passenger portal and crew console to a FastAPI backend. Seat-specific signed sessions protect requests, crew credentials protect operations, and SQLite persists tasks, announcements, flight state, accounts, bookings, and inventory.

The intent parser is deterministic and English-only. Seat rows 1–10 route to fore cabin, 11–20 to mid cabin, and 21–30 to aft cabin. Flight rules delay noncritical service requests during configured restrictions. Medical and emergency requests retain critical routing.

The backend supplies event notifications to both portals, with polling fallback. Production frontends use Nginx to serve compiled assets and proxy `/api`. The deployment supports one backend worker; distributed state is outside this release.

## Evaluation

The bundled dataset contains 510 rows, including repeated utterances. Local evaluation on the release changes produced 510/510 matches for intent, urgency, and crew-required labels. These scores measure agreement with the bundled annotations and do not establish generalization or safety compliance.

Backend checks include authentication denial, seat isolation, production demo denial, inventory preservation, flight-scoped history clearing, and passenger submission through crew acceptance and completion. See CI for the current test count and build results.

## Operational limits

No external airline booking integration, per-flight inventory segregation, formal aviation validation, or distributed event broker. Optional server speech requires Whisper and FFmpeg. Browser speech depends on browser support and permission, and failures remain explicit. Real emergencies require direct contact with cabin crew.

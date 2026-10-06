# CabinOps release audit

## Changes verified
- Unified product branding as CabinOps and package names as cabinops-crew / cabinops-passenger.
- Removed personal machine paths and outdated scaffold checkers.
- Fixed the backend container missing its required docs directory.
- Added production frontend images, proxy configuration, persistent database storage, and CI.
- Disabled production DEMO login and synthetic production bookings.
- Added optional crew account bootstrap from environment settings.
- Removed fabricated voice input from the browser and server.
- Scoped clear-history operations to the permitted flight and preserved inventory.
- Kept operational flight context in SQLite rather than overwriting it from shared JSON on reads.
- Added input bounds, authenticated transcription, stream heartbeats and bounded subscriber queues.
- Added visible crew write failures, expired-session handling, mobile layout, and keyboard focus styles.
- Added regression coverage for production auth, state isolation, transcription, and complete request lifecycle.

## Remaining scope limits
Single-flight cabin deployment; shared inventory; process-local events and rate limits; optional speech model; rule-based English parsing. The repository is not an aviation-certified system. Docker execution must be verified by CI or on a Docker-enabled machine.

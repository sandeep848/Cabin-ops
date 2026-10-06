# Release audit — 2.0

Replaced the crowded composite dashboard with distinct Requests, Cabin, Galley, Broadcasts, Activity, and Flight settings workspaces. Replaced the passenger 3D menu with accessible service selection and explicit submission. Removed obsolete components, 3D dependencies, external font calls, and decorative animation.

Added durable idempotency receipts, concurrent retry protection, named crew ownership, acknowledgement/completion timestamps, service metrics, audit history, database readiness, query-free request logging, a session outbox for undelivered nonurgent requests, and production protection for historical records.

See CI for API, browser, frontend, and production Compose verification. Airline integration and external acceptance remain outstanding as described in airline-integration.md.

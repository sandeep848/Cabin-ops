# Cabin Service Operations — technical release report

The platform coordinates passenger requests, crew ownership, service restrictions, inventory, announcements, and audit history for one cabin. React clients use a FastAPI API with signed sessions and SQLite transactions. Text parsing is deterministic; optional browser speech is explicitly limited by browser support.

Engineering evidence includes regression tests for concurrent idempotent retries, inventory rollback, staff ownership, audit isolation, production authentication, and the complete request lifecycle. Browser CI covers mobile layouts, failed-write drafts, navigation, offline retry, focus behavior, and live updates. Production CI builds and boots the complete Compose stack and checks both proxies.

Bundled parser evaluation still measures 510 synthetic dataset rows, including repeated examples; perfect agreement with those annotations does not establish generalization or safety compliance.

Deployment is bounded to one configured flight and one API process. Operator integrations, independent security assessment, aircraft hardware testing, and regulatory applicability review are required before airline operational use. See architecture.md and airline-integration.md.

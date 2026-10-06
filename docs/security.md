# Security model

This project implements explicit controls and regression checks. It cannot promise zero breaches, replace independent penetration testing, or establish regulatory/airline approval.

## Assets and trust boundaries

Passenger service messages, passenger names, booking credentials, crew credentials, task history and stock records are sensitive operational data. A seatback terminal is shared; passenger devices and their requests are untrusted. Crew can act only within live assigned flight scope. The operator CLI and catalogue/manifest files are privileged configuration sources. The host, TLS proxy, dependency supply chain and backups remain outside application authorization.

## Implemented controls

| Risk | Control and verification |
| --- | --- |
| Cross-seat or cross-flight access | Signed identity scope plus active flight and crew assignment checks; negative authorization tests |
| Credential theft through URLs or logs | Authorization-header SSE, no bearer query URLs, path-only application logs, no request body logging |
| Shared-screen credential persistence | Bearer state is memory-only; sign-out erases local outbox/preferences and revokes the server session when connected |
| Stale sessions | Six-hour expiry, revocation registry, password/booking rotation revocation, active assignment checks and flight closure |
| Credential disclosure in booking lookup | Booking references are salted PBKDF2 hashes; crew responses omit them |
| Username timing disclosure | Equal-cost password hashing on unknown accounts |
| Media URL credential leakage | 15-minute hashed opaque grants in HttpOnly, SameSite Strict cookies; Secure in production; session joins on each media read |
| Request flooding and memory growth | Per-principal throttling, bounded JSON/multipart bodies, capped event queues/subscribers, constrained input models |
| SQL injection and duplicate allocation | Parameterized SQL and transactional conditional updates; concurrent reservation/retry tests |
| XSS and embedding | React text escaping, same-origin CSP, no remote scripts, framing denial and nosniff headers |
| Container privilege | Unprivileged users, read-only root filesystems, dropped capabilities, no-new-privileges and an internal backend network with a separate portal ingress bridge |
| Excess entertainment tracking | No external analytics; optional position saving; seat-scoped deletion; aggregate recent device health only |

Validation errors omit supplied input values. The media manifest validates filenames and checksum structure; startup checks local asset hashes. Operator SVG/media ingestion must use trusted, reviewed files. Schema validation is not a sanitizer for arbitrary operator-authored media.

## Remaining work before airline use

Booking credentials are a controlled-deployment enrollment mechanism, not airline-grade passenger identity. Implement the supplier/operator's approved seat binding, SSO and role lifecycle. Add an edge WAF/network admission policy, distributed throttling for scale-out, independent code review and penetration testing, dependency/image vulnerability scanning, access review and incident procedures. The current HMAC format is a bounded custom session mechanism; migrating to an established OIDC provider is appropriate for airline identity integration.

TLS and encrypted storage/backups must be configured by the operator. SQLite files and service messages are not encrypted by this application. No application audit table is tamper-proof against a database/host administrator. Old backups and SQLite free pages can retain pre-migration plaintext credentials; protect and retire old backups and perform an operator-reviewed database compaction after migration. A successful SQL migration cannot erase copies outside the database.

An offline sign-out clears the terminal but cannot reach the server to revoke a copied credential; expiry still applies. Browser speech recognition is an optional explicit-consent path that may use a browser vendor's external service. Disable it in deployment policy if an entirely local speech path is required.

The rules parser is advisory and English-only. It must not be used for independent medical, safety or flight-control decisions. Passenger physical call and crew procedures remain authoritative.

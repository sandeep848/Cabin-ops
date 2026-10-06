# Architecture and engineering decisions

## Request path
Authenticate seat → parse bounded English text → apply crew-defined service rules → begin SQLite write transaction → check idempotency receipt → reserve inventory when dispatching → insert request → append creation audit → persist receipt → commit → publish invalidation event. Subscribers reload authoritative API data. A replay returns the stored response; a key reused for different input returns HTTP 409.

## Crew lifecycle
Pending or delayed → acknowledged by a named crew member → completed by that member. Timestamps record acknowledgement and completion. Repeated identical status actions do not duplicate audit records. Service restrictions and stock checks are server enforced. Delayed stock is reserved at acknowledgement. Routine service is held when the configured context restricts it; high-priority requests remain visible for human review.

## Connectivity
Server events provide immediate invalidation and 15-second polling recovers missed events. The passenger outbox uses tab-scoped sessionStorage, holds at most 20 nonurgent requests, and requires explicit retry. Stable UUID request keys make retries safe when the server committed but a response was lost. Sign-out removes local pending messages. Emergency delivery failures instruct passengers to use a physical call button. The outbox is not a service worker and cannot send after the tab closes.

## Security and accountability
Crew endpoints require the crew role. The bounded original passenger message is stored with the request and available in the crew detail drawer; operational retention rules must account for potentially sensitive text. Passenger requests are seat-bound. Audit events include actor, event type, request ID, flight, and timestamp; they omit booking references and passenger message bodies. Application code does not expose an audit update/delete operation, but SQLite audit records are not tamper-proof against database administrators. Production disables demo login and history clearing. Readiness tests storage access. Logs use URL paths without query strings so event tokens are excluded.

## Tradeoffs
A rule-based parser is explainable and inexpensive offline, but handles English phrases only and does not establish safety understanding. Single-flight scope keeps deployment reproducible without claiming a fleet-ready data model. Local audit records support debugging and review; regulatory evidence needs a protected external sink. The interface shows the up to 500 task records, with open requests prioritized before historical records and latest 200 audit events; historical analysis must use controlled database exports.

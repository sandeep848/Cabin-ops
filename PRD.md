# Cabin Atlas product requirements

## Problem

A cabin deployment must serve passengers on a constrained local network while crew manage service safely across different aircraft layouts and loading manifests. A generic seat grid, global stock table, invented movie catalogue or internet-only recommender cannot solve this operational problem.

## Product

An independent passenger entertainment/service portal paired with a focused crew workspace. Actual playback, recommendation ranking, quantity allocation, crew ownership and cancellation are implemented. No empty supplier adapters, fictitious aircraft telemetry, checkout/payment placeholders or reported synthetic AI accuracy are included.

## Acceptance criteria

| Area | Required behavior |
| --- | --- |
| Initial state | No automatically created flights, bookings or stock; no default login shortcut |
| Aircraft geometry | Explicit rows, mixed cabin labels, seat-letter omissions and multiple aisles; flight snapshot cannot be replaced silently |
| Authorization | Passenger seat binding and live crew flight grants; denied cross-flight reads and writes |
| Supply loading | Up to 100 operator-defined items per flight, physically loaded units and capacity validation |
| Requests | Quantity 1–4, stock/task/receipt/audit transaction, unchanged retry replay, changed-payload conflict |
| Crew handling | Server-side flight restrictions, named ownership and explicit acknowledgement/completion |
| Cancellation | Only eligible pending nonurgent requests; one refund regardless of repeated cancellation |
| Entertainment | Real local audio/video decode, captions and protected range delivery |
| Recommendations | Optional transient preferences, cold-start ranking, explainability, diversity and hard time filters |
| Journey plan | No repeated title, at most four from an eight-title shortlist, transitions and landing buffer accounted for |
| Announcements | Flight-scoped updates; active player pauses and requires explicit passenger resumption |
| Accessibility | Keyboard navigation, visible focus, captions, larger text, contrast and reduced motion; automated browser checks |
| Privacy | Credentials remain memory-only, revocable sessions, media-only HttpOnly grants, hashed booking credentials, optional history deletion |
| Deployment | Unprivileged read-only containers, private backend network, TLS boundary, online verified backup and documented operator provisioning |
| Flight closure | Open tasks must be resolved; closed-flight access blocked and passenger entertainment history cleared |

## Boundaries

One edge backend process and SQLite database; multiple configured flights with data isolation. Aircraft configuration is capped at 1,000 seats/250 rows and catalogue size at 500 titles. The application has three explicit service zones. Time to landing, route labels and food labels are operator-provided; there is no GPS, avionics, PA, Bluetooth, payment, DRM or supplier SDK integration claim. Local content licensing remains an operator responsibility. The English rule parser is advisory; crew procedures and the physical call button remain authoritative for urgent assistance.

Operational acceptance requires airline identity enrollment, supplier/hardware integration, independent security testing, approved retention and content policies, and target-hardware validation. No zero-breach, certification, airline adoption or hiring claim is made.

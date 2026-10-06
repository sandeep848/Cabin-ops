# Portfolio presentation

## Suggested project title
Cabin Service Operations — Resilient passenger-to-crew service platform

## Defensible resume bullets
- Built a FastAPI/React cabin service platform with authenticated seat-level requests, crew ownership, inventory reservations, and operational audit history.
- Implemented transactional idempotency and an offline passenger outbox to prevent duplicate requests and stock deductions during connectivity loss; tested concurrent retries.
- Delivered responsive passenger and crew interfaces, automated API/browser tests, and a reproducible Docker/Nginx deployment with database readiness checks.

Do not claim airline adoption, aviation certification, real passenger deployments, fleet-scale availability, or external-company approval. Use CI evidence, the measured build sizes, and the actual benchmark output if including quantitative results.

## Demonstration
1. Passenger login on a mobile-width browser.
2. Submit water, inspect the crew queue, acknowledge it, show ownership and timestamp, then complete it.
3. Turn off the passenger browser network, save a routine request, restore connectivity, and explicitly send saved requests.
4. Explain the stable idempotency key and show its concurrency regression test.
5. Open Activity and follow creation/acknowledgement/completion events.
6. Demonstrate flight-phase restrictions and the production Compose checks.

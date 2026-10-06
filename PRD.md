# Cabin Service Operations — PRD

## Problem
Cabin teams need an orderly way to acknowledge routine passenger requests, preserve accountability, and cope with intermittent cabin network connectivity. Passenger calls alone do not provide a searchable service history or clearly communicate request progress.

## Product
A self-hosted service coordination application for one aircraft cabin. The passenger portal prepares and submits requests, shows delivery state, and stores nonurgent unsent requests in a session outbox. The crew workspace prioritizes requests, records ownership, exposes acknowledgement targets, and separates seat inspection, galley stock, announcements, flight context, and audit history.

## Design decisions
- Clear white work surfaces, restrained navy accents, system typography, and generous spacing.
- A queue-first staff experience; operational controls live in their own workspaces.
- Service buttons prepare a message; passengers explicitly submit it.
- No animations, 3D decorations, fabricated operational data, or generated speech responses.
- Urgent delivery failures direct passengers to the physical call button.

## Acceptance criteria
- Signed passenger sessions are constrained to the authenticated seat.
- Replaying an idempotency key returns the original receipt without consuming stock again; changed payloads return 409.
- Concurrent submissions with the same key create one request.
- Task ownership prevents other crew members completing assigned work.
- Reservations, request receipts, and creation audit entries commit together.
- Routine service restrictions are checked on the server.
- Crew see open/urgent/in-progress/completed counts and per-request age.
- Operational changes are audited without duplicating passenger messages or booking references.
- Failed writes preserve form drafts and display errors.
- An offline nonurgent request is clearly marked undelivered, survives a same-tab reload, and can be sent explicitly on reconnection.
- Keyboard focus, dialog escape, mobile layouts, REST API workflows, and production containers are verified.

## Intended use and limits
Controlled demonstrations and airline service pilot evaluation. One flight APX-001, a fixed 30-row six-abreast seat layout, shared inventory, and one backend process. The product is not connected to flight control or aircraft safety systems. Emergency classification is an advisory signal, not a substitute for the physical call button or established crew procedures.

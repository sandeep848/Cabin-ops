# CabinOps product requirements

## Goal
Provide a passenger-to-crew service workflow for one cabin deployment, with clear request state and flight-phase restrictions.

## Users and workflows
- Passengers authenticate by seat and booking reference, submit requests, read announcements, and track completion.
- Crew authenticate separately, review urgency and zones, accept or complete tasks, change flight context, restock inventory, and broadcast announcements.

## Acceptance criteria
- Unauthenticated users cannot access crew operations or submit requests.
- Passenger tokens cannot submit or read another seat's requests.
- Production disables demo passenger access and synthetic booking generation.
- Requests persist in SQLite and stock reservations are atomic.
- Clear-history operations affect the authorized flight and preserve inventory.
- Speech failures never create invented requests.
- Failed crew writes are visible; failed settings updates restore server state.
- Both portals build with committed lockfiles and are served through a production proxy.
- Tests use isolated data and CI verifies backend and frontend builds.

## Scope limits
Single deployment with flight APX-001, shared galley inventory, deterministic English parser, single-process events and rate limits. No aviation certification, automatic emergency response guarantee, distributed operation, or airline booking provider integration.

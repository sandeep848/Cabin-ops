# Industry research and integration boundary

This project is independent of Panasonic Avionics. Public materials informed the problem selection; no proprietary SDK, aircraft data feed or supplier contract is available in this repository.

## Public sources

- [Panasonic SDK overview](https://hangar.panasonic.aero/sdk/overview): separates seatback, mobile passenger and companion SDKs; describes custom portals, local players and paired second-screen capabilities. SDK downloading depends on contract entitlement, and engineering loads are tested on the Virtual Rack.
- [Panasonic passenger experience](https://www.panasonic.aero/our-offerings/in-flight-entertainment-systems/passenger-experience): discusses personalized passenger experiences and airline-specific digital offerings.
- [Panasonic interactive design guide](https://hangar.panasonic.aero/docs/default-source/design-guidelines/design-guidelines_interactive_v1_1.pdf?sfvrsn=e065981b_1): public passenger-interface guidance. Cabin Atlas is an original design and does not claim supplier design acceptance.
- [OWASP API Security](https://owasp.org/API-Security/editions/2023/en/0xa5-broken-function-level-authorization): role/function authorization is an explicit boundary, complemented here by seat/flight object checks.
- [EASA Information Security](https://www.easa.europa.eu/en/regulations/information-security): operator/supplier information-security obligations require assessment beyond application code. This project has no Part-IS compliance claim.

## Implemented engineering response

A local seatback-style UI plays original rights-cleared short content, explains recommendations and offers a bounded journey plan without an internet model API. Crew and passenger domains have different permissions. Aircraft geometry and loading stock come from operator sources rather than a single hardcoded plane. Media delivery supports ranges and caption files; operational events have flight scope. Device health is browser-reported and aggregate, not fake equipment telemetry.

The deliberately novel feature is combining a duration-constrained entertainment plan with the same flight context that controls service availability, while separating private preferences from crew operations. This is useful engineering work to discuss in an IFEC interview; it is not evidence of Panasonic adoption or a guaranteed hiring outcome.

## Work required for an actual installation

| Integration | Before deployment on an aircraft |
| --- | --- |
| Seat and crew identity | Approved seat enrollment, operator SSO, device trust and live staff lifecycle |
| Aircraft state | Supplier-approved read-only phase/time/PA interfaces with freshness semantics; no connection to flight-control commands |
| Entertainment | Operator licensing/DRM, supplier player integration, content entitlement, storage and codec validation |
| Hardware | Target seatback OS/browser constraints, touch/focus behavior, captions, screen/power testing and rack validation |
| Companion device | Contracted pairing/control protocol, one-time authorization and command replay protection; no pretend pairing button is included |
| Fleet operations | Reviewed release signatures, ground-to-edge distribution, inventory/DCS reconciliation, rollback and incident response |
| Security | Independent penetration test, architecture review, encrypted storage/backups and policy/retention approval |
| Service process | Operator-validated SOPs, demand reconciliation, crew workload/usability studies and disruption drills |

Incremental rollout should begin with a ground/rack evaluation, followed by a tightly scoped operator pilot after acceptance. Container CI alone does not qualify the application for aviation operation.

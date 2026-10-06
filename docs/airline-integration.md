# Airline deployment boundary and integration plan

## Release boundary
This release is a working service-coordination application suitable for a controlled cabin-service pilot evaluation. It has not been approved by an airline, certified for aviation use, penetration tested, or validated on aircraft hardware. A working container deployment does not establish operational acceptance.

## Proposed deployment
Run the cabin server on an approved onboard application host. Passenger and crew web clients reach it over a segregated cabin network. Host the database on durable local storage; HTTPS ingress and staff access controls belong to the airline-managed deployment. Keep this system isolated from avionics and safety-critical networks. The runtime has no external font, analytics, model, or 3D asset dependencies. Browser speech recognition is optional and may use a browser provider service; disable it unless approved for that environment.

## Interfaces requiring airline integration
| Interface | Release behavior | Integration needed |
| --- | --- | --- |
| Passenger identity | Provisioned seat/reference in SQLite | Approved booking or manifest feed; avoid unnecessary passenger data |
| Crew identity | Local hashed credentials, signed sessions | Airline SSO, device policy, MFA, session revocation and roster permissions |
| Flight context | Explicit crew settings | Validated read-only operational feed with freshness and failure behavior |
| Seat configuration | 30 rows, A–F | Versioned aircraft-specific cabin layouts and accessibility review |
| Stock | One cabin inventory | Airline catering reconciliation and replenishment policy |
| Audit | Application audit rows | Retention rules, protected external audit sink, access monitoring |
| Monitoring | Readiness, request IDs and service metrics | Airline logging, alerts, incident-response and support ownership |

## Evidence required before operational use
Agree pilot acceptance criteria with cabin crew and IT, test network loss and recovery on target devices, review physical-call-button fallback, validate all flight-phase rules against the operator's procedures, test restore from backup, and assess security and privacy requirements with qualified reviewers. Review role separation, encryption, data retention, and device-loss controls. Independent security testing and operator approval remain outstanding.

EASA Part-IS addresses information-security risks with a potential impact on aviation safety; the operator must determine applicability to its deployment. This project makes no Part-IS compliance claim. OWASP ASVS supplies a useful web security verification framework; no ASVS certification is claimed.

Sources: https://www.easa.europa.eu/en/regulations/information-security and https://owasp.org/www-project-application-security-verification-standard/

## Scale limits
SQLite with WAL is appropriate for the bounded single-cabin deployment under test. A fleet service requires a separate tenant/flight model, PostgreSQL or equivalent durable shared storage, a distributed event broker, shared rate limits, and a tested disaster-recovery design. Do not increase Uvicorn workers in this release: live notifications and rate limits are process-local.

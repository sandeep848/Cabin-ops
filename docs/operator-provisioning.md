# Operator provisioning

Provision records from verified operational sources. Nothing in the examples below is automatically loaded. Choose unique flight-instance IDs, not a recurring flight number reused indefinitely.

## Aircraft templates

Create an aircraft JSON document with `aircraft_id`, `name`, and `rows`. Each row contains a physical `row` number, aisle-separated `blocks` of uppercase seat letters, a service `zone`, and a `cabin` label. For example, the schema permits `blocks: ["ABC", "DEFG", "HJK"]` for a ten-abreast row, or `["A", "DG", "K"]` for a mixed business cabin. Omit nonexistent seat letters and rows. Zones are `fore_cabin`, `mid_cabin` or `aft_cabin`; explicitly assign them rather than estimating from aircraft size.

No aircraft model implies a universal layout: the same model can have different operator cabins. Limits are 250 configured rows and 1,000 seats, with row numbers up to 999. Template changes affect new flight snapshots only.

```bash
python scripts/provision.py aircraft --file /path/to/operator-aircraft.json
python scripts/provision.py flight --id YOUR_FLIGHT_INSTANCE --aircraft YOUR_AIRCRAFT_ID --origin FRA --destination DXB
```

Replace the airport codes with the actual route. Route labels are operator-provided, not flight-tracking telemetry. A new flight begins in boarding with the seatbelt sign on, meal service inactive and no landing estimate. Crew must update flight conditions before routine service.

## Crew and passengers

```bash
python scripts/manage.py crew --username YOUR_CREW_ACCOUNT
python scripts/provision.py assign --username YOUR_CREW_ACCOUNT --flight YOUR_FLIGHT_INSTANCE
python scripts/manage.py booking --flight YOUR_FLIGHT_INSTANCE --seat YOUR_SEAT --name "Passenger name"
```

Password and booking credential entry is hidden. Crew password changes revoke existing sessions. Bookings require a seat in the flight layout; replacing a booking revokes that seat's sessions and clears its media history. Use a sufficiently random booking credential; an airline PNR alone is not suitable identity enrollment for a public-facing airline deployment.

Crew assigned to several active flights can switch scope in the crew header. The selected flight controls requests, stock, profile, context, announcements, audit and diagnostics. Existing task identifiers cannot bypass flight scope.

## Loading manifest

Supply a JSON array of items. Each item contains:

| Field | Meaning |
| --- | --- |
| `item` | Unique lowercase identifier, such as a verified operator stock code |
| `name` | Passenger-facing label |
| `category` | `food`, `beverage`, `comfort` or `equipment` |
| `stock` | Physically loaded, initially available units |
| `capacity` | Configured maximum onboard units for this item |
| `allergens` | Supplier-verified declared allergens; an empty list does not mean allergy-free |
| `dietary_tags` | Supplier-verified labels; never inferred by the recommendation service |
| `alternative` | Optional identifier within this manifest |

```bash
python scripts/provision.py stock --flight YOUR_FLIGHT_INSTANCE --file /path/to/operator-loading-manifest.json
```

Initial manifest replacement is forbidden after service requests exist. Crew replenish only physically received supplies through the audited galley workflow. Available plus outstanding reserved units cannot exceed configured capacity. A reservation deducts available units once; cancellation before handling refunds once; completion does not deduct again. Delayed service does not reserve stock until crew accept it. A requested quantity is limited to four per submission.

Alternatives are informational, require stock, and must have identical declared allergen/dietary metadata. There is no automatic dietary substitution. Food/allergy questions go to crew review.

## Close a flight

```bash
python scripts/provision.py close-flight --flight YOUR_FLIGHT_INSTANCE
```

Resolve open service requests first. Closure disables access, revokes passenger sessions and clears media history/health while preserving service and audit records. Adopt a separate operator-approved retention policy for those records and backups. Reusing an old flight ID or silently replacing an occupied aircraft snapshot is intentionally refused.

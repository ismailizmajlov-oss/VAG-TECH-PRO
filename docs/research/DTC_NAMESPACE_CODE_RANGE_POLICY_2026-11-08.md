# OBD-II DTC namespace range policy — 2026-11-08

## Decision

The generic SAE/ISO OBD-II namespace and manufacturer-controlled OBD-II namespace are separated by code-range validation in the product importer, JSON Schema and SQLite constraints. The P3xxx family is mixed and is handled conservatively because the current SAE J2012DA allocation table has not been acquired.

The normalized allowlists are:

- Generic: P0xxx, P2xxx, B0xxx, C0xxx and U0xxx.
- Manufacturer-controlled: P1xxx, P30xx-P33xx, B1xxx-B2xxx, C1xxx-C2xxx and U1xxx-U2xxx.
- Unresolved/quarantined: P34xx-P39xx, U3xxx, B3xxx and C3xxx.

The pinned OBDex CC0 source projection labels 155 P34xx records as generic. That upstream label does not establish their exact current SAE/ISO allocation. All P34xx rows remain in the isolated research pack and are excluded from normalized generic and manufacturer-specific DTC namespaces until exact current J2012DA assignments are independently verified.

## What the guard does not prove

A manufacturer-controlled range is not proof that a code is authored by Volkswagen Group, applies to a particular ECU, or is valid for a model, generation, year, engine, gearbox or market. It is only a standards-range classification boundary.

A VAG-specific record still requires an eligible VAG manufacturer identity, exact configuration and ECU links, a source document/revision/evidence locator/SHA-256, explicit commercial/display/bulk/offline-cache/redistribution rights, and independent technical review before publication.

Generic OBDex records remain generic-only and do not acquire VAG vehicle fitment. Community datasets with unclear record-level provenance remain quarantined.

## Verification

- Root SQLite insert/update triggers reject cross-range namespace assignments and reject all P34xx identifiers from the normalized generic namespace.
- The OEM DTC JSON Schema applies namespace-specific code patterns.
- The desktop package validator checks code ranges before opening the SQLite import transaction.
- Regression tests cover P34xx quarantine, manufacturer-controlled P1/P3/B/C/U ranges, and rollback/no-partial-write behaviour.
- An independent audit utility reports namespace mismatches and cross-namespace identifier overlap.

This policy is a classification guard, not a source licence or repair-data approval.

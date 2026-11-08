# OBD-II DTC namespace range policy — 2026-11-08

## Decision

The generic SAE/ISO OBD-II namespace and manufacturer-controlled OBD-II namespace are separated by code-range validation in the product importer, JSON Schema and SQLite constraints.

The ranges are pinned to the OBDex data-scope lock already used by the project:

- Generic: P0xxx, P2xxx, P34xx, B0xxx, C0xxx, U0xxx and U3xxx.
- Manufacturer-controlled: P1xxx, P30xx–P33xx, P35xx–P39xx, B1xxx–B2xxx, C1xxx–C2xxx and U1xxx–U2xxx.

The range check prevents a generic SAE/ISO code from being labelled VAG-specific and prevents a manufacturer-controlled code from being imported as generic. The independent overlap auditor also reports identifiers present in both namespaces.

## What the guard does not prove

A manufacturer-controlled range is not proof that a code is authored by Volkswagen Group, applies to a particular ECU, or is valid for a model, generation, year, engine, gearbox or market. It is only a standards-range classification boundary.

A VAG-specific record still requires an eligible VAG manufacturer identity, exact configuration and ECU links, a source document/revision/evidence locator/SHA-256, explicit commercial/display/bulk/offline-cache/redistribution rights, and independent technical review before publication.

Generic OBDex records remain generic-only and do not acquire VAG vehicle fitment. Community datasets with unclear record-level provenance remain quarantined.

## Verification

- Root SQLite insert/update triggers reject cross-range namespace assignments.
- The OEM DTC JSON Schema applies namespace-specific code patterns.
- The desktop package validator checks code ranges before opening the SQLite import transaction.
- Regression tests cover generic P34xx and manufacturer-controlled P1/P3/B/C/U ranges, including rollback/no-partial-write behaviour.
- An independent audit utility reports namespace mismatches and cross-namespace identifier overlap.

This policy is a classification guard, not a source licence or repair-data approval.

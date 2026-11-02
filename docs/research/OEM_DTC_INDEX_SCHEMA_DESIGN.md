# OEM DTC index: data model and publication gates

The canonical index is defined by:

- JSON Schema: `data/schemas/oem-dtc-index.schema.json`
- SQLite DDL: `data/sql/oem-dtc-index.sql`

## Indexed dimensions

Each DTC claim is linked to:
- DTC identifier and namespace (generic SAE/ISO vs manufacturer-specific VAG);
- manufacturer and market scope (RU/EAEU/EU/NAR/CN/RoW/unknown);
- model, generation/type code, model years and production range;
- engine code, gearbox code, drive configuration and explicit PR codes;
- ECU supplier/family, diagnostic address, part number, HW number/version, SW number/version, calibration ID and component string;
- source document ID, document type, revision, issue date, source URL and source hash;
- exact evidence locator (page/table/section/diagram);
- applicability evidence level and review status;
- license, reuse scope, redistribution rights and permission reference;
- linked repair-procedure and wiring-diagram references with separate storage permissions.

## Non-negotiable guards

1. A generic SAE/ISO code cannot be inserted under a VAG manufacturer label.
2. A record cannot be publication-approved unless the source record explicitly permits redistribution under CC0, public domain, an approved open license, or a written permission grant.
3. A record cannot be publication-approved if its evidence locator is empty or its applicability is only generic, unknown or model-year-only.
4. Generic OBDex data remains in the generic namespace. Identifier overlap with a third-party Audi/VW list is not OEM attribution.
5. Exact VINs are not committed to public Git. Use local protected records or anonymized sample IDs.
6. A repair procedure's text and a wiring diagram each have their own explicit storage-permission flags. Access to a document does not imply redistribution rights.

## Validation performed

The SQLite DDL was executed in an in-memory SQLite database on 2026-11-03. It created the four normalized tables, indexes and two guards. `PRAGMA integrity_check` returned `ok`. A test insert confirmed that a generic SAE/ISO code cannot be labelled as manufacturer-specific VW. A second test confirmed that a proprietary source with `redistribution_allowed=0` cannot be promoted to `publication_approved`.

No production rows have been imported into this schema yet. It is an empty, evidence-first index foundation; no OEM DTC applicability has been fabricated.

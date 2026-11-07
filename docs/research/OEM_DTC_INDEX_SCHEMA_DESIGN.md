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

1. Generic SAE/ISO rows must use manufacturer `UNKNOWN`; insert and update guards prevent relabelling them as a VAG make.
2. A `manufacturer_specific_vag` row must name Volkswagen, Audi, Škoda, SEAT or CUPRA. Other manufacturer-specific rows use the separate `OTHER` identity.
3. The VIN-free `oem_dtc_vehicle_applicability` bridge accepts only `manufacturer_specific_vag` rows. Generic SAE/ISO definitions remain searchable in their own namespace and cannot acquire VAG fitment through this bridge.
4. A record cannot be publication-approved unless the source record explicitly permits redistribution under CC0, public domain, an approved open license, or a written permission grant.
5. A record cannot be publication-approved if its evidence locator is empty or its applicability is only generic, unknown or model-year-only.
6. Generic OBDex data remains in the generic namespace. Identifier overlap with a third-party Audi/VW list is not OEM attribution.
7. Exact VINs are not committed to public Git. Use local protected records or anonymized sample IDs.
8. A repair procedure's text and a wiring diagram each have their own explicit storage-permission flags. Access to a document does not imply redistribution rights.

## Validation performed

The SQLite DDL was executed in an in-memory SQLite database on Windows x64. The current checks cover namespace/manufacturer consistency on insert and update, the VAG-only vehicle-applicability bridge, immutable linked classification, source-rights publication gates, exact powertrain evidence and technical-record provenance. The JSON Schema also binds each DTC namespace to the permitted manufacturer identity.

- Windows DTC bridge/evidence workflow run 32: https://github.com/ismailizmajlov-oss/VAG-TECH-PRO/actions/runs/42354754579 — passed.
- Windows OEM DTC schema workflow run 6: https://github.com/ismailizmajlov-oss/VAG-TECH-PRO/actions/runs/42354924207 — passed.

`PRAGMA integrity_check` and foreign-key checks are part of the tests. These are schema-contract fixtures only; no OEM DTC rows or factory applicability have been fabricated or imported.

No production rows have been imported into this schema yet. It is an empty, evidence-first index foundation; no OEM DTC applicability has been fabricated.

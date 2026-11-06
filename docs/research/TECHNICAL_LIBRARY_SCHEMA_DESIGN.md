# VAG TECH PRO — technical library schema v1

This is a storage contract, not a claim that factory repair content has been acquired or that every desktop screen is complete. It separates the source document, its reuse rights, the vehicle/ECU applicability evidence and each versioned technical record.

## Data model

- `technical_source_rights` records rights for technical source documents; `vehicle_catalog_source_rights` separately records rights for model/variant and powertrain evidence. Both require explicit display, offline-cache, bulk-reuse and redistribution rights, plus the exact license-text hash or permission reference. A license name alone is not enough.
- `technical_documents` stores the source document revision, market scope, content hash and storage mode.
- `technical_applicability` records the market, model years, exact variant, engine, transmission, ECU identity, evidence locator, evidence hash, precision and review state.
- `technical_document_applicability` links a source document to its approved applications.
- `technical_records` stores versioned JSON payloads for DTC test plans, repair procedures, wiring diagrams, ECU pinouts, torque specifications, adaptations, service intervals, ECU profiles and OEM parts. Every record is linked to one document revision and one applicability record.

## Publication gates

A record is visible through `v_published_technical_records` only after the document, applicability and record each reach `publication_approved`. SQLite triggers reject sources without approved display/offline/bulk/redistribution rights for the requested storage mode. Published views re-check current rights on every query, so a later revocation immediately hides the affected technical records; broad, unknown or model-year-only applicability; exact engine/transmission claims without a published variant, engine, transmission and approved pair evidence; exact ECU claims without exact hardware/software identity; DTC namespace mismatches; and in-place edits to provenance or payload fields. Corrections require a new revision.

Generic SAE/ISO DTC test plans and VAG-specific test plans have separate views: `v_generic_dtc_test_plans` and `v_vag_specific_dtc_test_plans`.

## Payload validation and hashes

Before import, the desktop importer must validate the wrapper `{schema_version, record_kind, payload}` against `data/schemas/technical-record-payloads.schema.json`. It must compute `record_sha256` from canonical UTF-8 JSON with sorted keys, compact separators and NaN disallowed. SQLite checks JSON object shape and SHA-256 format; the importer verifies the hash against canonical payload bytes.

The SQL schema is packaged under `resources/sql-schema/technical-library.sql`; the payload schema is packaged under `resources/schemas/technical-record-payloads.schema.json`. Packaging and lifecycle checks prove those exact files are present and hashed. This does not by itself activate a desktop migration or populate repair data; those remain separate release gates.

## Safety and privacy

Manual vehicle selection remains supported; VIN entry is not required. `exact_vin` is only a source-evidence precision class for a published VIN range and must not contain a customer's actual VIN. ECU security access fields are references to documentation only: never store passwords, PINs, SFD tokens, secret keys or credentials. Candidate records remain hidden from published views.


## Desktop import enforcement (run78)

The offline desktop importer now validates every imported technical payload against the versioned JSON Schema before opening the SQLite write transaction. The packaged schema is resolved from the Electron resources directory (or the source tree in development); a missing schema blocks technical imports. Record-type mappings are explicit: `pinout` → `ecu_pinout`, `ecu_reference` → `ecu_profile`, and `oem_supersession` → its own schema definition. The generic OBDex namespace accepts only the observed standard ranges P0/P2/P3 and B/C/U0/U3, excluding manufacturer-controlled P1/B1/B2/C1/C2/U1/U2 ranges; VAG-specific payloads may use uppercase SAE/ISO codes or five-digit legacy VAG codes such as `17978`, while remaining behind the VAG-specific namespace and exact ECU/configuration gates; the existing namespace and exact ECU/configuration gates remain in force. Invalid payloads therefore fail before any import batch or technical row is written.

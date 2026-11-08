# DTC namespace range review and conservative correction — 2026-11-08

## Decision

The run87 importer policy was still too permissive for the mixed P3xxx family. The upstream OBDex snapshot labels all 155 P34xxx records as generic, but that upstream label is not sufficient evidence of their exact current SAE/ISO allocation. The normalized importer now rejects the entire P34xxx-P39xxx family from both generic and manufacturer-specific namespaces. These rows may remain only in the `unknown` research quarantine until exact current assignments are independently verified.

## Evidence and limits

The historical SAE J2012 DEC2007 publication classifies P3xxx as a mixed manufacturer-controlled / ISO-SAE-reserved family. Its section 5.6.4 and code-structure description do not justify treating the whole P34xxx block as generic merely because a third-party dataset labels it that way. The current SAE catalogue lists J2012_202509 (revised 2025-09-01) and the current digital annex J2012DA_202607 (revision dated 2026-07-29). The current digital annex is licensed; VAG TECH PRO has not acquired it under a reuse licence.

- Historical public reproduction of SAE J2012 DEC2007 (secondary copy; used only to understand the mixed P3xxx allocation family): https://www.slideshare.net/slideshow/sae-dtc-definitions-j2012-revised-dec2007/259479876
- SAE official catalogue, current J2012_202509 revision: https://saemobilus.sae.org/standards/j2012_202509-diagnostic-trouble-code-definitions
- SAE official catalogue, current J2012DA_202607 revision: https://saemobilus.sae.org/standards/j2012da_012013-digital-annex-diagnostic-trouble-code-definitions-failure-type-byte-definitions

No current J2012DA allocation table or DTC definition text is stored. Consequently, no P34xxx code is promoted to a normalized generic or manufacturer-specific namespace from a prefix, a historical allocation table, or an upstream CC0 label alone.

The pinned OBDex CC0 research pack contains 155 P34xxx rows and 174 U3xxx rows. They remain in the separate research database only. The CC0 grant covers the upstream data files, not the copyrighted SAE annex or third-party references embedded in those rows. The P34xxx records are not deleted from the research pack; they are simply excluded from normalized product DTC namespaces.

## Normalized importer policy

- Generic SAE/ISO ranges: P0xxx, P2xxx, B0xxx, C0xxx and U0xxx.
- Manufacturer-controlled ranges: P1xxx, P30xx-P33xx, B1xxx-B2xxx, C1xxx-C2xxx and U1xxx-U2xxx.
- Unresolved/reserved for this importer: P34xxx-P39xxx, U3xxx, B3xxx and C3xxx. These identifiers may be retained only in the `unknown` quarantine namespace; they are rejected from both normalized generic and manufacturer-specific namespaces until exact current-standard assignments are verified.
- A manufacturer-controlled range does not prove Volkswagen Group authorship. VAG-specific records still require a named VAG manufacturer, source-document revision, evidence locator, SHA-256, explicit rights for storage/display/redistribution, exact ECU/configuration applicability and independent technical review.

## Rights

The source register contains `sae-j2012-dtc-standard` as metadata-only. `permission_status=not_obtained`; standard text, current DTC tables and allocation spreadsheets are not ingested, cached, displayed or redistributed. No SAE content is represented as CC0.

## Verification

- The machine-readable contract is `data/policies/dtc-namespace-ranges.json`.
- JSON Schema patterns, SQLite insert/update triggers, the Python validator, the Node overlap auditor and the desktop pre-transaction importer must match the same allowlists.
- Regression tests reject P34xxx-P39xxx, U3xxx, B3xxx and C3xxx from both normalized generic and manufacturer-specific namespaces, including pre-transaction rollback.
- The isolated OBDex research pack may retain upstream P34xxx/U3xxx labels, but the local normalization lock explicitly prohibits promotion into the normalized product DTC index.
- No DTC definition text, current SAE annex spreadsheet or restricted standard content is copied into the repository.

# DTC namespace range review and conservative correction — 2026-11-08

## Decision

The run86 namespace guard was too broad in two places: it treated P35xx–P39xx as manufacturer-controlled and treated every U3xxx identifier as generic. The run87 correction removes both assumptions from the normalized product DTC namespaces.

## Evidence and limits

The publicly accessible SAE J2012 MAR2013 document's Figure 3 distinguishes P3000–P3399 (manufacturer-controlled) from P3400–P3999 (SAE-reserved). Therefore P35xx–P39xx must not be classified as manufacturer-specific. The same edition says that only a portion of the U3 range is reserved for uniform codes assigned by the standard; the public figure does not identify the exact assigned U3 codes. Exact current assignments are contained in the licensed J2012DA digital annex.

- SAE J2012 MAR2013 PDF: https://files.infocentre.io/files/docs_clients/126_2007751625_1263573_J2012_201303.pdf (Figure 3 and sections 5.2–5.7).
- SAE official catalogue, current J2012_202509 revision dated 2025-09-01: https://saemobilus.sae.org/standards/j2012_202509-diagnostic-trouble-code-definitions
- SAE official catalogue, current J2012DA_202607 revision dated 2026-07-29: https://saemobilus.sae.org/standards/j2012da_012013-digital-annex-diagnostic-trouble-code-definitions-failure-type-byte-definitions

The current J2012DA is licensed and has not been acquired under a reuse licence. No current allocation table or DTC definition text is stored. Consequently, U3xxx is not promoted to a normalized generic or VAG-specific namespace from a prefix or third-party dataset label alone. B3xxx and C3xxx also remain quarantined until exact current assignments are established.

The pinned OBDex CC0 research pack contains 174 U3xxx rows and upstream labels them generic. Those rows remain in the separate research pack only; they are not merged into the normalized product DTC index. The upstream CC0 grant covers its data files, not the copyrighted SAE annex or third-party references embedded in those rows.

## Normalized importer policy

- Generic source-backed ranges: P0xxx, P2xxx, P34xx, B0xxx, C0xxx and U0xxx. P34xx is accepted only for an exact identifier present in a pinned source snapshot.
- Manufacturer-controlled ranges: P1xxx, P30xx–P33xx, B1xxx–B2xxx, C1xxx–C2xxx and U1xxx–U2xxx.
- Unresolved/reserved for this importer: P35xx–P39xx, U3xxx, B3xxx and C3xxx. These identifiers may be retained only in the `unknown` quarantine namespace; they are rejected from both normalized generic and manufacturer-specific namespaces until exact current-standard assignments are verified.
- A manufacturer-controlled range does not prove Volkswagen Group authorship. VAG-specific records still require a named VAG manufacturer, source-document revision, evidence locator, SHA-256, explicit rights for storage/display/redistribution, exact ECU/configuration applicability and independent technical review.

## Rights

The source register contains `sae-j2012-dtc-standard` as metadata-only. `permission_status=not_obtained`; standard text, current DTC tables and allocation spreadsheets are not ingested, cached, displayed or redistributed. No SAE content is represented as CC0.

## Verification

- The machine-readable contract is `data/policies/dtc-namespace-ranges.json`.
- JSON Schema patterns, SQLite insert/update triggers, the Python validator, the Node overlap auditor and the desktop pre-transaction importer must match the same allowlists.
- Regression tests reject P35xx–P39xx, U3xxx, B3xxx and C3xxx from both normalized generic and manufacturer-specific namespaces, including pre-transaction rollback.
- The isolated OBDex research pack may retain its upstream U3xxx classification, but the local research lock explicitly prohibits promotion into the normalized product DTC index.
- No DTC definition text, current SAE annex spreadsheet or restricted standard content is copied into the repository.

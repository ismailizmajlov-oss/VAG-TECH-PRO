# DTC namespace range review and conservative correction — 2026-11-08

## Decision

The run86 namespace guard was too broad in two places: it treated P35xx–P39xx as manufacturer-controlled and U3xxx as automatically generic. The run87 correction removes those assumptions from the normalized product DTC namespaces.

## Evidence

The standard metadata and rights decision are registered as source `sae-j2012-dtc-standard` in `data/source-manifests/vag-factory-source-register.json`; no standard text or allocation table is ingested.

The publicly accessible SAE J2012 MAR2013 document states in Figure 3 that P3000–P3399 is manufacturer-controlled and P3400–P3999 is SAE-reserved. Sections 5.4–5.7 separately identify B3xxx and C3xxx as reserved and describe U3xxx as manufacturer-controlled and ISO/SAE-reserved. The document is copyrighted; VAG TECH PRO stores no copy or extracted definition text. Only the range-policy facts needed for validation are recorded.

- SAE J2012 MAR2013 PDF: https://files.infocentre.io/files/docs_clients/126_2007751625_1263573_J2012_201303.pdf (Figure 3; sections 5.4–5.7).
- SAE official catalogue, current J2012_202509 revision dated 2025-09-01: https://saemobilus.sae.org/standards/j2012_202509-diagnostic-trouble-code-definitions
- SAE official catalogue, current J2012DA_202607 revision dated 2026-07-29: https://saemobilus.sae.org/standards/j2012da_012013-digital-annex-diagnostic-trouble-code-definitions-failure-type-byte-definitions

The current J2012DA is a licensed digital annex and its full current allocation table has not been acquired under a reuse licence. Therefore no code-level changes from that revision are inferred. Until the current annex is lawfully obtained and reviewed, U3xxx and P35xx–P39xx remain unresolved and are not admitted to either normalized generic or VAG-specific namespaces.

## Normalized importer policy

- Generic source-backed ranges: P0xxx, P2xxx, P34xx, B0xxx, C0xxx, U0xxx and U3xxx. P34xx and U3xxx are accepted only for exact identifiers present in a pinned source snapshot.
- Manufacturer-controlled ranges: P1xxx, P30xx–P33xx, B1xxx–B2xxx, C1xxx–C2xxx and U1xxx–U2xxx.
- Unresolved/reserved for this importer: P35xx–P39xx, B3xxx and C3xxx. These identifiers may be retained only in the `unknown` quarantine namespace; they are rejected from both normalized generic and manufacturer-specific namespaces. U3xxx is ISO/SAE-controlled, but only exact source-backed rows are admitted.
- P34xx is admitted only when the exact record is present in the pinned source snapshot; the prefix alone is not proof that a code is assigned by the latest J2012DA.
- A manufacturer-controlled range does not prove Volkswagen Group authorship. VAG-specific records still require a named VAG manufacturer, source-document revision, evidence locator, SHA-256, explicit rights for storage/display/redistribution, exact ECU/configuration applicability and independent technical review.

## OBDex boundary

The pinned OBDex CC0 snapshot remains a separate research pack. Its P3/U3 family rows retain the upstream source's classification in that isolated namespace only; they are not automatically promoted to the normalized product generic DTC index. The pack does not establish VAG fitment, ECU applicability, or OEM repair procedures.

## Verification required

- JSON Schema patterns, SQLite insert/update triggers, the Python schema validator, the Node overlap auditor and the desktop pre-transaction importer use the same conservative ranges.
- Regression tests reject P35xx–P39xx, B3xxx and C3xxx from both normalized generic and manufacturer-specific namespaces, including pre-transaction rollback; U3xxx is accepted only in the generic namespace.
- Invalid records must fail before transaction commit; no partial technical record or import-batch row may remain.
- No DTC definition text, current SAE annex spreadsheet, or restricted standard content is copied into the repository.


## Current policy contract — run87

The machine-readable contract is `data/policies/dtc-namespace-ranges.json`. SAE's catalogue identifies J2012_202509 (revised 2025-09-01) and the J2012 digital annex's current revision J2012DA_202607 (verified 2026-07-29). The current annex is licensed and has not been acquired for redistribution; no current allocation spreadsheet or definition text is stored. The importer therefore uses the conservative range allowlist above, with unresolved ranges quarantined instead of guessing. The SAE catalogue describes J2012 as the standardized DTC definition and manufacturer-specific range reference, but does not provide a public reuse grant for the annex content.

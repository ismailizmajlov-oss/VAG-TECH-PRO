# ASTRA / FEDRO TAS open-data source review — 2026-11-06

## Decision

The Swiss Federal Roads Office (FEDRO / ASTRA) publishes its current Type Approval System (TAS) vehicle-type records as Open Government Data. The official FEDRO newsletter dated 23 February 2026 explicitly says that all listed type-approval data products are free to use as OGD and that FEDRO must be cited. This is a rights-cleared source for a separate **Switzerland-only** homologation research pack, subject to the exact source scope and attribution below.

This does **not** clear Russian or EAEU OТТС. Swiss type approvals must never be represented as Russian/EAEU approvals, and a type approval is not an individual VIN build sheet.

## Primary evidence

- [FEDRO vehicle-data newsletter, 23 February 2026](https://opendata.astra.admin.ch/ivzod/5000-Newsletter/2026_1/Newsletter_Fahrzeugdaten_1_2026_EN.pdf): pages/lines describing the TAS files, the passenger-car index, monthly updates, free OGD use and mandatory FEDRO attribution.
- [Official ASTRA vehicle-data page](https://www.astra.admin.ch/de/fahrzeugdaten): identifies vehicle-type data as freely available Open Government Data and says users must handle data carefully and professionally.
- [Swiss Open Data FAQ](https://opendata.swiss/en/faq): says data is free to access without registration and may be used commercially unless a dataset states otherwise.
- [EMBAG / EMOTA Art. 10](https://www.data-sharing.ch/en/index1): federal legal basis for publication of open government data, subject to statutory exceptions.
- [ASTRA TAS data directory](https://opendata.astra.admin.ch/ivzod/4000-Typengenehmigungen_TAS/): public machine-readable data directory.
- [ASTRA TAS JSON schema](https://opendata.astra.admin.ch/ivzod/4000-Typengenehmigungen_TAS/4250-json-Schema/govServices_TypeApproval_Schema.json).

## What is available

The FEDRO newsletter states that:
- more than 200,000 third-generation type approvals have individual bilingual JSON files with English attribute names;
- a passenger-car index is available as XLSB, while CSV files are available for the broader automobile group;
- the separate emissions dataset can contain one to four gearbox variants for an automobile, with each gearbox represented on a separate row;
- the data products are updated monthly;
- previous records are overwritten when approvals change;
- holder codes are not disclosed; and
- current-generation data sheets are not offered as PDF prints.

The official Windows probe runs have fetched and pinned the passenger-car index, other-automobile index, emissions/gearbox index and JSON schema, plus six sample approval JSON records. Source file sizes, SHA-256 hashes, row counts and sample field values are recorded in the source manifest.

## Rights and attribution

Approved uses for the published OGD products:
- display in VAG TECH PRO;
- offline caching in the local research database;
- transformation and filtering into a separate VAG/CH research pack;
- redistribution of the derived pack under the OGD reuse conditions; and
- commercial use, with FEDRO attribution.

Required attribution:

> Source: Federal Roads Office (FEDRO/ASTRA), Type Approval System (TAS) open data.

The OGD decision applies only to the published open-data products. It does not extend to fee-based datasets, personal/holder information, unrelated ASTRA portals, third-party websites, or copyrighted manufacturer repair material. No paid access, account, contract or external credential is required for the listed open-data files.

## Applicability boundaries

- Market scope is **CH** only.
- The approval record is the highest initial applicability level. Type, variant and version are usable only when explicit in the source record.
- Engine and gearbox codes are not considered verified until the schema probe identifies the exact fields and their parent/row relationship.
- If several gearbox variants are present, preserve each explicit row/link. Never cross-join all engines with all gearboxes.
- Model year, generation, production date and VIN-level fitment are not inferred from an approval number or first-registration date.
- This source does not provide VAG DTCs, ECU definitions, repair procedures, wiring diagrams, pinouts, torque values or adaptation instructions.

## Implementation status — 2026-11-06

1. **Completed:** official source indexes, JSON schema and six sample VAG approval records were probed; source sizes, SHA-256 hashes, row counts and field paths are pinned.
2. **Completed in code:** exact source make whitelist, official source identity/URL/rights gates, exact composite variant/version scope linker, wildcard preservation and CH-only SQLite schema are implemented.
3. **Completed in tests:** exact-version, wildcard, missing-scope, ambiguous-scope, wrong-gearbox-class, exact-make, source-identity, rights and CH-only boundary tests are present. The Windows source-contract workflow has passed these unit tests.
4. **Not yet verified:** the full generated SQLite pack artifact has not yet been confirmed by a recorded CI pack-build run. The source manifest deliberately records `pack_build_evidence_status=not_yet_recorded`; no desktop integration or production release is claimed.
5. **Not permitted by this source:** RU/EAEU fitment, VAG gearbox-code confirmation, individual-vehicle/VIN fitment, model-year inference or repair-data applicability.

The builder now records the raw source-manifest SHA-256, a deterministic source-snapshot hash, per-file hashes and the generated database hash. The pack remains a separate CH-only read-only research namespace.

## Field-level schema probe completed (2026-11-05)

The Windows 2022 probe downloaded the official passenger-car XLSB, official JSON schema and six individual CUPRA approval JSON records. The probe completed successfully.

Pinned snapshot evidence:
- `TAS_Personenwagen.xlsb`: 30,761,711 bytes; SHA-256 `0f66370e7414d0bfabf2cf1e97df3b8e190f4a66ba38d2012e2791cb5c9b2774`.
- `govServices_TypeApproval_Schema.json`: 65,421 bytes; SHA-256 `5fb35f59455aca0983a36328bfb11e418e05f7af98b82579874ca216b2523d9d`.
- Six official per-approval JSON records were downloaded with HTTP 200 and individually hashed; their hashes and observed values are pinned in the source manifest.

Confirmed fields include `chTypeApprovalNumber`, `makeName`, `type`, `variant`, `version`, `manufacturerOfTheEngine`, `engineType`, `chEngineCodeAsMarkedOnTheEngine`, and `gearboxEmissions1..4.versionDefined` / `chGearboxType`.

Important semantic distinction from the official records:
- CUPRA Formentor approval 1XZ904 has `engineType=DNPA`, while `chEngineCodeAsMarkedOnTheEngine=DNP`; the stamped marking is not the same value as the engine-type designation.
- Approval 1XZ734 has `engineType=DPCA` and stamped marking `DPC`.
- Approval 1XZ326 has `engineType=DNFB` and stamped marking `DNF`.
- The linked `chGearboxType` is `m7a` for these Formentor records. CUPRA Born approvals show `m1a`.
- `gearboxEmissionsN.versionDefined` carries the variant/version scope for the gearbox/emissions row.

Therefore the source can provide an official **engine-type designation** and a Swiss gearbox-type classification at approval/variant/version scope. It does **not** provide a confirmed VAG gearbox code in the reviewed schema. Neither `engineType` nor the stamped marking is promoted to a confirmed VAG engine-code record without independent validation. The separate emissions XLSB and non-passenger-car index are being probed before pack construction.


## Full index and emissions workbook probe completed (2026-11-05)

A second Windows 2022 probe parsed all three official XLSB products (no scan cap was reached):

| Product | Rows scanned | SHA-256 |
|---|---:|---|
| Passenger-car index | 128,490 | `0f66370e7414d0bfabf2cf1e97df3b8e190f4a66ba38d2012e2791cb5c9b2774` |
| Other-automobile index | 83,301 | `fbf916b53c9e25f146108445ac984f38ebb04b12e4019119db1b7d90f6329768` |
| Emissions / gearbox rows | 282,866 | `dd89f6ba2ed7df8206a23b893dcc7d8ef2c7839bf6917446513e02617217c86d` |

The two vehicle indexes contain **45,215 VAG-group approval rows** in the 2026-10-29 CH snapshot:

- Passenger cars: Audi 14,510; Bentley 286; Bugatti 9; Cupra 222; Lamborghini 263; Porsche 1,374; Seat 3,443; Skoda 4,101; VW 13,696 — total 37,904.
- Other automobile groups: Lamborghini 124; Seat 12; Skoda 15; VW 7,160 — total 7,311.

These are Swiss type-approval rows, not Russian/EAEU vehicle counts or individual-vehicle fitments. Make names are exact source labels; `VW` is preserved as `VW`, not silently rewritten to `Volkswagen`.

The emissions workbook schema exposes `chTypeApprovalNumber`, `makeName`, `gearboxNumber`, `chGearboxType`, `chMapping` and `versionDefined`. It contains one row per gearbox/emissions variant. The official type-approval JSON exposes the same gearbox classification under `gearboxEmissionsN.chGearboxType` and its `versionDefined` scope.

The six sample CUPRA JSON records all have `version="*"`, while `gearboxEmissionsN.versionDefined` contains the composite raw `variant/version` scope (for example, approval 1XZ904 has `variant="CXDNPAX0"` and `versionDefined="CXDNPAX0/*"`). The trailing `*` is a wildcard version, not an exact version. The importer must compare the complete composite string and preserve the wildcard as approval/variant-wide scope.

The emissions data does not expose a VAG factory gearbox code in the reviewed schema. `chGearboxType` and `chMapping` are Swiss approval/emissions classifications and must remain separate from any future VAG gearbox-code field. The index's `engineType` remains an official engine-type designation; `chEngineCodeAsMarkedOnTheEngine` remains a separate stamped marking and can differ (e.g. DNPA vs DNP).


## Exact variant/version scope-link correction (2026-11-06)

A review of the pinned official JSON sample values exposed a linker defect in the first research-pack build: the builder compared gearboxEmissionsN.versionDefined to the approval's version field alone. The official source stores the emissions-row scope as the composite variant/version string. For example, approval 1XZ904 has variant=CXDNPAX0, version=*, and gearboxEmissions1.versionDefined=CXDNPAX0/*. The prior comparison could not match this correctly.

The corrected linker now requires all of the following:
1. a unique approval record for the same chTypeApprovalNumber + makeName;
2. exact string equality between versionDefined and that approval's raw variant + "/" + version;
3. the emissions row's chGearboxType must be explicitly present in the same approval record's gearboxEmissionsN.chGearboxType list.

On the pinned 2026-10-29 snapshot, this yields 5,420 exact variant/version rows, 28,489 variant-wide rows where the version is *, and 19,505 unlinked rows. The unlinked rows remain unlinked; no fuzzy matching or model-name inference is used. These links remain CH type-approval-scope associations only. They do not establish VAG factory gearbox codes, individual-vehicle fitment, Russian/EAEU applicability or repair applicability.

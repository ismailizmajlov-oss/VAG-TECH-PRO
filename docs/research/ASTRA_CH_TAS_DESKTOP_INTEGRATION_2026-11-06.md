# ASTRA / FEDRO CH type-approval research pack in desktop

Reviewed: 2026-11-06

## Purpose

The desktop application may ship the separately licensed ASTRA / FEDRO Type Approval System (TAS) research pack as an offline, read-only reference. This is a Swiss (CH) type-approval dataset. It is not Russian or EAEU OTTS, not a VAG factory vehicle-configuration catalogue, and not repair documentation.

## Rights and attribution

The source manifest is `data/source-manifests/astra-ch-tas-open-data.json`. The reviewed FEDRO notice dated 2026-02-23 permits OGD reuse, including commercial use, display, offline caching, bulk reuse and redistribution, subject to attribution. No SPDX identifier is assigned by the publisher. The application must display:

> Source: Federal Roads Office (FEDRO/ASTRA), Type Approval System (TAS) open data.

Evidence: https://opendata.astra.admin.ch/ivzod/5000-Newsletter/2026_1/Newsletter_Fahrzeugdaten_1_2026_EN.pdf

## Data boundary

- Market scope is exactly `CH`.
- The pack is stored in its own SQLite database and its own research namespace.
- It is not imported into production vehicle fitment, OEM catalog, engine-code or gearbox-code tables.
- `engineTypeDesignation` is the official designation carried by the type-approval record. It is not automatically a VAG factory engine code.
- `stampedEngineMarking` is kept separately from the approval designation.
- `chGearboxType` and `chMapping` are Swiss type-approval classifications, not VAG gearbox codes.
- A relation marked `approval_version_exact` is exact only within the approval's variant/version scope.
- A relation marked `approval_variant_wildcard` is variant-wide and does not prove exact version applicability.
- Unlinked emissions/gearbox rows remain unlinked. The integration never guesses a relation.
- The pack contains no DTC, ECU, VIN fitment, model-year, repair procedure, wiring diagram, pinout, torque, adaptation or service-interval claims.

## Desktop integration checks

The Windows desktop workflow downloads the latest successful pack artifact, checks the pack manifest, source manifest, rights notice, attribution, SHA-256 values, SQLite integrity, foreign keys, row counts, CH-only scope and the zero-factory-fitment flags. It copies the pack into `resources/research-data`, registers it in the desktop research manifest and exposes a read-only search tab.

The installer lifecycle must query the ASTRA summary and a pinned sample search with external network access blocked. The first and upgrade NSIS builds must both verify the packaged pack. The search UI must preserve the source revision and record/database/manifest hashes on each result.

## Pinned snapshot

The current reviewed pack is based on source snapshot revision `2026-10-29`. Its manifest is the authority for current row counts; code compares database counts against the pack manifest instead of hard-coding a count that would break on the next legitimate source refresh.


## ASTRA TARGA per-gearbox pack refresh — run 16, 2026-11-07

The latest official-source acquisition and SQLite build completed successfully in [Windows workflow run 16](https://github.com/ismailizmajlov-oss/VAG-TECH-PRO/actions/runs/42388349228), using the unchanged 2026-07-30 source file revision. The exact 70,829,020-byte source file remains SHA-256 `a11c1727440d6d587a1bd0b37eaeb011afc050b8f356ef746fdd6e18898fdd92`.

- 280,993 source rows scanned; 53,240 exact VAG-make rows retained; zero malformed rows.
- 53,240 source-defined approval/gearbox-variant rows; **zero** exact VAG factory engine/gearbox code pairs.
- Zero exact vehicle-fitment rows and zero RU/EAEU applicability rows.
- SQLite `integrity_check=ok`; no foreign-key violations.
- Database SHA-256: `408980e7a8923223b5f7f4fe5120be961b65317d8e96abb25e2b9e4965ccd926` (28,864,512 bytes).
- Inner research-pack archive SHA-256: `5bf0a552cfc057b52c66640db36d6c671e9994a613f4c6d7b5d296948be33be3` (5,683,005 bytes).
- Pack manifest SHA-256: `6699777df7619ad9394d52471b2b34c494b0089fac46d55c260a7a9a2ff5506c`.
- Outer CI artifact ID `13580905833`, 11,229,081 bytes, SHA-256 `fac173f744dcd5d7acb47702371771d684034c8a5141251ec1eb685dfe71d51c`.

The per-gearbox source row is a source-defined CH approval variant link. Engine designation and gearbox classification remain raw source fields; they are not promoted to a confirmed VAG factory code pair. The pack is research-only, separately namespaced, attribution-required and not imported into production fitment or RU/EAEU data. The subsequent desktop CI run resolves the latest successful pack at build time; integration is only claimed after that Windows installer lifecycle succeeds.


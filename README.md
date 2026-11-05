# VAG TECH PRO

Non-commercial VAG repair-workflow and technical-data project, Russian market first. The first desktop delivery target is **Windows 10/11 x64 only**.

## Product and desktop architecture

The desktop application uses Electron with a local Next.js runtime and a per-user SQLite database. Manual vehicle selection does not require a VIN. The local workspace includes a garage, query history, bookmarks, and local source/import administration.

The SQLite catalog schema covers:

- VAG brands, models, generations, factory engine and transmission identities, explicit engine/transmission pairs, ECU identities and vehicle configurations;
- separate generic SAE/ISO DTC and VAG-specific DTC namespaces;
- diagnostic test plans, repair procedures, wiring diagrams, pinouts, torque specifications, adaptations and service intervals;
- OEM parts and supersession relationships;
- immutable source snapshots, source revisions, SHA-256 evidence, market scope, applicability precision, review states and import audit records.

The technical schema and desktop workflows exist, but the presence of a table or screen does **not** mean that its technical content is populated or approved. User-owned garage/history/bookmark data is stored separately from imported technical catalog data.

## Evidence and safety rules

- Generic SAE/ISO OBD-II records are never represented as VAG-specific.
- Community signals, model labels, generation links and manufacturer-labelled DTC candidates remain research candidates until their provenance and applicability are independently verified.
- Engine codes, gearbox codes, ECU identities and exact pairings are never inferred from descriptive engine labels or model-year overlap.
- Critical repair and diagnostic records require source revision, rights evidence, market, model/generation/year, exact engine/transmission/ECU relationships, applicability precision and technical review.
- Import packages are hash-checked and rights-gated before a transaction commits. Revisions are retained; user vehicles are not overwritten by catalog imports.
- Backups are integrity-checked, restore keeps a safety copy of the current database, and uninstall must preserve the per-user database.
- No leaked, access-controlled or OEM-derived data with unresolved rights is imported, displayed, cached or redistributed.

## Licensed research packs — research only, not repair authorization

The current research snapshots contain useful public data, but none of the following counts is a count of verified VAG repair records:

| Pack | Snapshot contents | License and boundary |
|---|---:|---|
| OBDex generic reference | 9,533 generic DTC identifiers and 132 generic OBD-II PIDs | CC0-1.0 for upstream data files; generic SAE/ISO only, no VAG fitment |
| VehiclesDB identity | 260 model candidates and 1,524 market-evidence rows | CC BY 4.0; model identity candidates, not factory engine/gearbox codes |
| OBDb signal research | 2,315 command candidates, 2,480 signal candidates, 15 ECU candidates and 32 generation candidates | CC BY-SA 4.0; community signal research, not OEM-confirmed fitment |
| Wikidata model taxonomy | 376 model entities, including 171 Russian labels | CC0-1.0; candidate identity only, market UNKNOWN |
| Wikidata series membership | 9 member entities, 10 model/member links and 14 source bindings | CC0-1.0; series-member candidates, not verified generations or year ranges |
| MechanicDB generic guidance | 275 generic guidance rows and 75 generic SAE DTC references | ODbL-1.0; generic educational reference only, no VAG or exact-vehicle applicability |
| AutoDiag2 VAG community candidates | 110 model candidates, 259 version candidates, 1,083 unverified engine fields, 179 ECU candidates and 3,170 configuration candidates; 956 unattributed make-level DTC rows excluded, 0 retained | ODbL-1.0 / DbCL-1.0; separate read-only research pack, market UNKNOWN; no verified engine codes, transmission records or exact fitment |
| MechanicDB manufacturer-labelled DTC candidates | 2 rows | ODbL-1.0; quarantined from normal DTC lookup pending technical review; not OEM-confirmed |
| ASTRA / FEDRO Swiss TAS VAG research | 45,215 VAG-group type-approval index rows and 53,414 emissions/gearbox rows in the 2026-10-29 source snapshot; 5,420 exact variant/version links, 28,489 wildcard-scope links, 19,505 unlinked | Swiss OGD with FEDRO attribution; separate CH-only research namespace; `engineType` and stamped marking stay distinct; `chGearboxType` is not a VAG gearbox code; no RU/EAEU or repair fitment |

Each pack remains in its own namespace with its own manifest, attribution/license material, source revision and hashes. Share-Alike obligations are retained. Generic DTC and generic repair guidance are not linked to a VAG configuration or ECU.

## Production-data status — 2026-11-06

**VAG TECH PRO is not yet a professional repair database or a release candidate.**

No verified Russian/EAEU OTTS records have been imported. No rights-cleared dataset currently supplies exact Russian/EAEU factory engine/gearbox pairs with market and production-year scope. No OEM-approved VAG-specific DTC/ECU test-plan corpus or rights-cleared repair procedures, wiring diagrams, pinouts, torque values, adaptations, service schedules or OEM parts catalog is populated in the production technical catalog.

The OpenVAG DTC project (995 publisher-claimed code/title rows) was reviewed on 2026-11-05 and quarantined: the MIT software licence does not establish the provenance or reuse rights of its unversioned, gitignored database; no row-level sources or reproducible seed process were found. See the [OpenVAG DTC rights review](docs/research/OPENVAG_DTC_SOURCE_RIGHTS_REVIEW_2026-11-05.md).

The commercial OTTS.BOT aggregator was also reviewed on 2026-11-05 and quarantined: its published terms prohibit automated collection beyond ordinary use and redistribution of database information as a proprietary product; advertised downloads/subscriptions were not used. See the [OTTS.BOT rights review](docs/research/OTTS_BOT_SOURCE_RIGHTS_REVIEW_2026-11-05.md).

The EAEU register has a legal public-query basis, but the reviewed open-data catalogue did not identify an OTTS-specific OData/REST resource. Public query visibility does not grant bulk extraction, offline caching or redistribution rights. The official Russian FGIS registry information describes access software for accredited certification bodies and testing laboratories; it does not establish a general public bulk-export license. Commercial aggregators and subscription APIs are not used as bulk sources.

The current source register records the EAEU, Rosstandart/Interstandart, ELPTS, Audatex, VAG-Wiki and aggregator access/rights boundaries. VAG-Wiki was reviewed on 2026-11-05 and quarantined: its Terms of Service (Legal Revision 2026.01) prohibit unauthorized mass scraping, automated extraction and redistribution; no dataset-specific license or written permission for offline product use was found. It is explicitly excluded from Windows offline packs. See the [VAG-Wiki rights review](docs/research/VAG_WIKI_SOURCE_RIGHTS_REVIEW_2026-11-05.md), [machine-readable source register](data/source-manifests/vag-factory-source-register.json) and [owner-controlled source approval procedure](docs/OWNER_SOURCE_RIGHTS_APPROVAL.md). Autoevolution-derived ODbL candidates, uncleared manufacturer DTC CSVs and ODIS MCD-derived community material remain excluded or quarantined.

## Windows build and verification

The desktop source is stored as a SHA-256-pinned source payload plus deterministic patches and is assembled by [the Windows x64 CI workflow](.github/workflows/windows-desktop-ci-run71.yml). The pipeline is configured to build two NSIS x64 installers (0.2.3 and 0.2.4), validate the packaged offline research resources, and test clean install, offline launch, backup/restore, in-place upgrade and uninstall preservation. A separate Windows Server 2022 lifecycle job checks compatibility. A workflow-run recorder is configured to write `ci-status/latest-windows-run.json` after each completed run; the record is evidence only after that file exists and contains a completed run. A workflow definition alone is not evidence that a run passed.

The latest recorded Windows x64 validation run, [run 161 / 42100737036](https://github.com/ismailizmajlov-oss/VAG-TECH-PRO/actions/runs/42100737036), completed successfully on 2026-11-05 for source commit `854410281eefcc3a02bcad80ed2845acab66fc12`. The build-and-lifecycle job passed desktop/local-core/research tests, ESLint, TypeScript, assembly and verification of the pinned desktop source, independent offline research-pack checks, and both NSIS x64 installer builds (0.2.3 clean-install baseline and 0.2.4 in-place upgrade). The lifecycle step passed clean installation, external-network-blocked offline launch, SQLite backup/restore, in-place upgrade, integrity checks and uninstall preservation. A separate Windows Server 2022 compatibility job also passed the installer lifecycle.

Recorded run artifacts (GitHub artifact API SHA-256 digests):
- `vag-tech-pro-windows-x64-run70`: 532,121,844 bytes; artifact ZIP SHA-256 `4cc2b4f61fa6bdc514e160503f48624e0e43d2183ca80452d306121aa1047653`.
- `vag-tech-pro-windows-2022-lifecycle-run70`: 3,761 bytes; artifact ZIP SHA-256 `58d577612f608ef33446ca30537ce69694a3b6c12d1758c0dec2109711d39053`.
- `vag-tech-pro-vehiclesdb-schema-diagnostic`: 24,437 bytes; artifact ZIP SHA-256 `61244b4303453f01d2ddc9f1ea3835ed1d73c9c65e9cc10dcf61d6bf552364e3`.

The run status is recorded in [`ci-status/latest-windows-run.json`](ci-status/latest-windows-run.json), with upstream run ID, source SHA, job conclusions, artifact IDs/digests, and native-client gate state. This is CI evidence, not a public release; `release_ready=false`. The source commit tested by run 161 is the parent of the status-record commit on `main`; the status-only commit does not change the tested desktop source. Subsequent main-branch commits add source-rights metadata and tests for the quarantined Automotive-9 candidate, the Wal33D dataset's MIT/provenance and generic-vs-manufacturer namespace boundary, and the official VW Group Info Services OEM ODX source's contractual access restrictions. No rows from the newly reviewed/quarantined sources enter any SQLite pack. These source-register/documentation/test changes are newer than run 161 and must pass the source-rights workflow and be included in the next Windows build before a new installer is considered current.

The run 161 build log explicitly reports that no code-signing certificate was configured and signing was skipped for the application, uninstaller and NSIS installer. The generated EXE is therefore unsigned; a production distribution still needs an owner-provided Windows code-signing certificate and protected signing workflow (or an explicit owner decision to accept unsigned distribution).

This is Windows-hosted CI and Windows Server 2022 evidence, **not a native Windows 10/11 client test**. The separate native Windows 10/11 workflow was skipped because the owner-controlled runner gate is disabled and no owner-provided isolated Windows 10/11 x64 runner is registered. Required labels are `self-hosted`, `windows`, `x64`, `vag-tech-pro-win10-11`; the owner must also set `VAG_TECH_PRO_WIN10_11_RUNNER_AVAILABLE=true`. No runner or external account is created by the project.

Installer code signing was skipped because no signing certificate is configured. The installers remain CI artifacts, not a public release. No paid signing service or certificate has been acquired.

## Release blockers

1. Written source-owner permission or an explicit dataset license covering commercial use, display, offline caching, bulk reuse and redistribution for Russian/EAEU OTTS data.
2. Independent, rights-cleared factory evidence for exact model/generation/year, engine code, gearbox code, engine/gearbox pairing, market and ECU applicability.
3. Licensed VAG-specific DTC definitions, ECU identities and diagnostic test plans.
4. Licensed and technically reviewed repair procedures, wiring diagrams, pinouts, torque values, adaptations, service schedules and OEM parts/applicability data.
5. A successful native Windows 10/11 x64 lifecycle run on an owner-provided isolated client runner.
6. An owner-supplied code-signing certificate if signed public distribution is required.

Until the data and native-platform blockers are cleared, the application must not be described as a ready professional repair database. The generic and candidate research packs are supplementary references only.

## Historical research and schemas

- [OBDex generic acquisition report](docs/research/OBDEX_RUN_2026-11-02.md)
- [VAG factory source access review](docs/research/VAG_FACTORY_SOURCE_ACCESS_REVIEW_2026-11-03.md)
- [VIN-free vehicle catalog schema](data/sql/vehicle-catalog.sql)
- [VIN-free catalog design note](docs/research/VIN_FREE_VEHICLE_CATALOG_SCHEMA.md)
- [VAG open engine candidate review](docs/research/VAG_OPEN_ENGINE_CANDIDATES_2026-11-03.md)
- [Wikidata VAG taxonomy review](docs/research/WIKIDATA_VAG_TAXONOMY_REVIEW_2026-11-04.md)
- [Local catalog import v2 contract](docs/LOCAL_CATALOG_IMPORT_V2.md)
- [Owner-controlled source rights approval](docs/OWNER_SOURCE_RIGHTS_APPROVAL.md)

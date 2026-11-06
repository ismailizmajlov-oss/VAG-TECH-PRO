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
| Wikidata model taxonomy | 521 candidate entities (490 car-model class; 40 model-series class), 285 Russian labels, 530 source bindings | CC0-1.0; candidate identity only, market UNKNOWN |
| Wikidata series membership | 109 member entities, 125 model/member links, 187 source bindings; 32 parent models, 83 Russian labels, 155 raw date statements | CC0-1.0; series-member candidates, not verified generations or year ranges |
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

EEC Decision No. 225 establishes publication of national register parts on official sites and requests for registry information to authorized bodies; Decision No. 88 defines intergovernmental technical-exchange documents and the registry schema, not the public-access or data-reuse license. The reviewed EAEU open-data catalogue did not identify an OTTS-specific OData/REST resource. Public query visibility does not grant bulk extraction, offline caching or redistribution rights. The official Russian FGIS registry information describes access software for accredited certification bodies and testing laboratories; it does not establish a general public bulk-export license. Commercial aggregators and subscription APIs are not used as bulk sources.

The current central source register contains 43 entries and the Russian/EAEU register contains 11 sources; both retain explicit access, rights, market and import boundaries. The current source register records the EAEU, Rosstandart/Interstandart, ELPTS, Audatex, VAG-Wiki and aggregator access/rights boundaries. VAG-Wiki was reviewed on 2026-11-05 and quarantined: its Terms of Service (Legal Revision 2026.01) prohibit unauthorized mass scraping, automated extraction and redistribution; no dataset-specific license or written permission for offline product use was found. It is explicitly excluded from Windows offline packs. See the [VAG-Wiki rights review](docs/research/VAG_WIKI_SOURCE_RIGHTS_REVIEW_2026-11-05.md), [machine-readable source register](data/source-manifests/vag-factory-source-register.json) and [owner-controlled source approval procedure](docs/OWNER_SOURCE_RIGHTS_APPROVAL.md). Autoevolution-derived ODbL candidates, uncleared manufacturer DTC CSVs and ODIS MCD-derived community material remain excluded or quarantined.

## Windows build and verification

The desktop source is stored as a SHA-256-pinned source payload plus deterministic patches and is assembled by [the Windows x64 CI workflow](.github/workflows/windows-desktop-ci-run71.yml). The pipeline is configured to build two NSIS x64 installers (0.2.3 and 0.2.4), validate the packaged offline research resources, and test clean install, offline launch, backup/restore, in-place upgrade and uninstall preservation. A separate Windows Server 2022 lifecycle job checks compatibility. A workflow-run recorder is configured to write `ci-status/latest-windows-run.json` after each completed run; the record is evidence only after that file exists and contains a completed run. A workflow definition alone is not evidence that a run passed.

The latest completed successful Windows x64 validation run is [run 240 / 42166095994](https://github.com/ismailizmajlov-oss/VAG-TECH-PRO/actions/runs/42166095994), completed on 2026-11-06 for source commit `9b86c35eaa47e776f3595f5b458a7629c27fdb29`. Both the Windows build-and-lifecycle job and the separate Windows Server 2022 lifecycle job passed. The run assembled the pinned desktop source, synchronized the central source-rights register into desktop staging, passed offline data-pack rights checks, EAEU manifest/importer tests, desktop/local-core/research tests, ESLint and TypeScript, and built NSIS x64 installers 0.2.3 and 0.2.4. The external-network-blocked lifecycle passed clean install, offline launch, SQLite backup/restore, in-place upgrade, integrity checks and uninstall preservation.

The run 240 build metadata records:
- Installer 0.2.3: 254,992,901 bytes; SHA-256 `e04645f94e9a6dba74687f1fb4628e04392383b39e701ef7d3f253e0084142d6`.
- Installer 0.2.4: 254,992,697 bytes; SHA-256 `06823af456743b2e96da2246d8c09c135315f5bd7247211f207e1f2c7851ea9c`.
- Source archive SHA-256: `e041ce167f083192a11f4b86b19e7bbc51fe8a1bb8e732a0d2944229af713216`.
- Packaged source register: SHA-256 `2e6ca97907d2030a857b0353366074ca19fdf7babcf6daab4cb1d7a4bc7cbd2a`, 41 entries.
- Packaged source-manifest index: SHA-256 `d463f8764d854d20f26408d9083ce093550701361e83f4a8506df7600972b35d`, 13 manifests.
- Packaged Russian/EAEU OTTS manifest: SHA-256 `b24e26624434d8e1b9a14df3ae1aa937986843feab42709b4c6ccbd0f5c18c8d`, 11 sources.
- Technical payload schema SHA-256: `e11a4a2fe9cdf7705ed13d1bf773b574e6c57306c10a06885ca8f6568e4b010a`.

The package manifest maps `data/source-manifests` to the packaged `resources/source-manifests` directory and runs an `afterPack` verifier. Run 240 verified the packaged source register at SHA-256 `2e6ca97907d2030a857b0353366074ca19fdf7babcf6daab4cb1d7a4bc7cbd2a` with 41 entries and the Russian/EAEU manifest at 11 sources. The current `main` source register has 43 entries and the Russian/EAEU manifest still has 11 sources but a newer content hash; these later source-rights and manifest changes are not covered by run 240. Runs 241, 242 and 243 were cancelled before jobs or artifacts were created. Run 240 remains the latest completed successful validation, but it does not validate the current `main`; a new successful build is required.

The run status is recorded in [`ci-status/latest-windows-run.json`](ci-status/latest-windows-run.json). This is CI evidence, not a public release; `release_ready=false`. The source register remains provenance metadata, not proof that technical records from its sources are reusable. No rows from newly reviewed or quarantined sources are promoted into a production VAG fitment or repair database.

Run 240 pinned the root `minimatch` dependency to 11.0.1, verified the installed dependency tree against the lockfile, and both production-only and full `npm audit` reported zero vulnerabilities. Deprecated transitive-package warnings remain non-blocking maintenance items.

Run 240 reports that no code-signing certificate was configured; signing was skipped for the application, uninstaller and NSIS installers. The generated EXEs are unsigned; public distribution still needs an owner-provided Windows code-signing certificate and protected signing workflow (or an explicit owner decision to accept unsigned distribution).

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

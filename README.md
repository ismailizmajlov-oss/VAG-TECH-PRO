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

The Open Vehicle Schema (OVS) repository was reviewed on 2026-11-06 as a possible open vehicle-identity taxonomy. At pinned commit `d7223f3edfe4adcebf22d3ffa7a60599ae25016c`, all four reference arrays (`vehicles.json`, `engines.json`, `transmissions.json`, `bodies.json`) are empty five-byte JSON files; no populated release or row-level upstream provenance was found. A root MIT license exists, but no separate data license or explicit data-file scope was identified. The source is registered but excluded from all packs; no data was imported. See [the OVS source review](docs/research/OPEN_VEHICLE_SCHEMA_SOURCE_REVIEW_2026-11-06.md).

The commercial OTTS.BOT aggregator was also reviewed on 2026-11-05 and quarantined: its published terms prohibit automated collection beyond ordinary use and redistribution of database information as a proprietary product; advertised downloads/subscriptions were not used. See the [OTTS.BOT rights review](docs/research/OTTS_BOT_SOURCE_RIGHTS_REVIEW_2026-11-05.md).

EEC Decision No. 225 establishes publication of national register parts on official sites and requests for registry information to authorized bodies; Decision No. 88 defines intergovernmental technical-exchange documents and the registry schema, not the public-access or data-reuse license. The reviewed EAEU open-data catalogue did not identify an OTTS-specific OData/REST resource. Public query visibility does not grant bulk extraction, offline caching or redistribution rights. The official Russian FGIS registry information describes access software for accredited certification bodies and testing laboratories; it does not establish a general public bulk-export license. Commercial aggregators and subscription APIs are not used as bulk sources.

An ELPTS operator notice dated 2026-08-21 says an internal AS EOTTS data-entry issue involving additional-reduction and hydraulic transmissions was fixed. This is evidence about an internal entry workflow only: it does not expose a public Annex 2 gearbox field, identify an exact internal schema or factory gearbox code, or grant extraction/cache/display/redistribution rights. The ELPTS source remains permission-required and no records were imported. See [the ELPTS gearbox-entry notice review](docs/research/ELPTS_AS_EOTTS_GEARBOX_ENTRY_NOTICE_2026-11-06.md).

A separate Rosstandart recall-campaign open-data source has been identified at easy.gost.ru. Historical public statements describe the register as open data for non-commercial services, and a 2023 webinar report describes reuse by business services. The current official dataset page and archive timed out during review on 2026-11-06. A separate metadata-only Windows CI probe [run 5](https://github.com/ismailizmajlov-oss/VAG-TECH-PRO/actions/runs/42205049421) also failed to connect to both official URLs (WinError 10060); it downloaded no data file and found no current file or terms link. The current file schema and dataset-linked terms were therefore not retrieved. It is registered as a high-priority RU candidate only: no VIN rows, repair-completion/dealer fields or campaign text have been imported, and no snapshot hash is claimed. Recall remedy text must not be represented as a factory workshop procedure. See [the Rosstandart recall-campaign rights review](docs/research/ROSSTANDART_RECALL_CAMPAIGNS_OPEN_DATA_REVIEW_2026-11-06.md).

The current central source register contains 46 entries and the Russian/EAEU register contains 11 sources; both retain explicit access, rights, market and import boundaries. The current source register records the EAEU, Rosstandart/Interstandart, ELPTS, Audatex, VAG-Wiki and aggregator access/rights boundaries. VAG-Wiki was reviewed on 2026-11-05 and quarantined: its Terms of Service (Legal Revision 2026.01) prohibit unauthorized mass scraping, automated extraction and redistribution; no dataset-specific license or written permission for offline product use was found. It is explicitly excluded from Windows offline packs. See the [VAG-Wiki rights review](docs/research/VAG_WIKI_SOURCE_RIGHTS_REVIEW_2026-11-05.md), [machine-readable source register](data/source-manifests/vag-factory-source-register.json) and [owner-controlled source approval procedure](docs/OWNER_SOURCE_RIGHTS_APPROVAL.md). Autoevolution-derived ODbL candidates, uncleared manufacturer DTC CSVs and ODIS MCD-derived community material remain excluded or quarantined.

## Windows build and verification

The desktop source is stored as a SHA-256-pinned source payload plus deterministic patches and is assembled by [the Windows x64 CI workflow](.github/workflows/windows-desktop-ci-run71.yml). The pipeline builds two NSIS x64 installers, validates packaged offline research resources and source manifests, and runs clean install, external-network-blocked offline launch, backup/restore, in-place upgrade, integrity and uninstall-preservation checks. A separate Windows Server 2022 lifecycle job checks compatibility. The workflow-run recorder writes `ci-status/latest-windows-run.json`; that record is evidence only for the exact commit and run it names.

The latest completed successful Windows x64 validation is [run 299 / 42204474154](https://github.com/ismailizmajlov-oss/VAG-TECH-PRO/actions/runs/42204474154), completed on 2026-11-06 for source commit `811c329ff808b62a06ffdb5789997a1290b35b4b`. Both the main `build-and-lifecycle` job and the separate Windows Server 2022 compatibility lifecycle job passed. The run assembled the pinned source and research packs, passed source-rights and package-integrity gates, desktop/local-core/research tests, ESLint and TypeScript, built NSIS x64 installers 0.2.3 and 0.2.4, verified packaged source manifests and technical-library schemas, and passed clean install, external-network-blocked offline launch, SQLite backup/restore, in-place upgrade, integrity and uninstall-preservation checks.

The run 299 build metadata records:
- Installer 0.2.3: 268,678,807 bytes; SHA-256 `87bef2d9c358fa5bd5f1f06114bfaba8d0a69e0752fe9254eff3b3e23ae3cf42`.
- Installer 0.2.4: 268,678,636 bytes; SHA-256 `a9b5499e9b8f6fe3fcd3df1dbeee0b3663f90316f18a73a968cd340cbf4742d8`.
- Source archive SHA-256: `e041ce167f083192a11f4b86b19e7bbc51fe8a1bb8e732a0d2944229af713216`.
- Packaged central source register: SHA-256 `ea1a6f1274e83d6ee90c478637c186cf8532b60c299fcbb1ee329646c14c7f4b`, 45 entries.
- Packaged source-manifest index: SHA-256 `c9c5ad227fcaf7f3c73ba07618c467eaa7eaf152c13e872f69879eebc3316e82`, 14 manifests.
- Packaged Russian/EAEU OTTS manifest: SHA-256 `e2bdbf05d25d7526409121220d0e132421b6c67f41a24ff1a085eaa2179bd5d9`, 11 sources.
- Vehicle catalog SQL SHA-256: `0406352d5664fc8aa5450aada0ed7acbc2a23f0b8287795808f73485031ff8f3`.
- OEM DTC index SQL SHA-256: `40eda7222d5d2ff61ee6867a93eea28f2b0830317243d4aaaf66e50ab92ab88e`.
- DTC/catalog links SQL SHA-256: `8d024b9d717b751b94d996c9170080c697ccaaf145f17481f9059734cf326ba7`.
- Technical library SQL SHA-256: `8306bf559c3b745975305ea4e264bc1df621621cce70efa710a00c35f979c2f2`.
- Technical payload schema SHA-256: `e11a4a2fe9cdf7705ed13d1bf773b574e6c57306c10a06885ca8f6568e4b010a`.

Run 299 predates the Open Vehicle Schema source review. The current repository central register now contains 46 entries; run 299 packaged the previous 45-entry revision. The Russian/EAEU register remains at 11 sources. The OVS candidate is recorded as excluded and not ingested; no populated data or source snapshot is claimed. A subsequent Windows CI run must package and verify the 46-entry register before that revision is considered desktop-validated.

The run 299 hashes above identify the exact packaged artifacts and source files for that run. They do not grant reuse rights or establish that registered sources contain populated, approved repair records. The current source registers remain rights/provenance metadata; no permission-required or quarantined source has been promoted into the production technical catalog.

The run status is recorded in [`ci-status/latest-windows-run.json`](ci-status/latest-windows-run.json). This is CI evidence, not a public release; `release_ready=false`. The generated EXEs are unsigned because no owner-supplied code-signing certificate is configured. They remain CI artifacts and have not been published as a release.

Run 299 used Windows-hosted CI and a separate Windows Server 2022 lifecycle runner. This is **not a native Windows 10/11 client test**. The actual `Windows 10/11 x64 clean install and data-preservation lifecycle` job remains `skipped`; the owner-controlled runner gate is disabled and no owner-provided isolated Windows 10/11 x64 runner is registered. Required labels are `self-hosted`, `windows`, `x64`, `vag-tech-pro-win10-11`; the owner must also set `VAG_TECH_PRO_WIN10_11_RUNNER_AVAILABLE=true`. No runner or external account is created by the project.

A previous dependency audit in run 240 reported zero vulnerabilities for production-only and full dependency trees; run 299 did not repeat that audit. Deprecated transitive-package and GitHub Actions Node.js compatibility warnings remain maintenance items.

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
- [Open Vehicle Schema source review](docs/research/OPEN_VEHICLE_SCHEMA_SOURCE_REVIEW_2026-11-06.md)
- [Local catalog import v2 contract](docs/LOCAL_CATALOG_IMPORT_V2.md)
- [Owner-controlled source rights approval](docs/OWNER_SOURCE_RIGHTS_APPROVAL.md)

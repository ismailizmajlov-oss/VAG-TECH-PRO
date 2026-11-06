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

The current central source register contains 47 entries and the Russian/EAEU register contains 11 sources; both retain explicit access, rights, market and import boundaries. The current source register records the EAEU, Rosstandart/Interstandart, ELPTS, Audatex, VAG-Wiki and aggregator access/rights boundaries. VAG-Wiki was reviewed on 2026-11-05 and quarantined: its Terms of Service (Legal Revision 2026.01) prohibit unauthorized mass scraping, automated extraction and redistribution; no dataset-specific license or written permission for offline product use was found. It is explicitly excluded from Windows offline packs. See the [VAG-Wiki rights review](docs/research/VAG_WIKI_SOURCE_RIGHTS_REVIEW_2026-11-05.md), [machine-readable source register](data/source-manifests/vag-factory-source-register.json) and [owner-controlled source approval procedure](docs/OWNER_SOURCE_RIGHTS_APPROVAL.md). Autoevolution-derived ODbL candidates, uncleared manufacturer DTC CSVs and ODIS MCD-derived community material remain excluded or quarantined.

## Windows build and verification

The desktop source is stored as a SHA-256-pinned source payload plus deterministic patches and is assembled by [the Windows x64 CI workflow](.github/workflows/windows-desktop-ci-run71.yml). The pipeline builds two NSIS x64 installers, validates packaged offline research resources and source manifests, and runs clean install, external-network-blocked offline launch, backup/restore, in-place upgrade, integrity and uninstall-preservation checks. A separate Windows Server 2022 lifecycle job checks compatibility. The workflow-run recorder writes `ci-status/latest-windows-run.json`; that record is evidence only for the exact commit and run it names.

The latest completed successful Windows x64 validation is [run 302 / 42226340981](https://github.com/ismailizmajlov-oss/VAG-TECH-PRO/actions/runs/42226340981), completed on 2026-11-06 for source commit `9cfba4f5dad6dcb4ba5addbdc7e2e2f107ad89f4`. Both the main `build-and-lifecycle` job and the separate Windows Server 2022 compatibility lifecycle job passed. Run 302 assembled the pinned desktop source and current research packs, passed source-rights and package-integrity gates, desktop/local-core/research tests, ESLint and TypeScript, built NSIS x64 installers 0.2.3 and 0.2.4, verified the packaged source manifests and technical-library schemas, and passed clean install, external-network-blocked offline launch, SQLite backup/restore, in-place upgrade, integrity and uninstall-preservation checks. The source commit included the 47-entry central source register and 11-entry Russian/EAEU register. Run 302 did not run the native Windows 10/11 client lifecycle; that job remained skipped.

The run 300 build metadata records historical installer and source-payload hashes for the earlier 46-entry revision:
- Installer 0.2.3: 268,680,243 bytes; SHA-256 `586c2d695e90070a6169a64800593e52cf2b3013664db222c94a7bc26bc4c24f`.
- Installer 0.2.4: 268,680,202 bytes; SHA-256 `65e3946051cf51432c325516d1b1e94f44a20ce3d94eb949cbf616262231a8e9`.
- Source archive SHA-256: `e041ce167f083192a11f4b86b19e7bbc51fe8a1bb8e732a0d2944229af713216`.
- Packaged central source register: SHA-256 `cb0141bd9401620fa150ea00cfc29cba9ebbe33ca24c735e70dc29b5e2e0be51`, 46 entries.
- Packaged source-manifest index: SHA-256 `0547281c8431f7699a7396aaf3204f5d172a8da7d943405d8252d72eb79cb84e`, 14 manifests.
- Packaged Russian/EAEU OTTS manifest: SHA-256 `e2bdbf05d25d7526409121220d0e132421b6c67f41a24ff1a085eaa2179bd5d9`, 11 sources.
- Combined offline research-pack bundle: SHA-256 `659d8a98b543a7e965136cee5ad229264bd647e9d6c258cef27c87161dab3d5c`.
- Vehicle catalog SQL SHA-256: `0406352d5664fc8aa5450aada0ed7acbc2a23f0b8287795808f73485031ff8f3`.
- OEM DTC index SQL SHA-256: `40eda7222d5d2ff61ee6867a93eea28f2b0830317243d4aaaf66e50ab92ab88e`.
- DTC/catalog links SQL SHA-256: `8d024b9d717b751b94d996c9170080c697ccaaf145f17481f9059734cf326ba7`.
- Technical library SQL SHA-256: `8306bf559c3b745975305ea4e264bc1df621621cce70efa710a00c35f979c2f2`.
- Technical payload schema SHA-256: `e11a4a2fe9cdf7705ed13d1bf773b574e6c57306c10a06885ca8f6568e4b010a`.

Run 300 is the first completed Windows x64 build that packaged the 46-entry central source register at that time, including the Open Vehicle Schema review entry. That source remains excluded and not ingested: its four pinned reference arrays are empty, with no populated data or source snapshot claimed. The Russian/EAEU register remains at 11 sources. The packaged manifests and hashes prove the exact files included in this CI build; they do not grant reuse rights or establish that registered sources contain populated, approved repair records. No permission-required or quarantined source has been promoted into the production technical catalog.

The run status is recorded in [`ci-status/latest-windows-run.json`](ci-status/latest-windows-run.json). This is CI evidence, not a public release; `release_ready=false`. The generated EXEs are unsigned because no owner-supplied code-signing certificate is configured. They remain CI artifacts and have not been published as a release.

Run 300 used Windows-hosted CI and a separate Windows Server 2022 lifecycle runner. This is **not a native Windows 10/11 client test**. The latest native workflow [run 171 / 42215158370](https://github.com/ismailizmajlov-oss/VAG-TECH-PRO/actions/runs/42215158370) completed successfully only because its recorder job succeeded; the actual `Windows 10/11 x64 clean install and data-preservation lifecycle` job was `skipped`. The owner-controlled runner gate remains disabled and no owner-provided isolated Windows 10/11 x64 runner is registered. Required labels are `self-hosted`, `windows`, `x64`, `vag-tech-pro-win10-11`; the owner must also set `VAG_TECH_PRO_WIN10_11_RUNNER_AVAILABLE=true`. No runner or external account is created by the project.

A previous dependency audit in run 240 reported zero vulnerabilities for production-only and full dependency trees; run 300 did not repeat that audit. Deprecated transitive-package and GitHub Actions Node.js compatibility warnings remain maintenance items.


## Current source work after run 300 — 2026-11-06

The current main branch contains 47 central source-register entries and 11 entries in the dedicated Russian/EAEU register. The source-manifest bundle now contains 15 manifests. The latest completed Windows build is run 302; it packages the 47-source revision. Subsequent source-pack builder changes are newer than run 302 and require their own CI validation before they can be considered part of a verified installer.

A new official RDW source group is registered for a separate read-only NL/EU type-approval research pack. The Dutch national data catalogue lists the selected RDW vehicle identity and TGK datasets under CC0 1.0: [RDW base vehicle data](https://data.overheid.nl/dataset/basisregistratie-voertuigen---rdw), [TGK drive](https://data.overheid.nl/dataset/81ac19f5-d0e5-4411-847e-f8698d4a42f2), [TGK gearbox](https://data.overheid.nl/dataset/8a5be559-87b6-4224-9bbc-45dae886c427), [TGK base](https://data.overheid.nl/dataset/38afb954-4d3b-4363-9875-4a16117ab86b), [TGK make](https://data.overheid.nl/dataset/68f02697-4c7a-4a5c-ae1d-b253aa3ecc89), and [TGK manufacturer trade name](https://data.overheid.nl/dataset/1f00bd5c-63e9-4262-9603-311712339a30). The source is NL registration evidence with EU type-approval identifiers; it is not RU/EAEU evidence.

The live Windows schema/scope probe passed twice: [probe run 1](https://github.com/ismailizmajlov-oss/VAG-TECH-PRO/actions/runs/42225909008) and [probe run 2](https://github.com/ismailizmajlov-oss/VAG-TECH-PRO/actions/runs/42226340948). The current probe report SHA-256 is `b1d2ae64c32b7d58c80237fa103d847c49766be921c6fd2c0441919d1b8173d8`; its artifact ZIP SHA-256 is `37a9043413ac2367f574c053597db06d98b081ba748e4bb534d046375ff33569`. It verified an exact RDW approval scope for a Dutch-registered Volkswagen Tayron: approval `e1*2018/858*00403*07`, variant `ACDUCAX0`, version `FD6FD6DD002PR4VNB50OO`, revision `0`. The RDW Motorcode value `DUC` remains an engine-designation candidate; the separate gearbox classification `A` is not a VAG gearbox code. Although one engine row and one gearbox-classification row were found under the same approval scope, **no engine/gearbox pair is claimed**. No model year, generation, individual-vehicle fitment or RU/EAEU applicability is inferred.

The probe did not download a full source snapshot. The RDW source remains `data_ingested=false`, `product_import_allowed=false`, and `source_snapshot_sha256=null`; it is not yet included as an offline data pack or exposed as a product fitment result. The explicit registration-field allowlist excludes licence plates, VIN and holder/ownership data. Full import requires the next separate research-pack build with per-file and per-row hashes and the same no-pairing policy.

The Rosstandart recall-data metadata probe completed as a workflow but retrieved zero of two official pages because both requests timed out; it found no downloadable data file and produced no source snapshot. The source remains blocked and un-ingested. See [probe run 7](https://github.com/ismailizmajlov-oss/VAG-TECH-PRO/actions/runs/42225908849).


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

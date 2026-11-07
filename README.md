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
| KBA DE VAG stock identity research | 264,847 aggregate observations, 8 exact manufacturer labels, 802 make/trade-name pairs, 4,155 make/raw-type-key pairs, 17 federal states and four annual reference dates (2023–2026) | DL-DE BY 2.0; DE-only aggregate stock; Typschlüssel remains a raw field, not confirmed TSN; no engine/gearbox, ECU, DTC, repair or individual-vehicle fitment |
| ASTRA / FEDRO Swiss TAS VAG research | 45,215 VAG-group type-approval index rows and 53,414 emissions/gearbox rows in the 2026-10-29 source snapshot; 5,420 exact variant/version links, 28,489 wildcard-scope links, 19,505 unlinked | Swiss OGD with FEDRO attribution; separate CH-only research namespace; `engineType` and stamped marking stay distinct; `chGearboxType` is not a VAG gearbox code; no RU/EAEU or repair fitment |
| ASTRA / FEDRO TARGA per-gearbox VAG research | 53,240 source-defined approval/gearbox-variant rows; 0 exact VAG factory-code pairs; 0 production-fitment rows | Swiss OGD with attribution; CH-only; raw `Motortyp` and `Getriebe` labels; no RU/EAEU, model-year, generation or repair applicability |
| ASTRA / FEDRO TARGA legacy automobile approvals | 45,041 approval records; 45,041 unverified engine-marking candidates; 53,476 separate gearbox classifications; 0 engine/gearbox pairs | Swiss OGD with attribution; CH-only; source engine markings and gearbox fields stay separate; no RU/EAEU, model-year, generation, ECU, DTC or repair applicability |

Each pack remains in its own namespace with its own manifest, attribution/license material, source revision and hashes. Share-Alike obligations are retained. Generic DTC and generic repair guidance are not linked to a VAG configuration or ECU.

## Production-data status — 2026-11-07

**VAG TECH PRO is not yet a professional repair database or a release candidate.**

No verified Russian/EAEU OTTS records have been imported. No rights-cleared dataset currently supplies exact Russian/EAEU factory engine/gearbox pairs with market and production-year scope. No OEM-approved VAG-specific DTC/ECU test-plan corpus or rights-cleared repair procedures, wiring diagrams, pinouts, torque values, adaptations, service schedules or OEM parts catalog is populated in the production technical catalog.

The OpenVAG DTC project (995 publisher-claimed code/title rows) was reviewed on 2026-11-05 and quarantined: the MIT software licence does not establish the provenance or reuse rights of its unversioned, gitignored database; no row-level sources or reproducible seed process were found. See the [OpenVAG DTC rights review](docs/research/OPENVAG_DTC_SOURCE_RIGHTS_REVIEW_2026-11-05.md).

The Open Vehicle Schema (OVS) repository was reviewed on 2026-11-06 as a possible open vehicle-identity taxonomy. At pinned commit `d7223f3edfe4adcebf22d3ffa7a60599ae25016c`, all four reference arrays (`vehicles.json`, `engines.json`, `transmissions.json`, `bodies.json`) are empty five-byte JSON files; no populated release or row-level upstream provenance was found. A root MIT license exists, but no separate data license or explicit data-file scope was identified. The source is registered but excluded from all packs; no data was imported. See [the OVS source review](docs/research/OPEN_VEHICLE_SCHEMA_SOURCE_REVIEW_2026-11-06.md).

The commercial OTTS.BOT aggregator was also reviewed on 2026-11-05 and quarantined: its published terms prohibit automated collection beyond ordinary use and redistribution of database information as a proprietary product; advertised downloads/subscriptions were not used. See the [OTTS.BOT rights review](docs/research/OTTS_BOT_SOURCE_RIGHTS_REVIEW_2026-11-05.md).

EEC Decision No. 225 establishes publication of national register parts on official sites and requests for registry information to authorized bodies; Decision No. 88 defines intergovernmental technical-exchange documents and the registry schema, not the public-access or data-reuse license. The reviewed EAEU open-data catalogue did not identify an OTTS-specific OData/REST resource. Public query visibility does not grant bulk extraction, offline caching or redistribution rights. The official Russian FGIS registry information describes access software for accredited certification bodies and testing laboratories; it does not establish a general public bulk-export license. Commercial aggregators and subscription APIs are not used as bulk sources.

An ELPTS operator notice dated 2026-08-21 says an internal AS EOTTS data-entry issue involving additional-reduction and hydraulic transmissions was fixed. This is evidence about an internal entry workflow only: it does not expose a public Annex 2 gearbox field, identify an exact internal schema or factory gearbox code, or grant extraction/cache/display/redistribution rights. The ELPTS source remains permission-required and no records were imported. A 2026-11-07 recheck found CSV/PDF/XML export controls on the public OTTS page, but no export file was downloaded and no export scope or reuse rights were established; see [the export-control rights recheck](docs/research/ELPTS_OTTS_PUBLIC_REGISTRY_RIGHTS_REVIEW_2026-11-07.md) and [the ELPTS gearbox-entry notice review](docs/research/ELPTS_AS_EOTTS_GEARBOX_ENTRY_NOTICE_2026-11-06.md).

The current consolidated EEC Decision No. 232 OTTS/OTSH Annex 1 form was reviewed on 2026-11-07. Its attachment-level "General characteristics" fields include engine make/type, ECU marking, transmission type, gearbox make/type, gear count and ratios, transfer-case and final-drive data. This is a useful schema for a future document-level importer, but it is **not** proof that the ELPTS summary table exposes those values: the visible summary table still did not show engine or gearbox fields, and no filled approval attachment was retrieved. Raw manufacturer make/type strings must not be silently converted to VAG three-letter codes; a candidate pair requires the same annex and exact variant scope plus independent technical mapping. Decision No. 52 of 2026-05-12 updates the form rules, with the relevant form changes effective 2026-10-08; this review does not claim the engine/gearbox fields were newly introduced by that amendment. No data were imported and no reuse rights were changed. See [the EAEU OTTS/OTSH Annex 1 powertrain schema review](docs/research/EAEU_OTTS_OTSH_ANNEX1_POWERTRAIN_SCHEMA_REVIEW_2026-11-07.md).

A separate Rosstandart recall-campaign open-data source has been identified at easy.gost.ru. Historical public statements describe the register as open data for non-commercial services, and a 2023 webinar report describes reuse by business services. The current official dataset page and archive timed out during review on 2026-11-06. A separate metadata-only Windows CI probe [run 5](https://github.com/ismailizmajlov-oss/VAG-TECH-PRO/actions/runs/42205049421) also failed to connect to both official URLs (WinError 10060); it downloaded no data file and found no current file or terms link. The current file schema and dataset-linked terms were therefore not retrieved. It is registered as a high-priority RU candidate only: no VIN rows, repair-completion/dealer fields or campaign text have been imported, and no snapshot hash is claimed. Recall remedy text must not be represented as a factory workshop procedure. See [the Rosstandart recall-campaign rights review](docs/research/ROSSTANDART_RECALL_CAMPAIGNS_OPEN_DATA_REVIEW_2026-11-06.md).

The current central source register contains 54 entries and the Russian/EAEU register contains 13 sources; both retain explicit access, rights, market and import boundaries.

A new Kyrgyz Single Window public vehicle-approval registry was reviewed on 2026-11-07. The operator describes a no-login pilot public registry for OTTS/OTSH and the separate cert.trade.kg landing page shows one-OTTS and zero-OTSH UI counters, which are not verified public-register corpus counts. The related certification application form includes engine characteristics, but this is not evidence that those fields are public-record fields. No dataset-specific reuse licence, documented API or bulk-export contract was found; the source is registered as permission-required, no records were downloaded and no hash is claimed. See the [Kyrgyz Single Window public registry review](docs/research/KYRGYZ_SINGLE_WINDOW_PUBLIC_REGISTRY_REVIEW_2026-11-07.md).

A related Kazakhstan EOKNO public register was reviewed on 2026-11-07. Its public title refers broadly to conformity documents under TR TS 018/2011, and official 2023 releases confirm that SBKTS and OTTS/OTSH records flow into the register. The latest indexed homepage snapshot (crawled approximately two months before review) routes new conformity-document issuance to TechReg, but a live fetch timed out; bulk reuse rights remain unconfirmed. No dataset licence, bulk API or offline reuse permission was identified, no records were downloaded, and the source remains discovery-only with no snapshot hash. See [the EOKNO register review](docs/research/KAZAKHSTAN_EOKNO_TRTS018_PUBLIC_REGISTER_REVIEW_2026-11-07.md).

## Windows build and verification

The desktop source is stored as a SHA-256-pinned source payload plus deterministic patches and is assembled by [the Windows x64 CI workflow](.github/workflows/windows-desktop-ci-run71.yml). The pipeline builds two NSIS x64 installers, validates packaged offline research resources and source manifests, and runs clean install, external-network-blocked offline launch, backup/restore, in-place upgrade, integrity and uninstall-preservation checks. A separate Windows Server 2022 lifecycle job checks compatibility. The workflow-run recorder writes `ci-status/latest-windows-run.json`; that record is evidence only for the exact commit and run it names.

The latest completed successful full Windows x64 validation is [run 597 / 42364351787](https://github.com/ismailizmajlov-oss/VAG-TECH-PRO/actions/runs/42364351787), completed on 2026-11-07 for source commit `279c0b1d43fa1bf608389ae98514821bbbca36e3`. Both the main `build-and-lifecycle` job and the separate Windows Server 2022 compatibility lifecycle job passed. Run 597 reassembled the pinned desktop source; verified the 53-entry central source-rights register and 13-entry Russian/EAEU OTTS register against their SHA-256 pins; verified the 19-file source-manifest index; passed source-rights, catalog-import, local-core, research and desktop tests, ESLint and TypeScript; applied the run81 strict technical-payload validation; built NSIS x64 installers 0.2.3 and 0.2.4; verified the packaged source manifests and technical-library schemas; and passed clean install, external-network-blocked offline launch, SQLite backup/restore, in-place upgrade, integrity and uninstall-preservation checks on Windows 2025 and Windows Server 2022. Run81 validates 12 technical payload schema kinds, keeps generic DTC and VAG-specific DTC separate, checks DTC alias consistency and preserves provenance. The main Windows artifact is artifact ID `13572015151` (1,266,561,027 bytes); the separate Windows Server 2022 lifecycle evidence is artifact ID `13571693163` (5,425 bytes); the desktop source audit is artifact ID `13572090043` (484,983 bytes). Build metadata pins source archive SHA-256 `e041ce167f083192a11f4b86b19e7bbc51fe8a1bb8e732a0d2944229af713216`, central source register SHA-256 `99bb9378420869537cd96854b10ddfa5d77e47503a944be60fc4ff08a6ae9c05`, Russian/EAEU manifest SHA-256 `0e4adf026a0f15431232b4206c5eacdfdf67cded5157a9ea2b70811c1028382c`, technical payload schema SHA-256 `d5b117738c21e135a346a57b46a0704d28085678d167d2da0c2f3faa9de165b1`, and technical-library SQL SHA-256 `8306bf559c3b745975305ea4e264bc1df621621cce70efa710a00c35f979c2f2`. The two installer SHA-256 values are `81f899375685ccf08dcf730fb031907679c0e9d4cb1bd59ff88f81fb9e1b8405` for 0.2.3 and `edf6b8571b4f195f55a206d92212e65a9daacb5277de910bfa3c5df612734e45` for 0.2.4. These are CI artifacts, not a public release. This validation applies only to source SHA `279c0b1d43fa1bf608389ae98514821bbbca36e3`; it does not establish native Windows 10/11 client compatibility.

The run status is recorded in [`ci-status/latest-windows-run.json`](ci-status/latest-windows-run.json). This is CI evidence, not a public release; `release_ready=false`. The generated EXEs are unsigned because no owner-supplied code-signing certificate is configured. They remain CI artifacts and have not been published as a release.

Run 300 used Windows-hosted CI and a separate Windows Server 2022 lifecycle runner. This is **not a native Windows 10/11 client test**. The latest native workflow [run 387 / 42353757455](https://github.com/ismailizmajlov-oss/VAG-TECH-PRO/actions/runs/42353757455) has its actual `Windows 10/11 x64 clean install and data-preservation lifecycle` job `skipped`. Its status-recorder job is not a native installation test. Native runs 381–386 also skipped the actual lifecycle job. The owner-controlled runner gate remains disabled and no owner-provided isolated Windows 10/11 x64 runner is registered. Required labels are `self-hosted`, `windows`, `x64`, `vag-tech-pro-win10-11`; the owner must also set `VAG_TECH_PRO_WIN10_11_RUNNER_AVAILABLE=true`. No runner or external account is created by the project.

A previous dependency audit in run 240 reported zero vulnerabilities for production-only and full dependency trees; run 300 did not repeat that audit. Deprecated transitive-package and GitHub Actions Node.js compatibility warnings remain maintenance items.


## KBA DE VAG stock research pack — 2026-11-07

The KBA FZ Hersteller Handelsnamen Pkw dataset is published by Kraftfahrt-Bundesamt through GovData/Mobilithek under Datenlizenz Deutschland – Namensnennung – Version 2.0 (DL-DE BY 2.0). The published licence permits commercial use, display, offline caching, bulk reuse and redistribution with attribution and a notice for modified data. The separate official whole-vehicle type-approval XLSX remains unavailable (HTTP 503); no approval-list data or hash is claimed for that dataset. The GovData record for the whole-vehicle approval list also explicitly marks the resource as freie Nutzung under DL-DE BY 2.0 and describes KBA M1/N1 approvals from 2019-01-01 onward. The official KBA XLSX endpoint returned HTTP 503 during the 2026-11-07 review; no approval-list bytes or SHA-256 are claimed. A separate read-only Windows probe now checks only the official KBA HTTPS host, validates the XLSX ZIP/XML structure, records the file hash and reports candidate header rows; it never imports data or enables production fitment. Its result must be reviewed before a research-pack builder is added.

The passenger-car stock CSV was acquired on 2026-11-07 through the KBA Statistikportal ArcGIS Hub legacy download endpoint. The 65,366,675-byte snapshot contains 1,047,991 source rows; the exact VAG manufacturer allowlist retains 264,847 aggregate observations across eight labels. The normalized research SQLite contains 17 federal states, four annual reference dates (2023-01-01 through 2026-01-01), 794 trade names and 2,225 raw type keys. There are 802 make/trade-name pairs, 4,155 make/type-key pairs and 16,301 make/trade/type/reference-date tuples.

The latest successful pack build is [KBA research workflow run 7](https://github.com/ismailizmajlov-oss/VAG-TECH-PRO/actions/runs/42328320491). Independent artifact audit verified:
- artifact ZIP SHA-256: fd75f0e2c0dd260cf95540f7bcf6cda7d4bfc79948cd332ff2ac3402461281bd (27,883,868 bytes);
- source CSV SHA-256: 03bd9f85e384b2b8bcd0e7d80b5f755eca568e9ad1c45e7fb3fe512e7fedc468;
- generated source-manifest SHA-256: 3aab2daa3c03914001f8b80c92b0e47c1883e3e1ec6eb8589ac3065d2e1c04da;
- pack manifest SHA-256: 0322d9acc4236e89702377a1c8a90daea253f4b14f86d996fd28bbf505e4c8e2;
- SQLite SHA-256: 879ff1f66d3615ee2324b98d4d2defdcfae8018f48fe78f865fc1d3f13a5f4b9.

The SQLite audit returned PRAGMA integrity_check=ok, no foreign-key violations and nine expected tables. Source-row hashes are SHA-256 over canonical JSON of the original parsed CSV field strings; original column names and raw Typschlüssel values are retained.

This pack is Germany-only aggregate stock research, not a vehicle build sheet. The downloaded columns contain no HSN field. Typschlüssel is not promoted to HSN or confirmed TSN; annual Berichtszeitpunkt is not model year or generation. The source provides no engine code, gearbox code, engine/gearbox pair, ECU, DTC, wiring, repair procedure or individual-vehicle fitment. No Russian/EAEU applicability is inferred.

The pack remains separate from the production vehicle catalog: research_pack_ingested=true, while data_ingested=false, product_database_ingested=false and product_import_allowed=false. Historical KBA integration run 474 staged the run-7 pack but failed in its verifier patch. The patch was corrected and the integration was subsequently validated by Windows run 556: the KBA DE stock research pack is included in the offline desktop research catalog. It remains a separate DE-only read-only research resource, not production vehicle fitment.

## CarDir CC BY 4.0 VAG owner-manual facts — 2026-11-07

CarDir publishes a curated CSV/JSON dataset of 41,649 verified owner-manual facts across 561 models (snapshot date stated as 2026-11-07). Its dataset page explicitly grants CC BY 4.0 reuse, including offline caching and redistribution with attribution. A Windows-only builder filters exact VAG brand labels, preserves raw model qualifiers and each row's source title/page/URL/verification date, and hashes the downloaded source CSV and every retained source row. The first reproducible acquisition is pending; no source-file hash is claimed until the workflow actually downloads the CSV.

The planned SQLite pack is separate and read-only. Its market scope is UNKNOWN because the CSV has no market field. It will not infer generations, model years, engine/gearbox codes, exact engine/gearbox pairs, ECU, DTC, repair procedures, wiring or pinouts. Publisher verification is retained as publisher verification, not represented as independent VAG OEM review. The source is not added to the Russian/EAEU OTTS register.

See the [CarDir CC BY 4.0 source and applicability review](docs/research/CARDIR_CC_BY_VAG_OWNER_MANUAL_FACTS_REVIEW_2026-11-07.md).

## Current source work after RDW pack run 34 — 2026-11-07

The current main branch contains 54 central source-register entries and 13 entries in the dedicated Russian/EAEU register; the source-manifest bundle contains 22 JSON manifests. RDW pack run 34 and KBA DE stock research pack run 7 remain separate market-specific research packs. Windows run 556 integrated the ASTRA CH/TARGA, RDW NL and KBA DE packs into the offline desktop research catalog. They remain read-only research resources, not Russian/EAEU production fitment.

The Dutch national data catalogue lists the six selected RDW vehicle identity and TGK datasets under CC0 1.0: [RDW base vehicle data](https://data.overheid.nl/dataset/basisregistratie-voertuigen---rdw), [TGK drive](https://data.overheid.nl/dataset/81ac19f5-d0e5-4411-847e-f8698d4a42f2), [TGK gearbox](https://data.overheid.nl/dataset/8a5be559-87b6-4224-9bbc-45dae886c427), [TGK base](https://data.overheid.nl/dataset/38afb954-4d3b-4363-9875-4a16117ab86b), [TGK make](https://data.overheid.nl/dataset/68f02697-4c7a-4a5c-ae1d-b253aa3ecc89), and [TGK manufacturer trade name](https://data.overheid.nl/dataset/1f00bd5c-63e9-4262-9603-311712339a30). The source is NL registration evidence with EU type-approval identifiers; it is not RU/EAEU evidence.

The live Windows schema/scope probe passed twice: [probe run 1](https://github.com/ismailizmajlov-oss/VAG-TECH-PRO/actions/runs/42225909008) and [probe run 2](https://github.com/ismailizmajlov-oss/VAG-TECH-PRO/actions/runs/42226340948). The report SHA-256 is `b1d2ae64c32b7d58c80237fa103d847c49766be921c6fd2c0441919d1b8173d8`; its artifact ZIP SHA-256 is `37a9043413ac2367f574c053597db06d98b081ba748e4bb534d046375ff33569`. It verified one NL Volkswagen Tayron approval scope: `e1*2018/858*00403*07`, variant `ACDUCAX0`, version `FD6FD6DD002PR4VNB50OO`, revision `0`. RDW `DUC` remains an engine-designation candidate; gearbox classification `A` is not a VAG gearbox code. No engine/gearbox pair, model year, generation, individual-vehicle fitment or RU/EAEU applicability is inferred.

The isolated RDW NL/EU pack build [run 34 / 42304030420](https://github.com/ismailizmajlov-oss/VAG-TECH-PRO/actions/runs/42304030420) completed successfully. Artifact ID `13548640460`; ZIP size 148,741,631 bytes; ZIP SHA-256 `157fb4ad67153c05bff64e2d4fed71d48c50d181f992a927414cb158b0ebe41b`. The pack-manifest SHA-256 is `e0feecf32b85b9fd5152134189676b530eac7dbab6614c274759817e3e99d095`; the pinned RDW source-manifest SHA-256 is `c4b45564b97407febeee8f8ce64de2a5a6acb8dbf2f75f4877f40911bc9104a8`; the 404,602,880-byte SQLite database SHA-256 is `7bf620549d046a3324b7e6d31b8cfb40f88e1d326e260fd88691060f4111f418`; the aggregate six-file source snapshot SHA-256 is `896a34b9b8377f2ed20c34d7e0e33b4cf2ce1958e2cdd2b7326ee8c3157b0706`.

An independent read-only audit of the downloaded run-34 artifact verified the ZIP, manifest, source-manifest, database and all six source-file hashes; byte sizes and JSONL row counts; per-dataset source-row parity; SQLite `integrity_check=ok`; and zero foreign-key violations. The database contains 604,785 source rows, 96,519 exact approval/variant/version/revision scopes, 102,662 registration observations, 93,836 engine-designation candidates, 93,548 gearbox classifications and 314,739 auxiliary rows. It has eight expected tables and no pair table. All approval scopes are NL-only; no model year, generation, exact vehicle fitment or RU/EAEU applicability is populated. Selected source fields contain no VIN, registration plate, holder, owner, address or personal-data columns.

The builder reports 93,548 scopes with both separate engine and gearbox observations, 190 engine-only scopes, 98 scopes with multiple engine rows, 908 distinct engine-designation strings and four gearbox-classification values. These are coverage diagnostics only; they do not create or confirm a pair. The central source register keeps `data_ingested=false` and `product_import_allowed=false` because this is a separate research pack, not production fitment.

Historical RDW desktop integration run 400 failed before NSIS packaging on a `database.file` / `database.path` mismatch. The path validation fix was committed with regression coverage and was subsequently exercised in Windows run 556, which integrated the run-34 RDW pack into the offline desktop research catalog and passed packaged-resource verification and lifecycle checks. The pack remains NL/EU research only; no RU/EAEU fitment or engine/gearbox pair is inferred.

The Rosstandart recall-data metadata probe retrieved zero of two official pages because both requests timed out; it downloaded no data file and produced no source snapshot. The source remains a high-priority RU candidate only. The Kazakhstan EOKNO public register remains discovery-only because bulk reuse rights and a public export were not confirmed. The EAEU open-data portal review found no dedicated OTTS/OTSH dataset among the reviewed public catalogue resources; its general REST API and unrelated conformity-body/certificate registries are not treated as OTTS permission or data. See [the EAEU open-data portal OTTS discovery review](docs/research/EAEU_OPEN_DATA_PORTAL_OTTS_DISCOVERY_REVIEW_2026-11-07.md).

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
- [EAEU open-data portal OTTS discovery review](docs/research/EAEU_OPEN_DATA_PORTAL_OTTS_DISCOVERY_REVIEW_2026-11-07.md)
- [Local catalog import v2 contract](docs/LOCAL_CATALOG_IMPORT_V2.md)
- [Owner-controlled source rights approval](docs/OWNER_SOURCE_RIGHTS_APPROVAL.md)

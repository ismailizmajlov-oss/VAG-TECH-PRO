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
| MechanicDB manufacturer-labelled DTC candidates | 2 rows | ODbL-1.0; quarantined from normal DTC lookup pending technical review; not OEM-confirmed |

Each pack remains in its own namespace with its own manifest, attribution/license material, source revision and hashes. Share-Alike obligations are retained. Generic DTC and generic repair guidance are not linked to a VAG configuration or ECU.

## Production-data status — 2026-11-05

**VAG TECH PRO is not yet a professional repair database or a release candidate.**

No verified Russian/EAEU OTTS records have been imported. No rights-cleared dataset currently supplies exact Russian/EAEU factory engine/gearbox pairs with market and production-year scope. No OEM-approved VAG-specific DTC/ECU test-plan corpus or rights-cleared repair procedures, wiring diagrams, pinouts, torque values, adaptations, service schedules or OEM parts catalog is populated in the production technical catalog.

The EAEU register has a legal public-query basis, but the reviewed open-data catalogue did not identify an OTTS-specific OData/REST resource. Public query visibility does not grant bulk extraction, offline caching or redistribution rights. The official Russian FGIS registry information describes access software for accredited certification bodies and testing laboratories; it does not establish a general public bulk-export license. Commercial aggregators and subscription APIs are not used as bulk sources.

The current source register records the EAEU, Rosstandart/Interstandart, ELPTS, Audatex and aggregator access/rights boundaries. See [the machine-readable source register](data/source-manifests/vag-factory-source-register.json) and [owner-controlled source approval procedure](docs/OWNER_SOURCE_RIGHTS_APPROVAL.md). Autoevolution-derived ODbL candidates, uncleared manufacturer DTC CSVs and ODIS MCD-derived community material remain excluded or quarantined.

## Windows build and verification

The desktop source is stored as a SHA-256-pinned source payload plus deterministic patches and is assembled by [the Windows x64 CI workflow](.github/workflows/windows-desktop-ci-run71.yml). The pipeline is configured to build two NSIS x64 installers (0.2.3 and 0.2.4), validate the packaged offline research resources, and test clean install, offline launch, backup/restore, in-place upgrade and uninstall preservation. A separate Windows Server 2022 lifecycle job checks compatibility. A workflow-run status record is maintained separately; a workflow definition alone is not evidence that a run passed.

The last fully inspected Windows CI baseline, run [41951432204](https://github.com/ismailizmajlov-oss/VAG-TECH-PRO/actions/runs/41951432204), built NSIS installers 0.2.0 and 0.2.1. Its three automated test suites passed 21 + 40 + 22 tests (83 total), lint and TypeScript checks passed, and the clean-install/offline/backup/restore/upgrade/uninstall-preservation lifecycle passed. This was a Windows-hosted CI runner, **not a native Windows 10/11 client test**.

A separate [native Windows 10/11 x64 lifecycle workflow](.github/workflows/windows-10-11-native-lifecycle.yml) is now wired to successful desktop CI runs. It is deliberately owner-gated: the repository owner must attach an isolated Windows 10/11 x64 self-hosted runner with labels `self-hosted`, `windows`, `x64`, `vag-tech-pro-win10-11` and set `VAG_TECH_PRO_WIN10_11_RUNNER_AVAILABLE=true`. No runner or external account is created by this project workflow.

The inspected installer logs show that code signing was skipped because no signing certificate is configured. No paid signing service or certificate has been acquired.

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

# VAG TECH PRO engineering journal — 2026-11-03

## Run scope

Branch: `automation/rdw-eu-type-approval-research-run19`

Target remains Windows 10/11 x64. No Linux/macOS build work, production deployment, account creation, paid subscription or payment integration was performed.

## Baseline re-check

- Reviewed the latest available Windows offline data-pack artifact from workflow run `41569514426`.
- Re-opened all five SQLite databases read-only; each returned `PRAGMA integrity_check = ok`.
- Confirmed that the bundle keeps licenses separate and does not merge records across datasets.
- Rechecked that generic SAE/ISO DTCs are isolated from manufacturer-controlled DTC candidates.
- Supabase remains outside the first-delivery local SQLite path; no cloud writes or migrations were made in this run.

## Existing offline SQLite evidence

The inspected bundle contains five separate SQLite databases:

| Pack | Rows / evidence | Boundary |
|---|---:|---|
| OBDex | 9,533 generic DTCs; 132 PIDs | CC0 generic SAE/ISO only; no VAG fitment |
| VehiclesDB | 260 model candidates; 1,524 market-presence records | CC BY 4.0; foreign-market model names only |
| VAG engine research | 823 generation candidates; 5,081 engine-variant candidates | ODbL research-only; upstream provenance still requires review |
| OBDb VAG signals | 2,480 signal candidates; 2,315 command candidates; 15 ECU candidates; 32 generation candidates | CC BY-SA research-only; no confirmed ECU/vehicle fitment and no command execution |
| Wal33D DTC candidates | 530 manufacturer-controlled code candidates | Repository-level MIT notice, but rights and record provenance not confirmed; research-only |

The pack counts are from the downloaded workflow artifact, not estimates. These datasets are not represented as verified repair data.

## RDW CC0 type-approval acquisition

Added:

- `data/source-manifests/rdw-eu-type-approval-cc0.json`
- `scripts/build_rdw_type_approval_pack.py`
- `scripts/test_rdw_type_approval_pack.py`
- `.github/workflows/acquire-rdw-eu-type-approval.yml`
- `docs/research/RDW_EU_TYPE_APPROVAL_CC0_REVIEW_2026-11-03.md`

The source set is five RDW datasets: TGK Basis Uitvoering, TGK Merk Uitvoering, TGK Aandrijving Uitvoering, TGK Handelsbenaming Fabrikant and TGK Versnelling Uitvoering. Each selected government-catalogue record declares CC0-1.0. The acquisition stores dataset-specific license evidence, CC0 legal text, Socrata metadata, query URLs/text, raw filtered CSV pages, source revisions and SHA-256 hashes.

The first full export attempt was correctly rejected because the unfiltered TGK Basis export exceeded the configured safe response size. The builder was changed to discover RDW make codes first and retrieve only VAG make rows and related approval-number rows through paginated SoQL queries.

Applicability is deliberately limited:

- market: Netherlands RDW register / European type approvals recorded by RDW;
- precision: type-approval variant;
- status: source-published candidate;
- no Russian/EAEU fitment;
- no exact production-vehicle/VIN fitment;
- RDW `Motorcode` is not promoted to a VAG factory engine code;
- RDW gearbox-type code is not promoted to a VAG factory gearbox code;
- no generation/year, ECU, PR-code or repair-data claim.

### Windows CI status at journal time

- The initial Windows run `41571138506` passed all 10 offline regression tests and then failed on the oversized unfiltered export.
- The filtered SoQL acquisition run `41571524577` was still executing its acquisition step.
- The six-pack Windows bundle runs `41571731692` and `41571789988` were queued/pending.
- Therefore no RDW SQLite artifact or six-pack bundle is marked verified in this journal entry.

## DTC source-rights triage

Added `docs/research/VAG_SPECIFIC_DTC_SOURCE_TRIAGE_2026-11-03.md`.

- OpenVAG is excluded: the repository contains schema/API code but no reviewable SQLite data snapshot or row-level source provenance.
- AutoDiag2 is excluded unless individual source rights are established: the inspected Audi record attributes content to OBDCodeX without a commercial redistribution license.
- OBDex remains generic-only and isolated.
- OBDb remains a separately licensed community signal candidate pack.
- Wal33D remains research-only; repository-level MIT is not treated as proof of rights over every underlying record.

## Windows bundle integration

The offline bundle assembler now expects six independent SQLite packs and independently verifies the RDW pack, including source revisions and applicability boundaries. The bundle workflow is Windows x64 only. The separate licensed databases remain separate; no cross-license merge is performed.

No application-ready or repair-accuracy claim is made by this journal entry.

---

## Latest available desktop workspace baseline — run 16

The latest desktop source snapshot available in the Library is `VAG_TECH_PRO_run16_source.zip` (source root `vag_next`), with its companion `VAG_TECH_PRO_run16_verification.json` dated 2026-11-03 01:02:36 UTC. This is a separate workspace snapshot; it is not present in the canonical GitHub repository.

Verified in that snapshot:

- 228/228 automated tests passed: 7 VIN, 190 integrity, 24 OEM-provider and 7 desktop-runtime tests.
- Main `vag-tech-pro.sqlite`: 212,992 bytes; `PRAGMA integrity_check=ok`; zero foreign-key violations; 134 research records; zero production vehicle, engine, transmission or ECU-hardware rows.
- OTTS staging `vag-tech-pro-otts-staging.sqlite`: 139,264 bytes; integrity and foreign keys passed; 25 engine candidates, 19 transmission identifiers, 26 explicit engine/transmission evidence pairs, 31 ECU-hardware candidates, 4 vehicle-type candidates, 4 VIN patterns and 12 evidence records. Its status is `staging_only_rights_unverified`; zero documents were visually verified. These candidates must not be promoted.
- Desktop runtime already exposes the research directory as a read-only extra resource through `node:sqlite`; the writable user database is under `%APPDATA%/VAG TECH PRO/data/vag-tech-pro.sqlite`. The local API smoke checks returned 200 for summary, DTC, vehicle and PID endpoints, and 400 for a deliberately short invalid query. Isolated TypeScript checks passed.
- The snapshot declares that uninstall preserves user data, but this is not a substitute for the required Windows install/update/uninstall test matrix.

The run16 package is not release-ready: `package-lock.json` and `node_modules` were absent; ESLint was unavailable; full typecheck and production build were not run; GitHub Actions was not connected to this desktop source; no NSIS `.exe` was built; clean installation, offline launch, upgrade-over-existing, backup/restore and uninstall-preserves-database were not tested on Windows.

## Current read-only Supabase audit (not the Windows product database)

A fresh read-only audit after run16 found 30 public tables, all with RLS enabled; 62 recorded migrations; zero Security Advisor findings; and 45 informational unused-index notices. Current row counts include 5 brands, 277 models (44 active), 784 generations (zero verified), zero engines, transmissions, ECU units or vehicle configurations, 9,943 DTC rows (all draft), 2 technical documents, and zero procedures, specifications, wiring diagrams or diagnostic tests. There are 26 source-registry entries. No cloud writes or migrations were performed. Supabase is not being treated as the first-delivery local SQLite store.

## Latest verified Windows data-pack build — run 24

Verified against GitHub Actions run `41578436264`, branch `automation/rdw-eu-type-approval-research-run19`, commit `7f186c5ef9f392968c9b21fdecd69705a62d65db` (2026-11-03 04:29:41–04:36:59 UTC).

All seven Windows x64 jobs completed successfully, including acquisition and verification of the six separate data packs and the final offline bundle assembler. The assembler re-opened the source databases read-only and independently verified their manifests, licenses, hashes, namespaces, applicability boundaries, SQLite integrity and foreign keys.

| Pack | Artifact ID | Bytes | GitHub artifact SHA-256 |
|---|---:|---:|---|
| OBDex generic CC0 | 13204297411 | 14,810,790 | `e1148142a07066135b9b5459a38e0d5a5d737f834289432150178243b00ec0d1` |
| VehiclesDB identity CC BY 4.0 | 13205006730 | 94,876 | `2b98a687ab23e4d3e4886d2b39c651cb8c9e1d1c03b04ccd7ff048af262b7a38` |
| VAG engine candidates ODbL 1.0 | 13204383180 | 2,796,913 | `037632efb7a2dc7a9199d6ab55da8b45a51250327ef6b63b8e51ce413aa53a94` |
| OBDb VAG signal candidates CC BY-SA 4.0 | 13205061536 | 839,847 | `ed35e99afbd78a958bd8131e41365326857cfb02b41f24daa01ec2628e4a2619` |
| Wal33D manufacturer-controlled DTC candidates | 13203913121 | 65,781 | `bdf68c8ba74d8f746b5c8e00ea186d310b133da87c7e584e795a9de252fdbcd5` |
| RDW EU/NL type-approval CC0 | 13204363126 | 105,290,617 | `ee548ddb4e261bc5347b3a7e7ed1cfaaf20fb1a36bf1c16ed7801409333c582c` |
| **Combined Windows offline SQLite data-pack bundle** | **13204873219** | **123,920,480** | **`82e0d0244b974f497c450db5bc00c031ee303a8d5d0f7d63af54cd6ac2d9c9d6`** |

The bundle contains six separate SQLite databases and a metadata-only pack index; it does not merge records across CC0, CC BY, CC BY-SA, ODbL or the unverified MIT-labelled research candidate. The bundle is an offline data resource, not an NSIS installer and not an integrated desktop release.

### Data interpretation remains restricted

- OBDex: 9,533 generic SAE/ISO DTCs and 132 generic PIDs only. No VAG namespace or fitment.
- VehiclesDB: 260 make/model identity candidates and 1,524 foreign-market presence records; no Russian evidence, generations, years, engine/gearbox codes or fitment.
- ODbL VAG identity: 5 makes, 233 models, 823 generation candidates and 5,081 descriptive engine-variant candidates. Market remains UNKNOWN; zero factory engine codes, zero gearbox codes and zero exact fitment claims.
- OBDb: 2,480 signal candidates, 2,315 service-0x22 command candidates, 15 ECU-header candidates and 32 generation labels. Market and exact ECU/vehicle fitment remain UNKNOWN; command execution is disabled.
- Wal33D: 530 manufacturer-controlled DTC candidates (528 Volkswagen and 2 Audi). Repository MIT declaration is not a verified data license; all records remain research-only with no exact applicability.
- RDW: five CC0 datasets describing Netherlands-held European type-approval records. They are not Russian/EAEU OTTS and do not establish VAG factory engine/gearbox codes or repair applicability.

### Current Russian/EAEU rights gate

The official FGIS «Реестры КТС» is still the highest-priority Russian source, but the reviewed public-site search/attribute publication does not grant bulk extraction, commercial display, offline caching or redistribution rights. The EAEU OData catalogue review has not identified a dedicated OTTS bulk dataset with dataset-specific reuse terms. HPT.SU API terms restrict third-party equivalent/derived databases and full mirroring without separate written consent. A fresh terms review also confirmed that OTTS.BOT prohibits automated scraping and redistribution of its database/documents, while АВТОРЕГИСТР permits internal professional use but prohibits substantial systematic extraction for a competing catalogue. Both aggregators are now explicitly marked restricted_for_product_distribution in the machine-readable register. No Russian/EAEU OTTS data was imported, no account or API key was created, no document was downloaded, and no paid terms were accepted.

## Russian/EAEU source-rights guard — verified on Windows

Added `scripts/validate_russian_eaeu_otts_sources.py` and `.github/workflows/validate-russian-eaeu-otts-sources.yml`. The validator is fail-closed: it refuses ingestion unless commercial use, display, offline caching, bulk reuse, required PDF redistribution, a source revision, market scope, applicability precision and a valid source SHA-256 are all explicitly recorded. It also asserts that FGIS remains permission_required, the EAEU catalogue remains discovery_only, and HPT.SU, OTTS.BOT and АВТОРЕГИСТР remain restricted and unimported.

Windows x64 workflow run `41591282473` completed successfully on commit `842eda2789648efa3af84c008a88e04dc3a3fe70`. The run records the Python runtime and executes the current validator. The machine-readable register contains five source entries, zero ingested records and three explicitly blocked commercial aggregators. This gate validates permission metadata only; it does not fetch or import OTTS data.

## VAG-specific DTC source quarantine — verified on Windows

Rechecked `riz4d/OpenVAG` at default-branch commit `407d5e042cf46d55087ed4ae4e056605f2b04f08`, tree `d9101f504ef15d522c8f4f517cc96471bcac1619`. The repository README and `db/README.md` claim a 2.1 MB database with 995 DTCs and related variants, but the complete current Git tree contains no SQLite/database blob, no seed-data directory and no GitHub release asset. The MIT license covers project code; a separate database-data license and row-level provenance are not established. The source register now pins the commit/tree and explicitly records `data_ingested=false`, `source_snapshot_sha256=null`, `applicability_precision=none`, and `verification_status=quarantine_only`.

Added `scripts/validate_vag_dtc_source_rights.py` and `.github/workflows/validate-vag-dtc-source-rights.yml`. Windows x64 run `41591897343` completed successfully on commit `e5e21756651a71daf2038a8e93487c41f7a8197c`. The gate fails if a quarantined or unlicensed source is marked as imported, and keeps generic OBD separate from manufacturer-controlled candidates.

## Current external delivery boundary

- The canonical GitHub repository is still the acquisition/schema/validation pipeline; its README states that the complete desktop application source has not been mirrored into this repository.
- No Windows NSIS installer workflow or verified `.exe` artifact exists in this repository.
- The six-pack bundle is not yet wired into the Windows desktop runtime or its user-data-preserving updater.
- Clean install, upgrade-over-existing, offline launch, backup/restore, and uninstall-preserves-user-database remain untested on Windows.
- The existing application workspace snapshot is separate from this repository; do not assume the successful data-pack workflow is a successful application build.

## Next engineering gate

1. Integrate the metadata-only six-pack index into the Windows desktop runtime, keeping each SQLite database read-only and separate by license/namespace; add tests proving generic DTCs cannot appear as VAG-specific and that no candidate pack can enter verified repair search.
2. Mirror/reconcile the complete current desktop source into the canonical repository without secrets or generated dependencies, then add Windows 10/11 x64 semantic typecheck, lint, application build and UI smoke tests.
3. Add the Windows NSIS pipeline only after the real desktop source and pack-resource layout are canonical; test clean install, offline launch, in-place update, user SQLite preservation, backup/restore and uninstall without deleting user data.
4. Continue Russian/EAEU OTTS discovery only when the exact dataset and commercial display/cache/reuse rights are documented. Do not scrape or infer rights from public search availability.
5. Keep OEM procedures, torque values, wiring, pinouts, ECU mappings and repair test plans empty until traceable, licensed, revisioned and exact-applicability evidence is available.

No application-ready or repair-accuracy claim is made by this journal entry.

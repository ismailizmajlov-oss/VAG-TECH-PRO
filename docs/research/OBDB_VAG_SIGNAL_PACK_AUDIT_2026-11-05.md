# OBDb VAG signal pack — independent artifact audit

Audit date: 2026-11-04 UTC  
Scope: licence, source-file and SQLite integrity; not a technical validation of the signals or vehicle applicability.

## Pinned pack

- Dataset ID: `obdb-vag-signalsets-cc-by-sa`
- Licence: CC BY-SA 4.0
- Commercial use, display, caching and redistribution: allowed by the declared licence
- Attribution: required
- Share-alike: required
- Source repositories: 6 pinned OBDb repositories
- Upstream files checked: 24
- SQLite file: `vag-obdb-research.sqlite`
- SQLite SHA-256: `d3c54051e2f3f73c211e6d84c4e84541a60901e01eeee843b8357efa1e421aa1`

## Contents

| Record type | Count |
|---|---:|
| Source repositories | 6 |
| Generation candidates | 32 |
| ECU candidates | 15 |
| UDS command candidates | 2,315 |
| Signal candidates | 2,480 |

Repositories cover Audi A4, Audi Q7, SEAT Tarraco, Volkswagen Golf, Volkswagen ID.4 and Volkswagen Passat. This is a small community sample, not a complete VAG catalogue.

## Independent integrity checks

- All 24 source-file SHA-256 values and byte counts match the pack manifest.
- All 2,315 command-record hashes match their stored raw JSON.
- All 2,480 signal-record hashes match their stored raw JSON.
- All 15 ECU-record hashes match their stored raw JSON.
- SQLite `PRAGMA integrity_check`: `ok`
- SQLite foreign-key violations: 0
- All 2,315 commands use UDS service `0x22`.
- All command records have `execution_allowed=0`.
- All records remain `market_scope=UNKNOWN` and `verification_status=unverified_community_candidate`.

## Technical and applicability boundary

This pack contains UDS read-data signal definitions and candidate ECU headers; it is **not a DTC database or a validated diagnostic test-plan library**. It contains no DTC definitions, no approved repair procedures and no executable diagnostic commands. A Data Identifier and its byte format do not prove that a given ECU supports it on a particular vehicle.

Generation names and year ranges are community candidates. They are not promoted to verified generation/year applicability. The pack does not establish exact engine/gearbox pairs, RU/EAEU market scope, PR-code/VIN fitment or exact ECU applicability.

## Product decision

Keep the pack in a separate read-only CC BY-SA research namespace with the upstream repository revisions, file hashes, attribution and share-alike notice intact. It may support candidate discovery only. Do not merge it into the main proprietary database or enable command execution without a separate licence-compatibility review and independent technical validation.


## License-file review added 2026-11-05

The `LICENSE` file was fetched from each of the six repositories at the exact pinned commit listed in `data/source-manifests/vag-factory-source-register.json`. All six files identify **Attribution-ShareAlike 4.0 International (CC BY-SA 4.0)**. The pack therefore remains a separately licensed adapted database: retain contributor attribution and the CC BY-SA 4.0 share-alike notice for the adapted database. No repository's licence is inferred from the OBDb umbrella README alone.

The licence review confirms permission for commercial use, display, offline caching and redistribution subject to CC BY-SA terms. It does not validate technical correctness, generation mapping, ECU support, RU/EAEU market applicability or safe execution. All command execution remains disabled.


## Verified build artifact — workflow run 4, 2026-11-03

The pinned research pack was built and independently verified in [Windows workflow run 4](https://github.com/ismailizmajlov-oss/VAG-TECH-PRO/actions/runs/41562106883), source commit `eebcc64541de325ecfc26d2c2dcb1eadc0841cf0`. The uploaded artifact is ID `13198105454`, 839,847 bytes, SHA-256 `db6014167149322c8928d7f8762ea33421f7e142bd8864b0ae60307207578069`. The included SQLite database SHA-256 is `d3c54051e2f3f73c211e6d84c4e84541a60901e01eeee843b8357efa1e421aa1`; `manifest.json` SHA-256 is `29ec10e68214c66a5c3c14734b9f30e0eb9d25f0d03be3384a454c3ef1833f46`.

The pack remains a separate CC BY-SA 4.0 candidate reference and is **not integrated into the desktop installer** or product database. It has 2,315 UDS 0x22 read-command candidates, 2,480 signals, 32 generation candidates and 15 ECU candidates, but zero DTC definitions, zero approved test plans, zero exact vehicle fitments and zero exact ECU fitments. All commands are read-only reference records with execution disabled. Any future desktop inclusion must preserve all upstream license copies, contributor attribution and the CC BY-SA 4.0 share-alike notice; it must not be mixed into the main product database.


## Expanded verified pack — Windows run #521, 2026-11-10

The source lock now pins **38** OBDb repositories and **152** upstream files. The separate CC BY-SA 4.0 research pack was built in [Windows offline-pack workflow run #521](https://github.com/ismailizmajlov-oss/VAG-TECH-PRO/actions/runs/42770036360), artifact ID `13741207907` (6,209,463 bytes; SHA-256 `5555247d7d7e25db1fe9ccb50566123a867f1948bbe3f955e0593ca95b5a3e91`). The included SQLite is SHA-256 `1a5cb45b03ab9439251d329de57d667ebea3e67b1a2b2dd9aa5333c14f2ed195`; the pack manifest is `6470cb542918a6bc773ac17960f639331abea5eff34d4de22b86ac687d3ad32f`; the attribution file is `507120ae0bd921f131623cb596cfd7cfcd16fa29efe2975c9c96878ad6ad89dd`.

The new pack contains 135 generation candidates, 71 ECU candidates, 18,387 UDS 0x22 command candidates and 19,799 signal candidates. All 152 upstream file hashes and all 38 pinned licence-file hashes match the manifest. SQLite `integrity_check=ok`; foreign-key violations: 0. Every command is service `0x22`, every command has execution disabled, all rows remain `market_scope=UNKNOWN` / `unverified_community_candidate`. Seven Škoda repositories contribute generation candidates only. There are still **zero DTC definitions**, zero approved test plans, zero exact vehicle fitments, zero confirmed engine/gearbox pairs, zero repair procedures, wiring diagrams or factory pinouts.

At the time of run #521, the encompassing three-database offline bundle failed at its final index inspection because the index builder and desktop sync guard still hard-coded the old 16-source/82-generation/44-ECU/7,890-command/8,446-signal snapshot. The stale count guard was subsequently corrected. Windows x64 desktop validation run #1264 passed the offline data-pack bundle verification and included the current OBDb pack in the 15-pack desktop research manifest. This integration is research-catalog only; the pack is not imported into production SQLite.


## Current offline desktop integration — Windows run #1264, 2026-11-10

The expanded OBDb pack is included in the packaged offline desktop research manifest `data/research/manifest.json` as `obdb-vag-signals-cc-by-sa`. The exact run-1264 desktop-source audit confirms 15 research packs in the packaged manifest. The pack is integrated as a separate read-only CC BY-SA research namespace, not as production diagnostic content.

Current pinned data and manifest:
- 38 unique OBDb repositories; 152 upstream files; all 38 repository licence-file hashes are verified.
- 135 generation candidates, 71 ECU candidates, 18,387 UDS 0x22 command candidates and 19,799 signal candidates.
- SQLite SHA-256: `1a5cb45b03ab9439251d329de57d667ebea3e67b1a2b2dd9aa5333c14f2ed195`.
- Current pack-manifest SHA-256 in the run-1264 build metadata: `ce781164ff253982816fb72ebca32939b0dc772f2908b75be8179d81588bf631`.
- The separately built source-pack artifact remains Windows offline-pack workflow run #521, artifact ID `13741207907`, SHA-256 `5555247d7d7e25db1fe9ccb50566123a867f1948bbe3f955e0593ca95b5a3e91`.

The run-1264 manifest retains the strict namespace policy: included service IDs are only `0x22`; service `0x01` is excluded; `dtc_definitions_included=false`; `command_execution_allowed=false`. All 38 repository records remain `market_scope=UNKNOWN` and `unverified_community_candidate`. No DTC definitions, approved test plans, exact vehicle or ECU fitments, exact engine/gearbox pairs, RU/EAEU applicability, repair procedures, wiring diagrams or factory pinouts are created by this pack.

Windows x64 build-and-lifecycle and the separate Windows Server 2022 compatibility lifecycle passed in run #1264. This does not establish native Windows 10/11 client acceptance; that owner-controlled runner gate remains disabled. Production import and command execution remain prohibited.

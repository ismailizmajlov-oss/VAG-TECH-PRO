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

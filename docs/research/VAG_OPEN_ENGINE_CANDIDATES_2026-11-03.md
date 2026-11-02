# VAG open-data candidate acquisition — 2026-11-03

## Dataset inspected

Repository: https://github.com/gor3a/vehicle-makes-models  
Pinned revision: `ee99776470a45214bf524cdfe22e5dbf4bd67f93`  
Data license: ODbL 1.0 (`LICENSE-DATA`)  
Declared upstream source: autoevolution.com  
Attribution: credit both the dataset project and autoevolution.com. ODbL share-alike and public availability obligations apply to publicly redistributed adapted databases.

The five VAG group files were inspected in the upstream JSON structure. Counts observed:

| Group | Models | Generations | Engine variants |
|---|---:|---:|---:|
| Audi | 78 | 340 | 2,049 |
| Volkswagen | 82 | 284 | 1,710 |
| Škoda | 36 | 106 | 660 |
| SEAT | 29 | 81 | 608 |
| CUPRA | 8 | 12 | 54 |
| **Total** | **233** | **823** | **5,081** |

These are upstream dataset counts, not counts of Russian-market vehicles and not OEM-certified fitments.

## Critical data-quality finding

The five brand files contain generation names, year ranges, body type and descriptive engine variants. The inspected engine records do **not** contain explicit factory engine codes or gearbox codes. Their transmission field is a descriptive label (for example, a number of speeds/type), not a gearbox code. Therefore:

- import them only into a separate research staging database;
- retain source revision, source URL, raw JSON and hashes;
- mark market scope `UNKNOWN`;
- do not parse a short token out of a display label and call it an engine code;
- do not create exact engine–gearbox pairings from a descriptive transmission string;
- require at least one independent primary or official market-specific source before promoting any claim; two independent sources are preferred for critical fitment.

The importer `scripts/import_vag_engine_candidates.py` preserves these boundaries and asserts that the upstream schema has not unexpectedly added code fields. The GitHub Actions workflow downloads the five pinned files, imports a separate SQLite research database, checks SQLite integrity/foreign keys and uploads it as a research artifact. It never touches production SQLite.

## Independent market cross-check plan

1. Russia/EAEU: type-approval and conformity documents can establish model/type/variant evidence. They do not establish individual engine/gearbox pairings unless those codes are explicitly listed.
2. EU: national type-approval/registration datasets can establish that a model/variant existed in that market; do not treat EU registration as RU fitment.
3. North America: NHTSA manufacturer communications and TSBS metadata are useful for NAR model/year/component cross-checks only. They are not evidence of Russian fitment or ECU calibration unless the actual communication explicitly states those fields.
4. OEM service documents: use only when access and reuse rights permit the intended extraction and redistribution.

## DTC and ECU boundary

OpenVAG was inspected as a candidate DTC source. Its project README says the project is MIT licensed, but the database documentation does not establish a complete provenance chain or a separate data license for every imported definition. The dataset includes mixed formats (legacy VAG numeric codes, generic P-codes and other namespaces) and component identifiers. It does not provide a dependable vehicle/engine/gearbox/ECU HW-SW applicability matrix.

Decision: quarantine; do not import its DTC descriptions or repair solutions into production until database-level provenance and data rights are clarified. A component reference such as J104 or N75 is not an ECU identity. DTC-to-ECU applicability requires an explicit document linking the DTC to an ECU family/address/part number/HW-SW or calibration, plus exact market/vehicle scope.

## Next source acquisition targets

- Official RU/EAEU vehicle type-approval documents for model/type/variant coverage.
- Independently documented engine codes from public manufacturer technical sheets, approved technical documentation or openly licensed engineering sources.
- Gearbox codes from sources that explicitly identify the transmission code, not merely "6-speed DSG" or "8-speed automatic".
- ECU identity and DTC applicability only from a traceable technical document or lawfully reusable dataset.

No records are promoted to production by this research pass.

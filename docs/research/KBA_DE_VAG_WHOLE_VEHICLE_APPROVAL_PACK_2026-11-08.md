# KBA DE whole-vehicle VAG approval metadata pack — 2026-11-08

## Result

A separate, verifiable German-market research pack was built from the official KBA whole-vehicle type-approval XLSX under the published GovData **Datenlizenz Deutschland – Namensnennung – Version 2.0 (DL-DE BY 2.0)**. The pack is deliberately isolated from the production vehicle/repair catalog.

- Pack workflow: [run 4](https://github.com/ismailizmajlov-oss/VAG-TECH-PRO/actions/runs/42483260589)
- Source probe: [run 13](https://github.com/ismailizmajlov-oss/VAG-TECH-PRO/actions/runs/42481409966)
- Workflow artifact: `kba-de-vag-approval-research-pack-42483260589`
- Artifact ID: `13617954986`
- Artifact size: 564,619 bytes
- Artifact ZIP SHA-256: `c94046ee4d8bf7a1047753db21b4e4e0aa7b6d2a829f72970ecbfa339536b4a7`
- Artifact retention: 14 days from 2026-11-08; this CI artifact is not a permanent product distribution.

## Source provenance

- Publisher: Kraftfahrt-Bundesamt (KBA), Germany.
- Official XLSX: https://www.kba.de/DE/Themen/Typgenehmigung/Informationen_TGV/Liste_erteilter_Typgenehmigungen/liste_typgenehmigungen_Excel.xlsx?__blob=publicationFile&v=13
- GovData catalogue: https://www.govdata.de/suche/daten/liste-der-erteilten-typgenehmigungen-gesamtfahrzeug?ids=1cb74abc-7356-49bf-bb07-ef5dd9d7abfb
- Licence: DL-DE BY 2.0 — https://www.govdata.de/dl-de/by-2-0
- Source revision: `last-modified:2026-08-17T04:28:44Z;etag:70d6df0340b32bbd12e01b41e42ba210`
- Source XLSX size: 909,912 bytes
- Source XLSX SHA-256: `127ae4a1beb236b35c1983f897b7bd234d9f8809e888920a155e4b7d72ff43b4`
- Source manifest SHA-256 in the pack: `3cc08b5392683a4243c95c05f5d67319a3d84c5b0e9654722711a1a0846e93f7`
- SQLite SHA-256: `dff939d4db69573d481bdd3a2513688ae930461ee4b63c7bc8349397caf697a2`

The probe verifier initially failed because the KBA server's HTTP `Last-Modified` value was RFC 7231 text while the pinned manifest stored the same instant in ISO-8601 UTC. The verifier now canonicalizes both representations to UTC before comparison and retains strict hash, ETag, byte-size, official-host, schema and market checks. Regression tests cover equivalent and mismatching timestamps.

## Pack contents and independent verification

The source workbook contains 3,782 data rows and 116 distinct manufacturer labels. Exact source-label filtering retained 918 rows across eight labels:

| Exact KBA manufacturer label | Rows |
|---|---:|
| Volkswagen AG | 450 |
| Audi AG | 353 |
| AUDI AG | 28 |
| Audi Sport GmbH | 52 |
| Audi_Sport | 22 |
| Audi Sport | 1 |
| SEAT S.A. | 8 |
| Seat S.A. | 4 |
| **Total** | **918** |

Fourteen `Bugatti Automobiles S.A.S.` rows were excluded from the VAG-related candidate filter. Labels are preserved verbatim; no case folding, fuzzy matching or alias normalization is performed. Audi Sport corporate relation labels remain review-only/unresolved where appropriate.

The downloaded artifact was independently reopened in this run:
- ZIP SHA-256 matched the GitHub artifact digest.
- SQLite `PRAGMA integrity_check`: `ok`.
- SQLite `PRAGMA foreign_key_check`: no violations.
- `approval_records`: 918.
- Distinct manufacturer labels: 8.
- Distinct approval-number candidates: 918.
- All rows remain `market_scope=DE`, `applicability_precision=type_approval_document_metadata_only`, `review_status=research_only`.
- All 918 rows have `exact_vehicle_fitment=0`, `exact_engine_gearbox_pair=0`, `ru_eaeu_applicability=0`, `ecu_fitment=0`, `dtc_fitment=0`, and `repair_applicability=0`.
- Model year, generation, engine code and gearbox code remain NULL.

## Explicit technical limits

The KBA workbook is a whole-vehicle approval metadata list, not an individual vehicle build sheet. It does not supply separate variant/version fields, VAG factory engine codes, gearbox codes, exact engine/gearbox pairs, ECU identifiers, DTC, wiring, pinouts, torque values, adaptations or repair procedures. Approval date is not treated as model year. DE approval metadata is not RU/EAEU applicability.

## Product decision

This pack is **research-only** and has not been imported into the production SQLite catalog or the desktop offline research bundle:

- `research_pack_ingested=false`
- `product_database_ingested=false`
- `product_import_allowed=false`
- `production_import=false`
- `ru_eaeu_applicability=false`

The licence permits reuse subject to attribution and a notice that the data were modified. The pack includes the licence text, rights evidence, attribution, original source XLSX, source manifest, SQLite and build report. Its existence does not authorize any VAG technical applicability claim.

# KBA DE whole-vehicle type-approval source review — 2026-11-08

## Source and rights

- Publisher: Kraftfahrt-Bundesamt (KBA), Germany.
- Resource: [official KBA XLSX](https://www.kba.de/DE/Themen/Typgenehmigung/Informationen_TGV/Liste_erteilter_Typgenehmigungen/liste_typgenehmigungen_Excel.xlsx?__blob=publicationFile&v=13).
- Catalogue record: [GovData/Mobilithek dataset](https://www.govdata.de/suche/daten/liste-der-erteilten-typgenehmigungen-gesamtfahrzeug?ids=1cb74abc-7356-49bf-bb07-ef5dd9d7abfb).
- Licence: [Datenlizenz Deutschland – Namensnennung – Version 2.0 (DL-DE BY 2.0)](https://www.govdata.de/dl-de/by-2-0).
- The GovData record identifies the dataset as freely reusable under DL-DE BY 2.0. Reuse requires attribution and a notice where data has been modified.
- No account was created and no paid terms were accepted.

## Acquisition evidence

The 2026-11-07 request returned HTTP 503. A fresh official-source probe on 2026-11-08 returned HTTP 200.

| Property | Verified value |
|---|---|
| Last-Modified | 2026-08-17 04:28:44 GMT |
| ETag | `"70d6df0340b32bbd12e01b41e42ba210"` |
| File size | 909,912 bytes |
| XLSX SHA-256 | `127ae4a1beb236b35c1983f897b7bd234d9f8809e888920a155e4b7d72ff43b4` |
| Probe | [GitHub Actions run 13](https://github.com/ismailizmajlov-oss/VAG-TECH-PRO/actions/runs/42481409966) |
| Probe artifact | `13618031218`, ZIP SHA-256 `ae4bf438a6b6802446230bffd97f956742834ce823e4892ecc6f72ab79123e68` |
| Probe report SHA-256 | `abe7e6e357fa1bed3e020759bf822f96b99e634e4a7ede7f66ea726a6333a3b0` |

## Workbook schema

- One worksheet: `Tabelle1`; header row 3; 14 source columns including blank spacer columns.
- 3,782 non-empty data rows and 116 distinct exact manufacturer labels.
- Source fields include manufacturer, trade name, type designation, approval object, type-approval number, technical service, procedure type, approval date and emissions-approval references.
- The workbook title describes M1/N1 whole-vehicle approvals. Some raw row values use broader M/N class labels; values are retained verbatim, not normalized.

## VAG-related source-label candidates

The filter uses exact string equality only; no fuzzy matching, case folding or alias normalization.

| Exact source manufacturer label | Rows | Treatment |
|---|---:|---|
| Volkswagen AG | 450 | Make-label candidate |
| Audi AG | 353 | Make-label candidate |
| AUDI AG | 28 | Make-label candidate |
| Audi Sport GmbH | 52 | Group relationship requires review |
| Audi_Sport | 22 | Unresolved source label; no alias mapping |
| Audi Sport | 1 | Unresolved source label; no alias mapping |
| SEAT S.A. | 8 | Make-label candidate |
| Seat S.A. | 4 | Make-label candidate |
| **Total included** | **918** | **Research-only candidate rows** |

`Bugatti Automobiles S.A.S.` occurs in 14 source rows but is excluded because the KBA row does not establish its historical/current group relationship for this scope. The exact raw label is retained in the exclusion policy.

Approval dates in the included rows range from 2019-01-08 through 2026-06-30. These are approval dates, not model years or production dates.

## Applicability boundary

This is a German type-approval metadata list, not a vehicle build sheet. It does not provide separate variant/version/revision fields in the inspected schema. It does not establish exact vehicle fitment, model year, generation, engine code, gearbox code or their pairing, ECU, DTC, repair procedure, wiring diagram, pinout, torque value, adaptation, service interval, or Russian/EAEU applicability.

The permitted next step is a separate DE-only research SQLite pack with raw source values, per-row SHA-256, source revision and snapshot hash, licence, attribution and explicit research-only flags. It must remain outside the production vehicle/powertrain catalog. No production import is authorized by this review.

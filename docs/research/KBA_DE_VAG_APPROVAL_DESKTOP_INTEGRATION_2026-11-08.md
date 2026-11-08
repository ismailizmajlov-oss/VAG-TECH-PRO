# KBA DE whole-vehicle type-approval research integration

Date: 2026-11-08

## Scope

This change integrates the independently built KBA whole-vehicle type-approval snapshot into the Windows desktop's **separate offline research namespace**. It does not add rows to the production vehicle catalog and does not make repair or fitment claims.

Source:
- KBA workbook: https://www.kba.de/DE/Themen/Typgenehmigung/Informationen_TGV/Liste_erteilter_Typgenehmigungen/liste_typgenehmigungen_Excel.xlsx?__blob=publicationFile&v=13
- GovData catalogue: https://www.govdata.de/suche/daten/liste-der-erteilten-typgenehmigungen-gesamtfahrzeug?ids=1cb74abc-7356-49bf-bb07-ef5dd9d7abfb
- Licence: DL-DE BY 2.0 — https://www.govdata.de/dl-de/by-2-0

## Independently inspected source pack

The existing KBA build artifact was downloaded and inspected before integration.

- Artifact SHA-256: 4658837938dffe3ee46abd2ac29f99c7e719adad93537edad21617ff4141251d
- Original XLSX SHA-256: 127ae4a1beb236b35c1983f897b7bd234d9f8809e888920a155e4b7d72ff43b4
- SQLite SHA-256: 328306d68902eb837a2d60aa69e47e6524d52b88f2976167a97e53ec0ee2e23c
- Source-manifest SHA-256: 4303ad532e1f96238d60a957b90b2753e9a35d2e1cda2bc58fdc29c8de1d9561
- Source revision: last-modified:2026-08-17T04:28:44Z;etag:70d6df0340b32bbd12e01b41e42ba210
- Original rows: 3,782
- VAG-related exact-label candidates: 918
- Exact manufacturer labels retained: 8
- Distinct approval numbers: 918
- Date range: 2019-01-08 through 2026-06-30
- SQLite integrity_check: ok
- SQLite foreign-key violations: 0

The integration rechecks the published licence, all rights flags, source-manifest and builder hashes, source XLSX hash, SQLite hash, row-level SHA-256 values, schema, indexes, counts and applicability flags. The original XLSX is retained in the desktop research pack with attribution and a modified-data notice.

## Desktop behaviour

A separate KBA · DE approvals research tab exposes raw approval-document metadata:
- manufacturer label, trade name and type designation;
- approval object and type-approval number;
- approval date and emissions-member-state field;
- source row, source revision, row hash, snapshot hash and source-manifest hash.

The UI explicitly states that the approval date is **not** a model year and that approval metadata are not individual-vehicle build data.

## Hard boundaries

Every row remains:
- market DE;
- precision type_approval_document_metadata_only;
- status research_only;
- exact vehicle fitment: false;
- model year and generation: absent;
- engine code and gearbox code: absent;
- exact engine/gearbox pair: false;
- ECU, DTC and repair applicability: false;
- RU/EAEU applicability: false;
- diagnostic execution: disabled.

Unresolved Audi Sport labels remain candidates only. Bugatti Automobiles S.A.S. remains excluded by the exact-label policy; no corporate-group inference is introduced.

The pack is not merged with generic OBD-II data, VAG-specific DTC, engine/transmission pairing or production catalog records. It is not evidence for Russian/EAEU approvals.

## Windows validation

The Windows workflow resolves the latest successful KBA approval-pack artifact, checks its artifact digest, independently validates the pack before copying it, runs the read-only SQLite reader and UI contract tests, verifies the central research-pack manifest, and exercises an offline API search in the installer lifecycle. The pack is packaged as research data only.

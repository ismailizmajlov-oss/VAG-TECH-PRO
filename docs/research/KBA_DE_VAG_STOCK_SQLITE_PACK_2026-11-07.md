# KBA Germany VAG stock research pack

**Status:** verified research-only pack; not production vehicle fitment.

## Source and licence

- Publisher: Kraftfahrt-Bundesamt (KBA), published through GovData/Mobilithek.
- Dataset: FZ Hersteller Handelsnamen Pkw.
- Dataset page: https://www.govdata.de/suche/daten/fz-hersteller-handelsnamen-pkw?ids=638594fd-195a-4e03-b91c-f5ea2eacfa39
- Resource: public ArcGIS CSV item d277ec18ff1e442597c9411d7c1aaeaa, layer 0.
- Licence: Datenlizenz Deutschland – Namensnennung – Version 2.0 (DL-DE BY 2.0): https://www.govdata.de/dl-de/by-2-0
- Commercial use, display, offline caching, bulk reuse and redistribution are allowed subject to attribution and a notice describing modifications. The pack includes both the licence reference and attribution text.

## Acquired snapshot

- Observed source revision: ArcGIS item modified 2026-08-05T07:52:21Z.
- Download date: 2026-11-07.
- Source CSV: 1,047,991 rows, 65,366,675 bytes.
- Source CSV SHA-256: 03bd9f85e384b2b8bcd0e7d80b5f755eca568e9ad1c45e7fb3fe512e7fedc468.
- Source manifest SHA-256: c40e207200762a9c901a20c024236f84b78699b0d8a68067e0f0a5db13b9e46d.
- Exact VAG-group manufacturer labels: eight, matched by exact normalized label only: Volkswagen (D), Audi (D), Audi (H), Škoda (CZ), SEAT (E), Porsche, Bentley (UK), Lamborghini (I).

## SQLite pack

- Database: kba-de-vag-stock-research.sqlite.
- Database size: 47,071,232 bytes.
- Database SHA-256: c61720c363d1f26a2618e16b420c91559634b90347149b312eb18e23be054111.
- Source rows: 1,047,991.
- Filtered stock observations: 264,847.
- Unique manufacturer/trade-name pairs: 802.
- Unique manufacturer/raw-type-key pairs: 4,155.
- Unique manufacturer/trade-name/type-key/reference-date tuples: 16,301.
- Federal states: 17.
- Reference dates: 2023-01-01, 2024-01-01, 2025-01-01, 2026-01-01.
- Row provenance: SHA-256 over canonical JSON of the original parsed CSV field strings without trimming; original column names are retained. The exact source-file hash is also stored.

## Applicability boundary

This dataset is **Germany-only aggregate stock data**. Typschlüssel is preserved as a raw KBA field and is not promoted to HSN or confirmed TSN. Berichtszeitpunkt is an annual stock reference date, not model year or generation. Anzahl is an aggregate count, not an individual vehicle record.

The pack does not contain or infer:
- individual VINs or vehicle build sheets;
- exact model/year/generation fitment;
- engine codes, gearbox codes or an engine/gearbox pair;
- ECU, DTC, test plans, repair procedures, wiring diagrams or torque values;
- Russian/EAEU applicability.

The pack is visible only in a separate research namespace. product_import_allowed=false, production_import=false, exact_vehicle_fitment=false, exact_engine_gearbox_pair=false and ru_eaeu_applicability=false. It must never be joined to the production vehicle-fitment graph.

## CI provenance

- KBA pack workflow run #3: https://github.com/ismailizmajlov-oss/VAG-TECH-PRO/actions/runs/42327842556
- Artifact SHA-256: cb61541e6ac5ad6c3eea2fba9fb2947cc6c83a63aea4f8777beb67b017536d82.
- Builder SHA-256: 4fdfd91ea7d5e5486f0de922767e8fba1dc4897625c24407fbffe09b8da45a32.
- The workflow re-downloads the public source, verifies its byte size and SHA-256, checks the exact manufacturer allowlist and schema, builds SQLite transactionally, recomputes every included row hash against the source CSV, runs integrity_check and foreign_key_check, and uploads the raw CSV plus pack for a 90-day audit window.

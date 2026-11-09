# EEA VAG type-approval variant research pack — 2026-11-10

## Purpose

Add a separately licensed, offline-readable research reference for exact core VAG make labels found in the European Environment Agency (EEA) passenger-car registration dataset. This is an auxiliary EU-market source, not a replacement for Russian/EAEU OTTS and not a factory repair database.

## Source and rights

- Publisher: European Environment Agency (EEA), Directorate-General for Climate Action (DG-CLIMA).
- Licence: CC BY 4.0, as declared by the official EEA dataset metadata.
- 2024 final metadata: https://sdi.eea.europa.eu/catalogue/datahub/api/records/5018ec17-2348-4c92-8761-6f2377bbd1c0?language=eng
- 2025 provisional metadata: https://sdi.eea.europa.eu/catalogue/datahub/api/records/b4044b06-2e6b-4f8e-a6e6-66e0e98bb0dd?language=eng
- SQL REST API documentation: https://discodata.eea.europa.eu/Help.html
- API endpoint: https://discodata.eea.europa.eu/sql
- Required attribution and indication of modifications are retained in the pack. No EEA endorsement is implied.

The source register is the authoritative rights gate. The builder refuses to run unless the register declares CC BY 4.0, commercial use, display, offline caching, bulk reuse and redistribution with attribution, and keeps product fitment import disabled.

## Acquisition scope

The Windows x64 workflow queries two versioned EEA tables:

| Dataset | Table | Year | Status |
|---|---|---:|---|
| 2024 final | \`CO2Emission.latest.co2cars_2024Fv30\` | 2024 | F |
| 2025 provisional | \`CO2Emission.latest.co2cars_2025Pv31\` | 2025 | P |

Only exact source make labels that normalize to Volkswagen, Audi, Škoda, SEAT or CUPRA are included. Raw labels are preserved. The builder does not infer group membership for Porsche, Bentley or other manufacturers.

The workflow discovers the source's raw make labels first, counts matching rows before download, enforces row/response/page limits, stores raw API response pages, and computes SHA-256 for each page, each normalized record, the filtered snapshot, the source manifest and the SQLite database.

## Data semantics and safety boundary

The pack is a research-only table of EEA-reported new M1 passenger-car registration/type-approval variants. It preserves reporting Member State, registration year, final/provisional status, make, commercial name, type, variant, version, type-approval number and selected technical attributes.

It does **not** establish:
- Russian or EAEU market coverage;
- model year, production date or generation;
- an individual vehicle's exact configuration or VIN fitment;
- a factory VAG engine code or gearbox code;
- an engine/gearbox pairing;
- ECU hardware/software applicability, DTC applicability or diagnostic test plans;
- wiring diagrams, pinouts, torque values, adaptations, service intervals or repair procedures.

Registration year is not model year. Engine capacity and power are raw source attributes, not factory engine codes. Type approval number/type/variant/version remain source identifiers. 2024 final and 2025 provisional records are kept distinct. All rows remain \`candidate_only\`; exact-fitment flags are fixed to false and product import is fixed to false.

## Build and verification

The workflow \`.github/workflows/build-eea-vag-approval-research-pack.yml\` runs on Windows x64. It runs regression tests, acquires the pinned EEA tables, creates a separate SQLite database and raw response snapshots, then reopens the database to verify integrity, foreign keys, raw-page hashes, row hashes, source provenance and non-fitment invariants.

The workflow artifact's \`pack-manifest.json\` is the authoritative record of actual row counts, raw make labels, source revisions and SHA-256 values. No counts or dataset hashes are asserted in this document before a successful live acquisition.

## Live acquisition status

The first documented SQL API probe from the GitHub-hosted Windows Server 2025 runner returned HTTP 403 while requesting distinct raw make labels from the pinned 2024 final table. The response body was not captured, no dataset bytes were received, and no dataset SHA-256 or row count is claimed. The source register records the attempt. The builder now retries with standard Discodata origin/referer headers and records any returned 403 response body for diagnosis. If access remains denied, the pipeline must stop and use only an EEA-supported export or access clarification; it must not switch to undocumented endpoints or circumvent the restriction.

The resulting pack must remain in the research namespace. It must not be imported into the production vehicle catalog or used to confirm repair applicability.

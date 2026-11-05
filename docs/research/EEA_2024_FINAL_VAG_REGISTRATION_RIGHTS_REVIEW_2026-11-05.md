# EEA 2024 final passenger-car registration evidence — source and rights review

Review date: 2026-11-05

## Source identity

- Publisher: European Environment Agency (EEA) / European Commission Directorate-General for Climate Action (DG-CLIMA).
- Dataset: *Monitoring of CO2 emissions from passenger cars — 2024 final*.
- Dataset revision/table: `co2cars_2024Fv30` / `[CO2Emission].[latest].[co2cars_2024Fv30]`.
- Dataset DOI: [10.2909/5018ec17-2348-4c92-8761-6f2377bbd1c0](https://doi.org/10.2909/5018ec17-2348-4c92-8761-6f2377bbd1c0).
- Metadata record: https://sdi.eea.europa.eu/catalogue/srv/api/records/5018ec17-2348-4c92-8761-6f2377bbd1c0
- Public SQL endpoint: https://discodata.eea.europa.eu/sql

## Rights decision

The dataset metadata identifies the data under Creative Commons Attribution 4.0 International (CC BY 4.0): https://creativecommons.org/licenses/by/4.0/. The license permits commercial reuse, display, offline caching, bulk reuse and redistribution subject to attribution and indication of changes. The app keeps this dataset in a separate research pack and includes a license notice, attribution, the pinned source lock, exact SQL query, raw API page snapshots, per-page SHA-256, row SHA-256, snapshot SHA-256 and SQLite SHA-256.

The attribution notice states that the data was filtered to the listed Volkswagen Group makes, restricted to 2024 final records, aggregated by market and type-approval/type/variant/version plus available powertrain descriptors, normalized, and stored as a read-only SQLite pack.

## Data scope

The source scope is EU-27 plus Iceland and Norway. It is not a Russian or EAEU source. The pack records each source country code separately. It is limited to passenger-car registration/CO2 monitoring evidence for registration year 2024.

The query is bounded to the pinned table, final status, registration year 2024 and an explicit VAG-make whitelist. It groups rows by country, make, commercial name, type-approval number, type, variant, version, fuel type/mode, engine capacity and engine power. The result is a registration-variant candidate index, not an individual vehicle registry.

## Applicability boundary — mandatory

- Registration year is not model year.
- Type/variant/version are type-approval identifiers, not VAG PR codes or internal generation identifiers.
- Engine displacement and power are not factory engine codes.
- The source does not establish gearbox codes, ECU applicability, PR-code applicability, VIN-level fitment, DTC, repair procedures, wiring diagrams, pinouts, torque values, adaptations or OEM parts.
- No exact vehicle fitment or repair instruction may be inferred from this pack.
- No Russian/EAEU coverage may be claimed.

Every row is marked `source_published_registration_record_candidate`, `fitment_status=not_established`, and `applicability_precision=type_approval_variant_version_registration_evidence`. The schema and verifier require model year, engine code and gearbox code to remain null; all exact-fitment and diagnostic/repair execution flags remain false.

## Build and verification gate

The Windows desktop CI must acquire the data from the public EEA SQL endpoint, preserve raw response pages, build the pack transactionally, and pass:
1. source-lock and CC BY 4.0 rights checks;
2. page/query/row/database SHA-256 checks;
3. SQLite integrity and foreign-key checks;
4. make and country whitelist checks;
5. candidate count and no-fitment-claim checks;
6. offline API search and lifecycle checks after clean install and in-place upgrade.

An API/schema failure, empty result, unexpected make/country, rights mismatch, excessive result count or provenance mismatch must fail the build. No empty or partially verified pack is packaged.

## Decision

Allow only a separate, read-only EEA registration-evidence research pack under CC BY 4.0 with attribution. Do not merge it with VAG-specific DTC, repair, ECU or exact-fitment namespaces. This source does not resolve the Russian/EAEU OTTS data gap.

# EEA passenger-car type-approval variant data — source and rights review

**Reviewed:** 2026-11-10  
**Source decision:** rights-approved for a separate offline research pack with attribution; no dataset rows imported yet.

## Official datasets reviewed

- **2024 final:** EEA metadata record 5018ec17-2348-4c92-8761-6f2377bbd1c0, table family CO2Emission.latest.co2cars, final status F, metadata revised 2026-08-19.
- **2025 provisional:** EEA metadata record b4044b06-2e6b-4f8e-a6e6-66e0e98bb0dd, table CO2Emission.latest.co2cars_2025Pv31, provisional status P, metadata revised 2026-08-19.
- The EEA metadata declares CC BY 4.0 and no limitations to public access. The license permits offline caching, display and redistribution with attribution and indication of modifications; it does not permit implying EEA endorsement or adding restrictions.

## Intended research-pack scope

The dataset concerns newly registered M1 passenger cars reported by EU Member States, Iceland and Norway. The available years are 2019–2024 final and 2025 provisional. The source fields include reporting Member State, registration year, make, commercial name, type, variant, version, type-approval number, fuel type/mode, engine displacement, engine power, mass, wheelbase, track width, WLTP CO2 and grouped registration count.

The intended pack will retain raw EEA identifiers and values, per-row source revision, raw-response SHA-256, database SHA-256, license evidence and field-level provenance. The VAG make filter must be discovered from the actual EEA data and checked against the official Volkswagen Group brand portfolio; no VAG make values or row counts are claimed yet.

## Strict applicability boundary

This is an official EEA registration/type-approval variant reference, not an OEM repair database. Registration year is not model year. Type, variant, version and type-approval number do not establish an engine code, gearbox code or exact engine/gearbox pairing. The source does not provide ECU mapping, DTC, wiring, pinouts, torque values, adaptations, repair procedures or service intervals. The 2025 provisional edition may change and must remain separate from final years.

Any future import will be a separate research SQLite pack, never a confirmed VAG fitment table. Each row will remain a source-verified candidate until independently matched to an authorized OEM source.

## Acquisition status

No Discodata query, bulk download or source-byte acquisition has been performed in this review. No dataset SHA-256 or row count is claimed. The source register therefore records data_ingested=false, source_snapshot_sha256=null and product_import_allowed=false. A Windows-only discovery run will first verify the EEA API schema and actual raw make strings; full acquisition is a separate gated step.

## Evidence

- EEA 2024 final metadata: https://sdi.eea.europa.eu/catalogue/datahub/api/records/5018ec17-2348-4c92-8761-6f2377bbd1c0?language=eng
- EEA 2025 provisional metadata: https://sdi.eea.europa.eu/catalogue/datahub/api/records/b4044b06-2e6b-4f8e-a6e6-66e0e98bb0dd?language=eng
- CC BY 4.0 legal code: https://creativecommons.org/licenses/by/4.0/
- Volkswagen Group brands and brand groups: https://www.volkswagen-group.com/en/brands-and-brand-groups-15811

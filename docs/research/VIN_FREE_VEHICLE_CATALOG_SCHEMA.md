# VIN-free VAG vehicle catalog schema

Status: schema design and executable guards; no vehicle records are asserted by this change.

## Scope

This schema models the catalogue hierarchy without VIN functionality:

`make → model → generation/type → variant → engine code / transmission code`

Engine-to-variant, transmission-to-variant, and exact engine/transmission pair relationships are separate evidence-backed records. A model-year range is descriptive metadata and never establishes a powertrain fitment by itself.

## Tables

- `vehicle_makes`, `vehicle_models`, `vehicle_generations`, `vehicle_variants`: normalized taxonomy.
- `engine_codes`, `transmission_codes`: distinct factory code dictionaries.
- `vehicle_catalog_sources`, `vehicle_catalog_evidence`: source provenance, revision, market, locator, hash and rights.
- `engine_fitments`, `transmission_fitments`, `powertrain_pair_evidence`: explicit supported relationships.

## Publication gates

1. Every fitment link references a source evidence record of the corresponding claim type.
2. An engine/transmission pair requires explicit `engine_transmission_pair` evidence; independent engine and gearbox fitments do not prove that pair.
3. Evidence can be promoted only when redistribution is explicitly allowed and the license is recognized.
4. Research-only, unknown-rights and proprietary sources remain non-publishable.
5. No VIN, VIN decoder, VIN query, VIN lookup, or VIN-based identity table is part of this schema.

## Source candidate boundary

VehiclesDB publishes a CC-BY 4.0 model/make taxonomy assembled from official registers in the countries listed in its source manifest. Its public README says the model-level dataset does not provide full technical configurations; it is suitable only as a candidate skeleton for makes/models where the source evidence covers the market. It does not supply VAG engine codes, gearbox codes, or exact engine/gearbox pairings. The required attribution must be preserved. See https://github.com/vehiclesdb/vehiclesdb and its `SOURCES.md` / `ATTRIBUTION.md`.

No VehiclesDB rows are imported by this schema-only change. No Russian-market coverage is assumed from the presence of a global model name.

## EAEU OTTS evidence (descriptor-only)

The additive SQLite schema in `data/sql/otts-type-approval-evidence.sql` introduces:

- `vehicle_catalog_source_rights`: explicit rights for commercial use, display, offline caching, bulk reuse and separately PDF redistribution, with license-text SHA-256, attribution, permission reference and review revision.
- `eaeu_otts_evidence`: approval descriptors with issuing member state, approval number/revision, form revision, market scope, manufacturer/make/model/type, engine make/type, ECU marking, gearbox make/type and ratios, evidence locator, source revision, source-snapshot SHA-256 and normalized-record SHA-256. Cached PDFs have their own SHA-256.

The evidence table has no VIN, factory engine-code or factory gearbox-code column and no foreign key to `engine_codes` or `transmission_codes`. Its `applicability_precision` is fixed to `type_approval_descriptor`; the form's engine, ECU and gearbox markings cannot be promoted to exact VAG fitment by changing a status. Exact links still require separate evidence in the engine, transmission and powertrain-pair tables.

Insert requires explicit commercial-use, display, offline-cache and bulk-reuse rights. PDF caching separately requires PDF redistribution permission. Publication requires a known market and member state, complete source/form revision and hash provenance, an evidence locator and prior technical verification. Rights narrowing or revocation automatically demotes published records. Metadata-only publication remains possible when PDF redistribution is not granted, provided metadata reuse rights are approved.

The EAEU form mapping follows Decision No. 232 as amended by Decision No. 52 effective 2026-06-14. These fields are type-approval descriptors, not guaranteed VAG factory codes or exact individual-vehicle fitment. The schema test uses synthetic fixtures only; no OTTS records are imported.

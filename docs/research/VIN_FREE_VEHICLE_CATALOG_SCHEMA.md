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

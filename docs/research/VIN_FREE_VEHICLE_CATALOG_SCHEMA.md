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

The additive SQLite schema in `data/sql/otts-type-approval-evidence.sql` introduces two tables:

- `vehicle_catalog_source_rights`: explicit, revisioned rights for commercial use, display, offline caching, bulk reuse and (separately) PDF redistribution, with license-text SHA-256, attribution and permission reference.
- `eaeu_otts_evidence`: type-approval document descriptors with issuing member state, approval number/revision, form revision, market scope, manufacturer/make/model/type, engine make/type, ECU marking, transmission/clutch/gearbox make/type, ratios, evidence locator, source revision, source-snapshot SHA-256 and normalized-record SHA-256. A cached PDF has its own SHA-256.

The table deliberately has no VIN, factory engine-code or factory transmission-code column and no foreign key to `engine_codes` or `transmission_codes`. `applicability_precision` is fixed to `type_approval_descriptor`; the raw OTTS engine/gearbox/ECU markings cannot be promoted to exact VAG fitment by changing a status field. Exact powertrain links still require separate evidence in `engine_fitments`, `transmission_fitments` and `powertrain_pair_evidence`.

Import is blocked unless the source registry and its rights record both explicitly allow commercial use, display, offline caching and bulk reuse. PDF caching additionally requires PDF redistribution rights. Publishing requires a known market and issuing state, a source locator, source/form revisions, source and record hashes, and prior technical verification. Narrowing or revoking rights automatically demotes published evidence; deleting the rights record does the same. Metadata-only OTTS publication remains possible when PDF redistribution is not granted, provided the metadata reuse rights are independently approved.

The review state machine is fail-closed: new rows must enter as `candidate`; source review, technical verification, publication and rejection require explicit timestamped notes and ordered transitions. Direct insertion as verified/published and skipped review stages are rejected. Published source facts and technical descriptors are immutable while publication status is retained; a correction must first demote the row to `candidate`, then pass the review stages again. Rights revocation can always demote a row, including when the source changes or the rights record is deleted.

The form mapping is based on the EAEU OTTS technical annex (Decision No. 232, as amended by Decision No. 52 effective 2026-06-14). The form can contain engine make/type, ECU marking, gearbox make/type and ratios, but those remain type-approval descriptors—not guaranteed VAG factory codes or exact individual-vehicle fitment.

Regression test: `scripts/test-otts-type-approval-evidence.py`. The Windows x64 workflow run `41592713974` passed all three schema suites: VIN-free catalog/evidence gates, OTTS rights/descriptor/PDF-cache/revocation/market/provenance gates, and DTC namespace/applicability gates. The fixtures are synthetic and are not product data; no OTTS records were imported.

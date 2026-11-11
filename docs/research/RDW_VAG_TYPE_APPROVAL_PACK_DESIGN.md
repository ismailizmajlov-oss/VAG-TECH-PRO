# RDW VAG type-approval research pack design

## Purpose and status

This design defines a separate, read-only research projection of six RDW Open Data datasets published with CC0 1.0 in the Dutch national data catalogue. The projection is limited to VAG-group make labels observed in the RDW registered-vehicle dataset and the exact EU type-approval scope keys that those observations expose.

It is **not** a production vehicle-fitment catalog, a VAG factory build sheet, a model-generation catalog, or a repair-data source. It must not be used to assert that an individual vehicle has a specific engine, gearbox, ECU, DTC, wiring configuration, or repair procedure.

## Rights and source set

The six source datasets are:

| Dataset | RDW ID | Role |
|---|---|---|
| Basisregistratie Voertuigen / Gekentekende voertuigen | **m9d7-ebf2** | Discover non-identifying NL make/trade-name/type-approval observations |
| TGK Aandrijving Uitvoering | **4by9-ammk** | RDW engine-designation observations (motorcode) |
| TGK Versnelling Uitvoering | **7rjk-eycs** | RDW gearbox-type classifications (codetypeversnellingsbak) |
| TGK Basis Uitvoering | **byxc-wwua** | Approval-scope base/revision attributes |
| TGK Merk Uitvoering | **kyri-nuah** | RDW make-code observations (merkcoderdw) |
| TGK Handelsbenaming Fabrikant | **x5v3-sewk** | Manufacturer trade-name/type-designation observations |

Official catalog evidence is recorded in data/source-manifests/rdw-eu-vag-type-approval-open-data.json and the central data/source-manifests/vag-factory-source-register.json. The pack builder fails closed unless the source identity, six dataset IDs, CC0 1.0 license statements, and offline/bulk/redistribution rights flags match those records.

Catalog URLs:

- https://data.overheid.nl/dataset/basisregistratie-voertuigen---rdw
- https://data.overheid.nl/dataset/81ac19f5-d0e5-4411-847e-f8698d4a42f2
- https://data.overheid.nl/dataset/8a5be559-87b6-4224-9bbc-45dae886c427
- https://data.overheid.nl/dataset/38afb954-4d3b-4363-9875-4a16117ab86b
- https://data.overheid.nl/dataset/68f02697-4c7a-4a5c-ae1d-b253aa3ecc89
- https://data.overheid.nl/dataset/1f00bd5c-63e9-4262-9603-311712339a30

## Privacy and field allowlist

The registered-vehicle dataset is queried using an explicit allowlist only:

- merk
- handelsbenaming
- typegoedkeuringsnummer
- variant
- uitvoering
- volgnummer_wijziging_eu_typegoedkeuring
- voertuigsoort
- cilinderinhoud
- aantal_cilinders

The query does not select registration plate, VIN/chassis number, holder, owner, address, postcode, or personal fields. datum_eerste_toelating is deliberately not selected and must never be relabelled as model year. Any forbidden field returned by the API causes acquisition to fail.

## Exact approval scope

Every approval scope is keyed by the exact tuple:

**typegoedkeuringsnummer + variant + version/uitvoering + revision**

The scope ID is SHA-256 over canonical JSON of those four values. TGK rows are admitted only when all four values match a registration observation exactly. A matching type-approval number alone is insufficient.

Each selected source row is hashed independently as SHA-256 over canonical JSON of the allowlisted row projection. Each dataset projection file and the combined projection bundle also have SHA-256 values. The source revision is taken from RDW dataset metadata before acquisition and checked again after acquisition; a revision change aborts the build.

The pack is a **filtered source projection**, not a full upstream snapshot. Consequently, source_snapshot_sha256 remains null. source_projection_bundle_sha256 identifies the exact six filtered projections and their source revisions.

## SQLite model and non-pairing rule

The SQLite pack stores:

- source_registry: six CC0 source records, revisions, query/projection hashes and row counts.
- approval_scope: exact approval/variant/version/revision keys with NL market scope and explicit false/null fitment fields.
- registration_observation: make and trade-name observations from the non-identifying registration projection.
- tgk_drive: RDW engine-designation candidates.
- tgk_gearbox: RDW gearbox-type classification candidates.
- tgk_base, tgk_make, tgk_trade_name: separate source observations.
- database_info: schema and pack-level safety/provenance flags.

There is deliberately no engine/gearbox pair table or view. Engine and gearbox rows are stored in separate tables and are never cross-joined into a pairing claim. A shared approval scope only means that the source records refer to the same approval/variant/version/revision scope; it does not prove that an engine and gearbox were installed together in a specific build.

## Applicability semantics

| Field | Permitted interpretation |
|---|---|
| motorcode | RDW engine-designation candidate; not independently confirmed as a VAG factory engine code |
| codetypeversnellingsbak | RDW approval gearbox-type classification; not a VAG gearbox code |
| handelsbenaming | Dutch registration trade-name observation; not a VAG generation |
| handelsbenamingfabrikant | Manufacturer trade-name candidate; not a generation |
| approval number / variant / version / revision | Exact RDW approval-scope identity only |

The pack explicitly sets all of the following to false or null:

- model year and VAG generation;
- individual-vehicle and production fitment;
- exact VAG engine code and exact VAG gearbox code;
- exact engine/gearbox pairing;
- ECU, DTC, diagnostic test-plan, repair, wiring, pinout, torque and adaptation applicability;
- RU/EAEU applicability.

## Build and verification

The Windows 2022 x64 workflow:

1. compiles the acquisition and verifier scripts;
2. runs unit tests for CC0 gates, privacy, Socrata query syntax, exact-scope hashing, separate engine/gearbox tables, tamper detection and rollback;
3. fetches metadata revisions and checks required dataset columns;
4. downloads only the filtered VAG projections, with bounded pages and retries;
5. re-checks dataset revisions after acquisition;
6. writes six projection JSON files with row hashes and a separate SQLite database in one transaction;
7. runs an independent verifier over the projection files, database hash, SQLite integrity, foreign keys, row hashes, exact-scope keys, market scope, license, privacy and no-pair policy.

The resulting pack remains research_pack_only=true, product_import_allowed=false, and production_import_allowed=false. It may be shown in a clearly labelled research/source-evidence view after separate desktop integration; it must not be promoted to production fitment without additional independent evidence and review.

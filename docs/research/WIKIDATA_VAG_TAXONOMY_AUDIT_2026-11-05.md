# Wikidata VAG identity pack — independent artifact audit

Audit date: 2026-11-04 UTC  
Scope: source/artifact integrity and candidate-only classification; this is not a vehicle-applicability review.

## Pinned source and rights

- Publisher: Wikidata / Wikimedia Foundation
- Endpoint: https://query.wikidata.org/sparql
- Source revision: `wikidata-snapshot-2d10b144bc8f`
- Data licence: CC0-1.0; the pack manifest records commercial use, display, offline caching, bulk reuse and redistribution as allowed.
- GitHub Actions run: `41875660206`
- Artifact ID: `13346487773`
- Artifact ZIP SHA-256: `5b6ec0423ceaab6dcd7f2ba69cc968fc38c19cf868b9c5eb277a18ec85966b03`
- Snapshot SHA-256: `2d10b144bc8f96016fde9488f91c3db8187d4649c4d07505d818221e51934387`
- SPARQL query SHA-256: `f8fbeb478d48887b9bc458f29f5e8369fc1bc3327dace391154ba1cefa5b027a`
- SQLite SHA-256: `660e9458fea3477fc877014f0a3db9b1857f2988a83c0efd39801723598235bc`

Only Wikidata structured statements are included. No Wikipedia article prose, Wikimedia images, logos or linked third-party documents are copied.

## Independently checked counts

| Record | Count |
|---|---:|
| Vehicle-model entities | 376 |
| Source bindings | 376 |
| Distinct manufacturer labels | 5 |
| Russian model labels | 171 |
| Date statements | 21 |

Manufacturer label counts in this snapshot:

| Manufacturer label | Model entities |
|---|---:|
| Audi AG | 118 |
| SEAT | 92 |
| Volkswagen | 39 |
| Volkswagen Commercial Vehicles | 4 |
| Škoda Auto | 123 |

The acquisition whitelist contains additional labels (including Porsche, Bentley, Lamborghini and Bugatti), but no entities for those labels were present in this snapshot. Their absence is not evidence that such models do not exist.

All 21 date statements are Wikidata inception statements (P571); no dissolution statements were present. These statements are not converted into production-year ranges.

## Integrity checks

- SQLite `PRAGMA integrity_check`: `ok`
- SQLite foreign-key violations: 0
- Snapshot bindings independently re-hashed against the SQLite `source_bindings` table: 376/376 match
- Model-to-source-binding cardinality mismatches: 0
- Rows violating the candidate-only market/applicability flags: 0
- Query result limit: 3,000; limit not reached

The artifact's ZIP digest, snapshot digest, query digest and SQLite digest match the pinned manifest.

## Applicability boundary

Every row remains:

- `market_scope=UNKNOWN`
- `applicability_precision=candidate_identity_only`
- `review_status=candidate`
- exact vehicle fitment = false
- generation verified = false
- engine-code fitment = false
- transmission-code fitment = false
- ECU fitment = false
- DTC fitment = false
- repair-procedure fitment = false
- production years inferred = false

Some labels contain body-code or generation-like text (for example, Audi A1 8X and Audi A3 8P). Those strings remain source labels only; they are not promoted to verified generation entities or year ranges. The pack contains no engine/gearbox codes, ECU identities, DTCs, test plans, repair procedures, wiring, pinouts, torque values, adaptations, OEM parts or VIN fitment.

## Product decision

Keep this pack in a separate read-only identity-candidate namespace. It may support discovery and candidate-name search only. It must not populate production vehicle configurations, establish generation/year applicability, create engine/gearbox pairs, or make technical records actionable. No production fitment rows were imported by this audit.

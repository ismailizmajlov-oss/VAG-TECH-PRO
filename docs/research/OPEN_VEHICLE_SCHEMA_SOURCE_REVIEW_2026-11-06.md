# Open Vehicle Schema candidate review — 2026-11-06

## Decision

**Do not import the reference dataset.** The repository is useful as a proposed general vehicle-data schema, but its pinned reference dataset contains no records. No VAG identity, generation, engine or transmission values can be obtained from the observed snapshot.

The root repository has an MIT license file. No separate data license or explicit statement defining the license scope for the reference data was found. The repository README says the identifiers are derived from public, non-proprietary information, but it does not provide row-level source citations or upstream dataset provenance. The empty data files make the current dataset unusable regardless of the licensing question.

## Pinned repository evidence

- Repository: https://github.com/ChristianJStarr/open-vehicle-schema
- Reviewed revision: `d7223f3edfe4adcebf22d3ffa7a60599ae25016c`
- Commit date: 2025-11-26T04:58:13Z
- Observed repository history: one initial commit; no release was listed.
- Root license: MIT; dataset-specific license scope not explicit.
- Market scope: UNKNOWN.
- VAG records observed: 0.

The following four reference files were fetched at the pinned revision. Each contained exactly five bytes (`[]\n\n\n`), zero JSON records, and the same Git blob SHA:

| File | Bytes | Records | Git blob SHA | SHA-256 |
|---|---:|---:|---|---|
| `data/reference/vehicles.json` | 5 | 0 | `9f1c8a72514a9f9f252f3959a732d40a914b2cc8` | `e4cf0694d2bd3ba2d319ba1552ee9f0d33eb1e8a6ddd0ce53b17921dd39da75c` |
| `data/reference/engines.json` | 5 | 0 | `9f1c8a72514a9f9f252f3959a732d40a914b2cc8` | `e4cf0694d2bd3ba2d319ba1552ee9f0d33eb1e8a6ddd0ce53b17921dd39da75c` |
| `data/reference/transmissions.json` | 5 | 0 | `9f1c8a72514a9f9f252f3959a732d40a914b2cc8` | `e4cf0694d2bd3ba2d319ba1552ee9f0d33eb1e8a6ddd0ce53b17921dd39da75c` |
| `data/reference/bodies.json` | 5 | 0 | `9f1c8a72514a9f9f252f3959a732d40a914b2cc8` | `e4cf0694d2bd3ba2d319ba1552ee9f0d33eb1e8a6ddd0ce53b17921dd39da75c` |

The repository tree also showed only placeholder `.gitkeep` files in `data/latest`, `data/csv` and `data/sqlite`; no populated release or downloadable data artifact was observed.

## Applicability and product boundary

- The schema is general YMM/trim/engine/transmission structure, not VAG-specific evidence.
- No model, generation, production-year, engine-code, gearbox-code, ECU or exact vehicle-fitment rows were present.
- The repository is not a source for Russian/EAEU market applicability.
- No values were copied into VAG TECH PRO SQLite.
- The repository-level MIT file is not treated as proof that a populated future dataset may be cached or redistributed.

## Reconsideration criteria

Reassess only when a later pinned revision provides populated data files, a versioned release, explicit dataset licensing that covers redistribution and offline caching, and row-level or dataset-level upstream provenance. Any future VAG rows must still pass independent technical review and exact market/model/generation/year applicability checks.

## Evidence and status

- Review date: 2026-11-06
- Data records imported: 0
- Source snapshot: no populated dataset snapshot
- Source-file SHA-256 values above identify the four observed empty JSON files only; they are not a hash of a full repository archive.
- Product decision: excluded from offline research and production packs pending populated, rights-cleared data.

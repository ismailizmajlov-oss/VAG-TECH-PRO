# OpenVAG DTC dataset — rights, provenance and applicability review (2026-11-10)

## Decision

OpenVAG is a potentially useful VAG-labelled DTC research lead, but the dataset is **not approved for import** into VAG TECH PRO. The repository has a root MIT software licence, but the reviewed files do not establish a separate dataset licence, the origin of the DTC rows, the rights in the fault descriptions/solutions, or a reproducible source snapshot. No records were imported, displayed, cached or redistributed.

## Evidence reviewed

- Repository: https://github.com/riz4d/OpenVAG
- README: https://github.com/riz4d/OpenVAG/blob/main/README.md
- Database documentation: https://github.com/riz4d/OpenVAG/blob/main/db/README.md
- SQLite schema: https://github.com/riz4d/OpenVAG/blob/main/db/schema.sql
- Root MIT licence: https://github.com/riz4d/OpenVAG/blob/main/LICENSE
- Current reviewed repository revision: `407d5e042cf46d55087ed4ae4e056605f2b04f08`

## Publisher claims and technical shape

The README and database documentation claim:

| Table / relation | Publisher-claimed rows |
|---|---:|
| DTC code/title combinations | 995 |
| Fault variants | 1,103 |
| Component identifiers | 341 |
| DTC-component links | 712 |
| Related-code links | 276 |
| FTS rows | 1,103 |

The schema describes legacy five-digit codes, combined VAG/OBD/internal strings, and P/B/C/U-shaped identifiers. Fault variants contain symptoms, causes, solutions and special notes. The component table contains VAG-style G/N/V/J/F/E/Z/R/Q identifiers.

These are repository-published counts and schema descriptions, not independently verified production counts or OEM-approved records.

## Provenance and rights findings

1. The repository root contains an MIT licence for the software. No separate data licence, dataset-specific rights statement, row-level source attribution or primary-document reference was found in the reviewed README, database README or schema.
2. The database file `db/openvag.db` is explicitly excluded by `.gitignore`; it is not present in the reviewed repository snapshot.
3. The README instructs users to run `python scripts/init_db.py`, but that path is absent from the reviewed main branch. No `seed.sql` or `seed_db.py` was found. The schema exists, but the data acquisition/build process is not reproducible from the reviewed repository.
4. No source revision or SHA-256 for the database snapshot is published.
5. The MIT software licence does not, by itself, establish the provenance or reuse rights of database content whose origin is not identified.

## Applicability and namespace limits

- The reviewed documentation does not bind codes to exact model, generation, model year, market, engine code, gearbox code, engine/gearbox pair, ECU part number or HW/SW revision.
- A five-digit identifier or VAG-style component label is not sufficient evidence of exact VAG applicability.
- The schema accepts mixed legacy, combined and P/B/C/U-shaped strings. Each record would need a separately verified namespace; generic SAE/ISO DTCs must remain separate from VAG-specific records.
- The `solutions` and `special_notes` fields are not traceable to a primary technical document or revision. They must not be treated as approved repair procedures.

## Required evidence to reconsider

The maintainer must provide:

1. The exact database snapshot and SHA-256.
2. The reproducible acquisition/seed scripts and source revision.
3. Per-row or per-source provenance identifying the original source and rights holder.
4. A dataset-specific licence or written permission covering commercial use, display, offline caching, bulk reuse and redistribution.
5. Clear separation of generic and manufacturer-specific namespaces.
6. Independent technical review and exact ECU/vehicle applicability evidence before any diagnostic or repair advice is enabled.

## Project action

The source is registered as `openvag-riz4d-dtc-candidate` in `data/source-manifests/vag-factory-source-register.json`. Status is quarantined; `data_ingested=false`; `source_snapshot_sha256=null`. It is excluded from Windows offline packs and from all DTC lookup namespaces.

No external account, paid access, API key, download or contact with the maintainer was initiated.


## Recheck — 2026-11-10

The pinned upstream `main` revision remains `407d5e042cf46d55087ed4ae4e056605f2b04f08`. The root `LICENSE` file is present (Git blob SHA-1 `e4d04cc8ef5aaf11907d50758fc397fe05215391`) and declares MIT for the repository software and associated documentation. The current `.gitignore` explicitly excludes `db/openvag.db`; a direct GitHub Contents API lookup for that path returned HTTP 404. `app/main.py` references `scripts/init_db.py`, but that path also returned HTTP 404. The database bytes remain unavailable, so the publisher's README row counts cannot be reproduced and no database SHA-256 can be recorded. No acquisition, extraction, import, display, cache or redistribution was performed.

This recheck does not change the decision: keep the source quarantined. The repository-level MIT declaration is not treated as a dataset-specific licence or evidence that the maintainer can sublicense third-party DTC definitions, fault variants, symptoms, causes or repair solutions.

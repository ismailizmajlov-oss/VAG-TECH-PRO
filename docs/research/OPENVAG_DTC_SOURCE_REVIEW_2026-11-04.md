# OpenVAG DTC source review — 2026-11-04

## Decision

OpenVAG is a **quarantined source candidate, not an importable DTC dataset**. No OpenVAG records have been copied into VAG TECH PRO, displayed, cached, or bundled.

The upstream repository declares MIT for the project, but the pinned repository does not contain the advertised SQLite database, a reproducible database-generation script, or a separate data license. The repository's `.gitignore` explicitly excludes `db/openvag.db`; the tracked tree contains only the database README and schema under `db/`. No GitHub release artifact was found.

## Pinned upstream evidence

- Repository: https://github.com/riz4d/OpenVAG
- Reviewed branch revision: `407d5e042cf46d55087ed4ae4e056605f2b04f08`
- Repository license: MIT (`LICENSE`)
- Repository created: 2026-06-27
- Last push reported by GitHub at review: 2026-06-27
- Files reviewed:
  - `README.md` — Git blob SHA-1 `1c85ac53a5d50b34d2caebe2340420497918cf12`
  - `db/README.md` — Git blob SHA-1 `9cfb62e9e5a939a58dcc8f0d7b3a2db843eec63c`
  - `db/schema.sql` — Git blob SHA-1 `b2bcb53b115acd3c8eb0eaa29de08d5df8c0a122`
  - `.gitignore` — Git blob SHA-1 `6fe697c8fe8a3bb7bb2892b3d27892164393fef8`

These are Git blob identifiers, not SHA-256 hashes of a DTC database. No database artifact was available to hash. The machine-readable review manifest records `data_snapshot_sha256: null` for that reason.

## Upstream documentation claims

The database README claims:

| Table | Claimed rows |
|---|---:|
| DTC code/title pairs | 995 |
| Fault variants | 1,103 |
| Component identifiers | 341 |
| DTC/component links | 712 |
| Related-code links | 276 |

These counts are documentation claims only. They could not be reproduced because the database is not tracked and no downloadable release artifact was found.

## Provenance and applicability gaps

The documented schema has DTC code/title, fault variants, components, links and full-text search. The documented DTC examples mix five-digit VAG-labelled codes, combined VAG/OBD/internal strings, generic OBD-II P-codes, body codes, chassis codes and network codes.

The reviewed schema does not provide a per-record source registry, source URL, source revision, source-file hash, source-line evidence, or per-record license. The documentation does not establish exact model, generation, year, engine, gearbox, ECU, PR-code or RU/EAEU market applicability.

A project-level MIT notice is not accepted as proof that every imported definition is original or that the repository author can sublicense upstream material. The source of each DTC description and fault variant must be established independently before any data reuse.

## Product decision

- Import: **blocked**
- Display in the product: **blocked**
- Offline cache: **blocked**
- Redistribution: **blocked**
- Diagnostic execution or repair advice: **not authorized**
- Market scope: `UNKNOWN`
- Applicability precision: `unverified_make_label_only`
- Verification status: `quarantined_no_data_rights_or_artifact`

Re-review only if the upstream maintainer supplies the actual database artifact, reproducible build inputs, record-level provenance, and an explicit data license that covers commercial display, offline caching and redistribution. If the data is derived from third-party sources, their rights must be evidenced separately.

## References

- Repository: https://github.com/riz4d/OpenVAG
- Project license: https://github.com/riz4d/OpenVAG/blob/main/LICENSE
- Database schema: https://github.com/riz4d/OpenVAG/blob/main/db/schema.sql
- Database documentation: https://github.com/riz4d/OpenVAG/blob/main/db/README.md

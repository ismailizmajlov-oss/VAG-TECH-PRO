# VAG DTC source review — 2026-11-03

## Decision

The pinned Wal33D repository snapshot is accepted only as an isolated **research candidate** source. It is not approved production repair data and must not be shown as an OEM-confirmed DTC definition or as exact vehicle applicability.

- Repository: https://github.com/Wal33D/dtc-database
- Immutable revision: `04c43d72e7db7197658b6f72fe582c5076d9eee8`
- Publisher attribution: Wal33D / Waleed Judah
- Repository license declaration: MIT
- License scope: repository-level README/LICENSE declaration; no separate data-specific license statement
- Rights status: MIT declaration is recorded, but upstream provenance of individual records is not independently verified
- Market scope: `UNKNOWN`
- Applicability: manufacturer/make-label candidate only
- Verification: `unverified_candidate`
- Product eligibility: research-only pending provenance and vehicle validation
- Exact VIN/model/generation/year/engine/transmission/ECU/PR-code fitment: none asserted
- Diagnostic execution: disabled

## Included rows

The pinned source files contain:

| Source file | Included manufacturer-controlled candidates | Excluded generic rows | Excluded malformed rows |
|---|---:|---:|---:|
| `volkswagen_codes.txt` | 528 Volkswagen P1xxx | 0 | 0 |
| `audi_codes.txt` | 2 Audi P3xxx (P3000, P3100) | 126 | 1 |
| **Total** | **530** | **126** | **1** |

The pack includes only manufacturer-controlled OBD-II ranges: P1xxx, P30xx–P33xx, B1xxx–B2xxx, C1xxx–C2xxx and U1xxx–U2xxx. The pinned files currently contain Volkswagen P1xxx and Audi P3000/P3100 candidates.

The Audi source file also contains generic SAE/ISO codes (including P0/P2 families); those are deliberately excluded. The malformed `PP2002` line is also excluded. No Skoda or SEAT source files exist in this pinned repository snapshot.

## Namespace separation

Generic OBD-II reference data remains in the separate OBDex CC0 pack. Its allowed generic ranges are P0xxx, P2xxx, P34xx–P39xx, B0xxx, C0xxx, U0xxx and U3xxx. Manufacturer-controlled ranges are explicitly excluded from that pack. The bundle verifier checks that the two code sets do not overlap.

The Wal33D pack uses the namespace `manufacturer_controlled_candidate`, not `manufacturer_specific_vag`. A source-file make label alone does not prove that a definition is correct for every vehicle from that manufacturer.

## Provenance and integrity

The Windows CI builder pins the upstream commit and preserves:
- raw upstream README, LICENSE and both make-labelled source files;
- SHA-256 for each upstream file;
- SHA-256 for each source line referenced by a DTC candidate;
- source URL, repository commit, license declaration, market scope and verification status;
- a separate SQLite database with source registry and candidate rows;
- the complete MIT notice and attribution.

The latest successful Windows bundle run was GitHub Actions run `41568986227` on 2026-11-03. It assembled five separate SQLite databases; the pack index reports 71 files. Bundle artifact ID: `13199894644`; artifact SHA-256: `f66a1e60f70cd531ad3a3752c85716603229ebac8ed08588c8d397c25714eb3d`; uploaded size: 18,617,900 bytes.

The standalone Wal33D candidate artifact ID is `13200970516`; artifact SHA-256: `f9e13f3c523546a2b0f8ef4e25294ad7280294a862af5d6d7045ec43a6e9bff7`. The SQLite database SHA-256 is `d0d72e90ce92f30bd2e7de9f33b30bd34abfde0fb7642d8d88f79d5d4d7c81a0`. It contains 530 rows (528 Volkswagen, 2 Audi), with the full source-file hashes and per-record source-line hashes recorded in `manifest.json` and the SQLite `source_files`/`dtc_candidates` tables.

The same Windows bundle run enforces the generic OBDex ranges (P0xxx, P2xxx, P34xx–P39xx, B0xxx, C0xxx, U0xxx, U3xxx), excludes manufacturer-controlled ranges, and verifies that the generic and manufacturer-specific DTC sets do not overlap.

## Explicit non-claims

This source does **not** provide:
- Russian/EAEU market applicability;
- model, generation or model-year links;
- engine, gearbox, ECU hardware/software or PR-code applicability;
- per-record source documents or independent technical validation;
- verified test plans, repair procedures, wiring diagrams, pinouts, torque values, adaptations or service schedules.

Do not publish, recommend parts from, or execute diagnostic tests based on these candidates. Promotion requires independently sourced technical evidence, verified record provenance, a rights review and an exact applicability review.

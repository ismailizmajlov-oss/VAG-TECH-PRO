# MechanicDB generic repair-guidance sample review — 2026-11-04

## Decision

The pinned MechanicDB public sample may be used as a **separate generic SAE/ISO educational guidance pack** under its published ODbL 1.0 terms. It is not a VAG-specific technical corpus and does not establish vehicle applicability.

The sample's current repository revision is `c788dfe9ed1517d4cd0be27f5aacb4776abf4864`. Its 2026-10-30 licensing clarification explicitly states that ODbL permits commercial use when attribution and Share-Alike requirements are met. The full commercial MechanicDB datasets are not used.

## Exact import boundary

The pinned sample contains 90 DTC rows: 75 generic SAE rows and 15 manufacturer-labelled rows. Its 326 guidance rows divide into 275 rows linked to generic SAE codes and 51 rows linked to manufacturer-labelled codes.

The pack imports only:

- 75 generic SAE DTC identifiers and their source record IDs;
- 275 MechanicDB-authored generic diagnostic guidance records;
- source revision, source file SHA-256, Git blob SHA-1, physical source line number and source-line SHA-256 for every record;
- ODbL licensing and attribution metadata.

The pack does **not** import DTC descriptions or detailed explanations, manufacturer-labelled records, replacement-parts mappings, parts costs, labor estimates, or OEM part numbers. The MIT upstream notice is retained as attribution evidence; it is not used to claim VAG-specific data rights.

## Rights and redistribution

- Dataset license: ODbL 1.0.
- Commercial use, display, offline caching and redistribution are allowed under the published sample license, subject to attribution, Share-Alike and keeping redistributed copies reusable.
- Attribution: “MechanicDB” with a link to https://github.com/MechanicDB/MechanicDB-public.
- The derived SQLite database remains separately licensed under ODbL 1.0.
- The sample's full commercial editions are excluded.

## Technical scope

- Namespace: `generic_sae_iso`.
- Market scope: `UNKNOWN`; no Russian or EAEU applicability is asserted.
- Applicability: `generic_only`.
- Manufacturer: `UNKNOWN`.
- No model, generation, model year, engine, transmission, ECU, PR-code or VIN mapping.
- No VAG-specific attribution or OEM confirmation.
- No diagnostic command execution.
- No OEM repair procedure, wiring diagram, pinout, torque value, adaptation or parts mapping.

The source field `probability_rank` is stored as `consideration_order`. MechanicDB's data dictionary defines it as authored procedure consideration order, not measured cause probability, repair success, severity, urgency or minimum cost.

## Review and safety status

The source snapshot and row-level provenance are machine-verified. The guidance content has not been independently reviewed by a VAG engineer and is not an OEM workshop procedure. It must be shown only as generic educational reference with a visible warning. For brakes, steering, SRS, ADAS, high-voltage and other safety-critical systems, use the exact manufacturer procedure and safety instructions.

## Reproducibility

The builder pins the upstream commit and verifies Git blob SHA-1 values for the two CSVs, both license files and the provenance documents. It records SHA-256 values for each source file and each imported physical source line, then builds a separate SQLite database with immutable provenance and candidate-only constraints. Generic and manufacturer-labelled records are never merged.

## References

- Public sample: https://github.com/MechanicDB/MechanicDB-public
- Pinned sample revision: https://github.com/MechanicDB/MechanicDB-public/tree/c788dfe9ed1517d4cd0be27f5aacb4776abf4864
- ODbL 1.0: https://opendatacommons.org/licenses/odbl/1-0/
- Source provenance: https://github.com/MechanicDB/MechanicDB-public/blob/c788dfe9ed1517d4cd0be27f5aacb4776abf4864/SOURCES.md
- Data dictionary: https://github.com/MechanicDB/MechanicDB-public/blob/c788dfe9ed1517d4cd0be27f5aacb4776/DATA_DICTIONARY.md

## Published reproducible SQLite pack

The reviewed pack is published in the repository at `data/research/generic-repair-guidance/` under ODbL 1.0, with the attribution and license notices alongside the SQLite file.

- SQLite SHA-256: `78edf7af654c3599fc29407d58542359db5239c5f7611739600e66f24214ecd6`
- Logical content SHA-256: `492c7fc86b7ea669b519294c601ad4b2bd774849abc5404c62562777fc3fb4d7`
- Source snapshot SHA-256: `603619e65832d57b8eed9171c998ddb43c8542c1ceaad495e9576989d713546f`
- Windows CI build and pack-publication run: https://github.com/ismailizmajlov-oss/VAG-TECH-PRO/actions/runs/41868492071

The workflow rebuilds from the pinned upstream revision on Windows, verifies source and row hashes, and rejects an in-place logical-content change to the published database. A changed dataset requires a reviewed successor pack rather than silently replacing this one.

# VAG TECH PRO

Non-commercial technical knowledge base and repair-workflow project for Volkswagen Group vehicles, initially focused on the Russian market.

## Evidence and safety principles

- Keep generic SAE/ISO OBD-II definitions separate from manufacturer-specific VAG diagnostics.
- Never infer engine, transmission, ECU, PR-code, VIN fitment or repair-procedure applicability.
- Preserve source revision, hashes, scope and data license for every research snapshot.
- Do not promote research imports into production without technical review and confirmed reuse rights.
- Wal33D/manufacturer-specific DTC candidates are excluded from distributable bundles: the repository-level MIT notice does not establish data-specific display, cache or redistribution rights.

## Repository contents and current state

The repository currently contains the acquisition workflow and its research policy/reporting. The full application source tree from the development workspace has not yet been mirrored into this GitHub repository. This repository is therefore not yet a complete installable Windows application.

## Verified research acquisition — 2026-11-02

GitHub Actions run #2 completed successfully:
[Acquire DTC research snapshots](https://github.com/ismailizmajlov-oss/VAG-TECH-PRO/actions/runs/41517889631)

The run acquired an OBDex CC0-1.0 data snapshot and validated:

- 9,533 unique generic SAE/ISO DTC definitions.
- 119 Mode 01 PIDs and 13 Mode 09 PIDs (132 total).
- A separate SQLite research import of 9,533 DTCs and 132 PIDs; integrity check passed.
- Exact identifier overlap against an ephemeral pinned Wal33D read-only inspection: 126 overlaps with the Audi text/database set and 0 with the Volkswagen text set.

The overlap is not proof of manufacturer attribution, ECU applicability, vehicle fitment or a repair instruction. Wal33D data rights remain unestablished; its binary and manufacturer definition text were not retained in the artifact or imported.

Detailed counts, source hashes, pinned upstream revision, license scope and import checks are recorded in [the acquisition report](docs/research/OBDEX_RUN_2026-11-02.md). The current VAG OEM-source access and reuse review is in [VAG factory source access review](docs/research/VAG_FACTORY_SOURCE_ACCESS_REVIEW_2026-11-03.md), with a machine-readable [source register](data/source-manifests/vag-factory-source-register.json). VIN decoding, VIN queries and VIN-based vehicle identification are explicitly out of scope for the application; earlier VIN-source assessments remain historical research notes only and are not an implementation requirement. The VIN-free vehicle taxonomy and evidence-backed engine/gearbox relationships are defined in [the vehicle catalog schema](data/sql/vehicle-catalog.sql) and [its design note](docs/research/VIN_FREE_VEHICLE_CATALOG_SCHEMA.md). The pinned ODbL VAG generation/engine candidate acquisition is documented in [the open-data research report](docs/research/VAG_OPEN_ENGINE_CANDIDATES_2026-11-03.md); its importer and manual [research acquisition workflow](.github/workflows/acquire-vag-engine-candidates.yml) create a separate staging database only. The importer does not infer factory engine or gearbox codes. The explicit evidence-gated bridge from DTC records to vehicle variants is in [dtc-catalog-links.sql](data/sql/dtc-catalog-links.sql); apply it after the two base schemas. The evidence-first DTC index is defined by [the JSON Schema](data/schemas/oem-dtc-index.schema.json), [the SQLite schema](data/sql/oem-dtc-index.sql), and [the schema design note](docs/research/OEM_DTC_INDEX_SCHEMA_DESIGN.md).

## Research workflow

Workflow: `.github/workflows/acquire-dtc-research.yml`

It runs on changes to the workflow file on `main` and can also be run manually. OBDex generic records are retained as research-only data; Wal33D is used only for ephemeral identifier comparison. No production database is modified.

## Important limitation

OBDex covers generic SAE/ISO diagnostic definitions only. It does not establish VAG ECU-specific applicability, vehicle-generation fitment, factory wiring or repair procedures. OEM technical sources and exact model/engine/ECU applicability still require independent evidence and review.


## Windows offline bundle rights filter — 2026-11-03

The Windows data-pack assembler now packages only four separately licensed datasets: OBDex CC0 generic OBD-II, VehiclesDB CC BY 4.0 identity candidates, the ODbL VAG identity candidate set, and OBDb CC BY-SA 4.0 community UDS signal candidates. Each remains a separate SQLite database with its own license and provenance.

The Wal33D manufacturer-DTC candidate pack is excluded from the Windows bundle and is not treated as a VAG-specific DTC source. A repository-level MIT notice is not accepted as proof of data-specific reuse, display, caching or redistribution rights. The bundle therefore contains no manufacturer-specific DTC dataset. Generic OBD-II records remain generic and are never relabeled VAG-specific.

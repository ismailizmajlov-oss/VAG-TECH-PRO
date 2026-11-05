# Automotive-9 Volkswagen DTC candidate — rights and data-quality review

Review date: 2026-11-06

## Decision

**Quarantined. Do not import, display, cache, bundle or redistribute this dataset.** The repository contains a Volkswagen-labelled JSON file with 9,137 keys, but the repository has no root `LICENSE` file, the README contains no data-licence grant, and no row-level source attribution or reproducible acquisition process was found. The publisher describes the collection as manufacturer-specific/proprietary DTC codes, but that description is not a licence.

No dataset records were imported into VAG TECH PRO. Only source metadata, the Git object identifier and aggregate triage counts are recorded.

## Exact source revision reviewed

- Repository: https://github.com/Automotive-9/dtc-codes
- Branch: `main`
- Repository head reviewed: `e5cf6906badc81e2bdac3ec7b7c1bba5c01fa108`
- Last commit that added the uploaded data files: `10244f095c78c53800ec9d6b5cabc980ad7c4528`
- File: `Volkswagen.json`
- Git blob SHA-1: `9a2f7303a0d28a9e60259c3c91646484d04d4266`
- README blob SHA-1: `6adb678bd09c161256af8bbf9b92fba234afb059`
- A request for the repository-root `LICENSE` returned HTTP 404; the README has no licence statement.

The README badge links to a different repository, `MCDxAI/open-source-dtc-databases`, but the reviewed file does not identify that project as the legal source of each row or establish a licence for the copied JSON. No rights are inferred from a badge link or from public GitHub visibility.

## Independent structural triage

The JSON parses and contains 9,137 keys. The key/value structure is not a clean, homogeneous DTC dictionary:

| Observation | Count |
|---|---:|
| Numeric legacy/component-style keys | 7,131 |
| P/B/C/U-shaped keys | 2,006 |
| Descriptions containing multiple semicolon-separated segments | 5,339 |
| Numeric-key rows whose descriptions embed an SAE-shaped code | 2,153 |
| Numeric-key rows with component/function-like labels (control unit, module, motor, sensor, switch, valve, actuator, relay or button) | 3,691 |
| Empty descriptions | 2 |

Examples include numeric keys labelled as control blocks or control units, while other numeric-key rows embed generic P-codes such as P0030 inside the description. A single value can combine a legacy identifier, a generic SAE-shaped code, multiple translations and component text. The source does not define which namespace is authoritative for each segment.

Consequently, the README's count of 9,137 entries must not be interpreted as 9,137 validated Volkswagen DTC definitions. The file cannot safely be split into generic OBD-II and VAG-specific records by string heuristics.

## Applicability gaps

The reviewed source does not provide reliable row-level binding to:

- VAG model or generation;
- model year or production-date interval;
- Russian/EAEU or other market;
- engine code, gearbox code or an exact engine/gearbox pair;
- ECU part number, hardware/software revision or diagnostic address;
- a primary technical document, revision, page or test-plan step.

A Volkswagen filename and a manufacturer label are not proof that a row is OEM-authored, VAG-specific, or applicable to a particular vehicle/ECU.

## Required evidence before reconsideration

The source may be reconsidered only after the maintainer/rightsholder provides:

1. A data-specific licence or written permission covering commercial use, display, bulk reuse, persistent offline caching and redistribution.
2. Row-level provenance naming the original source and rights holder, including any upstream database or service-document dependencies.
3. A reproducible, pinned acquisition process and exact source snapshot hashes.
4. An explicit schema that separates legacy VAG identifiers, generic SAE/ISO DTCs, component identifiers and descriptive aliases without merging namespaces.
5. Technical review against primary sources and exact ECU/vehicle applicability evidence before any record can be enabled for diagnostics.

## Project action

The source is registered as `automotive-9-vw-dtc-candidate` in `data/source-manifests/vag-factory-source-register.json`. It is quarantined with `data_ingested=false`, `display_status=quarantined_no_display` and `cache_status=quarantined_no_offline_cache`. No DTC row is added to the generic or VAG-specific SQLite tables.

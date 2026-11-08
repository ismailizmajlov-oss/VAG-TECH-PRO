# EAEU Unified NSI vehicle-reference objects — bounded review (2026-11-08)

## Decision

Keep the EAEU Unified Normative-Reference Information System (ЕС НСИ) as **metadata-only discovery**. The reviewed object pages provide document-type, passport-type and broad transport-category classifiers. They do not provide a VAG vehicle identity catalogue, OTTS/OTSH document corpus, engine/gearbox codes, exact engine/gearbox pairings, ECU records or repair information.

No object data were downloaded, no API endpoint was guessed or called, no SQLite rows were created, and no source snapshot SHA-256 is claimed. The existing source record remains `data_ingested=false`, `product_import_allowed=false`, `source_snapshot_sha256=null`.

## Official API access facts

The official API documentation says that unauthenticated users can query objects in the Unified EAEU NSI REST API. It documents the base pattern `https://nsi.eaeunion.org/api/v1/{endPoint}`, a maximum of 1,500 objects per request, and `limit` / `offset` pagination:

- API description: https://nsi.eaeunion.org/portal/info/api
- NSI overview: https://nsi.eaeunion.org/portal/info

The API page reviewed does not provide a verified endpoint catalogue/OpenAPI description or dataset-level terms for commercial reuse, bulk extraction, persistent local storage, offline display or redistribution. Unauthenticated API access is not treated as a data licence. No undocumented endpoint was guessed.

## Official object pages inspected

| Object code | Official classifier | Observed records | Last update shown | Relevance to VAG TECH PRO |
|---|---|---:|---|---|
| 2030 | Classifier of vehicle/passport types | 3 | 2016-10-30 | PTS/chassis/self-propelled machinery passport type only; visible codes 1–3 |
| 2001 | Classifier of conformity-assessment document types | 10 | 2023-01-19 | Document type only; code 30 is EAEU vehicle type approval (OTTS), 35 is chassis type approval, 40 is SBKTS and 45 is modified-vehicle conformity document; these are document-type codes, not approval records |
| 2024 | Classifier of international-transport vehicle types | 41 | 2015-06-12 | Broad transport category only; visible codes 301 (general-purpose passenger car) and 302 (special passenger car) |

Official pages:

- https://nsi.eaeunion.org/portal/2030
- https://nsi.eaeunion.org/portal/2001
- https://nsi.eaeunion.org/portal/2024

These are classification objects, not the national or Union OTTS/OTSH registry itself. Code 30 identifies the document type «одобрение типа транспортного средства ЕАЭС» (OTTS); it is not an OTTS record or a downloadable approval corpus. Code 35 is a separate chassis type-approval document type and must not be relabelled as a complete-vehicle OTTS record. The classifiers contain no exact VAG model/generation/year, factory engine code, gearbox code, engine/gearbox pair, ECU, DTC, wiring, repair procedure or parts applicability.

The counts and update dates above are observations from the official object pages, not counts of OTTS records. They are not evidence of current completeness of the wider EAEU approval registers.

## Rights and ingestion boundary

The API documentation establishes technical access, not data reuse rights. No dataset-specific open licence or written permission covering the following was found:

- commercial use and third-party display in VAG TECH PRO;
- bulk extraction or systematic download;
- persistent SQLite storage and offline caching;
- redistribution inside a Windows installer or to end users.

Accordingly, the source remains `permission_status=not_obtained`; all product-use flags remain false. No object rows or API responses were cached. No fabricated SHA-256 or source revision was added.

## Next lawful verification

1. Obtain the official endpoint catalogue/OpenAPI document through a link published by the NSI operator.
2. Confirm whether a specific object exists for OTTS/OTSH, vehicle make/type/variant/version, or vehicle technical characteristics.
3. Obtain dataset-level terms or written permission for bulk retrieval, local storage, offline display and end-user redistribution before downloading records.
4. If only document-type classifiers are eventually cleared, import them as a separate EAEU reference namespace. Do not infer vehicle, powertrain, ECU or repair applicability from them.

## Repository controls

The central source register now records object codes 2001, 2030 and 2024 as bounded discovery evidence while retaining all rights and ingestion gates. A regression test asserts that these observations cannot be mistaken for OTTS data or promoted into the product catalogue.

# EAEU open-data portal — OTTS discovery review (2026-11-07)

## Decision

**Discovery-only; not an OTTS dataset and not an import source.** No EAEU open-data resource specifically exposing the unified register of vehicle type approvals (OTTS/OTSH) was identified in the reviewed public catalogue or technical-regulation register pages. No records, exports, API responses, PDFs, or database snapshots were downloaded. No SHA-256 is claimed.

This review does not change the status of the Russian/EAEU source register, does not grant any new reuse rights, and does not authorize automated access to national OTTS systems.

## What was checked

1. The EAEU open-data catalogue describes 117 resources across thematic groups. Its public REST API documentation says portal data are available for reuse with minimal organizational and other restrictions. The catalogue's technical-regulation group is a discovery index, not itself a dataset license for every national register.
   - Catalogue: https://opendata.eaeunion.org/opendata/ru/resourses
   - REST API documentation: https://opendata.eaeunion.org/opendata/ru/api/restapi

2. The public EAEU technical-regulation portal pages surfaced in the review identify:
   - a unified register of conformity-assessment bodies (register page 36): https://tech.eaeunion.org/tech/en/registers/36
   - a unified register of issued conformity certificates and registered declarations (registry page 35-1): https://tech.eaeunion.org/tech/registers/35-1/ru/registryList/

   These are accreditation-body and product-conformity-document resources. They are not the unified OTTS/OTSH vehicle-type-approval register and do not provide VAG vehicle, engine, gearbox, ECU or repair applicability.

3. The public catalogue search/index did not surface a dedicated OTTS/OTSH dataset or a vehicle-type-approval REST resource. A portal-level statement that data are reusable with minimal restrictions cannot be generalized to a separate national source or to data that are not actually published in that portal.

4. EEC Decision No. 88 describes the information-exchange regulation and document formats for the common process, including the unified register of issued vehicle type approvals. It is a technical exchange/schema instrument, not evidence that a public bulk API exists or that national records may be cached and redistributed:
   - https://rulaws.ru/amp/acts/Reshenie-Kollegii-Evraziyskoy-ekonomicheskoy-komissii-ot-26.07.2016-N-88/

## Engineering and rights implications

- Do not add the EAEU portal as an OTTS data source merely because it has a general REST API.
- Do not treat the conformity-body register or product certificate/declaration register as OTTS records.
- Do not infer public bulk access, offline caching or redistribution rights for FGIS national OTTS records from Decision No. 88.
- Continue to require a source-specific license or written permission covering bulk extraction, local storage, display, offline caching and redistribution before any national OTTS data enters a distributable SQLite pack.
- If a future EAEU catalogue entry explicitly exposes OTTS/OTSH data, re-review its exact dataset owner, schema, market scope, revision, license and terms before downloading.

## Evidence limits

The catalogue and technical-regulation pages were reviewed through their public indexed pages on 2026-11-07. The REST API documentation page did not expose readable page text in the web reader during this review. No API call was made, no authentication was attempted, and no request was sent to any restricted national registry. Therefore this is a negative discovery result, not proof that no non-public OTTS API exists.

**Disposition:** `discovery_only_not_otts_data`; `data_ingested=false`; `product_import_allowed=false`; `market_scope=EAEU_portal_catalogue_only`; no snapshot hash.

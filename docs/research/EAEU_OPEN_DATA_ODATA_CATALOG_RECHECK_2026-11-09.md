# EAEU open-data OData catalogue recheck — 2026-11-09

## Finding

The official EAEU Open Data Portal advertises machine-readable reuse of published portal datasets through OData, with minimal organizational access restrictions:

- Portal root: https://opendata.eaeunion.org/
- Resource catalogue: https://opendata.eaeunion.org/opendata/ru/resourses
- OData/REST information page: https://opendata.eaeunion.org/opendata/ru/api/restapi

The official catalogue page returned by public search indexing lists 117 resources overall and 7 in the «Техническое регулирование» category. The same indexed page describes the catalogue as containing common EAEU information resources, including registers and lists, with information supplied by competent authorities and official/open sources.

## Evidence quality and limits

- Review/search retrieval date: 2026-11-09.
- The search result reported that the catalogue page had been crawled approximately nine months earlier. The 117 and 7 figures are therefore retained as indexed catalogue observations, not verified live counts.
- Direct opening of the catalogue and OData information pages returned no readable text lines in this review.
- A targeted search did not identify a dedicated OTTS/OTSH/SBKTS dataset among the indexed catalogue results. This does not prove that no such resource exists or that it is not exposed through a restricted or separately documented route.
- The portal-level OData statement does not identify a specific vehicle-approval dataset, its schema, its current endpoint, its dataset-level licence, or the permitted scope of third-party desktop display, persistent offline caching and redistribution in an installer.
- No OData request was sent. No catalogue record, dataset row, XML, CSV, JSON, document or source bytes were downloaded.

## Product and rights decision

The EAEU catalogue remains `discovery_only`. No permission status was upgraded:

- `data_ingested=false`;
- `product_import_allowed=false`;
- `source_snapshot_sha256=null`;
- dataset-specific licence: not confirmed;
- bulk OTTS export: not established;
- offline cache and third-party display: not confirmed;
- installer/update redistribution: not confirmed.

The existing public-access basis under EEC Collegium Decision No. 225 remains separate from the intergovernmental data-exchange schema in Decision No. 88. Neither is treated as a VAG TECH PRO bulk-reuse licence.

## Next research action

Enumerate the seven Technical Regulation catalogue entries through a documented official catalogue/API route, if the route becomes readable. For each entry, capture its exact resource identifier, owner, schema, source revision, dataset-specific licence/terms, API/export scope and permitted reuse. Only a resource explicitly identified as the vehicle-approval register and carrying sufficient reuse rights may proceed to a data download and hash-pinned importer. Do not infer OTTS inclusion from the category count or from the existence of the OData interface.

## Primary references

- Official EAEU Open Data Portal: https://opendata.eaeunion.org/
- Official resource catalogue: https://opendata.eaeunion.org/opendata/ru/resourses
- Official OData/REST information: https://opendata.eaeunion.org/opendata/ru/api/restapi
- EEC Decision No. 225 public-access framework: https://www.alta.ru/tamdoc/14kr0225/
- EEC Decision No. 88 registry-exchange schema reference: https://www.alta.ru/tamdoc/16kr0088/

Review date: 2026-11-09.

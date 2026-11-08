# EAEU Unified NSI API — discovery review (2026-11-08)

## Verified public API facts

Official API documentation: https://nsi.eaeunion.org/portal/info/api

The page describes a REST API for objects in the Unified EAEU Normative-Reference Information System (ЕС НСИ). It states that API access is available to unauthenticated users, uses the base URL `https://nsi.eaeunion.org/api/v1/{endPoint}`, and returns no more than 1,500 objects per request. Pagination is documented through `limit` and `offset`.

## Relevance to VAG TECH PRO

This is a promising discovery source for EAEU classification/reference objects, but the available documentation reviewed so far does not identify an OTTS/OTSH endpoint, vehicle type-approval registry, or any dataset containing VAG model, generation, engine or gearbox applicability. The API is therefore not yet an OTTS source.

## Rights and ingestion decision

Unauthenticated access is not a licence to bulk extract, cache offline, display, redistribute or commercially reuse records. The API page reviewed does not provide a dataset-level reuse licence or clear offline redistribution terms. The source is registered as `eaeu-nsi-rest-api` with `permission_status=not_obtained`, `data_ingested=false` and `product_import_allowed=false`.

No API endpoint was guessed or called. No records were downloaded, hashed or imported. Before any ingestion, the exact endpoint, dataset scope, field definitions, revision behaviour, reuse licence, caching rights and redistribution rights must be verified.

## Next verification steps

1. Obtain the official endpoint catalogue / OpenAPI description linked from the API page.
2. Search the actual object catalogue for OTTS, OTSH, vehicle category, manufacturer, type, variant and version reference objects.
3. Confirm whether records are regulatory identifiers only or include technical characteristics and applicability.
4. Obtain written or published terms explicitly covering local storage, offline display, bulk extraction and redistribution in VAG TECH PRO.
5. If the dataset is only nomenclature, import it as a separate EAEU reference layer; do not infer engine/gearbox fitment or VAG factory applicability.

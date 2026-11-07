# Cars Base Russian vehicle catalog — source and rights review (2026-11-08)

## Scope

Cars Base is a Russian-language vehicle catalog advertising makes, models, generations, body configurations, modifications, technical specifications, options, logos and photographs. The homepage counters observed on 8 November 2026 were 428 makes, 4,973 models, 10,166 generations, 14,501 configurations and 102,196 modifications. These are publisher counters, not independently reconciled record counts.

The public GitHub repository README describes a free basic marks/models JSON/CSV dataset and links to the API. It also says the expanded passenger-car catalog includes generation, production-year and body-type fields and references the Auto.ru catalog. Its LCV and motorcycle sections reference Auto.ru category pages. The reviewed root listing exposed README.md, cars.csv and cars.json but no LICENSE file or explicit dataset license.

## Access and contract findings

The publisher's public offer (reviewed 8 November 2026) says:

- Sections 2.1–2.3: Cars Base provides vehicle data for websites, CRM, catalogs, marketplaces, internal products and integrations; access can be via REST API, account/key and file exports.
- Section 5: the user may apply obtained data in their own products, but may not resell keys, publish the full database archive or distribute source exports/archives of photographs to third parties without the provider's written consent.
- Section 3: access to paid functionality is tied to the selected tariff and key activation.

The API documentation says:

- Basic `/full` is available without a token, but the documented `token=test` mode is demo data for integration testing.
- Detailed catalog routes such as marks, models, generations, configurations, modifications and specifications require a token; file downloads require an active key.
- The docs describe server-side caching and rate limits, not a license for a third-party offline copy.
- No dataset license, explicit offline-cache grant or end-user redistribution grant was stated in the reviewed API documentation.

The GitHub README references Auto.ru catalog pages as upstream sources for expanded data. The reviewed repository root had no LICENSE file. The project has not established whether Cars Base has permission to sublicense those upstream materials for offline redistribution.

## Technical applicability boundary

Even if the publisher's catalog is useful for Russian-language identity selection, it is not a factory VAG repair source:

- generic transmission labels are not VAG gearbox codes;
- generic engine specifications are not factory engine codes;
- a model/generation/year range is not proof of exact engine/gearbox pairing;
- no OEM ECU, DTC, wiring, pinout, repair-procedure or parts applicability is established by the reviewed metadata.

## Project decision

**Discovery-only; no ingestion.** No account, API key, paid plan, API request, file download or snapshot was used. No SHA-256 is claimed because no source data file was acquired.

Before reconsideration, obtain written permission that explicitly covers:

1. bulk acquisition of the selected fields;
2. offline caching and embedding in the redistributed Windows desktop application;
3. display to all end users of that application;
4. whether embedded subsets or derived records may be redistributed with the installer and updates;
5. attribution and notice requirements;
6. the publisher's rights to the Auto.ru-derived upstream material;
7. stable dataset revision, per-record provenance and change history.

Official publisher evidence:
- Homepage: https://cars-base.ru/
- Public offer: https://cars-base.ru/public-offer
- API documentation: https://cars-base.ru/api2
- Public repository: https://github.com/blanzh/carsBase

No data was imported into SQLite. The source is registered with `data_ingested=false`, `product_import_allowed=false`, `source_snapshot_sha256=null`, market `UNKNOWN`, and make/model/generation candidate precision only.

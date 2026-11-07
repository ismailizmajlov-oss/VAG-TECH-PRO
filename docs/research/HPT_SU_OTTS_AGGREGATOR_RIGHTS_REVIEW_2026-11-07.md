# HPT.SU aggregated OTTS registry — product-distribution rights review — 2026-11-07

## Decision

**Do not ingest, cache, bundle, mirror, or expose HPT.SU database records in VAG TECH PRO.** Keep the source restricted for product distribution. No account, MCP key, API key, subscription, payment, API request, document download, or data snapshot was created or used.

Reconsider only if the provider gives written permission that explicitly covers bulk retrieval, offline caching, redistribution, and display in a third-party Windows desktop product. A standard subscription or API key is not that permission.

## What the provider currently publishes

- The [MCP page](https://hpt.su/mcp/) advertises 50 requests/day on a free tier, but registration is required. It advertises paid API automation tiers from 1,000 RUB/month. PDF download requires a subscription to the corresponding registry.
- The [pricing page](https://hpt.su/pricing/) lists paid registry subscriptions and API tiers. The current page says PDF downloads are not included in API access and require a subscription to the relevant registry.
- The [public offer](https://hpt.su/p/oferta/) states that it is effective from 2026-08-22. Sections 2.1–2.3 grant only a non-exclusive, tariff-limited right of functional use and do not transfer database rights. Sections 11.3–11.5 permit viewing, local saving and processing of individual materials for the user's own activity, but restrict substantial or systematic extraction, third-party equivalent access, and derivative databases reproducing the provider's database without written consent.
- The [API terms](https://hpt.su/p/api-terms/) are effective from 2026-05-27. Section 2.2 requires an active API subscription. Section 3.3 prohibits embedding API keys in client applications distributed to end users without an intermediary server. Section 6.2 limits use to the subscriber's internal purposes. Sections 6.3 and 8.6 prohibit third-party equivalent access, redistribution, derivative databases reproducing the provider database, and systematic transfer of a full current database copy without separate written consent.
- The [open-source hptsu-mcp connector](https://github.com/HPT-SU/hptsu-mcp) is MIT-licensed as software. That licence applies to the connector code, **not** to HPT.SU's database, its compilation, or underlying third-party documents.

## Scope and provenance

The provider describes a registry aggregator covering OTTS, OTSH, SBKTS and other conformity documents. Registry-level search metadata is not an individual vehicle build sheet. Every document would require separate review against its issuing authority and exact document revision. No VAG engine/gearbox pairing, ECU, DTC, wiring, torque, adaptation, or repair applicability is established by the aggregator's landing page or registry-level search.

The offer's right to save and process an individual document for the subscriber's own use does not grant VAG TECH PRO the right to redistribute that document or reproduce the provider's database in an offline product. The API's internal-use permission likewise does not authorize exposing the data to VAG TECH PRO users.

## Project controls

- `status=restricted_for_product_distribution`
- `paid_terms_accepted=false`
- `data_ingested=false`
- `product_import_allowed=false`
- `source_snapshot_sha256=null` because no source bytes were downloaded
- No VIN query, personal-data processing, account creation, key issuance, or paid access
- No use of undocumented endpoints, scraping, bulk extraction, or CAPTCHA bypass

## Re-entry criteria

Only reconsider after receiving a signed written permission from the database rightsholder that specifically permits:
1. automated bulk retrieval using a documented endpoint or authorized export;
2. local/offline caching in VAG TECH PRO;
3. redistribution and display to third-party users in an installable Windows application;
4. retention and update of the relevant data after the subscription or access term ends, if applicable;
5. the precise data fields, document types, markets, attribution and update conditions.

Even with such permission, each underlying document must retain its issuing authority, document number and revision, source-file and row hashes, market scope, exact applicability precision, and a separate rights review for any embedded technical material.

## Evidence reviewed

1. [HPT.SU MCP page](https://hpt.su/mcp/) — reviewed 2026-11-07; free MCP tier requires registration, paid API tiers are advertised, and PDF downloads require a registry subscription.
2. [HPT.SU pricing](https://hpt.su/pricing/) — reviewed 2026-11-07; registry subscriptions and API tiers, including a 1,000 RUB/month entry tier.
3. [HPT.SU public offer](https://hpt.su/p/oferta/) — effective 2026-08-22; sections 2.1–2.3, 4.1.4 and 11.1–11.5.
4. [HPT.SU API terms](https://hpt.su/p/api-terms/) — effective 2026-05-27; sections 2.2, 3.3, 6.2–6.5 and 8.6.
5. [hptsu-mcp GitHub repository](https://github.com/HPT-SU/hptsu-mcp) — MIT licence for connector software only; not a data licence.

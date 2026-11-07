# Kyrgyz Single Window public vehicle-approval registry review — 2026-11-07

## Decision

Register the new State Enterprise «Single Window» public registry as an **EAEU-member-state discovery source only**. The operator describes a no-login public registry pilot that includes OTTS and OTSH, but no dataset-specific reuse licence, documented API or bulk-export contract was found. Do not import or cache records.

This source is distinct from the older `sbkts.trade.kg/otts` interface, which was previously observed behind a CAPTCHA. No CAPTCHA bypass was attempted.

## What the official operator confirms

- The [official portal](https://trade.kg/) says its public registers are open without registration. Its current homepage describes the OTTS/OTSH registry search by approval number, make and model.
- The [public-registry project page](https://trade.kg/projects/public-registry) describes a pilot, says no login is required, and says personal data are not displayed. It links to [smart.trade.kg/registry](https://smart.trade.kg/registry?lng=ru) for public lookup by document number or VIN.
- The separate [cert.trade.kg landing page](https://cert.trade.kg/) displays UI counters of one OTTS document and zero OTSH documents. These are portal counters only; they are not verified, complete or stable public-register corpus counts.
- The [vehicle-approval project page](https://trade.kg/projects/vehicles) identifies [car.trade.kg](https://car.trade.kg/) as the application system for certification bodies and experts. It describes application fields for the vehicle/chassis, engine and other characteristics, and says issued documents are published to the public registry.
- The [24 August 2026 announcement](https://trade.kg/news/24-avgusta-2026-goda-v-promyshlennoj-srede-zapuskaetsya-informaczionnaya-sistema) describes the OTTS/OTSH issuance workflow and publication of approved documents into an electronic register.

## Important separation of scopes

The engine fields described on the certification application form are input fields for a restricted professional workflow. They are **not evidence that the public registry exposes engine designations or factory codes**. The public record schema was not retrieved. No exact VAG engine code, gearbox code, engine/gearbox pair, ECU, DTC or repair applicability was established.

The register is Kyrgyz national data in the EAEU TR TS 018/2011 context. It is not Russian-market evidence and must not be promoted to RU applicability.

## Rights and acquisition

- No dataset-specific open licence or written permission for automated extraction, bulk export, offline caching, third-party display or redistribution was identified.
- The no-login public search interface is not treated as permission to scrape or mirror the registry.
- No documented API, bulk export contract, reproducible snapshot or dataset revision was identified.
- No records were downloaded. No source-file hash or snapshot SHA-256 is claimed.
- No VIN, applicant, address, owner or other personal data were collected.
- The source remains `permission_required`, `data_ingested=false`, and `product_import_allowed=false`.

## Evidence reviewed

1. [Official Single Window homepage](https://trade.kg/) — reviewed 2026-11-07; public registers without login and OTTS/OTSH search fields.
2. [CertTrade landing page](https://cert.trade.kg/) — reviewed 2026-11-07; one-OTTS and zero-OTSH UI counters, not verified corpus counts.
3. [Public registry project page](https://trade.kg/projects/public-registry) — reviewed 2026-11-07; pilot status, no-login lookup and personal-data display statement.
4. [Public registry application](https://smart.trade.kg/registry?lng=ru) — identified from the official link; JavaScript page did not expose a readable record schema in this review.
5. [SBKTS/OTTS/OTSH application system description](https://trade.kg/projects/vehicles) — reviewed 2026-11-07; professional user scope, application workflow and engine/vehicle form fields.
6. [Official 24 August 2026 launch announcement](https://trade.kg/news/24-avgusta-2026-goda-v-promyshlennoj-srede-zapuskaetsya-informaczionnaya-sistema) — reviewed 2026-11-07; electronic issuance and registry publication workflow.

## Re-entry criteria

Reconsider ingestion only after the operator provides (a) a documented public-record schema or supported API, (b) a reproducible dataset or authorized export method, and (c) explicit rights covering bulk retrieval, offline caching, third-party display and redistribution. Any future import must field-allowlist document-level non-personal data, retain source and row hashes, and keep OTTS/OTSH/SBKTS document types separate.

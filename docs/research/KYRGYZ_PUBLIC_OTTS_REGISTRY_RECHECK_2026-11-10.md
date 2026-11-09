# Kyrgyz public OTTS registry — privacy, schema and reuse recheck (2026-11-10)

## Decision

The Kyrgyz Single Window public OTTS/OTSH route remains **discovery-only**. The current official pages confirm a public, no-login pilot and describe its lookup fields, but the linked JavaScript registry did not expose a readable record, record schema, documented API or export. No source bytes or records were downloaded; no VIN or document query was submitted; no personal values were collected; no SHA-256 is claimed.

No bulk extraction, automated acquisition, SQLite caching, offline display, commercial third-party display or redistribution rights are established. data_ingested=false and product_import_allowed=false remain mandatory.

## Current official evidence

- [Operator homepage](https://trade.kg/) says public registers are open without registration and lists OTTS/OTSH lookup by approval number, make and model.
- [Registry landing page](https://trade.kg/registry) links to the [smart.trade.kg JavaScript registry](https://smart.trade.kg/registry?lng=ru). The landing page contains no record rows.
- [Public-registry project page](https://trade.kg/projects/public-registry) still labels the service a pilot, says login is not required, permits lookup by VIN or document number, and states that personal data are not displayed.
- [Vehicle-approval workflow page](https://trade.kg/projects/vehicles) describes a separate application system for certification bodies and experts. Its application input includes engine characteristics, but those inputs are **not** evidence that engine fields appear in the public record schema.
- [Privacy policy](https://trade.kg/privacy) says the information site does not require registration or set cookies and has no third-party analytics. It describes anonymized operator analytics; search text, document number and VIN are excluded from analytics. A document-check/search request is nevertheless sent to the server and is not linked to the visitor.
- The [24 August 2026 announcement](https://trade.kg/news/24-avgusta-2026-goda-v-promyshlennoj-srede-zapuskaetsya-informaczionnaya-sistema) describes the OTTS/OTSH issuance workflow and publication of issued approvals into the electronic register.

The privacy policy is a statement about visitor-data handling. It is **not a data-reuse licence**. No actual query was submitted during this review.

## Record schema and applicability boundary

The public project page's statement that personal data are not displayed is useful privacy evidence, but the actual returned record was not available for field-level inspection. The smart registry page yielded no readable rows in the reviewed extraction. No record-level schema, complete corpus count, API or export was verified.

The vehicle-approval application workflow is restricted by its stated purpose to certification bodies and experts. Engine and other technical fields shown as application inputs must not be conflated with the public registry record schema. No exact VAG make/model/generation/year, factory engine code, gearbox code, engine/gearbox pair, ECU, DTC or repair applicability was established.

## Legal and rights boundary

The Kyrgyz Digital Code No. 178 (effective 2026-02-05 under Law No. 179) was previously reviewed for public access, owner rights and open-data definitions. The operator's status as a state enterprise does not by itself prove that this specific registry is formally classified as a state/municipal digital resource; the observed JavaScript lookup does not establish a machine-readable open dataset without reuse restrictions. Record-owner identity and record-level metadata terms remain unknown.

Accordingly, public no-login lookup does not establish permission for automated extraction, bulk requests, persistent local SQLite storage, offline caching, commercial or third-party display, or redistribution in the Windows installer.

The source remains market-scoped to **KG** in the EAEU TR TS 018/2011 context. It is not Russian-market fitment evidence.

## Import decision and re-entry criteria

Keep permission_required, data_ingested=false, product_import_allowed=false, and source_snapshot_sha256=null. Do not create a source hash when no source bytes were retrieved.

Reconsider acquisition only after the operator or a formal legal review confirms the registry's legal classification, record owner, machine-readable record schema, documented API/export, and rights covering bulk retrieval, local storage, offline end-user display and redistribution in the Windows installer. Any approved import must exclude personal fields and preserve KG market scope, exact document type, revision, retrieval timestamp, source bytes and SHA-256.

## Evidence reviewed on 2026-11-10

- https://trade.kg/
- https://trade.kg/registry
- https://trade.kg/projects/public-registry
- https://trade.kg/projects/vehicles
- https://trade.kg/privacy
- https://smart.trade.kg/registry?lng=ru
- https://trade.kg/news/24-avgusta-2026-goda-v-promyshlennoj-srede-zapuskaetsya-informaczionnaya-sistema

No record query, document download, API call, CAPTCHA bypass, account creation or source-data import was performed.

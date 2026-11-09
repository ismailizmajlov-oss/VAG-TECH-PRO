# Kyrgyz Single Window public OTTS registry recheck — 2026-11-09

## Decision

The official Kyrgyz Single Window public-registry route remains a useful EAEU-member-state discovery lead, but it is still **metadata-only and rights-gated**. The operator describes a no-login pilot for public verification of issued documents. The current official pages confirm the public route and search fields, but the linked JavaScript application did not expose a readable OTTS record or record schema in this review.

No OTTS document, registry row, PDF, API response, export or raw source bytes were downloaded. No source SHA-256 is claimed. No data were imported into either the production catalog or an offline research pack.

## Current official route

- The [State Enterprise «Single Window» homepage](https://trade.kg/) identifies the operator as a state enterprise under the State Customs Service of the Cabinet of Ministers of the Kyrgyz Republic. It says public registers are open without registration and lists OTTS/OTSH search by approval number, make and model.
- The official [OTTS/OTSH registry landing page](https://trade.kg/registry?tab=OTTS.otts) links to the [smart.trade.kg public registry](https://smart.trade.kg/registry?lng=ru).
- The [public-registry project page](https://trade.kg/projects/public-registry) continues to label the service a pilot. It says issued documents are published for public lookup by VIN or document number without displaying personal data.
- The [vehicle-approval project page](https://trade.kg/projects/vehicles) describes the separate application workflow for certification bodies and experts. Its application fields include vehicle/chassis, engine and other characteristics. These are application-input fields, **not proof of fields exposed in the public record**.
- The separate [cert.trade.kg landing page](https://cert.trade.kg/) displays summary counters of one OTTS and zero OTSH. They are portal UI counters only, not a verified, complete or stable registry count.

## 2026-11-09 observation

The official homepage, registry landing page, project page and cert.trade.kg were rechecked on 2026-11-09. Opening the smart.trade.kg route returned a JavaScript application with no readable record rows in the reviewed page extraction. No individual OTTS record, record schema, documented API, export endpoint or reproducible dataset snapshot was verified.

The one-OTTS and zero-OTSH counters are retained only as dated portal observations. They must not be used as a coverage metric or as evidence that the single record concerns VAG.

## Rights and applicability

The no-login public lookup establishes a public verification route; it does not grant permission for automated extraction, bulk retrieval, persistent SQLite caching, offline display, commercial use, third-party display or redistribution in a Windows installer. No dataset-specific open licence or written permission was identified.

The source remains:

- market scope: KG, in the EAEU TR TS 018/2011 context; not Russian-market evidence;
- status: `permission_required`;
- `data_ingested=false`;
- `product_import_allowed=false`;
- source snapshot SHA-256: `null` because no source bytes were retrieved;
- applicability precision: document-level type-approval metadata only;
- exact VAG model/generation/year, factory engine code, gearbox code, engine/gearbox pairing, ECU, DTC and repair applicability: not established.

No CAPTCHA was bypassed. No account was created. No applicant, VIN, owner or other personal data were collected.

## Re-entry criteria

Reconsider ingestion only after the operator confirms, in writing or through an applicable formal open-data licence:

1. the public record owner and the registry's legal classification;
2. a supported, documented machine-readable API or export and its permitted query scope;
3. rights for bulk retrieval, persistent offline caching, end-user display and redistribution in the Windows installer;
4. the public record schema and field-level restrictions, including personal-data exclusions.

If permission is granted, import only allowlisted non-personal OTTS/OTSH document metadata, preserve the original record and revision provenance, hash the actual retrieved bytes, and keep the source's KG market scope. Promote engine/gearbox relationships only where the same exact type/variant/version evidence explicitly supports both canonical factory codes and an independent technical review approves the relationship.

## Primary sources

- https://trade.kg/
- https://trade.kg/registry?tab=OTTS.otts
- https://trade.kg/projects/public-registry
- https://trade.kg/projects/vehicles
- https://smart.trade.kg/registry?lng=ru
- https://cert.trade.kg/

Review date: 2026-11-09.

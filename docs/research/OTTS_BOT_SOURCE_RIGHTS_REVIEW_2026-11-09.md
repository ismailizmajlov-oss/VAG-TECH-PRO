# OTTS.BOT — source rights and provenance recheck (2026-11-09)

## Decision

Keep OTTS.BOT as a discovery-only, rights-restricted source. Do not scrape it, issue mass queries, download documents for VAG TECH PRO, cache its database, display its records as part of the offline product, or redistribute documents/database information. The published User Agreement expressly restricts scraping/mass requests beyond ordinary user scenarios and prohibits resale, publication or other distribution of documents and database information as a proprietary information product. The operator also reserves its website, database structure and site text; the underlying approval documents remain the property of their respective rightsholders.

The source remains registered in both authoritative manifests with `permission_status=not_cleared`, `data_ingested=false`, `product_import_allowed=false` and `source_snapshot_sha256=null`. No source bytes were acquired, so no source-file SHA-256 is claimed.

## Evidence reviewed

- [Published User Agreement](https://www.otts.bot/terms), last updated 2026-08-26, rechecked 2026-11-09:
  - Clause 3 permits ordinary free search, but prohibits automated scraping/mass requests that exceed ordinary user scenarios and prohibits resale, publication or other distribution of obtained documents and database information as a proprietary information product.
  - Clauses 4.3–4.4 require a contributor to warrant their own rights and grant the operator permission to place, reproduce and deliver documents to the operator's users. This is a grant to the operator, not a sublicense to VAG TECH PRO.
  - Clause 5 reserves website presentation, database structure, section text and code to the operator; rights to the underlying documents belong to their respective rightsholders.
- [OTTS search page](https://www.otts.bot/otts), reviewed 2026-11-09:
  - Free search by approval number, make, model or VIN is advertised.
  - The page headline says “46,000+” approvals, while the rendered result counter says 74,115. The discrepancy is unresolved; neither figure is an independently audited export.
  - One-off PDF delivery is advertised at 500 RUB per document.
- [Homepage](https://www.otts.bot/), reviewed 2026-11-09:
  - UI counters display 74,115 OTTS, 224,744 SBKTS and 1,655 OTSH.
  - Technical-characteristics and engine sections are described as not yet populated.

These counts are UI observations only. They do not establish dataset completeness, VAG record counts, a source snapshot, or reuse rights. No account, subscription, payment, automated request, document download, cache or import was used.

## Applicability and data-quality boundary

The search interface exposes document-level filters such as approval number, make, commercial name, vehicle type, category, environmental class, modification, chassis, VIN, applicant and manufacturer. It does not establish exact factory engine codes, gearbox codes, an engine/gearbox pair, ECU mapping, DTC fitment or repair applicability.

Even a future permitted document-level review must preserve the actual primary document, its revision and exact page/table locator, file SHA-256, market and vehicle scope, and an independent technical-review status. A provider counter or search-result label is not a fitment proof.

## Reconsideration criteria

Reconsider only after written permission from the operator and relevant underlying document rightsholders expressly covers the intended bulk retrieval, persistent SQLite storage, offline caching, third-party desktop display, commercial use, updates and redistribution. Any permission must identify the exact document population and whether it covers document contents, database metadata and derivative indexes separately.

No request was sent, no paid terms were accepted, no account was created and no credentials were used.

# Russian/EAEU OTTS aggregator rights recheck — 2026-11-11

## Decision

**No acquisition or product import.** Both reviewed services are private aggregators. Public search visibility and access to an individual document do not grant VAG TECH PRO rights to bulk extract, persistently cache, display, redistribute or ship the records/PDFs in an offline installer. No account, subscription, payment, automated request, PDF download, source-byte download or cache was used. No source-file SHA-256 is claimed.

## OTTS.BOT

Reviewed 2026-11-11:

- [OTTS search page](https://www.otts.bot/otts) exposes document metadata filters (approval number, make, commercial name, type, category, environmental class, modifications, chassis, VIN, applicant and manufacturer). The page displays **74,115 OTTS** in the results counter while the same page advertises **46,000+** in its headline. These are provider UI observations, not an audited dataset count.
- The homepage displays 74,115 OTTS, 224,744 SBKTS and 1,655 OTSH. Technical-characteristics and engine sections are still described as not yet populated. No exact VAG engine code, gearbox code, engine/gearbox pair, ECU, DTC or repair applicability was established.
- [Published User Agreement](https://www.otts.bot/terms), last updated 2026-08-26, was rechecked. Clause 3 prohibits scraping/mass requests beyond ordinary user scenarios and prohibits resale, publication or other distribution of documents and database information as a proprietary information product. Clauses 4.3–4.4 give the operator document-placement, reproduction and delivery rights from contributors; they do not sublicense rights to VAG TECH PRO. Clause 5 reserves the site's presentation, database structure and text to the operator; rights to underlying documents remain with their respective rightsholders.
- The page advertises a 500 RUB single-document price and paid subscriptions. No paid access was used.

**Decision:** no scraping, bulk requests, offline cache, third-party display or redistribution without separate written permission from the operator and the underlying document rightsholders.

## СпецРег / РусАвтоЛаб

Reviewed 2026-11-11:

- [Landing page](https://otts.rusavtolab.ru/) claims 77,802 official OTTS documents and says PDF downloads are free.
- [About page](https://otts.rusavtolab.ru/o-servise/) identifies the service as operated by СпецРег / РусАвтоЛаб, a private document-retrieval and vehicle-conversion business.
- [Public offer](https://otts.rusavtolab.ru/oferta/) describes delivery of an electronic OTTS copy from open sources for **200 RUB per document**. This conflicts with the landing page's free-PDF claim.
- No dataset-specific licence, documented bulk API, reproducible bulk export, per-document upstream provenance export or written permission for commercial reuse, automated extraction, offline caching, third-party display or redistribution was identified.

**Decision:** permission required; no automation or import until per-document provenance and written bulk-reuse rights are confirmed.

## Product-data boundary

Neither aggregator is treated as an official VAG technical source. A registry card or PDF is not automatically a confirmed VAG vehicle configuration. Exact model/generation/year, factory engine code, gearbox code, engine/gearbox pairing, ECU, DTC and repair applicability require review of the primary approval document and a separate source-specific rights decision.

## Recheck evidence

- OTTS.BOT page and terms: reviewed 2026-11-11; terms page still states last updated 2026-08-26.
- РусАвтоЛаб landing page, About page and public offer: reviewed 2026-11-11.
- No raw source files or documents were downloaded; source snapshot SHA-256 remains null.

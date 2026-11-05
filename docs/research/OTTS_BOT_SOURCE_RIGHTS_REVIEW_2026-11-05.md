# OTTS.BOT source rights and access review — 2026-11-05

## Decision

OTTS.BOT is a useful discovery lead for the Russian/EAEU vehicle-approval document landscape, but it is **not an approved source for VAG TECH PRO ingestion**. Its published User Agreement prohibits automated collection beyond ordinary user scenarios and prohibits redistribution of obtained documents and database information as a proprietary information product. The project must not scrape, bulk-query, cache, package, display or redistribute its records or PDFs without separate written permission expressly covering those actions.

No account, subscription, API key, payment, automated request, document download, cache or import was used.

## Public interface observations

Reviewed on 2026-11-05:

- Homepage: https://www.otts.bot/
- User Agreement: https://www.otts.bot/terms

The homepage advertises free search by approval number, make, model or VIN. It displayed the following live counts:

| Registry | Provider-displayed records |
|---|---:|
| OTTS | 74,115 |
| SBKTS | 224,744 |
| OTSH | 1,655 |

These counts are provider-displayed values observed on 2026-11-05. They are dynamic and were not independently audited. The page advertises a one-document download price of 500 RUB and subscriptions from 990 RUB for three days to 29,900 RUB per year. No paid access was used or accepted.

The public interface exposes approval number, make, commercial name, type, category, environmental class, modifications, chassis, VIN, applicant and manufacturer fields. The technical-characteristics and engine sections are described on the page as not yet populated. No exact factory engine code, gearbox code, engine/gearbox pairing, ECU mapping or repair applicability was established.

## Terms and rights boundary

The User Agreement states that:

1. Clause 3 provides free search and paid document access, prohibits automated collection/scraping or mass requests that exceed ordinary user scenarios, and prohibits resale, publication or other distribution of obtained documents and database information as a proprietary information product.
2. Clause 4.3 requires a partner/contributor to warrant that they lawfully hold the rights to submit a document.
3. Clause 4.4 grants the operator placement and distribution rights from that contributor. It does not grant VAG TECH PRO a licence or sublicense.
4. Clause 5 states that the website design, database structure, section texts and code belong to the operator, while rights to the underlying documents belong to their respective rightsholders.
5. Clause 6 disclaims a guarantee that database information is complete or current.

The agreement page states its last update was 2026-08-26. No dataset-specific open licence or written permission for bulk reuse, offline caching, third-party display or redistribution was found.

## Applicability controls

- Keep OTTS, SBKTS and OTSH as distinct document types.
- Do not infer exact engine or gearbox codes from a make/model label or free-text document metadata.
- Do not infer an engine/gearbox pairing unless the primary approval document explicitly binds both values to the same approved type/variant.
- Do not infer ECU, DTC, wiring, pinout, torque, adaptation, maintenance or repair applicability from registry metadata alone.
- Any future permitted document must retain its issuing authority, document type/number, revision/supplement, validity, market, source URL, lawful snapshot hash, permission evidence hash, extracted field location and applicability precision.

## Project action

The source is recorded in:

- `data/source-manifests/russian-eaeu-otts-sources.json`
- `data/source-manifests/vag-factory-source-register.json`

Status remains restricted; `data_ingested=false`; `source_snapshot_sha256=null`. It is excluded from desktop offline packs. The registry records the public counts as discovery metadata only, not as vehicle catalog records.

To unlock any product use, the project needs separate written permission from the relevant rights holders and/or operator covering commercial use, automated/bulk extraction, persistent SQLite caching, offline third-party display, updates/retention and redistribution. Payment or a standard user subscription would not satisfy this permission requirement.

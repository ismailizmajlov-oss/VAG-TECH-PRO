# VAG-Wiki independent technical reference — rights and provenance review (2026-11-05)

## Decision

**Do not ingest, scrape, cache, bundle, display or redistribute VAG-Wiki technical records in VAG TECH PRO.** The site is a discovery lead for engine-family/code and transmission-specification references, but its reviewed Terms of Service prohibit unauthorized mass scraping, automated data extraction and redistribution. No dataset-specific open license or written permission covering the VAG TECH PRO use case was found.

The source is recorded as quarantined with market scope `UNKNOWN`, no exact fitment, and no production import permission. No page content, images, tables, torque values, DTCs or technical records were copied into the application or SQLite.

## Evidence reviewed

1. Homepage: https://vag-wiki.com/ (reviewed 2026-11-05)
   - Describes VAG-Wiki as an independent technical database.
   - Claims coverage of engine-code indexing (EA888, EA288), transmission torque ratings (DSG/Tiptronic), and fluid/lubrication standards.
   - States that the project is not affiliated with Volkswagen AG.
2. Terms of Service: https://vag-wiki.com/terms-of-service (reviewed 2026-11-05)
   - Legal Revision: 2026.01.
   - Section 1 limits use to informational, educational or professional reference and prohibits unauthorized mass scraping, automated data extraction and redistribution without prior authorization.
   - Section 2 says technical specifications, torque settings and diagnostic codes are compiled from various independent sources and disclaims a guarantee of accuracy or currency.
   - Section 3.5 separately restricts commercial scraping and AI training.

## Rights and evidence gaps

| Capability / evidence | Reviewed result |
|---|---|
| Public web reference | Observed |
| Dataset-specific open license | Not found |
| Commercial use in a distributed desktop product | Not established |
| Product display rights | Not established |
| Offline SQLite caching | Not granted |
| Bulk automated extraction | Prohibited without prior authorization |
| Redistribution | Prohibited without prior authorization |
| Record-level primary provenance | Not established |
| Reproducible source revision / raw-document hashes | Not established |
| Russian/EAEU applicability | Not established |
| Exact engine/gearbox pairings or ECU/DTC fitment | Not established |

The site's use of phrases such as “expert verified” on individual pages is not a substitute for per-record source documents, revision identifiers, hashes, and an independently reviewable technical-validation record.

## Project action

- Added source ID `vag-wiki-community-technical-hub` to `data/source-manifests/vag-factory-source-register.json`.
- Rights status remains `not_obtained`; product import is disabled.
- No crawling, hidden-endpoint discovery, automated downloads, or account creation was performed.
- Reconsider only after the site owner provides written permission that explicitly covers commercial use, product display, offline caching, bulk reuse and redistribution, plus record-level source provenance and technical review evidence.

This source is not OEM documentation and must not be presented as factory-confirmed data.

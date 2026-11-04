# Russian / EAEU OTTS provider-rights review — 2026-11-04

## Decision

No newly reviewed commercial OTTS aggregator provides a public licence that permits VAG TECH PRO to bulk extract, cache, bundle and redistribute its database or PDFs in an offline third-party Windows application. These providers remain discovery leads only. No accounts, subscriptions, API keys, paid access, scraping, bulk requests or downloads were used. No OTTS records were imported.

## Provider findings

| Source | Public access | Relevant terms | VAG TECH PRO decision |
|---|---|---|---|
| [OTTS.BOT](https://otts.bot/terms) | Free search; paid document retrieval | The user agreement prohibits automated collection/scraping and mass requests beyond ordinary user scenarios; it also prohibits resale, publication or redistribution of obtained documents and database information as a proprietary information product. Its partner programme requires the contributor to warrant that they have rights to grant placement/use rights to the operator; it does not grant this project any rights. | Restricted; no automation, cache or import. Separate written rights required. |
| [АВТОРЕГИСТР / otts-baza.ru](https://otts-baza.ru/offer/) | Public search; paid access to PDFs | Access terms (edition 2026-10-04) permit personal tasks and internal professional work but prohibit systematic extraction of a substantial part for publication, resale or a competing catalogue without separate agreement. | Restricted; no automation, cache or import. |
| [HPT.SU](https://hpt.su/p/api-terms/) | Documented API; free request tier advertised; PDF download separately restricted | API terms reserve database rights and limit use to the subscriber's internal purposes; third-party database-equivalent access, substantial derived database distribution and systematic full-database transfer are prohibited without separate written consent. | Permission required; API client MIT licence is not a data licence. |
| [Rosstandart FGIS «Реестры КТС»](https://www.interstandart.ru/page/fgis_01) | Official registry/search obligation | Official registry status and public search fields do not themselves establish bulk export, third-party display, persistent cache or redistribution rights. | Permission required; owner-supplied export plus matching licence/written permission required. |
| [EAEU Open Data Portal](https://opendata.eaeunion.org/opendata/ru/api/restapi) | General OData/REST open-data portal | The reviewed catalogue search did not identify a specific OTTS/vehicle type-approval resource, resource-level licence, exact endpoint or bulk/caching terms. A portal-wide statement is not sufficient to clear an unidentified resource. | Permission required; continue exact resource discovery; no import. |

## Additional official historical context

A 2018 NAMI research report commissioned under a contract with the Eurasian Economic Commission describes the EAEU national conformity registers as providing free Internet access to necessary information. It also records that the registries were populated with scanned PDF copies and that missing attributes made search difficult. See the official EEC-hosted report, section 2.1, page 16: https://eec.eaeunion.org/upload/iblock/ffb/Otchet-OTTS-etap-1_664.pdf

This is historical system-context evidence, not a dataset licence. The report says its results were intended for official use by the EEC; it does not grant VAG TECH PRO bulk extraction, commercial display, persistent offline caching, PDF redistribution or database redistribution rights. The 2026 catalog review still did not resolve a dedicated OTTS open-data resource with dataset-specific terms. The ingestion gate therefore remains closed.

## Consequence for acquisition

1. Do not treat search-result visibility, a free API request allowance, a paid PDF download, or a software client's MIT licence as permission to reproduce a database.
2. For any provider export, require a signed permission or resource-specific open licence covering commercial use, persistent SQLite caching, offline third-party display, bulk extraction, updates/retention and redistribution. Hash the permission/licence text and the exact source snapshot.
3. If permission is internal-use-only, do not bundle the data. Keep any permitted lookup server-side and do not retain a distributable local copy.
4. Keep individual OTTS facts, engine-code candidates, gearbox mentions, VIN patterns and PR-code references in separate evidence namespaces. OTTS does not establish a factory engine/gearbox pairing unless the primary document explicitly ties those exact values together.

## Review limitations

This is a product source-rights gate, not a legal opinion. The provider terms were reviewed as published on 2026-11-04; terms can change. The FGIS legal-field review remains limited by the lack of a retrieved primary signed copy of the relevant Rosstandart orders.

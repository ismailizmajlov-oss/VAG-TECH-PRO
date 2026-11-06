# ELPTS public OTTS register — live route recheck (2026-11-06)

## Decision

The official ELPTS documentation host exposes a distinct public page titled **ОТТС** at `https://docs.elpts.ru/ncher/otts`, in addition to the previously reviewed multi-register route at `/ncher/esbkts`. This improves route discovery but does **not** change the import decision: the public page does not, in the reviewed material, provide a dataset-specific licence or permission for bulk extraction, persistent SQLite caching, offline third-party display or redistribution.

No registry records, attachments or PDFs were downloaded or imported. The page was consulted as a public search/discovery page only.

## Current public observations

- Official ELPTS site: https://elpts.ru/ — identifies the national part of the unified register of issued OTTS, OTSH and SBKTS.
- OTTS page: https://docs.elpts.ru/ncher/otts — page heading identifies the OTTS register. The rendered page showed a visible total label `Всего оформлено: 14822` while date filters were set to 05.11.2026–06.11.2026. This is a UI observation only; it is not treated as a verified complete-corpus count because the active filter state and count semantics were not independently established.
- OTSH page: https://docs.elpts.ru/ncher/otsh — page heading identifies the OTSH register and the rendered page showed `Всего оформлено: 828`; this is likewise only a UI observation, not a verified complete-corpus count.
- SBKTS page: https://docs.elpts.ru/ncher/esbkts — remains a separate page; its title identifies SBKTS while visible filters include OTTS, OTSH and ZOETS. Do not conflate the page title with the selected document type.
- Official ELPTS notice on EOTTS access/training: https://elpts.ru/tutorials-eotts/ — training materials require an organization profile in the request centre.
- Official ELPTS site describes additional statistical reports for SEP/EOTTS participants as separately contracted services: https://elpts.ru/.

## Rights and acquisition boundary

| Capability | Current status |
|---|---|
| Public OTTS search page | Observed |
| Public OTSH search page | Observed |
| Public SBKTS register page | Observed |
| Exact completeness and historical coverage | Not established |
| Resource-specific open licence | Not found |
| Commercial use | Not confirmed |
| Bulk export / automated extraction | Not established |
| Persistent local SQLite cache | Not confirmed |
| Offline third-party display | Not confirmed |
| PDF redistribution | Not confirmed |
| Product import | Blocked pending written permission or a resource-specific open licence |

A publicly reachable search page is not a data-reuse licence. Do not enumerate hidden endpoints, automate queries, scrape, bulk-download records or PDFs, or put records into the installer without written authorization.

## Applicability controls

- Preserve OTTS, OTSH, SBKTS and ZOETS as separate document types.
- An approval is type/variant homologation evidence only to the extent stated in the primary document and its annexes.
- Do not treat an OTTS as an individual VIN build sheet.
- Do not infer a VAG factory engine code from an engine descriptor or stamped marking without independent corroboration.
- Do not infer an exact engine/gearbox pair unless the primary approval explicitly binds both values to the same type/variant scope.
- Registry metadata alone does not establish ECU, DTC, wiring, pinout, torque, adaptation, maintenance or repair applicability.

## Project action

The source remains `permission_required`; `data_ingested=false`; `source_snapshot_sha256=null`. No account, subscription, API key, payment, automated request, bulk download or import was used.

To unlock ingestion, obtain written permission from AO “Electronic Passport” or the relevant register operator explicitly covering commercial use, bulk extraction, persistent SQLite caching, offline third-party display, updates/retention and redistribution in VAG TECH PRO. If permission is limited to internal use, do not bundle the data in the Windows installer.

## 2026-11-06 visible-table field audit

The indexed public page snapshot at [the official OTTS route](https://docs.elpts.ru/ncher/otts) showed the active date filters **05.11.2026–06.11.2026**, a visible total label **«Всего оформлено: 14822»**, and the filtered result label **«Найдено: []»**. The empty filtered result is not evidence that the register is empty. The total label remains an unverified UI observation, not a validated corpus count.

The visible table columns were: registration number, vehicle make, vehicle type, status, validity start/end dates, applicant, manufacturer, certification body, ecological class, title-sheet form number, application-sheet form numbers, additional-sheet form numbers and printable OTTS/OTSH form. The observed table did **not** expose engine code, gearbox code, an engine/gearbox pairing, ECU identifier or repair-data fields. The underlying approval attachment was not downloaded or inspected.

This narrows the public-page evidence to document identity/status metadata. It does not change the rights gate: no dataset-specific licence, bulk-export permission, automated extraction right, persistent SQLite cache right, offline display right or redistribution right has been established. No record was downloaded, cached or imported.


## 2026-11-07 manufacturer-filter recheck

The official [OTTS page](https://docs.elpts.ru/ncher/otts) was rechecked on 2026-11-07. The manufacturer filter options included **AUDI AG** and **Volkswagen AG**. The active date-filtered result label remained **«Найдено: []»**. These are filter-option labels, not returned records; no VAG OTTS record or VAG-specific corpus count was verified. The visible total label remains **«Всего оформлено: 14822»**, but its complete-corpus semantics remain unverified.

The page also exposes a visible printable-form column. No PDF or underlying approval attachment was opened or downloaded. No machine-readable API or bulk endpoint was identified. The licence and reuse status remain unchanged: commercial use, persistent offline caching, automated extraction, third-party display and redistribution are not confirmed.

A separate indexed [SBKTS page](https://docs.elpts.ru/ncher/esbkts) snapshot for 04.11.2026–05.11.2026 showed 155 results and included a Volkswagen/FAW-Volkswagen metadata row. That observation is explicitly **SBKTS**, not OTTS; it was not downloaded and is not vehicle-fitment evidence. It must not be merged into the OTTS namespace.

**Decision unchanged:** source status remains `permission_required`; `data_ingested=false`; `source_snapshot_sha256=null`. The only safe current action is public document discovery with the document type and issuing authority kept explicit. No scraping, bulk export, local cache or product integration is authorized by this observation.

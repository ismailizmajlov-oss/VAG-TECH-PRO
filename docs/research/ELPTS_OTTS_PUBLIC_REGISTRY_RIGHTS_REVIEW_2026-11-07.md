# ELPTS public OTTS register — export-control recheck (2026-11-07)

## Decision

The official ELPTS public OTTS page was rechecked on 2026-11-07. The page exposes CSV, PDF and XML export controls in its rendered UI. This is a new access observation, **not** a licence or permission grant. No export was activated, no file was downloaded, and no API endpoint or export scope was verified. The source remains blocked for bulk extraction, persistent SQLite caching, offline third-party display and redistribution until the operator confirms those rights in writing or publishes resource-specific reuse terms.

No OTTS records, attachments or PDFs were downloaded or imported.

## Observed page state

Official route: https://docs.elpts.ru/ncher/otts

- Page title: «ОТТС».
- Visible total label: «Всего оформлено: 14822».
- Active date filter: 06.11.2026–07.11.2026.
- Filtered result label: «Найдено: []»; zero rows in the indexed active filter.
- Manufacturer options include AUDI AG and Volkswagen AG. These are filter values, not returned records.
- Visible export controls: CSV, PDF, XML.
- Visible table columns: approval number, vehicle make/type, status, validity dates, applicant, manufacturer, certification body, ecological class, title/application/additional sheet form numbers and printable OTTS/OTSH form.
- No engine code, gearbox code, exact engine/gearbox pair or ECU field is exposed in the visible summary table.
- The 14,822 label is a UI observation under a date filter, not a verified full-corpus count or VAG record count.

Related official pages:
- ELPTS national registers: https://elpts.ru/
- OTSH: https://docs.elpts.ru/ncher/otsh
- SBKTS: https://docs.elpts.ru/ncher/esbkts

## Export and rights status

| Capability | Status |
|---|---|
| Public OTTS page | Observed |
| CSV/PDF/XML controls | Visible |
| Export endpoint | Not verified |
| Export scope and completeness | Not established |
| Export file downloaded | No |
| Machine-readable API | Not verified |
| Dataset-specific licence | Not found |
| Commercial reuse | Not confirmed |
| Automated/bulk extraction | Not confirmed |
| Persistent SQLite caching | Not confirmed |
| Offline third-party display | Not confirmed |
| Redistribution | Not confirmed |
| Product import | Blocked |

The public page and visible export controls do not grant permission to scrape, cache, display or redistribute the underlying data. No automated requests or hidden endpoints were used.

## Applicability boundary

- Keep OTTS, OTSH, SBKTS and ZOETS as distinct document types.
- A manufacturer filter option is not an issued approval record.
- The active date-filtered query returned no rows; this does not establish that the historical register contains no VAG approvals.
- The visible summary table does not establish engine/gearbox codes, exact pairs, VIN build data, ECU, DTC or repair applicability.
- A printable-form column does not establish that the underlying document or annex may be cached or redistributed.

## Project state

- Source ID: `elpts-national-otts-register-public-query`
- Market scope: RU/EAEU
- `data_ingested=false`
- `source_snapshot_sha256=null`
- `permission_status=not_obtained`
- `bulk_reuse_allowed=not_established`
- `offline_cache_allowed=not_established`
- `redistribution_allowed=not_established`

The only permitted project action at this stage is documenting the public discovery route and asking the operator for written rights covering commercial use, bulk extraction, persistent local caching, offline display, update/retention and redistribution. No account, paid service or external request was initiated.

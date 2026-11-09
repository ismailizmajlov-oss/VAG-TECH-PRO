# ELPTS OTTS / SBKTS cross-register recheck — 2026-11-09

## Scope

This is a metadata-only review of the public ELPTS register search pages. It does not download a document, invoke an export control, or create an offline copy.

- OTTS search page: https://docs.elpts.ru/ncher/otts
- Separate SBKTS search page: https://docs.elpts.ru/ncher/esbkts
- Operator homepage: https://elpts.ru/

## OTTS observation

A fresh indexed rendering of the OTTS page showed:

- UI total label: `Всего оформлено: 14822`
- Active date filter: 08.11.2026–09.11.2026
- Filtered result label: `Найдено: []`
- Manufacturer filter option reproduced: `Volkswagen AG`
- No approval rows, engine codes, gearbox codes, exact engine/gearbox pairs or ECU fields were observed.

The UI total is not a verified complete-corpus count. The manufacturer option is not an approval record. A fresh search of the indexed OTTS page did not reproduce `AUDI AG`; that label appears on the separate ESBKTS page and must not be transferred between document registers.

## Separate SBKTS observation

The indexed ESBKTS page showed 155 results for 04.11.2026–05.11.2026 and two VOLKSWAGEN metadata rows:

| SBKTS registration number | Vehicle type | Manufacturer | Date |
|---|---|---|---|
| ТС RU А-CN.ОО14.59210 | FV6462HADCG | FAW-Volkswagen Automotive Co Ltd. | 2026-11-04 |
| ТС RU А-CN.ОО14.59209 | SVW71421GT | SAIC Volkswagen Automotive Co., Ltd. | 2026-11-04 |

These are SBKTS entries, not OTTS. The displayed type strings are vehicle-type identifiers, not engine or gearbox codes. The indexed table does not expose ECU data or exact powertrain pairing. `AUDI AG` and `Volkswagen AG` are filter options only, not proof of records.

## Rights and ingestion decision

The public page and search-indexed metadata do not establish a dataset-specific licence or permission for bulk extraction, persistent SQLite caching, offline display, commercial reuse or redistribution. No CSV/PDF/XML export was activated. No PDF, record attachment, raw page bytes or source file was downloaded. No SHA-256 is claimed for unavailable bytes.

Both registers remain `permission_status=not_obtained`, `product_import_allowed=false`, and `data_ingested=false`. The SBKTS rows are retained only as source-discovery metadata and are not fitment evidence.

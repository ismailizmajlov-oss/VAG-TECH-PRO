# ELPTS public OTTS register — recheck (2026-11-08)

## Decision

The public OTTS route at https://docs.elpts.ru/ncher/otts was rechecked on 2026-11-08. The visible date filter was 07.11.2026–08.11.2026, the filtered result label was empty, and the UI total label remained 14,822. AUDI AG and Volkswagen AG appear as manufacturer filter options, not returned approval records. This confirms a publicly visible search route and a current page state only; it does not establish corpus completeness, VAG coverage, a machine-readable API, bulk extraction, offline caching, display or redistribution rights.

No record, export, PDF or approval attachment was downloaded. No raw HTML response was captured, so no raw-page SHA-256 is claimed. The source remains permission-required and is not imported.

## Observed route and page state

- Public route: https://docs.elpts.ru/ncher/otts
- Separate document routes: https://docs.elpts.ru/ncher/otsh and https://docs.elpts.ru/ncher/esbkts
- Page title: «ОТТС».
- Visible total label: «Всего оформлено: 14822» (UI label only; not a verified complete-corpus count).
- Active date filter: 07.11.2026–08.11.2026.
- Filtered result label: «Найдено: []» (zero rows in this indexed page snapshot).
- Manufacturer filter options include AUDI AG and Volkswagen AG. These are selectable filter values only; no VAG OTTS record or count was returned.
- Visible table columns remain document number, make, type, status, validity dates, applicant, manufacturer, certification body, ecological class, form numbers and printable OTTS/OTSH form.
- The visible table does not expose engine code, gearbox code, exact engine/gearbox pair, ECU, DTC or repair applicability.
- CSV/PDF/XML export controls were last observed on 2026-11-07. They were not re-verified in the 2026-11-08 page snapshot; no export endpoint or scope is known.

The opened page shell exposes the title, date filters and result/total labels, but not the raw HTML or a documented API contract. No undocumented endpoint was guessed or called.

## Rights and import boundary

| Capability | Status |
|---|---|
| Public page and date-filtered query route | Observed |
| Current 07.11.2026–08.11.2026 result | Empty |
| UI total label | 14,822; not a verified corpus count |
| VAG OTTS records returned | None observed |
| Manufacturer filter values AUDI AG / Volkswagen AG | Options only |
| CSV/PDF/XML export controls | Last observed 2026-11-07 |
| Export endpoint and completeness | Not established |
| Dataset-specific licence | Not found |
| Commercial reuse | Not confirmed |
| Automated/bulk extraction | Not confirmed |
| Persistent SQLite caching | Not confirmed |
| Offline third-party display | Not confirmed |
| Redistribution | Not confirmed |
| Product import | Blocked |

Public visibility is not a grant to scrape, cache, display or redistribute the data. Keep OTTS, OTSH, SBKTS and ZOETS in separate namespaces. A SBKTS row mentioning Volkswagen is not an OTTS record and is not powertrain fitment evidence.

## Provenance

- Source ID: `elpts-national-otts-register-public-query`
- Market scope: RU/EAEU
- Observed at: 2026-11-08
- Page URL: https://docs.elpts.ru/ncher/otts
- Capture method: public indexed rendering plus opened page shell
- Raw page bytes captured: no
- Raw page SHA-256: not available
- Source snapshot SHA-256: null (no source bytes downloaded)
- `data_ingested=false`
- `permission_status=not_obtained`
- Bulk reuse, offline cache, display and redistribution: not established

The next lawful step is written clarification from the operator covering the exact record fields, commercial use, bulk export, persistent local caching, offline display, update/retention and redistribution. No request was sent and no account or paid service was used.

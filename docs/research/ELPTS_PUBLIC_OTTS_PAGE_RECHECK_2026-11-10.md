# ELPTS public OTTS page recheck — 2026-11-10

## Observation

The official national-register page was checked on 10 November 2026:

- OTTS page: https://docs.elpts.ru/ncher/otts
- The search-indexed rendering shows the page title **ОТТС** and the visible UI label **«Всего оформлено: 14822»**.
- The active date filter is **09.11.2026–10.11.2026** and the visible filtered result label is **«Найдено: []»**.
- The manufacturer selector includes **AUDI AG** and **Volkswagen AG**. These are selector options only, not returned approval records.
- The opened page exposes a dynamic shell with unresolved result-count placeholders. No record rows, raw HTML bytes, downloadable PDF, or API/export endpoint were independently captured.

## Interpretation and product boundary

This is a current public-query discovery observation, not a verified export of the national OTTS corpus. The UI total 14,822 is not treated as a verified complete-corpus count. An empty one-day date filter does not establish that older VAG approvals are absent. Manufacturer filter options do not establish that a corresponding approval record exists.

The visible columns are document/registry metadata: approval registration number, make, vehicle type, status, validity dates, applicant, manufacturer, certification body, environmental class, form identifiers, and a printed OTTS/OTSH form reference. They do not expose factory engine codes, gearbox codes, an exact engine/gearbox pair, ECU, DTC, wiring, pinouts, repair procedures, torque values, adaptations, or service intervals.

## Rights and ingestion decision

Public search visibility is not a reuse licence. The source manifest continues to record commercial use, third-party display, bulk extraction, persistent offline caching, and redistribution as **not confirmed**. No automated extraction, export, PDF download, raw-byte capture, SQLite ingestion, or product display was performed. No source SHA-256 is claimed because no source bytes were captured.

The existing decision remains unchanged: manual document-level lookup only after the document type and issuing authority are confirmed; no scraping, bulk export, offline caching, product display, or redistribution until a dataset-specific open licence or written permission is verified.

## Evidence

- Official OTTS page: https://docs.elpts.ru/ncher/otts
- Official operator homepage and registry navigation: https://elpts.ru/
- Search-indexed page rendering checked on 2026-11-10; opened official page shell checked on the same date.

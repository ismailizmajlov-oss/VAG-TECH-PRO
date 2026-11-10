# ELPTS public OTTS UI recheck — 2026-11-11

## Result

The official public query page remains a discovery-only source. The direct page renderer loads the shell and dynamic placeholders but does not expose the underlying result rows. A search-indexed result showed a displayed counter of 14,822 and a query date range of 2026-11-09 through 2026-11-10 with zero returned records. That counter is not independently reproduced by the direct page renderer and is recorded only as a search-index observation.

Official page: https://docs.elpts.ru/ncher/otts

## What was not established

- No raw OTTS record bytes were retrieved.
- No downloadable bulk export or documented public API contract was confirmed.
- No dataset-specific license or permission for commercial use, offline SQLite caching, end-user display, bulk reuse or redistribution was found.
- No written permission request was sent.
- No source snapshot SHA-256 was created because no source data bytes were retrieved.
- No Russian/ЕАЭС OTTS record was imported and no VAG model, generation, engine, gearbox or ECU applicability was inferred.

## Product decision

Keep `elpts-national-otts-register-public-query` as `metadata_only_permission_required`. The public UI counter is not a record count for VAG and is not evidence of a reusable dataset. Do not scrape, download, cache or redistribute the records. Continue to use the official UI only for individual discovery where its access terms allow it, and obtain written dataset-specific permission before any automated acquisition or offline product use.

The related «Справочник марок» and «Справочник технических характеристик» XLSX links remain metadata-only. The software-use tariff and public hyperlinks do not grant dataset reuse rights.

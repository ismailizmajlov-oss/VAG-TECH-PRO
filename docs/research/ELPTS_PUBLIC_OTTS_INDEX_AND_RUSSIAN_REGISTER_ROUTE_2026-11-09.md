# ELPTS public OTTS index and Russian national-register route recheck — 2026-11-09

## Finding

A fresh public search-indexed rendering of the ELPTS electronic OTTS page exposed more metadata than the page-shell extraction available in the previous review. This improves source discovery, but it does **not** provide a reusable data snapshot or establish a VAG approval record.

- Public OTTS page: https://docs.elpts.ru/ncher/otts
- Official operator homepage: https://elpts.ru/
- Official Russian national-register link shown under the homepage section «Реестры»: https://www.rst.gov.ru/portal/gost/home/activity/compliance/evaluationcompliance/AcknowledgementCorrespondence

## What the public OTTS page exposed

The fresh search-indexed rendering observed on 2026-11-09 showed:

- UI label «Всего оформлено: 14822»;
- active date filters 07.11.2026–08.11.2026;
- «Найдено: []» for that filtered interval;
- manufacturer filter options including «AUDI AG» and «Volkswagen AG»;
- columns for approval registration number, vehicle make/type, status, validity dates, applicant, manufacturer, certification body, environmental class, title/additional-sheet form numbers and a printable OTTS/OTSH form link.

These are **UI/index observations only**. The value 14822 is not independently verified as a complete or current corpus count. Manufacturer filter values are options, not returned approval rows. The empty date-filtered result does not establish that older VAG approvals are absent. No VAG OTTS row or VAG approval count was verified.

The separately opened page still rendered unresolved dynamic placeholders for its result counters and exposed no record rows in the page text extraction. This explains the difference between the richer search-indexed rendering and the limited page-shell extraction; it does not prove that the underlying browser application or export interface is fully accessible.

The visible summary columns do not expose factory engine code, gearbox code, an exact engine/gearbox pair or ECU identity. A printable-form link is only a possible document route; no filled form or attachment was retrieved.

## Official Russian national-register route

The official ELPTS homepage lists «Национальная часть единого реестра выданных ОТТС, ОТШ, СБКТС» under «Реестры» and links to the RST.gov.ru path above. A direct fetch of that linked page timed out during this review. Its content, search behaviour, export format and technical fields therefore remain unverified.

The ELPTS homepage also states that additional statistical reports are provided to system participants under a separate agreement after a request through its Centre for Applications. That statement concerns the described report service; it is not treated as proof that public OTTS search is paid, nor as a data licence for VAG TECH PRO.

## Rights and ingestion decision

No rights have changed:

- individual public-page visibility: observed;
- bulk extraction and automated collection: not established;
- API/export endpoint and permitted export scope: not verified;
- persistent SQLite caching: not established;
- offline end-user display: not established;
- commercial or non-commercial third-party reuse: not established;
- redistribution in installers or updates: not established;
- written permission: not obtained.

No record, PDF, CSV, XML, workbook or raw page bytes were downloaded. No source snapshot SHA-256 is claimed. No rows were imported. The source remains `permission_status=not_obtained`, `data_ingested=false`, `product_import_allowed=false`, and `source_snapshot_sha256=null`.

## Technical applicability boundary

Even after rights are cleared, the public summary page can at most support document-identity and status metadata unless the actual approval and annexes are lawfully available. Do not infer:

- a VAG model/generation or production-year fitment from a manufacturer filter option;
- an engine code or gearbox code from a free-text make/type field;
- an exact engine/gearbox pair unless both are explicitly tied to the same exact type/variant/version and annex scope;
- ECU, DTC, wiring, pinout, torque, adaptation or repair applicability from an OTTS summary row.

Any future approved import must preserve the original document number/class/status/revision, exact type/variant/version, annex/page locator, raw values, market scope, source bytes SHA-256, rights evidence and independent technical-review state.

## Primary sources

- ELPTS public OTTS page: https://docs.elpts.ru/ncher/otts
- ELPTS official homepage and register links: https://elpts.ru/
- RST.gov.ru national-register destination linked by ELPTS: https://www.rst.gov.ru/portal/gost/home/activity/compliance/evaluationcompliance/AcknowledgementCorrespondence
- EEC temporary electronic register navigation page: https://eec.eaeunion.org/comission/department/deptexreg/tr/temprorary_otts.php

Review date: 2026-11-09.

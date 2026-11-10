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


## Official ELPTS homepage follow-up

The official [ELPTS homepage](https://elpts.ru/) links to the national part of the unified OTTS/OTSH/SBKTS register at [rst.gov.ru](https://www.rst.gov.ru/portal/gost/home/activity/compliance/evaluationcompliance/AcknowledgementCorrespondence). That route timed out when opened on 10 November 2026; no registry rows, files or API were obtained.

The same official homepage exposes a section called **«Справочники АС СЭП»** and links to:

- [Справочник марок](https://elpts.ru/wp-content/uploads/2023/06/spravochnik-marok.xlsx) — XLSX link, not downloaded.
- [Справочник технических характеристик](https://disk.yandex.ru/d/VeYxsi3IcnmK2w) — the public Yandex Disk listing shows `Справочник технических характеристик_202601109_1755.xlsx`, dated 09.11.2026 18:03, 16.9 MB; not downloaded.
- The same Yandex Disk listing also shows an XLSX on maximum permissible mass ranges, dated 09.04.2026, 10 KB; not downloaded.

No licence or permission for reuse, display, offline caching or redistribution was stated on the linked pages. These files are recorded as source leads only. No files were downloaded, no SHA-256 values are claimed, and no content was imported into SQLite.

The official homepage states that AS EOTTS training materials require an official organisation profile in the application processing centre, with the login email specified in the contract; it also links to an electronic-document offer and confidentiality agreement. Paid EOTTS reports require a separate agreement or invoice-contract. No account, contract, paid access or request was created.

An [ELPTS notice dated 21 August 2026](https://elpts.ru/uvazhaemye-polzovateli-as-eotts/) says a software issue was fixed for entering gearbox information, including additional reduction and hydraulic transmissions. This confirms that gearbox information exists in the EOTTS workflow; it does **not** expose VAG factory gearbox codes, exact engine/gearbox pairs, or individual vehicle fitment in the public OTTS query.

A 2018 [NAMI/EEC research report](https://eec.eaeunion.org/upload/iblock/ffb/Otchet-OTTS-etap-1_664.pdf) describes national EAEU electronic conformity registers, public internet access to necessary information, authorised registry access for accredited certification bodies, and PDF scans of paper documents. This is historical process context, not a licence for bulk extraction or third-party offline redistribution.

## Decision

The new official links improve discovery, but do not clear the legal gate. Keep all ELPTS/RST/XLSX sources as **not licensed for product ingestion** until a dataset-specific open licence or written permission explicitly covers bulk extraction, local SQLite storage, offline display, commercial use and redistribution.

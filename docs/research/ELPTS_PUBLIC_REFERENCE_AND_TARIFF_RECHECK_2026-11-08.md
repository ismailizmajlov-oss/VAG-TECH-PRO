# ELPTS public reference files and tariff recheck — 2026-11-08

## Decision

**Keep all three ELPTS source entries permission-required and metadata-only. Do not download either XLSX, scrape OTTS records, cache content in SQLite, display source records in VAG TECH PRO, or redistribute any file.** The new official-page observations clarify where the links and commercial services sit, but they do not grant a dataset-specific reuse licence.

## Official observations

### Reference directories are linked under the AS SEP participant section

The official ELPTS homepage places «Справочник марок» and «Справочник технических характеристик» under the section «Справочники АС СЭП». The links are publicly visible in the rendered page, but the page provides no dataset-specific licence, rights statement, API contract or terms for bulk extraction, local persistent storage, offline end-user display, or redistribution.

The same homepage says that paid statistical reports are provided to AS SEP participants under concluded service agreements and separate additional agreements after a request through the Centre for Applications. This describes the report service; it does not prove that the two linked reference workbooks are themselves paid reports or categorically restricted. Equally, it does not authorize third-party reuse of the workbook contents.

### The 2026 tariff-plan amendment is about software use, not dataset reuse

ELPTS published a notice on 2026-10-02 stating that wording «и передача сведений в АС СЭП» was removed from paragraph 4 of the tariff-plan conditions for the right to use software, with the amendment effective 2026-11-01.

The current linked tariff-plan PDF is dated 2026-09-17 and describes the «Электронное одобрение типа транспортного средства» software for certification bodies included in the Russian part of the relevant unified register and manufacturers/authorized representatives working under TR TS 018/2011 and Government Resolution No. 855. It lists a paid workstation licence. This is a software-use tariff for the specified professional participants, not a licence to reuse ELPTS reference datasets in a separate third-party offline application.

No ELPTS software licence, participant account, paid report, API access, export or agreement was requested or accepted.

### Public OTTS register link

The ELPTS homepage links the national part of the unified OTTS/OTSH/SBKTS register to the official RST website. A public link establishes a route for individual discovery only. It does not establish a VAG TECH PRO right to automate extraction, retain document bytes, create a derivative database, cache records offline, display them to third parties or redistribute them with an installer.

## Source-by-source disposition

| Source ID | Observed item | Current decision |
|---|---|---|
| `elpts-national-otts-register-public-query` | Public OTTS page and registry navigation | Individual public lookup observation only; no bulk/API/cache/display/redistribution rights established |
| `elpts-sep-make-directory` | Direct XLSX link for «Справочник марок» | Metadata-only; workbook bytes not retrieved; no hash |
| `elpts-sep-technical-characteristics-reference` | Public Yandex Disk listing for «Справочник технических характеристик» | Metadata-only; workbook bytes not retrieved; no hash |

For all three sources, commercial use, bulk reuse, local persistent caching, offline display and redistribution remain unestablished. No technical applicability, VAG model coverage, engine code, gearbox code, exact engine/gearbox pair or ECU applicability is claimed.

## Evidence reviewed

- ELPTS homepage: https://elpts.ru/
  - «Реестры» section and national OTTS/OTSH/SBKTS register link.
  - «Справочники АС СЭП» section and the two reference-file links.
  - Paid statistical reports described as a service for AS SEP participants under agreements/additional agreements.
- ELPTS notice dated 2026-10-02: https://elpts.ru/uvedomlenie-o-vnesenii-izmenenij-v-tarifnyj-plan-k-oferte-pravo-ispolzovaniya-po/
  - Paragraph 4 wording change effective 2026-11-01.
- ELPTS tariff-plan page: https://elpts.ru/articles/tarifnyj-plan-dlya-organov-po-sertifikaczii-i-zayavitelej-s-19-02-2024/
- Linked tariff-plan PDF dated 2026-09-17: https://elpts.ru/wp-content/uploads/2026/10/tarifnyj-plan-k-oferte-po-17.09.2026.pdf

## Minimum permission required

Before downloading or inspecting either workbook, obtain written permission from the authorized data-rights holder covering, for each specific file or dataset:

1. download and inspection;
2. bulk extraction and normalization;
3. local persistent SQLite storage and historical revisions;
4. offline display to end users;
5. inclusion in installer/update packages or an approved user-initiated download;
6. redistribution of source or derived records;
7. commercial and non-commercial use;
8. attribution, share-alike, update, correction and deletion obligations.

A software-use tariff, a public hyperlink, a participant-only service description or a public file listing is not a substitute for that permission.

## Audit state

- Review date: 2026-11-08.
- XLSX downloads: 0.
- Source-file SHA-256 values: intentionally null because no file bytes were retrieved.
- OTTS records imported: 0.
- Rights flags upgraded: none.
- External account or paid access: none.
- Permission request sent: no.
- Product import: disabled.

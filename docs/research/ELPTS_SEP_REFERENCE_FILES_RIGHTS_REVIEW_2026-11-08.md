# ELPTS AS SEP reference files — rights and provenance review (2026-11-08)

## Finding

The public ELPTS homepage lists a section titled «Справочники АС СЭП» and links two potentially relevant reference files:

1. **Справочник марок** — direct XLSX link: https://elpts.ru/wp-content/uploads/2023/06/spravochnik-marok.xlsx
2. **Справочник технических характеристик** — public Yandex Disk listing: https://disk.yandex.ru/d/VeYxsi3IcnmK2w. The listing exposes `Справочник технических характеристик_202601106_1645.xlsx`, 16.9 MB, displayed modification time 06.11.2026 16:52.

The second file is a higher-priority discovery candidate for Russian vehicle identity/technical-characteristic fields. However, its columns and contents have not been inspected. Neither file is assumed to contain VAG rows, factory engine/gearbox codes, exact engine/gearbox pairs, model years, generations or ECU data.

## Access and rights review

The ELPTS homepage links these files under «Справочники АС СЭП» (public page: https://elpts.ru/). Public reachability and a publisher-provided link do not establish permission for downloading, bulk extraction, persistent local caching, offline third-party display or redistribution.

The published document titled «ОФЕРТА (право использования ПО)» is a paid software-use agreement, not a dataset-specific licence for these reference files:
- Offer page: https://elpts.ru/articles/oferta-pravo-ispolzovaniya-po/
- PDF: https://elpts.ru/wp-content/uploads/2023/04/oferta-pravo-ispolzovaniya-po-s-izmen-2.0.pdf

The offer describes a non-exclusive right to use ELPTS software under a tariff plan and prepayment; its IP section requires written permission for copying/reproducing/distributing the administrator's protected results. It does not grant VAG TECH PRO a data-reuse licence for the linked XLSX files. No offer was accepted, no payment made, no account created and no request submitted.

## Product decision

Both files are registered as RU-only metadata candidates in `data/source-manifests/vag-factory-source-register.json`:

- `elpts-sep-make-directory`
- `elpts-sep-technical-characteristics-reference`

For both:
- `data_ingested=false`
- `source_snapshot_sha256=null`
- `hash_status=not_downloaded_no_ingestion`
- `permission_status=not_obtained`
- commercial use, display, bulk reuse, offline cache and redistribution remain `not_established`
- no product or offline-pack import is allowed.

No XLSX file bytes were downloaded, so no SHA-256 is claimed. The make directory is only a candidate for make-name normalization. The technical-characteristics workbook is a high-priority candidate for schema review only after rights are cleared.

## Required next step

Obtain written permission from АО «Электронный паспорт» that explicitly covers:
1. downloading and inspecting the named files;
2. extracting fields and rows;
3. local SQLite storage and offline display;
4. refresh/update cadence and retention;
5. commercial and non-commercial use;
6. redistribution inside the VAG TECH PRO installer and update packages;
7. attribution and any restrictions on derived/normalized fields.

Until those points are confirmed, do not download or import the files.

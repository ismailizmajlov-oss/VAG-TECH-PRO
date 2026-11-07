# CarDir CC BY 4.0 owner-manual facts — source and rights review

Review date: 2026-11-07.

## Decision

**Approved for a separate, read-only, attributed VAG reference-facts research pack only.** The published CarDir open-data page explicitly licenses its CSV/JSON dataset under Creative Commons Attribution 4.0 International. The licence permits commercial and non-commercial copying, use in services and redistribution when CarDir is attributed. The project may therefore download and cache the published facts in a separate SQLite research pack, provided the pack retains attribution, the source snapshot hash, row hashes and the original source references.

This is not an OEM primary database. CarDir is the publisher of a curated dataset extracted from owner manuals. The underlying manuals remain the original sources; VAG TECH PRO will store the licensed factual rows and references, not copy or redistribute manual PDFs.

## Publisher-published dataset scope

The dataset page reviewed on 2026-11-07 states that the current snapshot was checked on 2026-11-07 and contains 41,649 verified values for 561 models. It offers CSV and JSON files and identifies these columns:

- brand, model, key, key_label_ru
- qualifier, value, unit
- source_title, source_page, source_url, page_url, verified_at

The parameter groups include engine oil, gearbox oil, coolant, brake fluid, tyre pressure and sizes, battery, spark plugs, service intervals and air-conditioning refrigerant. Each row carries an owner-manual title, page locator, CarDir source-card URL, model-page URL and last verification date.

The publisher's methodology describes source-manual discovery, page-level extraction, two independent extraction passes, citation/page matching, range checks and manual-model consistency checks. This is the publisher's verification claim; VAG TECH PRO will preserve it as publisher verification, not mislabel it as our independent OEM review.

## VAG filtering and applicability limits

The Windows pack builder uses exact case-insensitive brand equality against the reviewed allowlist only. It does not use substring or fuzzy matching.

- Keep the original brand, model, qualifier, value, unit and source fields.
- Keep the qualifier as raw text. Do not convert a phrase such as "2.0 TFSI" into an engine code or a gearbox label into a factory transmission code.
- Do not infer a generation or model year from the model name or qualifier.
- Set market scope to UNKNOWN: the CSV has no market column and mixes source manuals/markets.
- Do not infer an engine/gearbox pair, ECU, DTC, wiring, pinout or repair procedure.
- Do not promote a model-level or qualifier-level value to exact vehicle fitment.
- Keep the pack outside the production vehicle/repair database until independent applicability review and a separate integration decision.

This source can add traceable owner-manual reference facts for maintenance sections. It does not fill the missing factory diagnostic, repair, electrical or RU/EAEU type-approval corpus.

## Snapshot acquisition and hashes

The current source manifest pins the 2026-11-07 CSV snapshot at 14,291,343 bytes with SHA-256 `72b3c68490cdef52bbbc8e124700ddc3a627e6ed7d15e0f809010c72dec2c922`. It contains 41,649 rows and 561 brand/model pairs; exact VAG brand equality retains 773 facts across 24 models and the observed labels Audi, Porsche, Skoda and Volkswagen. Compared with the previous snapshot (`93709b613cd289cb50f2f13ed9f02319979d6b9be94330326df3fc24a9841375`), 1,658 all-brand source rows changed and one VAG fact changed: a Porsche Cayman 2009 rear-axle/summer-tyre wheel-size value changed from `10 J x 19 H2` to `8.5 J x 17 H2`. The publisher's qualifier is broader than one wheel-size option; this row remains raw, ambiguous and not independently resolved. No exact fitment is inferred.

The last successful SQLite pack build, Windows workflow run 36 on 2026-11-07, used the **previous** snapshot (`93709b...`), not the current `72b3...` snapshot. Its artifact is therefore stale for the current source revision and must not be packaged as the current pack. The current snapshot's acquisition and SQLite rebuild must pass again before a current database hash or artifact hash is recorded. Until then, the current source snapshot is pinned but its refreshed SQLite pack remains pending and outside the desktop installer.

A Windows-only workflow will acquire the exact published CSV over HTTPS from the URL below, reject redirects away from the CarDir host, enforce a download-size cap, validate the 12-column schema and the publisher-stated 41,649-row / 561-model snapshot, and calculate:

1. SHA-256 of the complete source CSV;
2. SHA-256 of every retained VAG source row over canonical JSON of the original parsed field strings;
3. SHA-256 of the generated SQLite database and pack manifest.

The workflow fails closed if the published snapshot changes from the pinned source hash, byte size, schema or reviewed counts. The successful Windows workflow run 36 (2026-11-07) independently built and verified a read-only SQLite pack for the **previous** source snapshot only: 773 VAG facts across 24 models, four brands and 19 parameter keys; SQLite integrity_check returned `ok`, foreign_key_check returned no violations, and all 773 rows carry source-row SHA-256 values. That historical artifact (ID `13575630528`) has source CSV SHA-256 `93709b613cd289cb50f2f13ed9f02319979d6b9be94330326df3fc24a9841375`, source-manifest SHA-256 `08e909410ce2a303ed6f6d811c72ad9de323e8ff250558c7c27a3d563348e727`, SQLite SHA-256 `6c076d38d9321acd9a121163161a5f9e60888756a09d2b7752ac38843baec6b6`, and uploaded artifact SHA-256 `17096994144710add18413e23287fff4150ac09f9321c99b44ceaf71a809b742`. These hashes identify the previous snapshot and must not be attributed to the current `72b3...` source. A fresh build and independent verification of the current snapshot are pending; no current SQLite or artifact hash is asserted. The research pack is not included in the desktop installer or production catalog.

## Rights and attribution

- Dataset: https://cardir.ru/dannye/
- Methodology: https://cardir.ru/metodika/
- Source index: https://cardir.ru/istochniki/
- Licence: https://creativecommons.org/licenses/by/4.0/
- Required attribution: **CarDir (https://cardir.ru/dannye/), CC BY 4.0.**
- Modification notice: filtered to the exact VAG-brand allowlist; original field values and qualifiers are preserved.

The published licence covers the dataset. It does not transfer rights in the underlying OEM manuals, and the pack will not bundle those PDFs.

## Evidence reviewed

1. CarDir open-data page, reviewed 2026-11-07: dataset size/date, field list, parameter groups, CSV/JSON download links and explicit CC BY 4.0 terms: https://cardir.ru/dannye/
2. CarDir methodology, updated 2026-11-04: source-manual extraction, page citations, independent passes and verification controls: https://cardir.ru/metodika/
3. CarDir source index and method: https://cardir.ru/istochniki/
4. Example VAG model pages showing model/generation and powertrain-conditioned reference sections: Volkswagen Golf https://cardir.ru/volkswagen/golf/ ; Audi A4 https://cardir.ru/audi/a4/ ; Skoda Octavia https://cardir.ru/skoda/octavia/

**Disposition:** verified licensed research pack only; market_scope=UNKNOWN; `data_ingested=false`; `production_import=false`; `product_import_allowed=false`; source snapshot and SQLite hashes are pinned above. Desktop integration and any production use remain disabled.

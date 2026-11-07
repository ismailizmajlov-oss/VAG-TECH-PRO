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

The Windows acquisition workflow downloaded the exact published CSV on 2026-11-07. The 14,291,137-byte source snapshot has SHA-256 `93709b613cd289cb50f2f13ed9f02319979d6b9be94330326df3fc24a9841375`. It contains 41,649 rows and 561 brand/model pairs; exact VAG brand equality retains 773 facts across 24 models and the observed labels Audi, Porsche, Skoda and Volkswagen. The source hash and byte size are now pinned in the committed source manifest.

A Windows-only workflow will acquire the exact published CSV over HTTPS from the URL below, reject redirects away from the CarDir host, enforce a download-size cap, validate the 12-column schema and the publisher-stated 41,649-row / 561-model snapshot, and calculate:

1. SHA-256 of the complete source CSV;
2. SHA-256 of every retained VAG source row over canonical JSON of the original parsed field strings;
3. SHA-256 of the generated SQLite database and pack manifest.

The workflow fails closed if the published snapshot changes from the pinned source hash, byte size, schema or reviewed counts. Windows CI run 29 (2026-11-07) rebuilt the read-only SQLite pack after the source-manifest note was corrected and independently verified 773 VAG facts across 24 models, four brands and 19 parameter keys. SQLite integrity_check returned `ok`, foreign_key_check returned no violations, and all 773 rows carry source-row SHA-256 values. The source CSV SHA-256 is `93709b613cd289cb50f2f13ed9f02319979d6b9be94330326df3fc24a9841375`; source-manifest SHA-256 is `759e656304a5975a2d7f0f0ab493d08733884832ea15d874380a6d6c73fcd8e8`; pack-manifest SHA-256 is `5eec1d907c6afa7c96abd4d6abb45a5691c4d946001769743c2fb600da1ec02f`; source-snapshot manifest SHA-256 is `6eed8c1df1218eb50b4480b46990055f42918a04d1495e42d439397f9ef83ec4`; SQLite SHA-256 is `b9a41abbf92e7d5e3dea183177cfb807f9e62c61e142552d727afb28b79798b2`; artifact ZIP SHA-256 is `f732d3311ebc103c4ae25ec918b76a10c7f923ed2e82c3bac0acd226f4692776` (artifact ID `13574171858`). The pack is still a CI research artifact and is not yet included in the desktop installer or production catalog.

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

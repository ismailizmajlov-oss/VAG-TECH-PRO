# CarDir CC BY 4.0 owner-manual facts — source and rights review

Review date: 2026-11-07.

## Decision

**Approved for a separate, read-only, attributed VAG reference-facts research pack only.** The published CarDir open-data page explicitly licenses its CSV/JSON dataset under Creative Commons Attribution 4.0 International. The licence permits commercial and non-commercial copying, use in services and redistribution when CarDir is attributed. The project may therefore download and cache the published facts in a separate SQLite research pack, provided the pack retains attribution, the source snapshot hash, row hashes and the original source references.

This is not an OEM primary database. CarDir is the publisher of a curated dataset extracted from owner manuals. The underlying manuals remain the original sources; VAG TECH PRO will store the licensed factual rows and references, not copy or redistribute manual PDFs.

## Publisher-published dataset scope

The dataset page reviewed on 2026-11-07 states that the current snapshot was checked on 2026-11-06 and contains 41,128 verified values for 548 models. It offers CSV and JSON files and identifies these columns:

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

No CSV bytes were available to the review process itself; the web reader does not expose the CSV body. Therefore no source-file SHA-256 is claimed in this document or the committed source manifest.

A Windows-only workflow will acquire the exact published CSV over HTTPS from the URL below, reject redirects away from the CarDir host, enforce a download-size cap, validate the 12-column schema and the publisher-stated 41,128-row / 548-model snapshot, and calculate:

1. SHA-256 of the complete source CSV;
2. SHA-256 of every retained VAG source row over canonical JSON of the original parsed field strings;
3. SHA-256 of the generated SQLite database and pack manifest.

The workflow must fail closed if the published snapshot changes without a reviewed source-manifest update. The committed manifest keeps the source snapshot hash null until the Windows acquisition actually succeeds.

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

**Disposition:** licensed research pack only; market_scope=UNKNOWN; data_ingested=false; production_import=false; product_import_allowed=false; source_snapshot_sha256=null until a Windows acquisition artifact supplies the actual file.

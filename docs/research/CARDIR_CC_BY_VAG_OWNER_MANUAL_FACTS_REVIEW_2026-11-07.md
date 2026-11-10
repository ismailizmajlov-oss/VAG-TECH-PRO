# CarDir CC BY 4.0 owner-manual facts — source and rights review

Original rights review: 2026-11-07. Snapshot recheck: 2026-11-10.

## Decision

**Approved for a separate, read-only, attributed VAG reference-facts research pack only.** The published CarDir open-data page explicitly licenses its CSV/JSON dataset under Creative Commons Attribution 4.0 International. The licence permits commercial and non-commercial copying, use in services and redistribution when CarDir is attributed. The project may therefore download and cache the published facts in a separate SQLite research pack, provided the pack retains attribution, the source snapshot hash, row hashes and the original source references.

This is not an OEM primary database. CarDir is the publisher of a curated dataset extracted from owner manuals. The underlying manuals remain the original sources; VAG TECH PRO will store the licensed factual rows and references, not copy or redistribute manual PDFs.

## Publisher-published dataset scope

The dataset page rechecked on 2026-11-10 states that the current snapshot was checked on 2026-11-09 and contains 44,245 verified values for 610 models. It offers CSV and JSON files and identifies these columns:

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

The first 2026-11-10 acquisition pinned 15,165,485 bytes, SHA-256 `64a507e4191a9047fe62ec17868488140dd14f692b012d4e1954b6c4322673be`, 44,245 rows and 610 brand/model pairs. That snapshot is now superseded. The latest Windows acquisition (2026-11-10 02:23 UTC) contains 15,174,126 bytes, SHA-256 `30f502729f08fa7a061ab0f6c19f62eab6385dea646c15878b8c3430b4b064f4`, 44,272 rows and 611 brand/model pairs. The publisher page still displays 44,245/610, so the page/file count discrepancy is explicitly recorded. Exact VAG brand equality retains the same 948 facts across 26 models and five labels: Audi, Porsche, SEAT, Skoda and Volkswagen. Exact multiset comparison of the previous pinned CSV with the latest CSV found 52 full rows added and 25 removed, all outside the VAG allowlist; the complete VAG row multiset and canonical SHA-256 `92720634c6f6ba907ea554e3bf59afea1ff312444897c365ffe4970b95c108ad` are unchanged. No VAG value, unit, qualifier, source title, source locator, source URL or verification date changed. The earlier comparison with the archived run-36 baseline (`93709b613cd289cb50f2f13ed9f02319979d6b9be94330326df3fc24a9841375`) remains historical; it is not substituted for the exact latest-snapshot delta.

The last successful current-pack build (Windows workflow run 58 on 2026-11-10) used the previous pinned CSV snapshot `64a507...`; it is stale for the latest `30f502...` file. The subsequent acquisition probe run 59 failed closed when it detected 44,272 rows / 611 model pairs instead of the old 44,245 / 610 pin. The exact VAG subset was independently compared and found unchanged. A new Windows SQLite build and independent verification against `30f502...` are required before the refreshed pack can be used by desktop CI; the previous artifact must not be substituted.

A Windows-only workflow acquires the exact published CSV over HTTPS from the URL below, rejects redirects away from the CarDir host, enforces a download-size cap, validates the 12-column schema and the pinned 44,272-row / 611-model file snapshot, and calculates. The publisher page's 44,245 / 610 summary remains a separate page observation and is not treated as the downloaded-file count.

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


## 2026-11-10 initial source snapshot recheck (superseded by the later refresh below)

The current publisher page (https://cardir.ru/dannye/) reports 44,245 verified values for 610 models, data last checked 2026-11-09, and CC BY 4.0 terms permitting commercial use, display in services, offline copying and redistribution with attribution. The Windows source-change probe retrieved the CSV directly from the publisher's HTTPS URL and independently computed the SHA-256 and row/model counts. The complete CSV and snapshot manifest were retained as a CI audit artifact; no owner-manual PDF was downloaded or bundled.

The current VAG subset contains 948 rows across 26 models and Audi, Porsche, SEAT, Skoda and Volkswagen. Against the archived run-36 CSV baseline, no VAG values or units changed and no VAG verification dates changed. There were 121 new VAG identity groups, 205 added rows, 30 removed full-row variants and 22 page-URL-only groups. Because the intermediate 72b3 snapshot has no available CSV artifact, no exact delta from that intermediate revision is claimed.

The refreshed SQLite pack is still pending its current-snapshot build and independent verification. The data remains a separate read-only reference-facts research resource: market UNKNOWN; no production import; no exact vehicle fitment; no exact engine/gearbox mapping; no RU/EAEU applicability; no ECU, DTC, wiring, pinout or repair-procedure claims.

## 2026-11-10 live CSV refresh — 02:23 UTC

The next Windows acquisition downloaded a new exact CSV snapshot from the same official HTTPS URL. The publisher page still displays **44,245 values / 610 models**, but the downloaded file contains **44,272 rows / 611 brand/model pairs**, 15,174,126 bytes, SHA-256 `30f502729f08fa7a061ab0f6c19f62eab6385dea646c15878b8c3430b4b064f4`. The page/file count discrepancy is preserved explicitly; the file hash and observed row/model counts, not the stale page summary, are now the pinned acquisition contract.

The previous pinned CSV (`64a507e4191a9047fe62ec17868488140dd14f692b012d4e1954b6c4322673be`) and the new CSV were both available as CI artifacts and compared as exact row multisets:

- 52 full rows added, 25 removed (net +27), producing one additional non-VAG brand/model pair.
- VAG exact-allowlist subset: 948 rows / 26 models before and after.
- Added/removed VAG rows: 0 / 0.
- VAG values, units, qualifiers, source titles, page locators, source URLs and verification dates: unchanged.
- Canonical SHA-256 of the sorted VAG row set in both snapshots: `92720634c6f6ba907ea554e3bf59afea1ff312444897c365ffe4970b95c108ad`.

Thus the upstream CSV changed, but the retained VAG facts did not. The source manifest and CI row-count contracts are updated to the new complete-file hash and counts. The previous Windows pack artifact was built against the old source hash and is stale; a fresh SQLite pack build and independent verification are required before it can be used by desktop CI. The pack remains a separate read-only CC BY 4.0 research resource with market scope UNKNOWN and no exact fitment, RU/EAEU applicability or production import.


## 2026-11-10 current SQLite pack rebuild — Windows run 68

The refreshed source snapshot was acquired and the isolated VAG SQLite research pack was rebuilt and independently verified on Windows x64 in workflow run 68 (run ID `42742855224`). The pack contains 948 VAG facts across 26 models, five brands and 19 parameter keys. The full source CSV contains 44,272 rows / 611 brand-model pairs; the VAG-only rows remain byte-for-byte identical to the previous pinned VAG subset.

Verified hashes:

- Source CSV SHA-256: `30f502729f08fa7a061ab0f6c19f62eab6385dea646c15878b8c3430b4b064f4`
- Source manifest SHA-256: `9ea9a26e8bd75e95016f3925fed4ee2b3119343fb67329bedfdb40ce0eb310fe`
- SQLite SHA-256: `bc6df970cff98f71980e402ac8744937d17741ccb0361e301610c65b1f0f8850`
- Pack manifest SHA-256: `463f527fe8582f58cf67320894c6ec0edc9b958ae5162926216105fc3e5a3524`
- Build report SHA-256: `435669848a9d34ea0f8457f10dd61f2fe4b76b6943f3d66cb4f7a7c24649e6e8`
- Windows artifact SHA-256: `32f2e3e5b39ad1fb8caedcc6bd8da28fc5f32eb3d8cd1360906950c32506487d`

SQLite `integrity_check=ok`, `foreign_key_check=0`; all 948 source-row hashes are valid. The pack records CC BY 4.0 attribution, market UNKNOWN, publisher verification but no independent OEM technical review, no exact engine/gearbox pair, no RU/EAEU applicability, and `production_import=false` / `product_import_allowed=false`. It remains a separate read-only research pack; desktop lifecycle integration is pending.

## Live source probe — 2026-11-10

A later live acquisition probe retrieved a byte-different CSV snapshot (SHA-256 `5b82f00adee26d165cc187e27952f9b2d9a2f3e6c6da216f3030b72cacac370a`, 15,174,126 bytes; retrieved at `2026-11-10T03:11:09.539790+00:00`). The pinned snapshot remains `30f502729f08fa7a061ab0f6c19f62eab6385dea646c15878b8c3430b4b064f4`.

The two CSVs were compared as exact multisets of all 12 source fields, not merely by row counts. Both contain 44,272 rows, 611 brand/model pairs, 948 exact-allowlist VAG rows and 26 VAG models. The order-independent full-row multiset SHA-256 is identical for both snapshots: `d147ca79d44472bc049d2dfd600a9a87ac5f1c7db6c2f21fc1b9f0e77fd02a74`. The VAG-subset multiset SHA-256 is also identical: `ded1df125225426b5bfae4377a7309c73453f7f7fc3800babe07633107c8a20b`. Exact multiset comparison found zero added rows, zero removed rows and zero changed VAG values; only CSV row order changed.

The new raw snapshot was therefore recorded as an unpinned live probe, not silently substituted for the reviewed pack input. The existing pinned CC BY 4.0 research pack remains valid and unchanged. The acquisition builder correctly fails closed on a raw SHA-256 mismatch until a new snapshot is explicitly reviewed and pinned. No production data was imported.


## 2026-11-10 source-order-only refresh — 03:11 UTC

A repeat acquisition of the official CarDir CSV returned a new byte-level snapshot: `5b82f00adee26d165cc187e27952f9b2d9a2f3e6c6da216f3030b72cacac370a`, 15,174,126 bytes. The previously pinned snapshot was `30f502729f08fa7a061ab0f6c19f62eab6385dea646c15878b8c3430b4b064f4`. An exact row-hash multiset comparison over all parsed CSV rows found no additions, removals or value changes: 44,272 rows and 611 brand/model pairs in both snapshots. Full-row multiset SHA-256: `d147ca79d44472bc049d2dfd600a9a87ac5f1c7db6c2f21fc1b9f0e77fd02a74`.

The exact VAG allowlist subset is unchanged at 948 rows across 26 models. Its row-multiset SHA-256 is `ded1df125225426b5bfae4377a7309c73453f7f7fc3800babe07633107c8a20b`. No VAG rows were added or removed. The byte-level hash changed because row order changed. The new exact source snapshot is pinned, and a fresh Windows SQLite pack build is required because source row numbers are part of the provenance. The old SQLite pack remains explicitly labelled as verified for the previous snapshot only until the new pack is independently built and verified.

All CarDir facts remain a separate CC BY 4.0 research resource with market UNKNOWN, publisher verification but no independent OEM review, no exact engine/gearbox codes or pair, no model generation/year, no RU/EAEU applicability, no ECU/DTC fitment, and no production import or repair authorization.

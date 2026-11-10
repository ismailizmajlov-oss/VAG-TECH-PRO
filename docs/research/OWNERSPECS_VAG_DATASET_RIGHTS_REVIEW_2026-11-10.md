# OwnerSpecs open vehicle-spec dataset — rights and applicability review

Reviewed: 2026-11-10  
Publisher: [ownerspecs.com](https://ownerspecs.com)  
Dataset: [Open vehicle-spec dataset](https://ownerspecs.com/data)  
Machine-readable descriptor: [dataset.json](https://ownerspecs.com/data/dataset.json)  
Licence: [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/)

## Decision

The publisher's published CC BY-SA 4.0 licence permits commercial reuse, display, offline caching, bulk reuse and redistribution with attribution. Adapted database material must remain under the same Share-Alike licence and be separately packaged from differently licensed production data.

A fresh live review on 2026-11-10 confirms that the HTML dataset page and JSON descriptor both report **111 generations**. The HTML page also reports **27 brands and 2,369 verified datapoints**. The earlier 112-generation observation came from a stale indexed response and is superseded by the current live page/JSON pair.

Windows x64 acquisition workflow run #13 completed on 2026-11-10 at 01:29:53 UTC. It downloaded the exact JSON snapshot (683,641 bytes; SHA-256 `7b39e1183bd2a7617d43fdbe1f2ae64662520cb62f89ba8fec4dadbcce79204d`), reconciled the actual 111-generation array and 2,369 datapoints, and built a separate SQLite pack with **20 VAG generation candidates and 233 VAG facts**. The initial pack passed SQLite integrity, foreign-key, row-hash, attribution and applicability-boundary checks. The source snapshot SHA-256 is now pinned in the source manifest; the pack is being rebuilt against the pinned manifest before it can be marked acquired for the current revision.

## What the dataset contains

The JSON describes vehicle generations with brand, model, generation label, canonical generation URL, year_start/year_end, body type, dimensions, fuel tank, and nested specification, mass and tyre records. Per-value fields include a stable field key, value/value_max, unit, range flag, source count and provenance kind.

The publisher defines provenance kinds as:
- `oem_portal` — manufacturer owner's manual / OEM portal;
- `workshop_dataset` — professional workshop technical dataset;
- `official_open_data` — government vehicle registry / open data;
- `first_party_scan` — first-party photograph of a vehicle placard or type plate.

The publisher states that facts are checked against primary documents and that manual text is not reproduced. The JSON exposes source counts and provenance kinds, but not a primary-document URL or revision for every individual value.

## VAG applicability boundary

The dataset includes VAG makes such as Audi, Volkswagen and Škoda. The publisher's “Global · multi-market” description is not a country-by-country applicability map; normalized market scope therefore remains `UNKNOWN`.

Generation labels and year spans are publisher candidates, not confirmed factory production boundaries for a specific market. Values in an `engine_code` field may be broad engine-family labels or grouped variant summaries, not necessarily canonical three-letter VAG engine codes. Even a code-shaped value such as `DPCA` remains a publisher candidate until its primary document, revision, market and exact variant scope are independently reviewed.

Neither those labels nor generation-level ranges establish an exact vehicle, engine, gearbox, ECU or engine/gearbox pair. The source does not establish VAG-specific DTCs, test plans, wiring diagrams, pinouts, adaptations or repair procedures. Critical service values must not be promoted to repair instructions without independent primary-document review tied to the exact engine/gearbox, market, model generation and production boundary.

## Rights and packaging

CC BY-SA 4.0 requires attribution and Share-Alike for adapted material. If acquired, the VAG-filtered SQLite database and any adapted database material must remain separately packaged and clearly labelled CC BY-SA 4.0. The application must show the required attribution and identify the VAG filtering/modifications. Do not include owner-manual PDFs, workshop documents, images or other underlying source files merely because factual rows are licensed.

## Required before publication

1. The exact public JSON snapshot is acquired and pinned by SHA-256. The CSV endpoint is not used by this pack builder and is not assumed to be part of the snapshot.
2. Windows CI reconciled JSON `generation_count=111`, actual generation-array length, HTML page count, unique brand count and the published 2,369 datapoints. If the CSV is acquired in a later revision, hash it separately and reconcile its rows before use.
3. The exact VAG brand allowlist retains 20 generations and 233 facts; raw brand/model/generation labels, year spans, values, units, source counts, provenance kinds and generation URLs are preserved.
4. The pack stores the source snapshot hash, source manifest hash, generation hashes, fact-row hashes, schema/revision, licence and attribution. Rebuild against the newly pinned source manifest before marking the current artifact revision acquired.
5. Keep every record in a separate research-only namespace with `market_scope=UNKNOWN`, `technical_review_status=not_independently_reviewed` and no production-fitment promotion.
6. Treat all engine-code strings as candidates; do not parse grouped strings into canonical factory codes or infer engine/gearbox pairs.
7. Independently verify any critical value against the cited primary document before it can enter the professional repair library.

The source-rights review itself did not download bytes; the separate Windows acquisition workflow did. No values were imported into the production vehicle/technical database. The research pack remains a separate CC BY-SA 4.0 dataset with market UNKNOWN and no critical-value or exact-fitment approval.

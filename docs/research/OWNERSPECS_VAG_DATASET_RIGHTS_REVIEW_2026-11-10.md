# OwnerSpecs open vehicle-spec dataset — rights and applicability review

Reviewed: 2026-11-10  
Publisher: [ownerspecs.com](https://ownerspecs.com)  
Dataset: [Open vehicle-spec dataset](https://ownerspecs.com/data)  
Machine-readable descriptor: [dataset.json](https://ownerspecs.com/data/dataset.json)  
Licence: [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/)

## Decision

The publisher's published CC BY-SA 4.0 licence permits commercial reuse, display, offline caching, bulk reuse and redistribution with attribution. Adapted database material must remain under the same Share-Alike licence and be separately packaged from differently licensed production data.

A fresh live review on 2026-11-10 confirms that the HTML dataset page and JSON descriptor both report **111 generations**. The HTML page also reports **27 brands and 2,369 verified datapoints**. The earlier 112-generation observation came from a stale indexed response and is superseded by the current live page/JSON pair. The count metadata is now consistent; the actual downloaded array and datapoint totals still must be checked against pinned bytes before publishing a pack.

No dataset bytes were downloaded in this review. No source SHA-256 is claimed.

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

1. Download the exact public JSON and CSV snapshots from the published URLs; calculate and pin each SHA-256 before parsing.
2. Verify JSON `generation_count=111`, actual generation-array length, HTML page count, unique brand count and the published 2,369 datapoints. Cross-check the CSV row count against the JSON facts.
3. Filter only an exact VAG brand allowlist; preserve raw brand/model/generation labels, year spans, values, units, source counts, provenance kinds and generation URLs.
4. Calculate row-level hashes and record the source snapshot hash, schema/revision, licence and attribution.
5. Keep every record in a separate research-only namespace with `market_scope=UNKNOWN`, `technical_review_status=not_independently_reviewed` and no production-fitment promotion.
6. Treat all engine-code strings as candidates; do not parse grouped strings into canonical factory codes or infer engine/gearbox pairs.
7. Independently verify any critical value against the cited primary document before it can enter the professional repair library.

No dataset bytes were downloaded, no source hash was fabricated, and no records were imported or displayed during this review.

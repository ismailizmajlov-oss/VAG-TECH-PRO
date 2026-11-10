# OwnerSpecs open vehicle-spec dataset — rights and applicability review

Reviewed: 2026-11-10  
Publisher: [ownerspecs.com](https://ownerspecs.com)  
Dataset: [Open vehicle-spec dataset](https://ownerspecs.com/data)  
Machine-readable descriptor: [dataset.json](https://ownerspecs.com/data/dataset.json)  
Licence: [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/)

## Decision

The publisher's published CC BY-SA 4.0 licence permits commercial reuse, display, offline caching, bulk reuse and redistribution with attribution. The data may be considered for a **separate, read-only, attributed Share-Alike research pack**. It must not be merged into the production vehicle-fitment database or into a differently licensed database.

Acquisition is currently held because the publisher's HTML dataset page reports **111 generations**, while the current JSON descriptor reports **112**. The HTML page also reports 27 brands and 2,369 verified datapoints. No snapshot was downloaded in this review; no dataset SHA-256 is claimed.

## What the dataset contains

The JSON describes vehicle generations with brand, model, generation label, generation URL, year_start/year_end, body type, dimensions, fuel tank, and nested specification, mass and tyre records. Per-value fields include a stable field key, value/value_max, unit, range flag, source count and provenance kind.

The publisher defines provenance kinds as:
- `oem_portal` — manufacturer owner's manual / OEM portal;
- `workshop_dataset` — professional workshop technical dataset;
- `official_open_data` — government vehicle registry / open data;
- `first_party_scan` — first-party photograph of a vehicle placard or type plate.

The publisher states that the dataset contains facts only and does not reproduce manual text. The JSON exposes source counts and provenance kinds, but does not expose a primary-document URL or revision for every individual value.

## VAG applicability boundary

The dataset contains VAG makes and generation examples, including Volkswagen, Audi and Škoda. Its publisher-level “Global · multi-market” description is not a country-by-country applicability map; normalized market scope therefore remains `UNKNOWN`.

Generation labels and year spans are discovery candidates, not factory production boundaries for a specific market. Values in an `engine_code` field may be engine-family labels or grouped variant summaries, not necessarily canonical three-letter VAG engine codes. Neither those labels nor generation-level ranges establish an exact vehicle, engine, gearbox, ECU or engine/gearbox pair.

The source does not establish VAG-specific DTCs, test plans, wiring diagrams, pinouts, adaptations or repair procedures. Critical service values must not be promoted to repair instructions without independent primary-document review tied to the exact engine/gearbox, market, model generation and production boundary.

## Rights and packaging

CC BY-SA 4.0 requires attribution and Share-Alike for adapted material. If later acquired, the VAG-filtered SQLite database and any adapted database material must remain separately packaged and clearly labelled CC BY-SA 4.0. The application must show the required attribution and identify the VAG filtering/modifications. Do not include owner-manual PDFs, workshop documents, images or other underlying source files merely because factual rows are licensed.

## Required before acquisition or integration

1. Resolve the HTML/JSON generation-count discrepancy with the publisher or a subsequent consistent snapshot.
2. Download the exact public JSON/CSV snapshot from the published URLs; calculate and pin SHA-256 before parsing.
3. Reconcile the descriptor count with the actual generation array and the HTML page's published counts.
4. Filter only an exact VAG brand allowlist; preserve raw brand/model/generation labels, year spans, values, units, source counts, provenance kinds and generation URLs.
5. Calculate row-level hashes and record the source snapshot hash, schema/revision, licence and attribution.
6. Keep every record in a separate research-only namespace with `market_scope=UNKNOWN`, `technical_review_status=not_independently_reviewed` and no production-fitment promotion.
7. Independently verify any critical value against the cited primary document before it can enter the professional repair library.

No dataset bytes were downloaded, no source hash was fabricated, and no records were imported or displayed during this review.

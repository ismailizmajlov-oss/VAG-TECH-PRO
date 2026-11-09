# Wikipedia VAG engine-code lists: licence and quality review — 2026-11-08

## Decision

The four English Wikipedia engine-list articles expose text under **Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0)**. This licence permits commercial reuse, caching, display and redistribution of the covered text, provided attribution and ShareAlike obligations are met.

However, the pages carry material quality warnings: original-research concerns, insufficient or missing citations, incomplete lists, unsourced statements and accuracy disputes. Therefore **no engine code, engine-family statement, model application, model year, powertrain pairing or technical value from these pages is imported into the VAG TECH PRO database in this review**. The pages are registered only as licensed discovery leads for later primary-source verification.

## Pinned page revisions observed

| Article | Revision | Last edit (UTC) | Quality warning observed |
|---|---:|---|---|
| [List of Volkswagen Group petrol engines](https://en.wikipedia.org/w/index.php?title=List_of_Volkswagen_Group_petrol_engines&oldid=1383476161) | 1383476161 | 2026-11-02 22:06 | Original-research warning; insufficient inline citations; incomplete list |
| [List of Volkswagen Group diesel engines](https://en.wikipedia.org/w/index.php?title=List_of_Volkswagen_Group_diesel_engines&oldid=1383504097) | 1383504097 | 2026-11-03 01:27 | More citations needed; incomplete list |
| [List of discontinued Volkswagen Group petrol engines](https://en.wikipedia.org/w/index.php?title=List_of_discontinued_Volkswagen_Group_petrol_engines&oldid=1381198237) | 1381198237 | 2026-10-20 16:46 | Unsourced statements; lack of reliable references; incomplete list |
| [List of discontinued Volkswagen Group diesel engines](https://en.wikipedia.org/w/index.php?title=List_of_discontinued_Volkswagen_Group_diesel_engines&oldid=1375791889) | 1375791889 | 2026-09-20 02:37 | Unsourced statements; accuracy disputes; lack of reliable references; incomplete list |

Each page footer states that its text is available under CC BY-SA 4.0. The Wikimedia Foundation's Wikipedia reuse guidance independently confirms that article text may be reused under the Creative Commons Attribution-ShareAlike licence. This review applies only to the article text covered by that licence; it does not cover images, logos, third-party linked pages, referenced OEM documents or other material with separate rights.

## What the pages can and cannot support

Potential discovery fields visible in the pages include engine-family labels, displacement, fuel type, power/torque summaries, engine-code strings and narrative vehicle-application mentions.

These are **community-reported claims**, not factory-confirmed data. In particular:

- the articles are not a Russian or EAEU market catalogue;
- a listed model application does not establish a specific generation, production date, sales market or exact variant;
- an engine code appearing in a list does not prove the code is correct for a specific VIN, model year or market;
- no article provides a reliable, complete engine-to-gearbox pairing catalogue;
- references to ETKA, Volkswagen Self-Study Programmes or other OEM material do not grant rights to those referenced works;
- no DTC, ECU calibration, wiring, pinout, repair procedure, adaptation or tightening specification may be derived from these pages for professional repair use.

## Licence obligations if a future research-only pack is approved

Any adapted or redistributed article text must retain attribution to Wikipedia contributors, identify the source revision and provide a link to the licence. Adapted material must be released under CC BY-SA 4.0 or a compatible licence, with changes clearly indicated. The adapted pack must remain separate from proprietary/OEM technical content and must not be relicensed under terms that remove the ShareAlike obligations.

Suggested attribution form:

> Adapted from Wikipedia contributors, “[article title]”, revision [revision ID], CC BY-SA 4.0. Changes made by VAG TECH PRO are identified separately.

The attribution above is a template only; it is not evidence that any content has been copied into the product.

## Acquisition and provenance state

- Article revisions recorded: 4.
- Raw article/API bytes retrieved: 0.
- Raw snapshot SHA-256: not available; no hash is fabricated.
- Engine-code rows imported: 0.
- Vehicle-application rows imported: 0.
- Engine/gearbox pairings imported: 0.
- Production applicability claims created: 0.
- Rights status: CC BY-SA 4.0 for article text, subject to attribution and ShareAlike.
- Technical review status: not approved; source-quality warnings block data promotion.
- Next permitted step: obtain pinned revision bytes in CI, hash each source snapshot, extract only explicit engine-code candidates with section-level provenance, and independently verify each candidate against primary factory/approval sources before any promotion.

## Addendum — pinned research-pack build, 2026-11-09

The four reviewed article revisions were fetched as pinned MediaWiki wikitext and rendered-HTML snapshots. Their per-file SHA-256 values, byte sizes, revision IDs, row-level extraction hashes and source URLs are preserved in the generated `source-manifest.json` and SQLite database. The separate research pack contains 241 candidate code tokens from 64 source rows across four article revisions.

Verified pack evidence:

- Pack ID: `wikipedia-vag-engine-code-candidates-cc-by-sa-4-0`
- License: CC BY-SA 4.0; commercial use, offline caching, display and redistribution are permitted with attribution and ShareAlike. The database remains a separate licensed pack.
- SQLite SHA-256: `d44629eaf26f1fc3a54acff8b985a84e207b85d7cac7abd975dac16474585788`
- Source-manifest SHA-256: `e24ad006a3025860e01b3a0bd8395da4da9156ba7d0cb0c3e32b3516ccaae024`
- Combined source-snapshot SHA-256: `fd0be1562899f7dd7b46e33ecf5297b6bab551668f83d5bcf60bb32ce0dd130c`
- Counts: 4 source documents, 64 source rows, 241 candidate rows, 241 unique candidate tokens.

This is research-pack ingestion only. The source register explicitly keeps `data_ingested=false` and records `research_pack_ingested=true`. All rows remain `market_scope=UNKNOWN` and `community_engine_code_candidate_only`. Product import, exact vehicle fitment, generation/year fitment, engine/gearbox pairing, ECU fitment, DTC fitment, repair use and diagnostic execution remain prohibited. No candidate has been promoted to a verified factory engine code.

The source quality review remains blocking for technical use: incomplete lists, insufficient citations, unsourced statements and accuracy disputes remain attached to the affected article revisions. Primary-source verification is still required before any engine-code or application claim can be used in a repair recommendation.

# Wikipedia VAG engine-code candidate pack integration — 2026-11-10

## Decision

A separate, read-only research pack is integrated into the Windows desktop research catalogue. It is **not** a production engine-code catalogue and does not create any vehicle, generation, year, market, ECU, gearbox, DTC or repair applicability.

The source is four pinned Wikipedia article revisions. The article text is licensed CC BY-SA 4.0. The licence permits commercial reuse, display, offline caching, bulk reuse and redistribution provided attribution and ShareAlike obligations are met. The source is therefore shipped as a distinct CC BY-SA research pack; it is not merged into the core SQLite database.

## Pinned source revisions

| Article | Revision | Wikitext SHA-256 | Quality warnings |
|---|---:|---|---|
| [List of Volkswagen Group petrol engines](https://en.wikipedia.org/w/index.php?title=List_of_Volkswagen_Group_petrol_engines&oldid=1383476161) | 1383476161 | 527ad0a2b8f70eab2625a4e644091a812da77308a162475164124feecea5fc4a | Original research, insufficient inline citations, incomplete list |
| [List of Volkswagen Group diesel engines](https://en.wikipedia.org/w/index.php?title=List_of_Volkswagen_Group_diesel_engines&oldid=1383504097) | 1383504097 | c14ce9f4caa460f57d9afdfcd2e344e04c3ee51d2b5194cb3bafbcb115776bf4 | More citations needed, incomplete list |
| [List of discontinued Volkswagen Group petrol engines](https://en.wikipedia.org/w/index.php?title=List_of_discontinued_Volkswagen_Group_petrol_engines&oldid=1381198237) | 1381198237 | d359d16ea4cac498e9039ef6cd0e2bfa91d38ee5c01fd8eae3fffa1360f2e85c | Unsourced statements, lacking reliable references, incomplete list |
| [List of discontinued Volkswagen Group diesel engines](https://en.wikipedia.org/w/index.php?title=List_of_discontinued_Volkswagen_Group_diesel_engines&oldid=1375791889) | 1375791889 | 3ba3cec7a350b70e179c9921bfb55c6665fdd0412ee0969bb3b63b2b29eff3bb | Unsourced statements, accuracy disputes, lacking reliable references, incomplete list |

The raw Wikitext snapshots are pinned by revision ID and individually hashed. The pack also preserves the rendered HTML snapshots and their per-build SHA-256 values.

## Extracted research data

- 4 source documents
- 64 source rows containing code candidates
- 241 candidate rows
- 241 distinct candidate strings
- Stable canonical Wikitext snapshot SHA-256: 91eda1afd5c65fd5ea1f756d6c1620a02c9457975780a5f6001c19c9e409a787
- Stable canonical candidate-content SHA-256: 3b8fea2cdbbfb5e42694d8316face591b61996b4e5bae7887df544da776387b5

The stable candidate-content fingerprint is calculated over ordered tuples of candidate code, source revision, source-row kind and number, source-row SHA-256 and extracted candidate text. The desktop integration recomputes both stable fingerprints before accepting the pack.

Rendered HTML, composite source snapshot, source-manifest, SQLite, pack-manifest, inner archive and outer workflow-artifact hashes can vary between builds because the rendered HTML contains non-source presentation changes. The exact values for each installed build are therefore stored in:

- data/research/wikipedia-vag-engine-candidates/manifest.json
- data/research/wikipedia-vag-engine-candidates/build-provenance.json
- data/research/manifest.json

The Windows workflow resolves the candidate-pack artifact for the exact same source branch and commit, checks the GitHub artifact digest, verifies the inner archive SHA-256, then checks all pack files and SQLite integrity before integrating it.

## Applicability and safety boundary

Every row remains:

- market_scope = UNKNOWN
- applicability_precision = community_engine_code_candidate_only
- review_status = candidate
- product_import_allowed = false
- exact_vehicle_fitment = false
- generation_year_fitment = false
- engine_gearbox_fitment = false
- ecu_fitment = false
- dtc_fitment = false
- repair_use_allowed = false
- diagnostic_execution_allowed = false

The desktop UI labels each item as a community candidate, displays its source revision, row text, quality warnings and SHA-256 provenance, and explicitly states that the entry is not OEM-confirmed and is not an applicability, parts-selection, repair or diagnostic instruction.

No candidate is promoted into production vehicle, engine, gearbox, ECU, DTC or technical-procedure tables. No engine-to-gearbox pair is inferred.

## Attribution and ShareAlike

The pack includes ATTRIBUTION.md and LICENSE-NOTICE.txt. Attribution identifies Wikipedia contributors, the four article revisions and the CC BY-SA 4.0 licence. The database remains a separate research pack to preserve the ShareAlike boundary. Images, logos, third-party linked pages, referenced OEM documents and materials with separate rights are excluded.

## Remaining verification

The source pages contain explicit quality warnings. Independent primary-source confirmation is still required for each candidate code and any claim about market, model, generation, production year, engine/gearbox pairing or vehicle applicability. Until that work is completed, this pack is for offline discovery and source inspection only, not professional repair guidance.

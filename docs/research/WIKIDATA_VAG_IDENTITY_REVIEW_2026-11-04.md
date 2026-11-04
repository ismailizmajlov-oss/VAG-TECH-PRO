# Wikidata VAG identity seed — rights and applicability review

Review date: 2026-11-04

## Rights decision

The inspected Wikidata item pages explicitly state that structured data in the main, Property, Lexeme and EntitySchema namespaces is available under CC0. This seed uses only structured entity labels, QIDs, manufacturer/brand/series/succession statements and explicit date statements. It does not copy Wikipedia article prose, images or other non-structured page text.

License: CC0-1.0 — https://creativecommons.org/publicdomain/zero/1.0/
Wikidata licensing statement: https://www.wikidata.org/wiki/Wikidata:Licensing

Commercial use, display, offline caching and redistribution are permitted for the structured data under CC0. Attribution is not required; the pack retains QID, pinned entity revision, item URL, retrieval timestamp and SHA-256 provenance.

## Data boundary

The initial pinned snapshot contains 20 curated Volkswagen, Audi and Škoda model/generation entities. It is a seed, not an exhaustive VAG taxonomy.

Every row is:
- community_reference_unverified
- market_scope=UNKNOWN
- applicability_precision=global_model_generation_candidate
- excluded from confirmed vehicle/engine/gearbox/ECU fitment
- excluded from DTC, repair, test-plan, wiring, pinout, torque and OEM-part functions

Years are stored only where an explicit structured date statement was inspected. The Passat B8 record has multiple plant/body-style date statements, so no single global year range is asserted. The Audi A3 8V page's 2012 presentation event is not treated as a production start. Missing dates remain NULL.

## Pinned entities

The snapshot records 20 QIDs and their exact Wikidata revision IDs. The source snapshot and lock manifest are hashed during SQLite pack generation. The resulting database is a separate research pack and must not be merged into the verified vehicle catalog without independent market-specific review.

## Explicit exclusions

No engine codes, gearbox codes, ECU applicability, DTC, service procedures, wiring diagrams, pinouts, torque values, adaptation steps or OEM part numbers are ingested from this source.

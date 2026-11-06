# Wikidata VAG model-identity candidate acquisition

Date: 2026-11-04

## Decision

Use Wikidata structured data under CC0 1.0 as a **research-only candidate identity source**. The pack is not an authoritative VAG model register and does not establish exact vehicle applicability.

Official Wikidata item pages state that structured data in the main, Property, Lexeme and EntitySchema namespaces is available under CC0 1.0. The query uses only structured entity statements from the official Wikidata Query Service. No Wikipedia article prose, Wikimedia images, logos, or third-party linked resources are copied.

## Query scope

The acquisition filters car-model entities with a direct P31=Q3231690 statement by an explicit, project-maintained English manufacturer-label whitelist covering core Volkswagen Group passenger-car manufacturers. This whitelist is an acquisition filter only; it is not proof of corporate ownership. The snapshot preserves the manufacturer QID and label, model QID and English/Russian labels, and optional Wikidata inception/dissolution/date-modified statements.

The query is pinned by its SHA-256. Each raw SPARQL binding receives a canonical SHA-256 and binding index. The complete response snapshot is retained with its SHA-256. The SQLite rows preserve source revision, query hash, snapshot hash, source binding indexes and record hashes.

## Explicit limitations

- Market scope is UNKNOWN; no Russian or EAEU applicability is inferred.
- No generation entities or verified generation relationships are imported.
- Wikidata inception/dissolution statements are not converted into production-year ranges.
- No engine codes, gearbox codes, ECU, DTC, test plans, repair procedures, wiring diagrams, pinouts, torque specifications, adaptations, OEM parts or VIN fitment are imported.
- Every row remains candidate identity only. The pack cannot satisfy the exact vehicle-configuration gate for technical search.
- Completeness is unknown: the query is capped at 3,000 bindings; if the limit is reached the snapshot may be truncated. Missing manufacturer statements, labels or entities are not proof that a model did not exist.

## Rights

License: CC0 1.0 Universal for the structured data queried. Commercial use, display, offline caching, bulk reuse and redistribution are permitted under CC0. Attribution is not legally required by CC0 but is retained as provenance and good practice.

- Wikidata structured data: https://www.wikidata.org/wiki/Wikidata:Licensing
- CC0 1.0 legal code: https://creativecommons.org/publicdomain/zero/1.0/legalcode
- Wikidata Query Service: https://query.wikidata.org/

## Promotion policy

The pack remains outside production fitment and technical tables. A candidate can be promoted only after independent source review and primary evidence for exact model/generation/year/market applicability. Engine/gearbox links and all critical repair values require separate, rights-cleared evidence.


## 2026-11-06: include model-series entities and the group-level Volkswagen label

The previous query admitted only entities whose direct type path reached `car model` (Q3231690), and its manufacturer-label whitelist omitted the English label `Volkswagen Group`. This excluded series parents such as Volkswagen Passat (Q216754, instance of `car model series`, Q59773381) and generation/model members such as Volkswagen Passat B8 (Q15305561, instance of `car model`). The official Wikidata entity pages show the Passat series relationship and the B8 member relationship; the records are structured data, not article prose.

The acquisition query now includes both Q3231690 and Q59773381 and accepts the group-level manufacturer label `Volkswagen Group`. Each row retains the direct model type, its English label, the matched entity class, binding index, binding hash, source revision, query hash and snapshot hash. The SQLite pack remains identity-only and candidate-only. `car model series` records are not treated as confirmed vehicle generations; P179/P527 links remain separate candidates in the generation pack.

No market scope, Russian/EAEU applicability, production-year range, engine/gearbox fitment, ECU fitment, DTC, repair procedure, wiring, pinout, torque, adaptation or OEM-part applicability is inferred. The query remains capped at 3,000 bindings and completeness remains unknown.

Evidence:
- Volkswagen Passat series Q216754: https://www.wikidata.org/wiki/Q216754
- Volkswagen Passat B8 Q15305561: https://www.wikidata.org/wiki/Q15305561
- Volkswagen Golf Mk7 Q62362: https://www.wikidata.org/wiki/Q62362
- car model Q3231690: https://www.wikidata.org/wiki/Q3231690
- car model series Q59773381: https://www.wikidata.org/wiki/Q59773381
- Volkswagen Group Q156578: https://www.wikidata.org/wiki/Q156578
- Structured-data license: CC0 1.0, https://creativecommons.org/publicdomain/zero/1.0/

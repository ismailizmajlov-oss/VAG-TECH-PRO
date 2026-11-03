# RDW EU type-approval source review — 2026-11-03

## Decision

The Netherlands RDW publishes non-sensitive vehicle type-approval data as open data. The selected component datasets have dataset-specific CC0-1.0 declarations in the Dutch government data catalogue. They are therefore eligible for commercial use, display, offline caching and redistribution under CC0, subject to retaining accurate provenance and not misrepresenting the data.

This is an **additional EU/NL source**, not a substitute for Russian/EAEU OTTS. Its records must remain in a separate SQLite database and must never be labelled as Russian/EAEU applicability.

## Official publisher statements

- RDW open-data overview: https://www.rdw.nl/over-rdw/dienstverlening/open-data/algemene-informatie
  - RDW says the non-sensitive data from its type-approval register are released as open data.
  - RDW says the data are free and available without restrictions for reuse.
  - RDW describes its type-approval database as containing information from European type approvals recorded by RDW since 1998.
- RDW open-data portal: https://opendata.rdw.nl/
- CC0 1.0 legal text: https://creativecommons.org/publicdomain/zero/1.0/legalcode

## Selected dataset-specific license evidence

| RDW dataset | Socrata view | Government catalogue record | Declared license |
|---|---|---|---|
| TGK Basis Uitvoering | `byxc-wwua` | https://data.overheid.nl/dataset/46077-open-data-rdw--tgk-basis-uitvoering | CC0-1.0 |
| TGK Merk Uitvoering | `kyri-nuah` | https://data.overheid.nl/dataset/46081-open-data-rdw--tgk-merk-uitvoering | CC0-1.0 |
| TGK Aandrijving Uitvoering | `4by9-ammk` | https://data.overheid.nl/dataset/46074-open-data-rdw--tgk-aandrijving-uitvoering | CC0-1.0 |
| TGK Handelsbenaming Fabrikant | `x5v3-sewk` | https://data.overheid.nl/dataset/46083-open-data-rdw--tgk-handelsbenaming-fabrikant | CC0-1.0 |
| TGK Versnelling Uitvoering | `7rjk-eycs` | https://data.overheid.nl/dataset/46075-open-data-rdw--tgk-versnelling-uitvoering | CC0-1.0 |

The machine-readable declarations and download/metadata endpoints are pinned in `data/source-manifests/rdw-eu-type-approval-cc0.json`.

## Data model and join policy

The pack uses only RDW-published keys:

- type approval number;
- variant code;
- version code;
- revision sequence.

The make table is the anchor for selecting VAG-group candidates. The base, engine, manufacturer trade-name and gearbox-type tables are joined only on the published type-approval variant keys. No cross-product joins are allowed.

The RDW `Motorcode` field is retained as `rdw_motorcode_candidate`. It is **not** promoted to a confirmed VAG factory engine code. The RDW `CodeTypeVersnellingsbak` field is retained as a type-approval gearbox-type candidate. It is **not** promoted to a VAG factory gearbox code.

## Applicability limits

- Market scope: Netherlands RDW register / European type-approval records held by RDW.
- Not Russian/EAEU OTTS.
- Not a complete EU-wide corpus.
- No exact VIN build sheet.
- No confirmed VAG model-generation-year mapping.
- No confirmed production vehicle fitment.
- No confirmed factory engine or gearbox code mapping.
- No ECU, PR-code, wiring, repair procedure, torque or diagnostic-test applicability.

Every imported record is marked `source_published_candidate`, with `type_approval_variant` precision. All exact-fitment and factory-code confirmation flags remain false.

## Snapshot integrity

The Windows x64 acquisition job first snapshots the make-code inventory, then downloads only VAG-make rows and related type-approval rows through paginated Socrata queries. Every exact query string and URL is retained with each raw CSV page; Socrata view metadata, dataset-specific license pages, retrieval time and the CC0 legal text are also stored and hashed. The SQLite pack records row-level hashes for each retained source row. The unfiltered Basis export is intentionally not downloaded because it exceeds the safe snapshot size limit.

A changed source view, missing required column, unexpected HTML response, failed hash, or invalid join key must stop the import rather than silently produce partial data.

## Relationship to Russian/EAEU OTTS

The separate Russian/EAEU source review remains unchanged: the official FGIS register's public search does not by itself establish bulk extraction, commercial display, offline caching or PDF redistribution rights. No Russian/EAEU OTTS records are imported by this RDW pack. A Dutch/EU approval record must never be used to fill a Russian/EAEU approval field.

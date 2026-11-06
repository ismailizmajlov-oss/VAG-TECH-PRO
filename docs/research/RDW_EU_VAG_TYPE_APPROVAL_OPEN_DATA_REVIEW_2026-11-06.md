# RDW Netherlands / EU Type-Approval Open Data Review — 2026-11-06

## Decision

The RDW source group is rights-cleared under CC0 1.0 for a separate, read-only Netherlands/EU type-approval research pack. It is not a Russian/EAEU source and must never be promoted into the RU/EAEU production fitment catalogue.

The source group is useful because the official RDW datasets expose an EU type-approval number and raw approval variant/version/revision keys, an RDW Motorcode field, and a separate Codetypeversnellingsbak classification. It does not prove a VAG factory engine/gearbox pair. Engine and gearbox rows must remain separate.

## Rights evidence

The Dutch national data catalogue lists RDW as the data owner, public access and CC0 1.0 for the following datasets:

- [Basisregistratie Voertuigen - RDW](https://data.overheid.nl/dataset/basisregistratie-voertuigen---rdw) — includes the public Gekentekende_voertuigen dataset, API ID m9d7-ebf2.
- [TGK Aandrijving Uitvoering](https://data.overheid.nl/dataset/81ac19f5-d0e5-4411-847e-f8698d4a42f2) — 4by9-ammk.
- [TGK Versnelling Uitvoering](https://data.overheid.nl/dataset/8a5be559-87b6-4224-9bbc-45dae886c427) — 7rjk-eycs.
- [TGK Basis Uitvoering](https://data.overheid.nl/dataset/38afb954-4d3b-4363-9875-4a16117ab86b) — byxc-wwua.
- [TGK Merk Uitvoering](https://data.overheid.nl/dataset/68f02697-4c7a-4a5c-ae1d-b253aa3ecc89) — kyri-nuah.
- [TGK Handelsbenaming Fabrikant](https://data.overheid.nl/dataset/1f00bd5c-63e9-4262-9603-311712339a30) — x5v3-sewk.

The catalogue records explicitly show public access and CC0 1.0, and the TGK pages provide machine-readable CSV/JSON/XML downloads. The source manifest pins the catalogue page and Socrata dataset ID for every product. Attribution is not required by CC0, but a courtesy attribution is retained.

No third-party catalogue, dealer site, forum, scraped mirror or paid source is used. No external account or paid agreement is required.

## Observed fields and boundaries

The official RDW Socrata JSON endpoints were inspected on 2026-11-06:

- m9d7-ebf2: merk, handelsbenaming, typegoedkeuringsnummer, variant, uitvoering, volgnummer_wijziging_eu_typegoedkeuring, datum_eerste_toelating, voertuigsoort, cilinderinhoud and aantal_cilinders are present in the public vehicle records. The same dataset also contains registration identifiers and other fields. The probe and future importer must use an explicit $select allowlist that includes displacement/cylinder count only to choose a combustion-engine sample and must never request or persist kenteken, VIN, holder or ownership data.
- 4by9-ammk: includes motorcode, typegoedkeuringsnummermotor, cylinder count and displacement, keyed by type approval, variant, version and revision.
- 7rjk-eycs: includes codetypeversnellingsbak, keyed by type approval, variant, version and revision.
- byxc-wwua: includes approval variant/version and revision start date/category fields.
- kyri-nuah: includes RDW make-code rows keyed to the approval variant/version.
- x5v3-sewk: includes manufacturer trade name and type designation, keyed by approval variant/version.

The live schema probe will re-check the field names and current source revisions in Windows CI before any pack is built. No unfiltered full upstream dataset dump has been downloaded. A later run built six VAG-scoped filtered JSONL snapshots; their per-file hashes and row counts are recorded in the separate research-pack evidence below. Those filtered snapshots are not represented as complete RDW dataset dumps.

## Applicability policy

1. The market scope is NL registration evidence. The approval number itself is an EU type-approval identifier; this does not turn a Dutch registration observation into proof of sales or fitment in every EU country.
2. Preserve the exact composite key: type approval number + variant + version/execution + revision. Never normalize away leading zeros, punctuation, case or wildcard values.
3. motorcode remains an RDW engine-designation candidate. It is not automatically a VAG three-/four-letter factory engine code.
4. codetypeversnellingsbak remains an RDW type-approval gearbox classification. It is not a VAG gearbox code.
5. Do not join the separate engine and gearbox child tables into pairs. Shared approval scope is not an exact engine/gearbox combination.
6. datum_eerste_toelating is first-registration date, not model year or production date.
7. Trade names are not generation identifiers. No model generation is inferred.
8. No ECU, DTC, test-plan, repair, wiring, pinout, torque, adaptation or service-interval data is provided by these datasets.

## Probe and future pack policy

The first CI job remains a schema and exact-scope probe: it queries a small set of Volkswagen passenger-car rows with an explicit non-identifying field allowlist, then checks the matching official TGK tables using the exact approval/variant/version/revision key. A separate Windows CI pack job subsequently downloaded only the allowlisted VAG make observations and exact-scope TGK rows described below. Neither workflow downloads an unfiltered complete registration dataset or requests/persists a plate or VIN.

The separate run-11 research pack contains only:
- the selected make/trade-name and EU approval identifiers;
- raw approval variant/version/revision keys;
- RDW engine designation candidates and their approval-scope provenance;
- RDW gearbox type classifications in a separate table;
- source file hashes, row hashes, source revision and CC0 rights metadata.

The future pack must remain a separate read-only research namespace with production_import=false, ru_eaeu_applicability=false, individual_vehicle_fitment=false, and no engine/gearbox pairing table. Each source file and every imported row must retain provenance and SHA-256.

## Source URLs

- RDW public data portal: https://opendata.rdw.nl/
- RDW public vehicle identity API: https://opendata.rdw.nl/resource/m9d7-ebf2.json
- RDW TGK drive API: https://opendata.rdw.nl/resource/4by9-ammk.json
- RDW TGK gearbox API: https://opendata.rdw.nl/resource/7rjk-eycs.json
- RDW TGK base API: https://opendata.rdw.nl/resource/byxc-wwua.json
- RDW TGK make API: https://opendata.rdw.nl/resource/kyri-nuah.json
- RDW TGK manufacturer trade-name API: https://opendata.rdw.nl/resource/x5v3-sewk.json
- RDW official open-data information: https://www.rdw.nl/over-rdw/dienstverlening/open-data

## Live probe result — 2026-11-06

The Windows CI schema/scope probe passed: [run 1](https://github.com/ismailizmajlov-oss/VAG-TECH-PRO/actions/runs/42225909008). The 90-day evidence artifact is artifact ID 13504898995. Its ZIP SHA-256 is 7a34c9a0bd09b9c708d54ac029b21143ac6f3f9baff71d9a7f96428c671bed72; the report SHA-256 is ddab63bb946a3dc0b9d255de24b9b52b5dd49fdb479bab1fc57b11e396aa08be. The exact source-manifest SHA-256 used by the probe was 16c9871b32fa8305427ffbc145ef3dc90f06770cd266528c78ce6db8a80c78f5.

The official RDW query found one NL Volkswagen Tayron observation linked to EU approval e1*2018/858*00403*07, variant ACDUCAX0, execution FD6FD6DD002PR4VNB50OO, revision 0 (M1; revision start 2026-07-31). In that exact approval scope, RDW returned one engine row with Motorcode DUC, 1,498 cc and four cylinders, and one separate gearbox classification row with Codetypeversnellingsbak A. The manufacturer trade-name table returned TAYRON / R4; the RDW make table returned VOLK and VWVP.

This confirms the official source fields and exact approval-scope linkage, not a factory powertrain pair. DUC remains an engine-designation candidate pending independent OEM corroboration; A remains an RDW approval classification, not a VAG gearbox code. No engine/gearbox pair, production fitment, model year, generation or RU/EAEU applicability is asserted. The probe did not download a full source snapshot, so the full-source SHA-256 remains null and data_ingested remains false.


## Filtered research pack audit — run 11, 2026-11-06

The separate Windows pack workflow completed successfully: [run 11](https://github.com/ismailizmajlov-oss/VAG-TECH-PRO/actions/runs/42260969213), source commit `7c08e8d2335124e721078f456a7077a0112db2bb`.

- Artifact ID: `13526776486`; ZIP SHA-256: `86812d6f0ecc81b4894c2cde150f8dc4290ac83f4ec5d457865ce32c0440bf31`; size: 155,402,740 bytes.
- Pack manifest SHA-256: `1df346574069a18918eb1ec18a4813eafb372ca6ca0f552226301cdca11bd61c`.
- SQLite database: 500,994,048 bytes; SHA-256: `9c4bc992ee56aa0f308813c1ad384968a28d0296c80cb7e07100a21c2a8f8612`.
- Six filtered source snapshots contain 604,785 source rows: 102,662 registration observations, 93,836 engine-designation candidate rows, 93,548 gearbox-classification rows and 314,739 auxiliary rows, across 96,519 exact approval/variant/version/revision scopes.
- Source snapshot SHA-256 values and dataset revisions are recorded in `data/source-manifests/vag-factory-source-register.json` under `research_pack_build_evidence.source_snapshots`.
- SQLite `integrity_check` returned `ok`; `foreign_key_check` returned no violations.

An independent read-only audit of the artifact found 93,548 approval scopes with both an engine candidate row and a gearbox classification row, 190 engine-only scopes and no gearbox-only scopes. However, 98 scopes contain more than one engine candidate row. There are 908 distinct engine-designation strings and four gearbox-classification values. These are aggregate coverage diagnostics only: **they are not pair records**, and the 98 multi-engine scopes demonstrate why joining by approval scope alone can be ambiguous. The pack contains no pair table.

The pack remains NL-only and `verified_research_only`. RDW Motorcode values remain candidates, not OEM-confirmed VAG engine codes; gearbox values remain classifications, not VAG gearbox codes. No model year, generation, individual-vehicle fitment, ECU/DTC/repair applicability or RU/EAEU applicability is inferred. Product import is false and the pack is not integrated into the desktop installer.

Run 11 predates the latest RDW query-spec and source-column provenance changes. The current builder also adds a foreign key from each source row to its source-file artifact, verifies row-by-row parity between canonical JSONL snapshots and SQLite row hashes, and emits aggregate scope-overlap/ambiguity metrics without creating pair records. These latest integrity changes require a new successful build; the run-11 artifact is historical evidence and must not be described as validated by the newer checks.

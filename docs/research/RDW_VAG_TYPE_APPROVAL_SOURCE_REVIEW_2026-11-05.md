# RDW EU type-approval source review — 2026-11-05

## Decision

**Rights:** cleared for a separate CC0-1.0, read-only research pack, subject to a per-resource metadata check at ingest.

**Data status:** not yet ingested. No RDW row is currently promoted into the vehicle/engine/gearbox core tables by this review.

**Product scope:** supplementary EU type-approval and Netherlands registration evidence only. This is **not** Russian or EAEU OTTS evidence and must never be presented as such.

## Official sources and reuse basis

- RDW open-data portal: https://opendata.rdw.nl/
- RDW open-data policy: https://www.rdw.nl/over-rdw/dienstverlening/open-data/algemene-informatie
  - RDW states that non-sensitive vehicle type-approval data is published as open data and is available free of charge without restrictions.
- Dutch government catalogue entry for vehicle type approvals: https://data.overheid.nl/dataset/324bac6c-9ac4-460c-a672-a5bc4785e364
  - The catalogue entry identifies the type-approval dataset as CC0.
- CC0 legal text: https://creativecommons.org/publicdomain/zero/1.0/

The source register records CC0-1.0 with commercial use, display, offline caching and redistribution allowed. The ingest must still fetch the live metadata JSON for every Socrata resource and fail closed if a resource advertises a conflicting licence or its parent-dataset relationship cannot be established.

A third-party schema reference was consulted only to cross-check RDW field names and resource IDs: https://github.com/j3lte/rdw-data. It is **not** an imported data source and no third-party code is copied into VAG TECH PRO.

## RDW resources pinned for the proposed pack

| Resource | RDW dataset ID | Intended use |
|---|---|---|
| Gekentekende voertuigen | `m9d7-ebf2` | Make/model, EU category, type-approval number, variant, execution and first-registration observation |
| TGK Aandrijving Uitvoering | `4by9-ammk` | Source field `motorcode` and engine approval attributes |
| TGK Versnelling Uitvoering | `7rjk-eycs` | Source field `codetypeversnellingsbak` and gear-count range |
| TGK Handelsbenaming Fabrikant | `x5v3-sewk` | Manufacturer trade name and type designation |
| TGK Basis Uitvoering | `byxc-wwua` | Vehicle category and approval-execution revision dates |
| TGK Merk Uitvoering | `kyri-nuah` | RDW make code cross-reference |

Official resource URLs are stored in `data/source-manifests/rdw-vag-type-approval.lock.json`.

## Join and applicability rules

The proposed join key is:

1. `typegoedkeuringsnummer`
2. `codevarianttgk` ↔ vehicle-registry `variant`
3. `codeuitvoeringtgk` ↔ vehicle-registry `uitvoering`
4. `volgnummerrevisieuitvoering`

An engine/transmission association is recorded as a source-supported **type-approval execution candidate** only when the exact approval + variant + execution + revision key has exactly one engine row and exactly one transmission row. If either side has zero or multiple rows, the records remain separate or explicitly ambiguous; the importer must not create a Cartesian pairing.

Important namespace restrictions:

- RDW `motorcode` is stored as `RDW.motorcode`; it is not automatically labelled a VAG factory engine code.
- RDW `codetypeversnellingsbak` is stored as `RDW.codetypeversnellingsbak`; it is not a VAG three-letter gearbox code.
- A unique type-approval execution association is not VIN-level fitment.
- First registration date is not model year or production date.
- Type-approval revision dates are not vehicle production dates.
- No generation is inferred from model name alone.

## Privacy and minimisation

The vehicle-register resource contains registration identifiers and other fields that are unnecessary for this product. The importer must retain only the VAG make/model and type-approval crosswalk fields listed in the lock file. It must never store `kenteken`, keeper/owner information, registration-holder data, insurance status or unrelated registration fields. No full registry dump is permitted.

## Required integrity evidence at ingest

For each resource and each filtered response, record:

- exact request URL and query text;
- fetched-at UTC timestamp;
- live RDW metadata revision/update timestamp;
- raw response byte count and SHA-256;
- selected-row count and filter description;
- licence and rights status;
- normalized database SHA-256;
- SQLite `integrity_check` and `foreign_key_check` results.

The source revision is the set of live per-resource metadata revisions plus the query/snapshot hashes, not a guessed release tag. No candidate record is promoted unless these checks pass.

## Sample key observed in the public vehicle registry

A public RDW response contains a Volkswagen Golf record with:

- make: `VOLKSWAGEN`
- trade name: `GOLF`
- type: `AU`
- EU category: `M1`
- type approval: `e1*2007/46*0623*03`
- variant: `AC4CJZAX0`
- execution: `FM6FM6AJ009N7MJOVLVR2`
- first registration observation: `2013-01-25`

The registration identifier is deliberately omitted. This confirms that the registry exposes the approval/variant/execution crosswalk needed to query the TGK tables; it does **not** by itself confirm an engine or transmission pairing.

## Explicit exclusions

This pack contributes no:

- RU/EAEU OTTS records or RU/EAEU applicability;
- VAG generation mapping or production-year ranges;
- confirmed VAG factory engine-code or gearbox-code mappings;
- ECU identifiers, DTC definitions, test plans or diagnostic execution;
- repair procedures, wiring diagrams, pinouts, torque values, adaptations or maintenance schedules;
- OEM parts applicability or VIN-specific build data.

**Project decision:** allow a separate, read-only CC0 candidate pack after the importer and all integrity/ambiguity tests pass. Keep its market and code namespaces visible in the UI. Never use it as a substitute for Russian/EAEU OTTS or licensed VAG factory service data.

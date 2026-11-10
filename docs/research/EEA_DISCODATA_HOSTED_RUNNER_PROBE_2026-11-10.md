# EEA Discodata hosted Windows probe — 10 November 2026

## Result

The official EEA Discodata SQL REST endpoint was probed from a GitHub-hosted Windows 2025 x64 runner using a single read-only query for one 2025 provisional row restricted to the core VAG make allowlist and non-personal type-approval/variant fields.

- Workflow run: https://github.com/ismailizmajlov-oss/VAG-TECH-PRO/actions/runs/42843396637
- Probe timestamp: 2026-11-10T15:21:20.333233Z
- API host: `discodata.eea.europa.eu`
- Table: `[CO2Emission].[latest].[co2cars_2025Pv31]`
- Result: `blocked_http_403`
- Rows returned: 0
- Query SHA-256: `c8e1cebdd37bd712f084ac42d6c6ef19ffddae23f786f18ae5cce6895d160124`
- Response SHA-256: null (no response body retained)
- Raw response retained: no
- Source data acquired: no

The endpoint denied the request with HTTP 403. This establishes a restriction from this GitHub-hosted runner at this time; it does not establish that the endpoint is unavailable from every network or from an authorized owner-controlled runner.

## Source rights and scope

The official EEA dataset metadata describes the CO2 new passenger-car dataset and identifies the Discodata SQL REST endpoint. The dataset is published under CC BY 4.0. This permits a separately attributed research pack subject to the licence, but it does not establish VAG factory engine/gearbox codes or exact repair applicability.

- Dataset metadata: https://sdi.eea.europa.eu/catalogue/datahub/api/records/b4044b06-2e6b-4f8e-a6e6-66e0e98bb0dd?language=eng
- Public SQL REST endpoint: https://discodata.eea.europa.eu/sql
- Licence: https://creativecommons.org/licenses/by/4.0/

## Safety and data handling

The probe selected only `MS`, `Year`, `Status`, `Mk`, `Cn`, `T`, `Va`, `Ve` and `TAN`. It requested at most one row, rejected personal/vehicle-identifier fields, and emitted only status, query hash and (if reachable) a one-row response hash. No row values or raw response were retained.

No EEA data was imported into the research pack or production SQLite. The source manifest continues to state `data_ingested=false`, `product_import_allowed=false`, and `product_fitment_confirmation_allowed=false`.

## Next acquisition gate

The full acquisition workflow remains restricted to an owner-controlled Windows 10/11 x64 runner. It must still validate the complete pinned source snapshot, per-file SHA-256, licence attribution, exact core-VAG make filter, schema, row counts, SQLite integrity and foreign keys before creating a separate EU-only research pack. A successful one-row probe alone would not authorize or complete a full acquisition.

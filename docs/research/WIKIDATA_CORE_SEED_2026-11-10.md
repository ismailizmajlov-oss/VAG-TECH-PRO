# VAG TECH PRO — Wikidata identity candidates in local core SQLite (10 November 2026)

## Scope

The desktop bootstrap imports a pinned, public Wikidata snapshot into the local core SQLite database so that identity candidates are available in the administrator's source-review queue. This is an additive, one-time, transactional import. It does **not** create verified vehicle configurations or technical repair data.

The import is deliberately limited to:
- 6 manufacturer identity candidates;
- 521 vehicle-model identity candidates;
- 530 underlying source bindings;
- 285 entities with a Russian label; remaining display labels fall back to the source English label.

Every imported row remains `review_status=candidate`, `market_scope=UNKNOWN`, and candidate-only applicability. The manufacturer grouping field is set to `VAG identity candidate`; it is not an authoritative corporate-ownership claim.

## Source and rights evidence

- Publisher: Wikidata / Wikimedia Foundation.
- Dataset license: CC0 1.0 Universal.
- License URL: https://creativecommons.org/publicdomain/zero/1.0/
- Source repository: https://www.wikidata.org/
- Source revision: `wikidata-snapshot-630dbed1af15`.
- Source query SHA-256: `3892acac5f6b675ce0255943045e1d90940fc1abb04d998f3557f4659a45fcac`.
- Source snapshot SHA-256: `630dbed1af15a81180fdba562824eaad8aa92352f4a8debb8a624ad37172bff4`.
- Research SQLite SHA-256: `bf9939044cb53a187fb1dee178e1784f3efaa60e069d20f829f37d8313270206`.
- CC0 notice file SHA-256: `a3b69835af6ff3dd2f7fcf20324ada50b5175d4e6724bd881e735bc077e594e1`.
- Pack manifest SHA-256 (stored as rights-evidence hash): `80504169ca52b9e3a49b1212e141af0ac1fce3eb9db49c4ac08adfdf8333356f`.
- Deterministic local-core import package SHA-256: `52c4b195d8200594aca1cec2de93f64f8fbe94a746dea0406715da7348e057d2`.

The published CC0 terms permit copying, redistribution, commercial use, display and offline caching of the structured data. The desktop source registry stores the license identifier, license URL, notice-file hash, rights-evidence hash, snapshot hash and the approved-by-published-license status. Attribution is not legally required by CC0; the source's recommended attribution text is retained.

## Import and safety behavior

On the first local-core API request, the desktop checks the bundled pack's manifest, license notice, snapshot and SQLite hashes; checks SQLite integrity and foreign keys; checks the pinned source revision and rights flags; then builds a vehicle-catalog package and imports it through the existing transactional package importer.

- Source absent: register the CC0 source, then import the package.
- Same approved source metadata and same package already applied: return `already_applied`; do not rewrite records.
- Existing source metadata differs or rights were revoked: skip; never silently restore approval or overwrite the source record.
- Missing pack: skip without changing the database.
- Tampered snapshot, database, license notice, counts or rights: fail closed before catalog records are imported.
- Import failure: package transaction rolls back. Existing garage vehicles, bookmarks, history and user data are not replaced.

The importer stores source revision, source snapshot hash, rights evidence, license hash, package hash, per-record hash, model/manufacturer QIDs, original labels, raw date statements, entity classes, source-binding indexes and per-binding SHA-256 values.

## Explicit non-claims

This pack provides identity candidates only. It does not establish:
- Russian or EAEU market applicability;
- model generations or production-year boundaries;
- engine codes or gearbox codes;
- exact engine/transmission pairs;
- ECU hardware/software applicability;
- VAG-specific DTCs, test plans, wiring diagrams, pinouts, torque values, adaptations, service schedules or repair procedures.

No model years are inferred from Wikidata date statements. No generic DTC data is mixed into VAG-specific namespaces. The import creates **0 verified models, 0 generations, 0 engines, 0 transmissions, 0 engine/gearbox pairs, 0 ECU records and 0 technical records**.

## Verification

The run92 test set checks:
1. first import inserts exactly 527 candidate records (6 manufacturers + 521 models);
2. all records remain candidate-only and UNKNOWN-market;
3. no generation, engine, transmission, pair, ECU, vehicle-configuration or technical record is created;
4. garage, bookmarks and history survive the import unchanged;
5. repeat import is idempotent;
6. rights revocation is not overwritten;
7. tampered source bytes are rejected before source registration;
8. missing source pack is a non-destructive skip;
9. the local API exposes source provenance and the import batch to the administrator.

The Windows installer lifecycle additionally checks the exact pack hashes, rights flags, source record, review queue counts and package hash after clean install and after update. Passing the candidate-seed tests does not establish professional repair-data coverage or native Windows 10/11 acceptance.

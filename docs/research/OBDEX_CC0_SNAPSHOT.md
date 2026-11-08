# OBDex CC0 generic diagnostic snapshot

## Pinned upstream revision

- Repository: https://github.com/foerbsnavi/OBDex
- Commit: `9ba1ffa095f3140d9e21b985b322ddea3134bb60`
- Commit time: 2026-11-07 13:43:17 UTC
- Data licence: CC0 1.0 Universal, scoped by upstream `LICENSE-DATA` to the YAML, JSON and schema data files.
- Licence URL: https://github.com/foerbsnavi/OBDex/blob/9ba1ffa095f3140d9e21b985b322ddea3134bb60/LICENSE-DATA
- Build tooling is separately MIT-licensed and is executed in CI; it is not copied into the application.

## Scope and safeguards

This is a **generic SAE/ISO OBD-II reference layer**, not a VAG factory diagnostic corpus.

- Expected upstream projection: 9,533 generic DTC records.
- Expected upstream PID projection: 132 records across Mode 01 and Mode 09.\n- Upstream-labelled generic ranges in the source projection: P0xxx, P2xxx, P34xx, B0xxx, C0xxx, U0xxx and U3xxx; this upstream scope does not override the normalized product namespace policy.
- DTC namespace: `generic_sae_iso_obd2`.
- Manufacturer-controlled DTC families are excluded by validation. P3xxx is a mixed manufacturer-controlled / ISO-SAE-reserved family. All 155 upstream-labelled P34xxx entries remain in the research-only pack; no P3xxx row is admitted to normalized product DTC namespaces until exact current J2012DA assignments are independently verified.
- No exact VAG model, generation, engine, gearbox, ECU, PR-code or Russian-market fitment is asserted.
- No repair procedure, wiring diagram, pinout, torque value or adaptation is created from these records.
- Records are imported as `source_imported_unreviewed`; they remain research/reference data until independently reviewed.
- Any repair-cost estimates in the upstream raw record are retained only for source integrity and must not be displayed as Russian-market prices.

## Reproducible Windows acquisition

Workflow: `.github/workflows/acquire-obdex-cc0.yml`.

The Windows runner checks out the pinned OBDex commit, runs `npm ci`, `npm run check` and `npm run build`, verifies the CC0 data-license scope, records SHA-256 and Git blob identifiers for each source YAML file, normalizes the generic DTC/PID package, builds a separate SQLite research database, and runs SQLite integrity and foreign-key checks.

The workflow artifact contains:

- the exact upstream YAML source files and `LICENSE-DATA`;
- generated JSON projections and their hashes;
- a normalized review package compatible with the local importer;
- an isolated SQLite research database;
- source and SQLite verification manifests.

The artifact is retained for 30 days. This workflow does not write to Supabase, does not publish the data as VAG-specific, and does not modify the production application database.

## Attribution

CC0 does not require attribution, but the application should retain the voluntary credit:

> OBD-II code data: OBDex (https://github.com/foerbsnavi/OBDex), CC0-1.0.

## Remaining boundary

The dataset can populate the generic OBD-II layer only. A separate, independently licensed source is still required for VAG-specific DTC variants, ECU applicability, guided tests and factory repair instructions.


## Current Windows offline bundle evidence — 2026-11-07

The pinned revision was acquired and packaged successfully in [Windows offline data-pack workflow run 214](https://github.com/ismailizmajlov-oss/VAG-TECH-PRO/actions/runs/42391816422). The verified bundle artifact is ID `13581812389`, SHA-256 `3e83523699cf60f0aaf355e3ae760527378d6346bf46d1f85bc3f0522681c23e`. Its OBDex SQLite database SHA-256 is `1a6e98bb99495e584aa3606848acd8aac86f7959f1609a577d5ff43e816adb5a`; the source manifest SHA-256 is `d8bd107da550e826e4199311e54d993cfdef736ed31749c29e94961ea3d90fa2`. Independent read-only validation returned `integrity_check=ok`, zero foreign-key violations, 9,533 generic DTCs, 132 generic PIDs, zero VAG-specific DTC rows and zero fitment claims. No P3xxx records are admitted to normalized product DTC namespaces. All 155 upstream-labelled P34xxx entries remain research-only pending exact current J2012DA allocation evidence.


## Correction — 2026-11-08

The earlier statement that 155 P34xxx records were admitted from the mixed P3 family is superseded. The current normalized policy quarantines the entire P34xxx-P39xxx family because the current licensed SAE J2012DA_202607 allocation table has not been acquired. The 155 upstream-labelled P34xxx rows remain preserved only in the isolated CC0 research pack; the upstream CC0 label is not treated as proof of current SAE/ISO allocation.

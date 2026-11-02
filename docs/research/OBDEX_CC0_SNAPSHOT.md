# OBDex CC0 generic diagnostic snapshot

## Pinned upstream revision

- Repository: https://github.com/foerbsnavi/OBDex
- Commit: `09c8aac3d7cb3477a8d9345dfff90b82457b64d1`
- Commit time: 2026-11-02 19:36:08 UTC
- Data licence: CC0 1.0 Universal, scoped by upstream `LICENSE-DATA` to the YAML, JSON and schema data files.
- Licence URL: https://github.com/foerbsnavi/OBDex/blob/09c8aac3d7cb3477a8d9345dfff90b82457b64d1/LICENSE-DATA
- Build tooling is separately MIT-licensed and is executed in CI; it is not copied into the application.

## Scope and safeguards

This is a **generic SAE/ISO OBD-II reference layer**, not a VAG factory diagnostic corpus.

- Expected upstream projection: 9,533 generic DTC records.
- Expected upstream PID projection: 132 records across Mode 01 and Mode 09.
- DTC namespace: `generic_sae_iso_obd2`.
- Manufacturer-specific DTC families are excluded by validation.
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

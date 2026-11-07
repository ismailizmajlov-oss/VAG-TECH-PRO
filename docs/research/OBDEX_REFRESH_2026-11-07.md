# OBDex generic DTC source refresh review — 2026-11-07

## Decision

Refresh the isolated generic SAE/ISO OBD-II research pack from the upstream OBDex revision
`9ba1ffa095f3140d9e21b985b322ddea3134bb60` (2026-11-07 13:43:17 UTC). Keep it in the
separate `generic_sae_iso_obd2` namespace. It remains **generic reference data**, not a VAG
factory DTC corpus and not evidence of vehicle, engine, gearbox, ECU or market applicability.

The VAG TECH PRO lock file and central source register now pin this revision. The acquisition
workflow must rebuild the source snapshot, per-file hashes, per-record hashes and isolated SQLite
database before the refreshed pack is accepted. No new snapshot/database SHA-256 is asserted in
this review; CI-generated evidence is authoritative.

## Upstream revision delta

The upstream commit removes nine MyCarly URL references from generic code entries in the P0644–P06D8
range. The commit message and diff report the source-link count changing from 30,884 to 30,875 and
the number of linked sites from 245 to 244. The affected entries retain CARB and manufacturer or
technical-bulletin references in the reviewed diff. No DTC identifiers or PID definitions are
changed by this commit.

The upstream README continues to describe 9,533 generic DTCs and 132 Mode 01/Mode 09 PIDs. The
acquisition workflow independently rebuilds the pinned revision and enforces the exact expected
counts and allowed generic code ranges; any mismatch fails closed.

## Rights

The upstream `LICENSE-DATA` at the pinned revision states CC0 1.0 Universal and explicitly limits
that dedication to the repository's YAML, JSON and schema data files. The accompanying code is
separately MIT-licensed. VAG TECH PRO imports only the data files under the CC0 data dedication;
the upstream code is executed only in the isolated acquisition workflow and is not copied into
the desktop application.

Upstream source URLs embedded in DTC records are not covered by the dataset's CC0 dedication.
The importer preserves them only in the raw source record, performs syntax validation only, does
not fetch them, and does not render them as links. This prevents the data licence from being
misapplied to third-party source documents.

## Applicability and product boundary

- Namespace: `generic_sae_iso_obd2`.
- Market scope: `UNKNOWN`; no RU/EAEU, EU or North-American market claim.
- Manufacturer-specific ranges remain excluded: P1xxx, P30xx–P33xx, B1xxx–B2xxx,
  C1xxx–C2xxx and U1xxx–U2xxx.
- Only P34xx records are admitted from the mixed P3 family (155 records in this pinned snapshot). P35xx–P39xx remain excluded until the source and each code's standardized status are independently established.
- VAG-specific DTC rows: 0.
- Exact vehicle, generation, model-year, engine, gearbox, ECU and PR-code fitment: none.
- Repair-cost estimates and generic repair suggestions are not presented as VAG OEM procedures.
- Production catalog ingestion remains false; the pack is a separately licensed research reference.

## Verification sources

1. Upstream commit: https://github.com/foerbsnavi/OBDex/commit/9ba1ffa095f3140d9e21b985b322ddea3134bb60
2. Upstream data licence at the pinned revision: https://github.com/foerbsnavi/OBDex/blob/9ba1ffa095f3140d9e21b985b322ddea3134bb60/LICENSE-DATA
3. Upstream dataset and edition-2 review policy: https://github.com/foerbsnavi/OBDex
4. Local source lock: `data/source-manifests/obdex-generic-cc0.lock.json`
5. Local isolated-pack verifier: `scripts/build_offline_data_pack_index.py` and
   `tests/test_offline_data_pack_rights.py`

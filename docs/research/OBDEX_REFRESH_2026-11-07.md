# OBDex generic DTC source refresh review — 2026-11-07

## Decision

Refresh the isolated generic SAE/ISO OBD-II research pack from the upstream OBDex revision
`9ba1ffa095f3140d9e21b985b322ddea3134bb60` (2026-11-07 13:43:17 UTC). Keep it in the
separate `generic_sae_iso_obd2` namespace. It remains **generic reference data**, not a VAG
factory DTC corpus and not evidence of vehicle, engine, gearbox, ECU or market applicability.

The VAG TECH PRO lock file and central source register pin this revision. The acquisition workflow
rebuilds the source snapshot, per-file hashes, per-record hashes and isolated SQLite database. The
CI-generated run 212 evidence below is authoritative; no hash is inferred from the source revision
alone.

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


## Acquisition and offline bundle verification — run 212

The Windows offline data-pack workflow completed successfully on 2026-11-07 at 16:27:46 UTC:
[run 212](https://github.com/ismailizmajlov-oss/VAG-TECH-PRO/actions/runs/42391249456).

- OBDex source artifact ID: `13581581954`; ZIP size: 33,741,177 bytes; SHA-256: `92668d4dd8109a93084a6cb4f1e935a382427b82ea3589f828ac6adfa18afbca`.
- Verified Windows offline bundle artifact ID: `13581602022`; ZIP size: 37,222,865 bytes; SHA-256: `4d62975d1493ce494f1b967ae24c9d015493c256e2c0fc373d2bfd3125e588e7`.
- Packaged OBDex SQLite SHA-256: `fe82b6cf68fae49fe1c9ab4ea4ced4238b416d426a6258fc3c764f32e8d5766f`.
- OBDex source-manifest SHA-256: `620d40ecbdf60c0064d1cdeb207f851589cf187af38038a7171ac22b3a2317`.
- Counts: 9,533 generic DTC identifiers and 132 generic PIDs; 0 VAG-specific DTC rows, 0 exact-vehicle fitment claims and 0 production rows.
- The mixed P3 family contributes only 155 P34xx records in this pinned snapshot. P35xx–P39xx are explicitly excluded until their generic standardized status is independently established.
- An independent read-only check of the database extracted from the final offline bundle returned `PRAGMA integrity_check=ok`, zero foreign-key violations, 9,533 DTC rows and 132 PID rows. All P3 rows are P34; no manufacturer-specific namespace or vehicle-fitment claim is present.

The OBDex pack remains a separate generic SAE/ISO reference. Its generic descriptions, causes and repair suggestions are not VAG factory repair instructions. Source URLs embedded in raw records are not fetched or displayed. The pack is included in the offline research bundle, but not merged into the production vehicle/technical catalog.

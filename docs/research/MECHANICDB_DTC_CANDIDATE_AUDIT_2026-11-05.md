# MechanicDB make-labelled DTC candidates — independent audit

Audit date: 2026-11-04 UTC  
Scope: source provenance, database integrity and namespace separation; not OEM validation.

## Pinned pack and rights

- Pack ID: `mechanicdb-vag-dtc-candidates-odbl`
- Upstream repository: https://github.com/MechanicDB/MechanicDB-public
- Upstream revision: `c788dfe9ed1517d4cd0be27f5aacb4776abf4864`
- Database licence: ODbL-1.0 (commercial use, display, offline cache and redistribution allowed subject to attribution and share-alike)
- Upstream code notice: MIT
- Documentation licence: CC BY 4.0
- GitHub Actions artifact ID: `13223942420`
- Artifact ZIP SHA-256: `f294bf4ebe6384b2ad6a586244ba0c49011fb441c691006c460d8a070744a5d6`
- Source CSV SHA-256: `796fa2b18bdbff311f15eb4943b68adbf7241e564ce8eff32023a2d297694bff`
- SQLite SHA-256: `f123b251659b45f4acf64071329dec6dc3a4ba1c8b2f827ff1ad3b45e28e0c94`

## Retained rows

| Make label | Code | Namespace | Status |
|---|---|---|---|
| Audi | P3000 | `manufacturer_controlled_candidate` | `community_reference_unverified` |
| Volkswagen | P1128 | `manufacturer_controlled_candidate` | `community_reference_unverified` |

- Manufacturer-controlled candidate rows: 2
- Generic SAE/ISO rows in this pack: 0
- Repair-procedure rows: 0
- OEM part rows: 0

The two source-line hashes in the manifest were independently checked against the pinned CSV using the original CRLF line bytes; both match. The full source CSV hash and SQLite hash also match the pack manifest.

## SQLite and policy checks

- SQLite `PRAGMA integrity_check`: `ok`
- Foreign-key violations: 0
- Both rows have `market_scope=UNKNOWN`.
- Both rows have `applicability_precision=manufacturer_make_candidate`.
- Both rows have `vehicle_fitment_claim=0`, `ecu_fitment_claim=0`, `pr_code_claim=0`.
- Both rows have `diagnostic_execution_allowed=0`, `repair_procedure_included=0`, `oem_part_number_included=0`.

## Classification decision

These are **make-labelled community candidates, not confirmed VAG-specific DTCs**. A manufacturer-controlled code range does not prove that the code definition or description is correct for a particular VAG model, engine, ECU or market. In particular, P3000's high-voltage-battery description and P1128's fuel-trim description lack exact VAG model/ECU evidence in this source.

Keep these rows separate from the CC0 generic SAE/ISO OBD-II database and outside normal diagnostic lookup. If they are ever shown, display them only in a clearly labelled research-candidate area with the source, revision, licence, UNKNOWN market and unverified status. Do not turn them into test plans, repair advice or executable commands without primary technical evidence and a separate review.

# VehiclesDB VAG identity pack — independent audit

Audit date: 2026-11-05 UTC  
Scope: rights, provenance, SQLite integrity and market/applicability boundaries.

## Pinned pack and licence

- Pack ID: `vehiclesdb-vag-identity`
- Upstream repository: https://github.com/vehiclesdb/vehiclesdb
- Upstream tag/revision: `v2026.10.3`
- Dataset licence: CC BY 4.0
- Commercial use, display, offline caching and redistribution: allowed under CC BY 4.0
- Attribution: required — “Vehicle data by VehiclesDB (vehiclesdb.com)” plus the upstream register notices
- Share-alike: not required
- Database SHA-256: `b209771a518e71775aa5591a6ef64d0ccff73c47dd6699fad67f73add2b0ab11`
- Upstream catalog SHA-256: `5889bb4b3ca35cf933d83f030a04120ccf4c86e25a5a050c5ff218068720bd62`
- Upstream manifest SHA-256: `859d1173d674728b0616a17af2e1d67e3481328d1064c148f0a52af9c882d8b0`
- Attribution file SHA-256: `bf2ebd50a843d1b6e445ce3aff594b2ec94658aa1cd7b786e4e73db04ad6cd21`
- Licence file SHA-256: `48a2c12a43e8df6700e36440f089c1497e62a507e194e995d69a7d3530999e78`

The source lock now pins both SHA-256 and exact byte size for all four upstream files. The acquisition workflow fails closed if a tag is moved, an upstream file changes in place, a CDN response is altered, or a file is truncated—even when the upstream manifest version and row counts still match.

| Upstream file | Bytes | SHA-256 |
|---|---:|---|
| `dist/catalog.sqlite` | 9,781,248 | `5889bb4b3ca35cf933d83f030a04120ccf4c86e25a5a050c5ff218068720bd62` |
| `manifest.json` | 11,249 | `859d1173d674728b0616a17af2e1d67e3481328d1064c148f0a52af9c882d8b0` |
| `ATTRIBUTION.md` | 9,615 | `bf2ebd50a843d1b6e445ce3aff594b2ec94658aa1cd7b786e4e73db04ad6cd21` |
| `LICENSE` | 1,319 | `48a2c12a43e8df6700e36440f089c1497e62a507e194e995d69a7d3530999e78` |

## Contents

| Record type | Count |
|---|---:|
| Approved source registers | 14 |
| Model-name candidates | 260 |
| Market-presence evidence rows | 1,524 |

Make counts: Audi 65, CUPRA 7, SEAT 22, Škoda 37, Volkswagen 129.

The 14 market codes are: AR, AU, CA, DE, ES, FI, GB, IE, LU, MY, NL, NZ, UA and US. Russia, Kazakhstan, Belarus, Armenia and Kyrgyzstan are absent. Ukraine is not an EAEU market.

## Independent checks

- SQLite `PRAGMA integrity_check`: `ok`
- SQLite foreign-key violations: 0
- All four source-file hashes and byte counts match the pack manifest.
- All 260 model rows have `verification_status=identity_candidate`, `applicability_precision=make_model_name_only` and `fitment_status=not_established`.
- All 1,524 evidence rows have `applicability_precision=market_presence_only`.
- No RU/EAEU country codes occur in the market-evidence table.
- No generation, model-year, engine-code, gearbox-code, ECU, PR-code or exact-fitment data is included.

## Product decision

Keep this CC BY 4.0 pack separate, with attribution and upstream notices intact. It may provide foreign-market make/model identity candidates only. It cannot populate Russian/EAEU vehicle coverage, generation/year ranges, engine/gearbox pairings, ECU fitment, OEM catalogue applicability or repair guidance.

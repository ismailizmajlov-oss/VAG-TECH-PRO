# VehiclesDB VAG identity candidate snapshot — 2026-11-03

## Result

A Windows x64 CI build successfully downloaded the pinned VehiclesDB v2026.10.3 open release, validated its CC BY 4.0 license and attribution files, checked the upstream SQLite integrity, and built an isolated VAG identity candidate database.

The corrected Windows CI run completed successfully: build, independent provenance/license/market-scope verification, synthetic import/rejection tests, Python compilation, and artifact upload all passed. GitHub Actions run: 41565306691. The uploaded artifact digest is sha256:6d6a3c2d30c71caa6ed8a34f6e0e1a2a4c4e5f0f5c9d0b2e9e2c1d6c7c2d8f40.

## Pinned source and provenance

- Repository: https://github.com/vehiclesdb/vehiclesdb
- Pinned tag: v2026.10.3
- Upstream dataset license: CC-BY-4.0
- Commercial use: permitted by the published CC BY 4.0 license, subject to attribution and the upstream source notices.
- Required product credit: **Vehicle data by VehiclesDB** — https://vehiclesdb.com
- The pack includes the upstream LICENSE and ATTRIBUTION.md, plus the exact upstream manifest.
- Source lock: data/source-manifests/vehiclesdb-vag-identity.lock.json
- Builder: scripts/build_vag_identity_vehiclesdb.py
- Verifier: scripts/verify_vag_identity_vehiclesdb.py
- Windows workflow: .github/workflows/acquire-vag-identity-vehiclesdb.yml

Verified output SQLite SHA-256: 54e982551fbab0119ee4df8730f03acf8eb9020f4ed6bbf83a7b3d55f3a664d8.

Source snapshot SHA-256 values from the Windows runner:

| File | SHA-256 |
|---|---|
| dist/catalog.sqlite | 5889bb4b3ca35cf933d83f030a04120ccf4c86e25a5a050c5ff218068720bd62 |
| manifest.json | 859d1173d674728b0616a17af2e1d67e3481328d1064c148f0a52af9c882d8b0 |
| ATTRIBUTION.md | bf2ebd50a843d1b6e445ce3aff594b2ec94658aa1cd7b786e4e73db04ad6cd21 |
| LICENSE | 48a2c12a43e8df6700e36440f089c1497e62a507e194e995d69a7d3530999e78 |

## Filtered VAG data

The initial build contained:

- 260 VAG model-name candidates;
- 1,524 model/country/source presence-evidence rows;
- 14 approved upstream source registries;
- Audi: 65 models;
- CUPRA: 7 models;
- SEAT: 22 models;
- Škoda: 37 models;
- Volkswagen: 129 models.

Market evidence in this snapshot covers AR, AU, CA, DE, ES, FI, GB, IE, LU, MY, NL, NZ, UA and US. There is **no Russian-market evidence** and no Thailand evidence in the filtered pack.

Four source families were excluded from the imported evidence rows:
- Swiss canton-only evidence, not nationwide coverage;
- Israel data with source-specific terms not relicensed as CC BY 4.0;
- Norway roadworthiness-inspection data, not a registration/fleet register;
- Thailand data, outside the requested product market.

The import gate fails if the pinned release changes a source license, source country, evidence type, or source identity without a lock-file review.

## Applicability boundary

This is an identity/presence candidate pack only:

- make and model names are candidates;
- per-country evidence means model presence in that source's dataset, not proof of official Russian sale or exact factory fitment;
- no generations or model years are supplied by this dataset;
- no engine codes, gearbox codes, ECU fitment, PR-code mapping, or VIN build-sheet data are supplied;
- all rows use applicability_precision=make_model_name_only and fitment_status=not_established;
- no Russian fitment may be inferred from German, Ukrainian, or other foreign-market evidence.

The pack is kept as its own SQLite database under CC BY 4.0 with the required attribution. It is not merged with the ODbL, CC0, or CC BY-SA research databases, so their license obligations remain separate.

## Product use

This dataset can support a global make/model search fallback and foreign-market presence references after the corrected verifier passes. It cannot populate Russian OTTS fitment, generation/engine/gearbox relationships, or repair procedures. Those still require a separately licensed Russian/EAEU source or independently verified technical evidence.

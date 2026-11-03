# AutoDiag2 VAG candidate-pack attribution review — 2026-11-04

## Decision

The AutoDiag2 v6 data is usable as a **separate ODbL/DbCL research database** under the upstream license terms declared in its pinned LICENSE and README.md. It is not an OEM database, does not establish Russian/EAEU applicability, and must not be merged into the main proprietary SQLite database without a separate ODbL compatibility review.

The initial candidate pack contained 956 DTC rows that looked VAG-related only because a generic ECU record used the text audi or volkswagen as its model label. All 956 rows were source_scope=make_level, had ecu_manufacturer=generic, and had zero links to a vehicle configuration. They are **not VAG-specific DTC evidence** and have been excluded from the filtered candidate pack.

## Pinned source and artifact

- Upstream: https://github.com/autodiag2/database
- Release: v6
- Source revision: 59b4e774c4023b2daaee179177615f17a5967ae1
- Upstream SQLite asset: ad_database.sqlite
- Upstream asset SHA-256: 61f9398f479d2d59a8b44c05da72cb5d519232e915bc7dcdf43f4bb5265baaf3
- Upstream asset size: 10,649,600 bytes
- Upstream license file SHA-256: 50a8762802c3303f5612c002bd35a3e617dcc7315ff7073f784b8682ea646cb5
- Upstream README SHA-256: 993937e4edb4ddf03bf9c6435215d751ed8a867276cd16dc5086748d48bdae2d
- GitHub Actions artifact inspected: autodiag2-vag-community-candidate-pack
- Artifact ID: 13268484250
- Workflow run ID: 41715531679
- Artifact ZIP SHA-256: eab2029c26ecc73a6a6643fbb6a22a6e2a3107d31351324fa2d478ef27920ddf

The upstream license declares ODbL-1.0 for the database, DbCL-1.0 for database contents, and GPL-3.0-or-later for upstream source code. The candidate database remains a separate pack with attribution and share-alike obligations. The declared commercial use, display, offline caching and redistribution rights do not imply OEM endorsement or technical correctness.

## Data-quality finding

| Item | Count |
|---|---:|
| VAG model candidates | 110 |
| Vehicle-version candidates | 259 |
| Engine source-field candidates | 1,083 |
| ECU candidates | 179 |
| Vehicle/configuration candidates | 3,170 |
| DTC candidate rows before filtering | 956 |
| DTC rows linked to a VAG vehicle configuration | 0 |
| DTC rows with generic ECU manufacturer | 956 |
| DTC rows with source_scope=make_level | 956 |
| DTC-to-configuration candidate links | 0 |
| Transmission records | 0 |

The 956 DTC records were derived from generic-manufacturer ECU entries whose ECU model text matched a VAG make label. That string match is not manufacturer attribution. The records are therefore excluded, not relabelled as VAG-specific.

The source engine table also contains a code field, but a short alphanumeric shape is not proof of a factory engine code. Some values in this field are gearbox-like labels (for example, 6HP28, 8HP45, 8HP55). The final pack now marks every non-empty source code field as unverified_source_code_field; it does not infer a factory engine code or a transmission code from the value's shape.

## Filtered pack result

The filtered local pack was rebuilt from the pinned artifact and independently checked:

- 110 model candidates, 259 version candidates, 1,083 engine-source candidates, 179 ECU candidates and 3,170 configuration candidates retained as research-only.
- 0 DTC candidate rows retained.
- 0 verified VAG-specific DTC rows.
- 0 verified factory engine codes.
- 0 transmission records.
- Market scope remains UNKNOWN.
- No exact vehicle, engine, gearbox, ECU or repair applicability is asserted.
- SQLite integrity_check: ok.
- SQLite foreign-key violations: 0.
- Every file listed in SHA256SUMS.txt matches its SHA-256 digest.

Filtered SQLite SHA-256: 9e61c1b6a9e51ef6ae351aae493c56800413d582238c187a8777a482c9eaa0b3

## Code and CI gate

The main branch now contains:

- scripts/filter_autodiag2_vag_dtc_candidates.py
- tests/test_autodiag2_vag_dtc_policy.py
- Updated .github/workflows/acquire-autodiag2-vag-candidates.yml

The workflow runs regression tests, builds the pinned candidate pack, excludes make-level generic-ECU DTCs and unlinked/unknown-ECU rows, downgrades all engine source-code fields to explicitly unverified, and only then uploads the separate ODbL candidate artifact.

Relevant commits:
- DTC attribution filter: 32ddf149e4f5ada10b599028717ee849d9fe3e60
- Large-pack-safe filtering: 9f3b27dd55c0755a681998170dd12260385d69cd
- Workflow rights/attribution gate: fd3904527bfc429ad9d50510fc572eed209ef2e5
- Engine-code heuristic removal: 5b5abe7f6bd3d125657e600e667f7d1fe085e816
- Engine-code regression test: a1b27d881233148a27eedf1c2f4594dfde92daf6

The workflow result for the latest policy-gated rerun has not yet been observed. The locally filtered pack is verified, but it is not represented as a completed Windows installer or production import.

## Publication boundary

Do not promote this pack's models, engine source fields, ECU candidates or DTC records to production. Do not infer RU/EAEU market scope from the brand/model labels. Use the pack only for research discovery and candidate comparison until independent primary evidence, exact applicability, and publication rights are reviewed.

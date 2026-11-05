# AutoDiag2 VAG community pack — independent artifact audit

Audit date: 2026-11-04 UTC  
Scope: licence, package integrity, candidate counts and DTC/fitment policy; not OEM validation.

## Pinned source and rights

- Publisher: AutoDiag2/database
- Repository: https://github.com/autodiag2/database
- Release: `v6`
- Source revision: `59b4e774c4023b2daaee179177615f17a5967ae1`
- Upstream SQLite asset SHA-256: `61f9398f479d2d59a8b44c05da72cb5d519232e915bc7dcdf43f4bb5265baaf3`
- Database licence: ODbL-1.0
- Contents licence: DbCL-1.0
- Attribution and share-alike: required
- Separate pack: required
- Commercial use, display, offline cache and redistribution: explicitly allowed by the pinned pack licence metadata, subject to ODbL/DbCL obligations
- Acquisition workflow run: `41726841575`
- Artifact ID: `13275271441`
- Artifact ZIP SHA-256: `aeaffa50d7ee0208503053b01d73d30e4ae18f4d28d3f64153c398815b36dc87`
- Candidate SQLite SHA-256: `5b071814ec63516f3fc8c5dc114d746b86e67ab75476b604c2606678dfff5c1a`

## Retained candidate data

| Record type | Count |
|---|---:|
| Vehicle models | 110 |
| Vehicle versions | 259 |
| Engine source-field candidates | 1,083 |
| ECU candidates | 179 |
| Vehicle configuration candidates | 3,170 |
| Retained DTC candidates | 0 |
| DTC-to-vehicle/ECU links | 0 |
| Transmission records | 0 |
| Verified factory engine codes | 0 |
| Verified VAG-specific DTCs | 0 |

The source make labels are Audi, SEAT, Škoda and Volkswagen. The pack keeps `Volkswagen__VW_` as an alias candidate rather than silently merging it.

## DTC separation gate

The unfiltered upstream asset contained 956 make-level DTC rows. They were removed because a make label and a generic/unknown ECU identity do not establish VAG attribution or a vehicle-configuration link. The filtered manifest records:

- `dtc_policy_filtered=true`
- `unattributed_make_level=956`
- generic DTC rows in the retained pack = 0
- retained VAG-specific verified DTC rows = 0
- diagnostic execution = disabled
- repair advice approval = disabled

This pack must not be described as a VAG DTC database. Generic SAE/ISO DTC remain in the separate CC0 OBDex namespace.

## Integrity checks

- Candidate SQLite `PRAGMA integrity_check`: `ok`
- Candidate SQLite foreign-key violations: 0
- Candidate database SHA-256 matches manifest.
- Artifact ZIP SHA-256 matches the GitHub Actions artifact digest.
- The pack includes the upstream licence and README with their SHA-256 values in the manifest.

## Applicability boundary

All records remain `market_scope=UNKNOWN` and `verification_status=community_reference_unverified`. Version labels such as `8X` and year strings such as `2008-2018` are community source fields, not verified generation/year applicability. Engine strings may be trim labels or other source values; their quality is `unverified_source_code_field`. ECU candidates are not exact ECU fitment. No gearbox data is present and no gearbox may be inferred from an engine field.

## Product decision

Keep the ODbL/DbCL database as a separate read-only research pack with attribution and share-alike notices intact. It may support candidate discovery only. Do not merge it into the production vehicle configuration tables, expose its engine strings as confirmed factory codes, assert exact ECU/vehicle fitment, or enable diagnostic commands, DTC lookup or repair advice from this pack.

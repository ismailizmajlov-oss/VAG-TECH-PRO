# Licensed community VAG candidate packs — independent audit

Audit date: 2026-11-05  
Scope: artifact integrity, licence metadata, provenance and applicability boundaries. This is not OEM validation.

## AutoDiag2/database v6

- Repository: https://github.com/autodiag2/database
- Pinned revision: `59b4e774c4023b2daaee179177615f17a5967ae1`
- Upstream SQLite asset SHA-256 recorded in the pack manifest: `61f9398f479d2d59a8b44c05da72cb5d519232e915bc7dcdf43f4bb5265baaf3`
- Candidate SQLite SHA-256: `5b071814ec63516f3fc8c5dc114d746b86e67ab75476b604c2606678dfff5c1a`
- Downloaded GitHub Actions artifact ID: `13275271441`; ZIP SHA-256: `aeaffa50d7ee0208503053b01d73d30e4ae18f4d28d3f64153c398815b36dc87`
- Rights: database ODbL-1.0; database contents DbCL-1.0. Commercial use, display, offline cache and redistribution are allowed subject to attribution, share-alike and keeping the derived database separate. GPL-3.0-or-later applies to upstream source code, which is not used by this pack.
- Independent checks: downloaded ZIP hash matches; every entry in `SHA256SUMS.txt` matches; candidate SQLite `PRAGMA integrity_check` is `ok`; foreign-key violations are zero.

| Record type | Count |
|---|---:|
| Models | 110 |
| Versions | 259 |
| Engine source-field candidates | 1,083 |
| ECU candidates | 179 |
| Vehicle configuration candidates | 3,170 |
| Retained DTC candidates | 0 |
| Transmission records | 0 |
| Verified factory engine codes | 0 |

All rows have `market_scope=UNKNOWN` and `community_reference_unverified`. Engine values are source-field labels, not verified factory codes; sampled values include trim/displacement descriptions such as `1000 25 TFSI` and `1200 TSI`. The source's 956 make-level DTC rows were excluded. No exact vehicle/ECU fitment, engine/gearbox pairing, DTC lookup or diagnostic execution is justified.

## MechanicDB make-labelled DTC candidates

- Repository: https://github.com/MechanicDB/MechanicDB-public
- Pinned revision: `c788dfe9ed1517d4cd0be27f5aacb4776abf4864`
- Data: ODbL-1.0; documentation: CC BY 4.0; the upstream MIT attribution notice is preserved. Commercial use, display, offline caching and redistribution are allowed under ODbL, with attribution and share-alike.
- Source CSV SHA-256: `796fa2b18bdbff311f15eb4943b68adbf7241e564ce8eff32023a2d297694bff`
- Candidate SQLite SHA-256: `f123b251659b45f4acf64071329dec6dc3a4ba1c8b2f827ff1ad3b45e28e0c94`
- Downloaded artifact ID: `13223942420`; ZIP SHA-256: `f294bf4ebe6384b2ad6a586244ba0c49011fb441c691006c460d8a070744a5d6`
- Independent checks: all pack checksums match; SQLite integrity is `ok`; foreign-key violations are zero; the full CSV hash and both physical source-line hashes match the manifest.

| Candidate | Source line | Classification |
|---|---:|---|
| Audi P3000 | 77 | `manufacturer_controlled_candidate`, unverified |
| Volkswagen P1128 | 91 | `manufacturer_controlled_candidate`, unverified |

Both records remain `market_scope=UNKNOWN`, `applicability_precision=manufacturer_make_candidate`, and `community_reference_unverified`. The source lines establish only the upstream make labels; they do not establish a VAG ECU, model, generation, engine, gearbox, PR-code or VIN fitment. Generic SAE/ISO rows are not present in this pack and remain in the separate OBDex namespace. Diagnostic execution, repair procedures and OEM part mapping are disabled/absent.

## Product decision

Keep both datasets as separate, read-only research packs under their published licences. The AutoDiag2 pack is identity/configuration candidate data only; the MechanicDB pack is a two-row make-labelled DTC candidate set hidden from normal diagnostic lookup pending technical review. Neither pack is a verified VAG factory catalogue. Do not merge either into production vehicle variants, infer gearbox codes, enable diagnostic execution, or describe the two MechanicDB rows as confirmed VAG-specific DTCs.

# VehiclesDB v2026.11.3 refresh review — 2026-11-11

## Decision

Accept the pinned upstream release only as a separate, read-only identity-candidate research pack under CC BY 4.0. Do not import it into the production vehicle-fitment catalog and do not use it to make repair, safety-critical, engine/gearbox, ECU, DTC or exact-applicability decisions.

## Independent source verification

The Windows x64 count-only probe downloaded the four files from the immutable upstream tag `v2026.11.3`, checked each byte size and SHA-256 against the lock, revalidated the published CC BY 4.0 license and attribution notice, and applied the same approved-source and VAG make/kind filters as the pack builder.

| Upstream file | Bytes | SHA-256 |
|---|---:|---|
| `dist/catalog.sqlite` | 10,260,480 | `06aa916028e2d732ce087e9a566fc26717ae0a9a2ab8cd8487a0e6df31f1b172` |
| `manifest.json` | 12,498 | `7df6ec271cb5a7aae80164e28cb3b4be83612da42942b76989e43b7c99e8c075` |
| `ATTRIBUTION.md` | 10,256 | `47edb850ed4ff02f5c9d8de3efcdd314d7a0162b1067e1c15ca07b956acccf60` |
| `LICENSE` | 1,319 | `48a2c12a43e8df6700e36440f089c1497e62a507e194e995d69a7d3530999e78` |

Canonical source-snapshot digest (SHA-256 of sorted, compact UTF-8 JSON containing the four file sizes and hashes): `311decddc3e4a448d6b8c9556ba88159740fad87517e2a9387b182ec8a9a71aa`.

The read-only probe matched the pinned counts exactly:

- 14 approved source registers;
- 307 VAG make/model-name candidates;
- 1,621 foreign-market presence evidence rows.

The separate SQLite pack was built and independently verified in Windows workflow run [42874459366](https://github.com/ismailizmajlov-oss/VAG-TECH-PRO/actions/runs/42874459366). Pack database SHA-256: `1f23666dcb83a47ccceac272165c4a3495dd03ae9ac5082ffc5f1486967e2e71`. The three-database Windows x64 offline research bundle was independently verified in the same run; its artifact SHA-256 is `f971cc47c3651da7c2fc68022c151f5eccad9dbd18b84580618fb920883891be`. Neither artifact is an installer.

## Latest independent rebuild — 2026-11-10

A subsequent Windows x64 bundle build re-downloaded the pinned source snapshot and independently verified all three SQLite databases:

- Workflow run: [42887184918](https://github.com/ismailizmajlov-oss/VAG-TECH-PRO/actions/runs/42887184918)
- Source commit: `81b785244510681182ee9b7a7281f0bd6a53e8f4`
- VehiclesDB SQLite SHA-256: `52c59d92e6d10820dfe7f16fc5fa1b50aa2075e6894eee25135e5fa1cfa62465`
- Three-database Windows x64 research bundle: 42,745,584 bytes; SHA-256 `09b7018802352550b20931fb5a8c6268c724e9b5f48b5c62f62690ed43e0ee88`
- The bundle index identifies itself as `verified_offline_data_packs_not_installer`; the three SQLite files remain separate and are not merged.
- Independent checks: all three databases returned `PRAGMA integrity_check = ok`; all three returned zero foreign-key violations; each database SHA-256 matched the bundle index.
- VehiclesDB remains 307 identity candidates and 1,621 foreign-market presence rows, with zero Russian-market rows, zero populated model-year bounds, and every row still `identity_candidate` / `not_established`.
- OBDex remains 9,533 generic SAE/ISO DTC research rows and 132 PID rows, all in `generic_sae_iso_obd2`; no VAG fitment claims were found.
- OBDb remains 38 source repositories, 135 generation candidates, 71 ECU candidates, 18,387 command candidates and 19,799 signal candidates; zero commands are marked executable.

This rebuild supersedes the earlier bundle/database artifact hashes above for the latest pack build. It does not change the source-snapshot digest or the identity-only product decision.

## Scope and limitations

The included market-presence sources cover AR, AU, CA, DE, ES, FI, GB, IE, LU, MY, NL, NZ, UA and US. They do not provide Russian or EAEU evidence. Ukraine is not an EAEU market. The pack contains no verified generations, production years, engine codes, gearbox codes, ECU fitment, PR-code fitment, DTC definitions, wiring diagrams or repair procedures. Presence of a make/model name in a foreign-market register is not proof of a vehicle configuration or technical applicability.

The new upstream release lists `de_kba_nfz` as attach-only in its source notes. It is excluded rather than treated as a complete fleet/count source. `il_mot`, `th_dlt`, `ch_tg` and `no_svv_pkk` remain excluded for the reasons recorded in the lock file.

VehiclesDB's published open-data policy warns that the dataset is not designed or warranted for safety-critical reliance. VAG TECH PRO therefore imposes a stricter product boundary: identity-only display, no repair-decision use and no safety-critical reliance. The desktop guard now checks these flags and derives expected model/evidence counts from the pinned manifest instead of retaining stale v2026.10.4 constants.

## Product disposition

- Separate research namespace only; production `vehicle`, `engine`, `transmission`, `ECU`, OEM and repair tables remain unchanged.
- Candidate rows remain `identity_candidate`; fitment remains `not_established`.
- No candidate is promoted to confirmed applicability.
- Preserve VehiclesDB attribution and every upstream source notice.
- Recheck the source license and exact upstream file hashes before any later refresh.

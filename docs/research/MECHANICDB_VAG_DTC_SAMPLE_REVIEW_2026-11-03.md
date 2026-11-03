# MechanicDB Audi/VW DTC sample — source and rights review (2026-11-03)

## Decision

The pinned free sample may be retained as a separate, ODbL-licensed research candidate pack. It is **not** approved OEM repair data. The Windows acquisition pipeline includes only two make-labelled DTC candidate rows (Audi P3000 and Volkswagen P1128), with source-file and source-line SHA-256 evidence. It excludes the community fix and replacement-part tables entirely.

## Source and rights

- Publisher: MechanicDB / MechanicDB-public.
- Immutable source revision: \`c788dfe9ed1517d4cd0be27f5aacb4776abf4864\`.
- Data licence: Open Database License (ODbL) v1.0.
- Documentation licence: CC BY 4.0.
- Upstream DTC code spine: Wal33D / Waleed Judah's MIT-licensed compilation; the MIT notice is preserved.
- The free sample's published licence permits commercial use, display, caching and redistribution subject to ODbL attribution, share-alike and open-reuse obligations. No paid/full database material is included.
- Source files and licence texts are pinned by Git blob SHA-1 and independently recorded by SHA-256 in the built pack.

The ODbL database remains a separate SQLite file. It is not merged into CC0 generic OBDex or CC BY-SA community UDS data.

## Included candidate rows

| Make label | DTC | Source line | Status |
|---|---|---:|---|
| Audi | P3000 | 77 | community reference candidate |
| Volkswagen | P1128 | 91 | community reference candidate |

The pack uses the namespace \`manufacturer_controlled_candidate\`, not \`manufacturer_specific_vag_verified\`.

## Exclusions and limitations

- Generic SAE/ISO DTC rows are excluded; they remain in the separate CC0 OBDex pack.
- All community repair/fix and replacement-part rows are excluded.
- No OEM part numbers, costs, labour estimates, test plans or repair procedures are included.
- No exact vehicle, model, generation, year, engine, gearbox, ECU, PR-code, VIN or market applicability is asserted.
- Market scope is \`UNKNOWN\`; applicability precision is \`manufacturer_make_candidate\`.
- Diagnostic execution is disabled. The pack remains hidden pending independent technical review.

## Promotion requirements

A candidate may be promoted only after an independent technical source confirms the DTC definition and the exact vehicle/ECU applicability. The ODbL attribution and share-alike terms must remain attached to the separate database. This source cannot be used to infer Skoda or SEAT coverage.

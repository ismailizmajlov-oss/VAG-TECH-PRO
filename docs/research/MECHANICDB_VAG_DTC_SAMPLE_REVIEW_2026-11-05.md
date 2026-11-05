# MechanicDB Audi/VW DTC sample and community repair leads — source review (2026-11-05)

## Decision

The free MechanicDB sample is retained as a separate ODbL v1.0 research database. It contains two make-labelled DTC candidates (Audi P3000 and Volkswagen P1128), six community-authored repair leads and six generic part-name candidates. The repair leads are visible only in the separate research namespace. They are **not factory procedures, not OEM-confirmed, not exact-vehicle applicable and not executable test plans**.

## Source and rights

- Publisher: MechanicDB / MechanicDB-public.
- Immutable upstream revision: \`c788dfe9ed1517d4cd0be27f5aacb4776abf4864\`.
- Data licence: Open Database License (ODbL) v1.0.
- Documentation licence: CC BY 4.0.
- DTC code spine: Wal33D / Waleed Judah MIT-licensed compilation; the MIT notice is preserved.
- The published free-sample terms allow commercial use, display, offline caching and redistribution under ODbL attribution, share-alike and open-reuse requirements. No paid/full-dataset content is included.
- The ODbL SQLite database remains separate from the CC0 OBDex generic DTC pack and the main production SQLite.

## Included records

| Namespace | Rows | Meaning |
|---|---:|---|
| Make-labelled DTC candidates | 2 | Audi P3000; Volkswagen P1128 |
| Community repair leads | 6 | Three authored leads for each candidate code |
| Generic part-name candidates | 6 | Names only; not OEM part numbers |

Every DTC, repair lead and part-name candidate retains source file, pinned revision, physical source line and SHA-256. The pack also retains the source-file, licence and attribution hashes.

## Display and safety boundary

- DTCs remain \`manufacturer_controlled_candidate\`, review status \`community_reference_unverified\`.
- Repair leads remain \`community_repair_lead\`, not \`repair_procedure\`.
- Part names remain \`community_part_name_candidate\`, not OEM part numbers.
- Market is \`UNKNOWN\`; applicability precision is \`manufacturer_make_candidate\`.
- No model, generation, year, engine, gearbox, ECU, PR-code, VIN or market fitment is asserted.
- No diagnostic execution, actuator command, test-plan promotion, OEM procedure or OEM part mapping is allowed.
- US cost/labour estimates and external Amazon search URLs are excluded.
- \`probability_rank\` is rendered as authored consideration order, not probability, likelihood or success ranking.
- Publisher difficulty labels are editorial labels, not OEM safety classifications.
- The Audi P3000 leads concern high-voltage systems and remain professional-only community references. They do not replace the manufacturer's lockout, zero-voltage verification or service procedures.

## Exclusions

- 75 generic SAE/ISO rows are not copied here; generic codes and their community guidance remain in separate generic namespaces.
- 13 non-VAG OEM rows are excluded.
- No paid MechanicDB tier is accessed or included.
- No content is promoted to verified VAG-specific repair guidance.

## Promotion requirements

Promotion to production repair data requires independent authoritative technical evidence for the DTC definition and exact vehicle/ECU applicability, plus separate verification of each procedure and any part mapping. The ODbL attribution and share-alike obligations remain attached to this separate research database.

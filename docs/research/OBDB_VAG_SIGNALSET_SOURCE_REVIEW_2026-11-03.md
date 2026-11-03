# OBDb VAG signal-set source review — 2026-11-03

## Decision

The OBDb project is a community-maintained vehicle-signal reference. The selected model repositories each publish an explicit CC BY-SA 4.0 license file. That license permits commercial reuse, display, caching, and redistribution, subject to attribution and ShareAlike. The adapted signal database is therefore kept as a separate CC BY-SA 4.0 SQLite pack; it is not merged into the CC0 OBDex database or the ODbL identity database.

The pack is reference-only. It never sends a diagnostic request to a vehicle and does not treat a community signal definition as factory-verified technical data.

## Pinned repositories and source scope

| Repository | Make/model | Pinned commit | Source commands | Source signals |
|---|---|---|---:|---:|
| https://github.com/OBDb/Audi-A4 | Audi A4 | c85ca605894dd4f839099077f13ad78192d81d14 | 31 | 31 |
| https://github.com/OBDb/Audi-Q7 | Audi Q7 | 8feee3fb4069a7c3be6841a70f1a06a4808e3261 | 639 | 684 |
| https://github.com/OBDb/Volkswagen-Golf | Volkswagen Golf | 9a5635d49244757d6385c2496b6c73275ccb730e | 63 | 89 |
| https://github.com/OBDb/Volkswagen-Passat | Volkswagen Passat | 7d6e052a1bf8dcea58e0eafda41187ae31ba45f0 | 688 | 729 |
| https://github.com/OBDb/Volkswagen-ID.4 | Volkswagen ID.4 | 6d8e86890fbb0dc02e233be2071369ba677a9b79 | 251 | 288 |
| https://github.com/OBDb/Seat-Tarraco | SEAT Tarraco | 084bbc5b300f1a7a0b656f342d99c3f7b49f3c02 | 643 | 659 |

The selected snapshots contain 2,315 UDS service 0x22 read-data commands and 2,480 signal records. The ECU header inventory contains 15 rows. The Golf source has five repeated signal IDs; those records are retained as separate command-scoped rows rather than deduplicated.

The Skoda-Octavia repository was inspected at commit 11bc46b92edcb0d2811fbb19bf858d7098a03535. Its current default signal set has zero commands and zero signals, so no empty pack was added. The separate ODbL identity candidate pack remains the only Skoda nameplate discovery source at this stage.

## Provenance and licensing

Each selected repository has a committed LICENSE file identifying Creative Commons Attribution-ShareAlike 4.0 International. The acquisition pipeline pins full commit SHAs and downloads only these paths from raw.githubusercontent.com at that exact commit:

- LICENSE
- README.md
- generations.yaml
- signalsets/v3/default.json

The pack retains all four upstream files, per-file SHA-256 values, the exact upstream license copies, repository URL, commit SHA/date, and row-level canonical JSON hashes. The generated SQLite database, its manifest, and attribution file are distributed separately from other data packs. The database is offered under CC BY-SA 4.0; no DRM or additional restriction is applied.

The generation YAML references Wikipedia pages. The pack preserves the source YAML and records generation labels/year ranges only as candidates; it does not import the long narrative descriptions or link signal rows to those generations.

## Applicability and safety limits

- Market scope is UNKNOWN for every selected repository.
- The repository name identifies a model-level community dataset only; it does not establish a particular generation, year, engine, gearbox, PR-code, ECU hardware/software version, VIN range, or Russian/EAEU specification.
- Source filter and debug-filter JSON are preserved verbatim and are not interpreted as fitment rules.
- All rows carry unverified_community_candidate status.
- Every command is service 0x22, but execution is disabled. The app may display the request identifier as reference only; it must not transmit it.
- This pack contains no DTC definitions, repair procedures, factory wiring diagrams, pinouts, torque specifications, adaptations, or maintenance schedules.
- A signal must be independently checked on the actual vehicle and controller before being used in a diagnostic test plan.

## Russian/EAEU OTTS gate

The public EAEU open-data portal describes OData reuse for resources published in its catalogue, but the catalogue review did not identify an OTTS resource. Rosstandart Order No. 2038 provides for publication of OTTS/vehicle-approval register information on an official website, but the order itself does not grant a commercial bulk-reuse, caching, or redistribution license for the registry database. Therefore Russian/EAEU OTTS source records remain permission_required and are not included in this pack.

References:
- OBDb organization and CC BY-SA 4.0 data notice: https://github.com/OBDb
- Example selected model repository and license: https://github.com/OBDb/Volkswagen-Passat
- Creative Commons BY-SA 4.0: https://creativecommons.org/licenses/by-sa/4.0/
- EAEU open-data resource catalogue: https://opendata.eaeunion.org/opendata/ru/resourses
- EAEU OData portal description: https://opendata.eaeunion.org/
- Rosstandart Order No. 2038 (OTTS registry publication fields): https://law.tks.ru/document/779154

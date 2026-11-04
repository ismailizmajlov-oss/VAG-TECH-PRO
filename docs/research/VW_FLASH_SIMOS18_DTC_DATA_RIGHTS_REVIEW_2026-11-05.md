# VW_Flash Simos18 DTC CSV — provenance and rights review (2026-11-05)

## Decision

`bri3d/VW_Flash` contains a potentially useful VAG ECU-family DTC CSV (`data/dtcs.csv`, 657 data rows). The repository declares BSD 2-Clause for its software, but the reviewed commit and README do not establish the CSV's independent origin, author or data licence. The README also documents extraction of factory Simos12/Simos18 ODX containers. The CSV may therefore contain OEM ODX-derived material; that risk is not proven, but it is material.

**Decision: quarantine. No rows are imported, displayed, cached, used for repair advice or bundled.** Do not infer that the repository's BSD-2-Clause software licence clears the underlying dataset.

## Evidence

- Repository: https://github.com/bri3d/VW_Flash
- Repository README: https://github.com/bri3d/VW_Flash/blob/master/README.md
- Repository licence: https://github.com/bri3d/VW_Flash/blob/master/LICENSE
- DTC CSV: https://github.com/bri3d/VW_Flash/blob/master/data/dtcs.csv
- Commit adding the DTC CSV: https://github.com/bri3d/VW_Flash/commit/c8376416c4df7f12789679fb216c47b6e795ffc8

The reviewed repository licence is BSD 2-Clause and names Brian Ledbetter and contributors. The DTC CSV was added in commit `c8376416c4df7f12789679fb216c47b6e795ffc8` on 2021-11-09 with commit message `add DTC support`. That commit adds 658 lines to `data/dtcs.csv` (one header plus 657 data rows) and adds code that reads the CSV to describe ECU-reported DTC IDs. The commit provides no source attribution for the CSV rows.

The CSV fields are `code`, `pcode`, `name`, and `symbol`. The `symbol` values include internal-looking `SV_ERR_SYM_...` identifiers. The README describes extraction of factory Simos12/Simos18.1/Simos18.10 ODX containers, but does not state whether the DTC CSV is derived from those containers or identify a separate data source.

## Rights assessment

| Question | Finding |
|---|---|
| Repository software licence | BSD 2-Clause |
| Separate licence for `data/dtcs.csv` | Not established |
| Per-row source/provenance | Not supplied in the reviewed commit |
| Author's authority to license any underlying OEM-derived content | Not established |
| Commercial reuse / display / offline cache / redistribution | Not cleared for the dataset |
| Product import | Blocked |

A permissive repository software licence does not prove that the author owns or can sublicense any underlying OEM ODX-derived data. A DTC CSV containing internal VAG symbols is not automatically public-domain or freely redistributable.

## Applicability limits

The README describes Simos18.1/6 and Simos18.10 contexts, but the CSV has no per-row ECU part number, HW/SW revision, vehicle generation, model year, market, engine or gearbox binding. Therefore:

- retain this only as a Simos18-family candidate source lead;
- do not label any row as exact VAG ECU fitment;
- do not promote any row to verified VAG-specific DTC;
- do not merge P-code-shaped entries into the generic SAE/ISO DTC namespace;
- do not generate test plans, repair advice or diagnostic execution from these rows.

## Required before reconsideration

Obtain from the repository author:

1. the original source for each data group or a reproducible extraction method that identifies the source files and their rights;
2. confirmation whether the CSV was derived from Volkswagen/Audi factory ODX/PDX containers or other proprietary diagnostic material;
3. an explicit data-specific licence or written permission covering commercial use, offline caching, display in a third-party Windows application, updates and redistribution;
4. per-row ECU/HW/SW applicability evidence if the data is to be used for technical lookup.

Until all four are resolved, keep the source quarantined. The source register records the upstream commit and Git blob SHA-1 only; no local source snapshot was downloaded, so no SHA-256 snapshot is claimed.

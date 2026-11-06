# VW_Flash Simos18 DTC CSV — rights and provenance review (2026-11-06)

## Candidate

Repository: https://github.com/bri3d/VW_Flash  
Pinned commit introducing DTC support: c8376416c4df7f12789679fb216c47b6e795ffc8 (2021-11-09, “add DTC support”)  
File: data/dtcs.csv  
Observed shape: 657 data rows; columns code, pcode, name and symbol. The CSV is consumed by the repository's Simos18 DTC handling code.

## Integrity record

All hashes below were computed from UTF-8 bytes returned by the pinned GitHub file-content response. The Git blob SHA-1 identifiers match the upstream tree entries.

| File | Git blob SHA-1 | SHA-256 |
|---|---|---|
| data/dtcs.csv | e5c65fff0c6f0d98aafb082ff1acefa483be016e | 20f843763fafdb60b72296a8f6003512ee75970291b8a31ec59c40d74b4cc312 |
| LICENSE | 78fe76374aca450843661a30406a363e7a2ae93b | d08b7d9656eb0c078ebc71926be5a6c3fecb36f695e4d01105ba9f3b917d6ccc |
| README.md | 830a60eef56dd7d22b04250cdb5b87accc1205b4 | 4c788f80552b482c904fa76d7024d8e4772599fddfbc93c1951354d1ecdd7609 |

The data file has 60,369 upstream bytes and 657 data rows. No row-level source attribution was found in the reviewed README or in the commit that adds the CSV.

## Rights assessment

The repository declares BSD-2-Clause for its software. That is not sufficient by itself to establish the author's authority to license every item in a data file that may be derived from third-party OEM material.

The README documents extraction of factory Simos12/Simos18 ODX containers. This does not prove that data/dtcs.csv was copied from a restricted ODX package, but it makes the CSV's origin a material provenance question. The CSV contains internal-looking Simos18 symbols and does not identify the source document, revision, licence or rights holder for each row.

The following are therefore not established for the CSV dataset:

- permission for commercial use;
- permission for bulk reuse;
- permission for offline caching;
- permission for display in VAG TECH PRO;
- permission for redistribution;
- authority to relicense any OEM-derived content.

A repository-level software licence cannot be treated as independent proof of rights in potentially OEM-derived DTC data.

## Technical applicability limits

- The data is associated with a Simos18 ECU-family tool context, not a complete VAG DTC catalogue.
- No exact ECU part number, hardware/software revision, model generation, model year, market, engine code or gearbox code is attached to each row.
- P-code-shaped values are not automatically generic SAE/ISO definitions. The CSV remains in its own candidate namespace.
- No repair procedure, approved test plan or diagnostic execution is authorized by this dataset.

## Decision

**Quarantine: no import, no display, no offline cache and no redistribution.** Keep the source only as a research lead. Reconsider only after the data author supplies a written provenance statement identifying the origin of the CSV and evidence of rights covering commercial use, display, offline caching and redistribution. If the CSV is derived from OEM ODX material, the necessary rights must cover that underlying material as well.

No rows from this source have been copied into any VAG TECH PRO SQLite database.

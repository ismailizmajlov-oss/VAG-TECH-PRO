# Windows offline data-pack rights filter — 2026-11-03

The Windows x64 offline data bundle contains only four separately licensed SQLite packs:

| Pack | License | Boundary |
|---|---|---|
| OBDex generic OBD-II | CC0-1.0 | Generic SAE/ISO codes and PIDs only; no VAG attribution or vehicle fitment |
| VehiclesDB identity | CC BY 4.0 | Make/model names and market-presence candidates only; no generations, years or engine/gearbox codes |
| VAG identity candidates | ODbL-1.0 | Candidate model/generation/engine descriptions; market UNKNOWN; no factory codes or exact pairings |
| OBDb UDS signals | CC BY-SA 4.0 | Community signal candidates; market UNKNOWN; no exact ECU fitment; command execution disabled |

## Excluded manufacturer DTC source

The Wal33D Volkswagen/Audi candidate pack is excluded from the distributable bundle. The upstream repository has a repository-level MIT notice, but no separate data-specific rights statement was established for the manufacturer DTC records. That is insufficient to confirm commercial display, local caching and redistribution. The builder does not download, assemble or index this source as part of the Windows data bundle.

No manufacturer-specific VAG DTC dataset is included. Generic OBDex records remain in the generic namespace and are never relabeled as VAG-specific. No DTC-to-vehicle fitment or test plan is inferred.

## Verification gates

- The builder accepts exactly the four pack IDs listed above.
- Each pack retains a separate SQLite file, license, attribution, source revision and SHA-256 provenance.
- The Windows workflow compiles the assembler and verifier, runs the rights-registry unit tests, builds the pack, reopens every SQLite file read-only, checks integrity/foreign keys and validates pack hashes/counts.
- The output is a data bundle only, not an installer.

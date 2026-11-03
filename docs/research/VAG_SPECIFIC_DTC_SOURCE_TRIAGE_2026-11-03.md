# VAG-specific DTC source triage — 2026-11-03

## Purpose

Separate sources that can lawfully be cached in the Windows offline product from repositories that are merely useful for research. A repository-level license is not treated as proof that a contributor had rights to relicense third-party material.

## OpenVAG — excluded from data import

Repository: https://github.com/riz4d/OpenVAG

- The repository declares MIT for the project code and accompanying files.
- Its README and `db/README.md` describe a SQLite database with 995 DTC code/title rows, 1,103 variants, 341 component identifiers and 712 DTC/component links.
- Pinned default-branch commit: `407d5e042cf46d55087ed4ae4e056605f2b04f08`; recursive Git tree: `d9101f504ef15d522c8f4f517cc96471bcac1619`.
- The complete current tree contains `db/schema.sql`, `db/README.md` and API code, but zero `.sqlite`, `.db` or `.sqlite3` blobs and no seed-data directory.
- GitHub releases: zero.
- The documented schema has no row-level source/license field. The README's claimed row counts cannot be independently inspected or hashed from the pinned Git tree.
- The MIT LICENSE does not establish the license or provenance of the described DTC database contents.

Decision: **do not import**. The MIT project license is recorded for code, but there is no actual data snapshot, row-level provenance or separately established database-data license to verify. Re-evaluate only if the author publishes a data artifact with an explicit data license and source evidence.

## AutoDiag2 database — excluded unless row-level source rights are established

Repository: https://github.com/autodiag2/database

- The repository explicitly declares ODbL-1.0 for the database and DbCL-1.0 for database contents; source code is GPL-3.0-or-later.
- It provides YAML records with `evidence` fields and a generated SQLite release.
- The inspected Audi record `data-src/ecu/generic/audi/codes/P1004.yml` attributes its evidence to `obdcodex`, but does not provide a dataset-specific reuse license or a direct source URL. The upstream OBDCodeX material is not shown to be CC0, MIT or otherwise licensed for commercial offline redistribution.
- Several ECU metadata records cite third-party tuning-tool compatibility-list PDFs. Those references do not grant redistribution rights for the PDF contents.

Decision: **do not import the affected rows**. ODbL/DbCL on the repository cannot be treated as a blanket grant over third-party content that the repository contributors may not own. Re-evaluate only individual records whose underlying source and commercial display/cache rights are independently confirmed.

## Generic OBD-II — eligible but separate

OBDex: https://github.com/foerbsnavi/OBDex

- The upstream repository explicitly identifies the data as CC0-1.0 and tooling as MIT.
- It deliberately covers generic SAE/ISO OBD-II DTCs and excludes manufacturer-specific definitions.
- It is suitable for a separate generic DTC namespace only; it must not be relabelled as VAG-specific and must not establish VAG model/engine/ECU applicability.

The existing Windows pack keeps this dataset separate from VAG-specific candidate sources.

## VAG-specific community candidates

OBDb source: https://github.com/obdb/

- The upstream project documents CC BY-SA 4.0 for most contributed text.
- Its vehicle repositories are useful for open diagnostic signal and PID candidates.
- A record still needs its own repository, revision, license evidence, vehicle/year scope and row hash. A generic make-level signal definition is not an exact model/engine/ECU fitment statement.

The existing OBDb pack remains a separate CC BY-SA research dataset. It is not promoted to factory DTC, repair procedure, pinout or torque data without record-level evidence.

## Product import rule

A VAG-specific DTC record may be published only when all of the following exist:

1. an immutable upstream snapshot and SHA-256;
2. a license that explicitly permits commercial display, offline caching and redistribution of the actual data;
3. row-level source evidence and a source revision;
4. a clear DTC namespace (VAG numeric, manufacturer-specific P/B/C/U, UDS DTC, or generic SAE/ISO);
5. a separate applicability record with make/model/generation/year/engine/ECU scope and an explicit precision/status;
6. independent review before changing status from candidate to verified.

Until then, keep the record out of the production SQLite catalogue or in a clearly isolated research-only pack that the repair UI cannot present as confirmed guidance.

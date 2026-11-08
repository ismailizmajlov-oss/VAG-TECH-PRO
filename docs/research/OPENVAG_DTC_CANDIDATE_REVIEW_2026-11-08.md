# OpenVAG DTC project — candidate review (2026-11-08)

## What the repository claims

Repository: https://github.com/riz4d/OpenVAG  
Reviewed default-branch revision: `407d5e042cf46d55087ed4ae4e056605f2b04f08`

The README and `db/README.md` describe a SQLite dataset containing 995 DTC code/title combinations, 1,103 variants, 341 VAG component identifiers, 712 DTC-component links and 276 related-code references. The schema includes legacy five-digit VAG codes, combined VAG/OBD formats, OBD-II P-codes, and B/C/U examples.

The repository's `LICENSE` is MIT. That verifies a permissive licence for the repository's software code, but does not automatically grant rights to a separate/generated database whose content and provenance are not included.

## Availability and reproducibility findings

- `.gitignore` explicitly excludes `db/openvag.db` with the comment "Database (regenerated from scripts)".
- No `db/openvag.db` binary is tracked in the reviewed default branch.
- `app/main.py` tells the user to run `python scripts/init_db.py` when the database is missing, but `scripts/init_db.py` is absent from the reviewed branch.
- `db/schema.sql` defines the tables but contains no DTC seed records.
- Searches of the reviewed repository found no `INSERT INTO dtc_codes` / `INSERT INTO dtc_variants` seed data and no source attribution or per-record provenance for the claimed database contents.
- The linked `docs/DEVELOPMENT.md` is also absent from the reviewed branch.

## VAG TECH PRO decision

Registered as `openvag-dtc-api-project`, metadata-only. The code may be reused under MIT with the required copyright notice, but the claimed DTC database is unavailable and its data licence, origin, attribution, storage rights, display rights and redistribution rights are not established. No records were downloaded, hashed, copied, cached or imported. The 995/1,103 figures are upstream claims, not verified local row counts.

Reconsider only after the maintainer provides the actual database snapshot, its SHA-256, reproducible seed/build scripts, source-level provenance for the DTC records and an explicit licence covering the data itself (including offline storage and redistribution). Do not infer VAG ECU applicability from the repository name or code format.

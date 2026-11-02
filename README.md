# VAG TECH PRO

Non-commercial technical knowledge base and repair-workflow project for Volkswagen Group vehicles, initially focused on the Russian market.

## Evidence and safety principles

- Keep generic SAE/ISO OBD-II definitions separate from manufacturer-specific VAG diagnostics.
- Never infer engine, transmission, ECU, PR-code, VIN fitment or repair-procedure applicability.
- Preserve source revision, hashes, scope and data license for every research snapshot.
- Do not promote research imports into production without technical review and confirmed reuse rights.
- Wal33D is inspected only in a temporary quarantine; its repository MIT license is not treated as a data license.

## Current repository bootstrap

The GitHub repository has been initialized. The next commit adds a self-contained GitHub Actions workflow for acquiring and auditing OBDex generic DTC/PID snapshots and performing an exact-identifier comparison with the pinned Wal33D candidate. The complete application source package is maintained separately in the current development workspace and is not yet mirrored here.

## Research workflow

Workflow: `.github/workflows/acquire-dtc-research.yml`

It runs on the workflow-file push to `main` and can be run manually. It downloads OBDex data and its `CC0-1.0` data license, validates the advertised corpus size, imports only generic records into a separate research SQLite database, and produces an exact-code overlap report against the pinned Wal33D database and Audi/VW text files.

The Wal33D database is downloaded only to an ephemeral GitHub runner for read-only inspection. Its binary is not included in artifacts or imported. The report contains aggregate audit results, not copied manufacturer definitions.

## Important limitation

OBDex covers generic SAE/ISO definitions only. It does not establish VAG ECU-specific applicability, vehicle-generation fitment or factory repair procedures. The repository is not yet a complete installable Windows application.

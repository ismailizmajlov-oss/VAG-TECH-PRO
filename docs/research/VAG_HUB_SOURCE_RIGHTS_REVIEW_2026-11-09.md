# VAG-Hub workshop-document aggregator — rights and provenance review (2026-11-09)

## Decision

Do not ingest or reproduce material from VAG-Hub in VAG TECH PRO. The site exposes VAG-labelled DTC tables, workshop manuals, wiring diagrams, fuse/relay diagrams, ELSAWin/ETKA material, TPI reports and firmware/Dataflash downloads. The reviewed pages do not establish a data-specific licence, a rightsholder chain for the underlying OEM material, or row-level provenance. A statement that content was gathered from public sources is not a licence to reproduce or redistribute it.

The source is registered as `vag-hub-workshop-document-aggregator` with `permission_status=not_cleared`, `data_ingested=false`, `product_import_allowed=false` and `source_snapshot_sha256=null`. It is excluded from every product and offline research pack.

## Evidence reviewed

- [VAG-Hub about page](https://www.vag-hub.com/about/) — describes a VAG technical-document collection, says materials are compiled from publicly available sources and acknowledges that some information may have been edited or changed without the publisher's knowledge.
- [ELSAWin / ETKA / ETOS page](https://www.vag-hub.com/vag-programs/elsawin/) — describes ELSAWin as a dealer repair/service-information system, lists wiring diagrams and parts catalogues, and recommends purchasing original catalogues from Volkswagen AG for intended use.
- [Dataflash / TPI page](https://www.vag-hub.com/vag-programs/dataflash-vag/) — lists VAG firmware/Dataflash and TPI downloads and instructs users to delete downloaded files after reading. That instruction does not grant VAG TECH PRO a right to cache, display or redistribute the material.
- [VAG DTC table](https://www.vag-hub.com/vw-audi-seat-skoda-dtc/) — publicly displays decimal and hexadecimal legacy identifiers, OBD-II-shaped codes and Russian descriptions. The reviewed table did not provide per-row primary-source citations, source revisions, evidence locators or a dataset licence.

Review date: 2026-11-09. No files, manuals, PDFs, firmware, database exports or page snapshots were downloaded. No account was created, no paid terms were accepted and no automated collection was performed. No source-file SHA-256 is claimed because no source bytes were acquired.

## Rights assessment

The reviewed pages do not establish:

- a licence covering the underlying OEM text, diagrams, tables, firmware or service documents;
- the publisher's authority to sublicense those materials;
- commercial reuse or third-party display rights;
- persistent local SQLite storage or offline caching rights;
- bulk extraction or redistribution rights for a Windows installer or its updates;
- record-level source provenance sufficient to audit individual technical claims.

The site's public-source statement and free-download availability are not substitutes for permission from the relevant rightsholders. The page's suggestion to purchase original catalogues reinforces that the original OEM materials remain separately controlled.

## Technical and applicability boundary

The visible DTC table combines legacy decimal/hex identifiers and SAE-shaped codes. A code's syntax does not prove that it is VAG-specific. No inference is allowed from this table to:

- a verified VAG DTC namespace or ECU;
- a particular model, generation, model year, market or production date;
- an engine or gearbox code, or an exact engine/gearbox pair;
- a wiring diagram, pinout, torque value, adaptation, service interval or repair procedure.

Even if a future rightsholder grants permission, every imported record must retain its own source document, revision, exact locator, content hash, market scope, applicability precision and independent technical-review status.

## Project action

The central source register and a regression test explicitly quarantine this source. Do not scrape or copy the visible table, download the offered repair materials, use firmware/TPI files, or convert the site into a local database. Reconsider only after written permission from the actual rightsholders and the site operator expressly covers commercial use, local storage, offline display, updates and redistribution, and after record-level provenance can be verified.

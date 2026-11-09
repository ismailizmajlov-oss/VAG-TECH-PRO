# Bolidenforum VAG engine, transmission and PR-code reference — rights review (2026-11-09)

## Finding

A public Bolidenforum.de reference index exposes three potentially useful VAG lookup tables:

- [VAG Engine Code Database](https://www.bolidenforum.de/portal/en/vag/engine/) — publisher page claims 966 engine-code entries with description, power, years and vehicle names.
- [VAG Transmission Database](https://www.bolidenforum.de/portal/en/vag/transmission/) — publisher page claims 19 transmission/type-family entries with type, gear count, clutch and vehicle names.
- [VAG PR Code Database](https://www.bolidenforum.de/portal/en/vag/pr-code/) — publisher page claims 138 plain-text PR/option-code descriptions.

The public index pages were reviewed on 2026-11-09. The transmission table contains family/type labels such as 01J, DL501, DQ200, MQ250 and ZF8HP; the page's count of 19 must not be described as 19 complete gearbox-code variants. No engine-to-gearbox pairings were established.

## Rights decision

The engine and transmission pages display the footer notice **“Urheberrecht © 2026 Alle Rechte vorbehalten.”** No open data license, bulk reuse grant, API terms or offline redistribution permission was identified in the reviewed pages.

Therefore:

- permission status: `not_obtained`;
- data license: `all_rights_reserved_no_open_license_found`;
- bulk extraction, local SQLite caching, offline display, derived-fact export and redistribution: `not_established`;
- redistribution: not allowed unless separately authorized in writing;
- source bytes were not downloaded; no source snapshot SHA-256 is claimed;
- no rows were scraped, imported, cached or displayed in VAG TECH PRO.

A future written permission must explicitly cover bulk extraction, durable local storage, offline end-user display, derived facts, inclusion in installer/update packages, redistribution, commercial/non-commercial use, attribution and retention of source revisions. Permission to browse the public pages alone is insufficient.

## Applicability and quality limits

This is a secondary reference, not a primary Volkswagen Group source. No row-level primary citations were visible. The engine index can only be considered an engine-code candidate list after rights clearance and independent verification. The 19 transmission entries are broad transmission type/family records and do not establish exact three-letter gearbox codes, production ranges or exact engine/gearbox pairings. PR-code descriptions do not prove that a code belongs to a particular vehicle.

The dataset has no confirmed RU/EAEU market scope. No generation, model-year, VIN, ECU, DTC, repair-procedure, wiring, pinout, torque, adaptation or service applicability is inferred.

## Product decision

Register the source as metadata-only and quarantined. Do not download, scrape, import, cache, display or redistribute its rows until written reuse permission is obtained. If permission is later granted, retain raw source snapshots, SHA-256, upstream revision, per-row locators and separate technical-review status; never promote secondary-source candidates directly to verified factory applicability.

## Primary observations

- https://www.bolidenforum.de/portal/en/vag/engine/
- https://www.bolidenforum.de/portal/en/vag/transmission/
- https://www.bolidenforum.de/portal/en/vag/pr-code/

Review date: 2026-11-09.

# ASTRA / FEDRO TAS open-data source review — 2026-11-06

## Decision

The Swiss Federal Roads Office (FEDRO / ASTRA) publishes its current Type Approval System (TAS) vehicle-type records as Open Government Data. The official FEDRO newsletter dated 23 February 2026 explicitly says that all listed type-approval data products are free to use as OGD and that FEDRO must be cited. This is a rights-cleared source for a separate **Switzerland-only** homologation research pack, subject to the exact source scope and attribution below.

This does **not** clear Russian or EAEU OТТС. Swiss type approvals must never be represented as Russian/EAEU approvals, and a type approval is not an individual VIN build sheet.

## Primary evidence

- [FEDRO vehicle-data newsletter, 23 February 2026](https://opendata.astra.admin.ch/ivzod/5000-Newsletter/2026_1/Newsletter_Fahrzeugdaten_1_2026_EN.pdf): pages/lines describing the TAS files, the passenger-car index, monthly updates, free OGD use and mandatory FEDRO attribution.
- [Official ASTRA vehicle-data page](https://www.astra.admin.ch/de/fahrzeugdaten): identifies vehicle-type data as freely available Open Government Data and says users must handle data carefully and professionally.
- [Swiss Open Data FAQ](https://opendata.swiss/en/faq): says data is free to access without registration and may be used commercially unless a dataset states otherwise.
- [EMBAG / EMOTA Art. 10](https://www.data-sharing.ch/en/index1): federal legal basis for publication of open government data, subject to statutory exceptions.
- [ASTRA TAS data directory](https://opendata.astra.admin.ch/ivzod/4000-Typengenehmigungen_TAS/): public machine-readable data directory.
- [ASTRA TAS JSON schema](https://opendata.astra.admin.ch/ivzod/4000-Typengenehmigungen_TAS/4250-json-Schema/govServices_TypeApproval_Schema.json).

## What is available

The FEDRO newsletter states that:
- more than 200,000 third-generation type approvals have individual bilingual JSON files with English attribute names;
- a passenger-car index is available as XLSB, while CSV files are available for the broader automobile group;
- the separate emissions dataset can contain one to four gearbox variants for an automobile, with each gearbox represented on a separate row;
- the data products are updated monthly;
- previous records are overwritten when approvals change;
- holder codes are not disclosed; and
- current-generation data sheets are not offered as PDF prints.

The probe workflow will fetch the official passenger-car index, JSON schema and a small set of public VAG-group approval records. It records source hashes and field names before any production-facing import is attempted.

## Rights and attribution

Approved uses for the published OGD products:
- display in VAG TECH PRO;
- offline caching in the local research database;
- transformation and filtering into a separate VAG/CH research pack;
- redistribution of the derived pack under the OGD reuse conditions; and
- commercial use, with FEDRO attribution.

Required attribution:

> Source: Federal Roads Office (FEDRO/ASTRA), Type Approval System (TAS) open data.

The OGD decision applies only to the published open-data products. It does not extend to fee-based datasets, personal/holder information, unrelated ASTRA portals, third-party websites, or copyrighted manufacturer repair material. No paid access, account, contract or external credential is required for the listed open-data files.

## Applicability boundaries

- Market scope is **CH** only.
- The approval record is the highest initial applicability level. Type, variant and version are usable only when explicit in the source record.
- Engine and gearbox codes are not considered verified until the schema probe identifies the exact fields and their parent/row relationship.
- If several gearbox variants are present, preserve each explicit row/link. Never cross-join all engines with all gearboxes.
- Model year, generation, production date and VIN-level fitment are not inferred from an approval number or first-registration date.
- This source does not provide VAG DTCs, ECU definitions, repair procedures, wiring diagrams, pinouts, torque values or adaptation instructions.

## Import plan

1. Probe the official XLSB index, JSON schema and a small VAG sample; record SHA-256, source date and exact field paths.
2. Build a Windows CI acquisition step that filters only exact VAG make names from the official passenger-car index.
3. Fetch only the corresponding individual ASTRA JSON records and, where needed, the exact linked emission/gearbox rows.
4. Import into a separate read-only SQLite research pack with source ID, snapshot, record URL, per-file SHA-256, CH market scope, approval/variant/version and explicit applicability precision.
5. Add desktop search for this CH research pack only after integrity, provenance and no-cross-join tests pass.

No ASTRA record has been imported into the product database by this review. The field-level probe is the next implementation step.

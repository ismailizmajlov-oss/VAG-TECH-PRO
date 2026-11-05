# Owner action: request lawful FGIS / EAEU OTTS data access and reuse rights

**Status:** draft only — not sent. No account has been created, no paid access accepted, and no source data has been downloaded or imported.

This request is intended for the owner to submit to the competent Rosstandart / FGIS registry operator and, where applicable, the authorized EAEU registry operator. The requester’s legal name, contact details and intended distribution model must be completed and approved by the owner before sending.

## 1. Requested data scope

Please confirm whether the operator can provide a machine-readable, versioned export or documented API for electronically issued vehicle type-approval records relevant to:

- Russian Federation and EAEU market scope under TR TS 018/2011;
- OTTS and EOTTS records, including amendments/supplements and validity/status history;
- vehicle make, commercial name, type, base vehicle/chassis, modifications, category, environmental class, approval/form identifiers, issuing body, validity dates and publication dates;
- where legally and technically available, the Annex 1 technical attributes needed to establish exact powertrain applicability: engine manufacturer/type/designation/code, displacement, rated power, fuel, emissions family, transmission manufacturer/type/designation/code, driven axles, vehicle modification/variant/version, and the relationship between each engine and transmission option.

Please provide the field dictionary, field numbers, null/unknown semantics, record identifiers, revision identifiers, update cadence, market scope and historical-retention policy.

## 2. Rights that must be expressly confirmed

For every supplied field and every source document, please identify the applicable license or written permission and confirm whether the intended use permits all of the following:

1. acquisition of the export through the documented official method;
2. parsing and normalization into a local SQLite database;
3. persistent local storage and caching on Windows 10/11 x64 devices;
4. display of source-derived fields to end users inside VAG TECH PRO;
5. creation and distribution of offline application/database updates;
6. retention of source provenance, revision identifiers and source hashes;
7. creation and distribution of derived indexes and normalized factual relationships;
8. redistribution to users as part of a non-commercial offline repair-information product;
9. backup and restore of the locally stored dataset;
10. refreshes and replacement of prior dataset revisions.

Please state any restrictions on user count, territory, duration, attribution, redistribution, commercial use, derived databases, retention and onward sharing. A public search page or a public-search obligation is not by itself treated as permission for automated bulk collection, caching or redistribution.

## 3. Separate treatment of Annex 2 and Annex 1

The reviewed public Annex 2 search map contains 28 identity/status fields for electronically issued records. It does not expose engine/gearbox technical designations or codes, ECU identifiers, DTC, repair procedures or wiring data. Annex 2 metadata alone therefore cannot establish exact engine/gearbox pairs.

The Annex 1 PDF reference is not the PDF binary and is not a redistribution grant. If Annex 1 contains the technical attributes required for exact powertrain mapping, please separately confirm:

- whether Annex 1 technical fields can be supplied as structured data;
- whether the fields may be stored, displayed, cached and redistributed offline;
- whether Annex 1 PDF binaries may be retained or redistributed, and under what terms;
- whether a field-level license/permission can be issued without licensing the entire PDF.

The VAG TECH PRO importer currently accepts only explicitly classified OTTS/EOTTS records from the electronically issued Annex 2 public-search namespace. It rejects OTSH/EOTSH, SBKTS/ESBKTS, cancellation notices, non-electronic records and all engine/gearbox/ECU/repair fitment claims. This restriction will remain until the relevant source rights and technical field scope are confirmed.

## 4. Provenance and update requirements

For each delivered export, please provide:

- source/product identifier and official URL;
- source revision or extraction timestamp;
- market and document-type scope;
- exact field dictionary/revision;
- export format and encoding;
- record count and any exclusions;
- SHA-256 or another reproducible integrity mechanism, if available;
- attribution text and license/permission reference;
- update/change-log semantics and correction policy.

VAG TECH PRO will preserve source-level and row-level provenance, source revision, market scope, applicability precision and verification status. Unconfirmed relationships will remain candidates and will not be represented as factory-confirmed fitment.

## 5. Explicit exclusions

This request does not authorize or request:

- use of credentials belonging to another person or organization;
- bypassing authentication, access controls or rate limits;
- undocumented endpoints or automated browser imitation;
- scraping of a public website where the terms prohibit it;
- purchase or acceptance of paid terms without the owner’s separate approval;
- copying or redistributing PDF binaries without separate rights;
- production deployment or commercial distribution before legal review.

## 6. Owner completion before submission

- Requesting legal entity: **[owner to complete]**
- Authorized contact: **[owner to complete]**
- Intended first-release distribution: **non-commercial offline Windows 10/11 x64 application**
- Intended territory: **Russian Federation / EAEU**
- Intended user scope: **[owner to complete]**
- Requested license/permission reference: **[operator to provide]**

**Do not send this draft or accept any terms until the owner has reviewed and approved the completed request.**

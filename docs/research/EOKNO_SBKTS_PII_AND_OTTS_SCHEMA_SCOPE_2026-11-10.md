# Kazakhstan EOKNO: indexed SBKTS PII and EAEU register-field scope review

**Review date:** 2026-11-10  
**Decision:** discovery only; no source bytes or record data imported.

## What was newly observed

The search-indexed public page for the Kazakhstan EOKNO register, `https://eokno.gov.kz/public-register/register-ktrm2.xhtml`, exposes filters for registration number, EAEU/KZ scope, VIN, status, dates, document type, applicant, application number and document format. Its indexed preview rows are labelled as SBKTS. The preview visibly includes VIN and applicant identity fields.

The live page could not be independently fetched during this review. No result record was downloaded, no page snapshot was created, and no VIN, applicant name, identifier, address or contact value was copied into VAG TECH PRO. The indexed preview is not a verified corpus count and is not evidence of an OTTS record or VAG fitment.

## Legal schema distinction

EEC Collegium Decision No. 225 of 2014-12-02:

- **Section 8 — OTTS/OTSH:** lists approval metadata such as approval number, validity, make, commercial name, vehicle type, modification, category and environmental class; it also refers to information contained in approval annexes.
- **Section 9 — SBKTS:** explicitly lists technical fields including engine make/type, cylinder layout, displacement, power, fuel, transmission, gearbox make/type and clutch make/type.

The explicit engine/gearbox field list in section 9 must not be attributed to OTTS. Section 8's reference to annexes does not prove that the public EOKNO list exposes engine/gearbox codes or that an individual OTTS record contains a usable factory-code pairing.

## Rights and import decision

No dataset-specific licence or written permission for bulk extraction, automated acquisition, offline caching, third-party display or redistribution was found. Public lookup visibility is not a reuse grant. The EOKNO source remains `permission_required`, `data_ingested=false`, and `product_import_allowed=false`.

The existing EAEU importer continues to accept only the OTTS document kind under its explicit schema rules, skips SBKTS records, and excludes VIN/applicant/authority/manufacturer identity fields from the staging schema. No production SQLite changes were made.

## Evidence

- EOKNO public register (indexed preview; live retrieval unavailable): https://eokno.gov.kz/public-register/register-ktrm2.xhtml
- EEC Collegium Decision No. 225, 2014-12-02: https://old.adilet.zan.kz/rus/docs/H14EK000225
- Official KTRM workflow notice, 2023-12-28: https://www.gov.kz/org/mti-ktrm/press/news/details/679816?lang=ru

## Regression coverage

The source manifest now records the indexed PII boundary and the section 8/section 9 distinction. A regression test prevents the EOKNO preview from being treated as OTTS fitment evidence or as an importable data source.

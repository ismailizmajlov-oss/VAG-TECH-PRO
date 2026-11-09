# Rosstandart Order 2038 — FGIS OTTS/OTSH schema boundary

**Review date:** 2026-11-10  
**Evidence quality:** secondary republication of the current Order No. 2038 text; the primary official signed copy was not retrieved.  
**Decision:** schema discovery only; no FGIS record, OTTS PDF, SBKTS record, VIN, applicant identity or document bytes imported.

## What the current Order 2038 text specifies

Order No. 2038 dated 2025-09-24 requires the FGIS database to use the Annex 1 attribute inventory from 2025-10-01 and requires the Rosstandart official site to publish/search the Annex 2 fields for electronically issued records. Order No. 2335 dated 2025-10-30 adds internal resumption fields 86/87 and public cancellation-notice fields 27/28.

The text was reviewed through a secondary republication: [TKS current text of Order No. 2038](https://law.tks.ru/document/779154). The official signed copy and the live Rosstandart search endpoint remain unresolved; the repository's source register retains that limitation.

## OTTS/OTSH internal FGIS attributes — Annex 1

- Fields 50–54 are structured engine descriptors: engine make/type, displacement, fuel, fuel-supply system and ignition system.
- Fields 49 and 80 are PDF document routes: Annex 1 PDF text and the full OTTS/OTSH PDF.
- The OTTS/OTSH internal field inventory has no dedicated structured gearbox make/type field.
- Approval validity dates and approval dates are document dates, not vehicle model year.

Consequently, a raw engine make/type value is a homologation descriptor, not automatically a VAG three-letter engine code. A gearbox description may exist in the filled Annex 1/full PDF, but it is not a structured OTTS/OTSH field in this FGIS inventory.

## SBKTS is a separate, excluded schema

The separate SBKTS/ESBKTS field list includes transmission (field 63), clutch make/type (field 67) and gearbox make/type (field 68). It also includes VIN (field 15), production year (field 16) and personal identity fields (21 and 28). These are individual-vehicle safety-certificate fields, not OTTS type-approval fields. They must not be used to infer a factory OTTS engine/gearbox pairing, and their VIN/PII-bearing records are excluded from this import path.

## Public-site Annex 2 fields

Annex 2 contains 28 public-search fields for electronically issued OTTS/EOTTS and OTSH/EOTSH records. It exposes approval identifiers, dates/status, certification-body information, make, commercial name, type, base vehicle/chassis, modifications, category, environmental class and a PDF reference at field 19 (text of Annex 1). It does not expose structured engine or gearbox fields.

The PDF may contain the homologation-form technical characteristics, but the live endpoint has not been resolved and a publication/search obligation is not a license to bulk extract, persistently cache, display commercially, build a derivative database from, or redistribute the PDF.

## VAG TECH PRO ingestion decision

- Keep the FGIS Annex 1 internal namespace separate from public Annex 2 and from the EAEU Decision No. 88 XML schema.
- Do not import SBKTS into the OTTS catalog.
- Do not infer gearbox codes, model year, ECU, DTC or repair applicability from registry metadata.
- A future authorized OTTS PDF import must retain approval number, PDF SHA-256, page/annex, modification/variant scope, source revision, rights evidence and raw homologation strings. Any extracted engine/gearbox relationship remains a candidate until corroborated by an authorized source with exact VAG code semantics and same-variant evidence.
- No data ingestion is allowed until bulk retrieval, offline caching, display and redistribution rights are confirmed in writing or by a clearly applicable license.


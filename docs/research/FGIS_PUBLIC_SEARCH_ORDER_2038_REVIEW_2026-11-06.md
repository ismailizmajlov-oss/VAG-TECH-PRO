# Rosstandart FGIS public-search obligation — review 2026-11-06

## Finding

Rosstandart Order No. 2038 dated 2025-09-24, as amended by Order No. 2335 dated 2025-10-30, distinguishes the internal FGIS attribute schema (Annex 1) from the fields to be published and searchable on the official Rosstandart website for electronically issued documents (Annex 2). The transition date stated in the order is 2025-10-01.

The Annex 2 public-search field namespace includes approval/form identifiers, registration number, validity dates, certification-body details, make, commercial name, vehicle type, base vehicle/chassis, modifications, category, environmental class, an Annex 1 PDF reference, electronic-issuance flag, suspension/resumption data, early-termination data and publication date. The later amendment adds/clarifies cancellation-notice termination fields. These field numbers must not be joined to Annex 1 internal FGIS field numbers.

## Evidence reviewed

- Official system/operator overview: https://www.interstandart.ru/page/fgis_01 (reviewed 2026-11-06). It describes the FGIS register and the data-entry software supplied to accredited certification bodies and testing laboratories.
- Order 2038 secondary republication: https://law.tks.ru/document/779154 (reviewed 2026-11-06).
- Order 2038 secondary republication: https://base.garant.ru/412785907/ (reviewed 2026-11-06).
- Amendment 2335 secondary republication: https://oei-analitika.ru/kurilka/order_info.php?order_id=725730 (reviewed 2026-11-05).

The primary signed order copy was not retrieved. The official-site search route was not resolved during this review. The following likely official site paths were checked but did not yield a verifiable search endpoint:
- https://www.gost.ru/portal/gost/home/activity/documents
- https://www.rst.gov.ru/portal/gost/home/activity/documents

This is a bounded search result, not proof that the official route does not exist.

## Public Annex 2 technical-field boundary

The 28 public Annex 2 search fields are registry/document identity and status metadata: approval/form identifiers, validity dates, certification-body details, make, commercial name, vehicle type, base vehicle/chassis, modifications, category, environmental class, a reference to the Annex 1 PDF, electronic-issuance status, suspension/resumption and early-termination dates/reasons, and publication date.

They do **not** include an engine type/code, gearbox type/code, engine/gearbox pair, ECU identifier, DTC, test plan, repair procedure, wiring diagram, pinout, torque value, adaptation or service interval. The Annex 1 internal FGIS attribute namespace is separate and is not interchangeable with Annex 2. Field 19 is a PDF reference, not the PDF itself and not a redistribution grant.

This field-level conclusion is based on the two reviewed secondary republications of Orders 2038/2335; the primary signed order and exact official search endpoint remain unresolved. Even if an owner later obtains reuse permission for Annex 2 metadata, that metadata alone cannot populate the production engine/gearbox or repair-data tables.

## Rights and ingestion boundary

The order's requirement to publish and enable individual search of Annex 2 fields is not a bulk-data licence. It does not, by itself, authorize VAG TECH PRO to perform automated extraction, bulk export, persistent SQLite caching, commercial third-party display, offline distribution or redistribution of records or PDFs.

The separate Interstandart software procedure concerns data entry/registry operation by accredited organizations and requires the applicable accredited scope and licensed IBM/HCL Domino runtime. It must not be conflated with the public-site search obligation.

Accordingly:
- no FGIS/OTTS rows were downloaded or imported in this review;
- no PDFs were cached;
- no scraping, API probing or undocumented endpoint access was performed;
- bulk export, offline caching, third-party display and redistribution remain blocked pending written authorization or a dataset-specific open licence;
- any future OTTS record remains type-approval evidence only, not a VIN build sheet or repair-data source.

OTTS make/type descriptors do not establish factory engine codes, gearbox codes, engine/gearbox pairs, ECU identities, DTC applicability, wiring, pinouts, torque values or repair procedures. SBKTS gearbox descriptors must not be re-labelled as OTTS type approval or factory gearbox codes.

## Project action

The source register now records the Annex 2 public-search obligation separately from data-entry software access and separately from bulk/offline reuse rights. The exact public endpoint remains unresolved, and the source remains permission-required with zero imported records.

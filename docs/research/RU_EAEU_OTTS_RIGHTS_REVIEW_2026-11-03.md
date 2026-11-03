# Russian / EAEU OTTS source and rights review — 2026-11-03

## Decision

No Russian/EAEU OTTS records or PDFs were copied into the product database in this review. The official register is the highest-priority source, but public search/publication is not the same as a confirmed license for bulk extraction, commercial display, offline caching, or redistribution. Those rights remain unconfirmed. The source register records this as **permission_required**.

HPT.SU has a documented API, but its current API terms require an active API subscription and restrict equivalent third-party access, substantially reproducing derived databases, and full database mirroring without separate written consent. No subscription, account, API key, payment, or acceptance of paid terms was created.

The EAEU Open Data Portal offers an OData interface and describes reuse with minimal organizational restrictions. Its searchable catalog lists 117 resources, including 7 under technical regulation. No dedicated bulk OTTS dataset was confirmed in this review; this is not proof that no related resource exists. Dataset-specific metadata and license terms must be checked before import.

## Official Russian register

The FBU «КВФ «Интерстандарт» page describes FGIS «Реестры КТС» as a set of Rosstandart-maintained databases for vehicle type approvals, chassis type approvals, SBKTS, and cancellation notices. It also describes collection of data from certification bodies and testing laboratories.

- Register overview: https://www.interstandart.ru/page/fgis_01
- Rosstandart Order No. 2038 dated 2025-09-24: https://law.tks.ru/document/779154

Order No. 2038, as amended by Order No. 2335 dated 2025-10-30, defines the internal attribute structure and the separate fields to be published/searchable on the Rosstandart site. The reviewed copies do not grant a blanket license to bulk-copy the database, commercially redistribute the records, cache the full corpus offline, or redistribute the PDFs. Therefore no bulk import is enabled.

### Public-site publication contract and field-number namespaces

Order No. 2038 requires the Rosstandart site to publish and support search for the Annex 2 fields from 2025-10-01. Order No. 2335 (2025-10-30) amends that contract: it adds internal FGIS Annex 1 attributes 86 (resumption reason) and 87 (resumption date), updates public Annex 2 field 25, and adds public fields 27 and 28 for early termination based on a cancellation notice.

The two field-number namespaces must remain separate:

- **Annex 1** is the internal FGIS database attribute set. The existing `ot_ts_attribute_map` in the machine-readable manifest is explicitly scoped to Annex 1. For example, its field 50 is the internal engine make/type descriptor, not a factory VAG engine code.
- **Annex 2** is the public-site publication/search set. Its 28 fields are: approval form number; application form numbers; supplementary-sheet numbers; approval registration number; validity start/end; certification body name/address/phone/email/accreditation number; make; commercial name; vehicle type; base vehicle/chassis; modifications; category; environmental class; Annex 1 PDF; electronic-issue flag; suspension date/reason; resumption date/reason; early-termination date; publication date; early-termination date based on a cancellation notice; and the reason for that cancellation-based termination.

Annex 2 field 19 is a PDF reference/content field. Its presence in a public search contract is not a redistribution license for the PDF. The order establishes public-site publication/search for specified records; it does not document a bulk API or grant commercial reuse, third-party display, offline caching, bulk export, or PDF redistribution rights.

**Source quality limitation:** the FGIS operator overview is on the operator's official site. The text of Orders 2038 and 2335 was reviewed through secondary legal/document reproductions (TKS and OEI-Analitika); the signed primary order files were not retrieved from an official publication endpoint, so no primary-document SHA-256 is claimed. The official public-search endpoint was not resolved in this run.

### What OTTS can and cannot establish

The OTTS/ЭОТТС/ОТШ/ЭОТШ attribute list includes:

- approval registration number and validity dates;
- make, commercial name, type, base vehicle/chassis, modifications, category and environmental class;
- manufacturer and assembly-plant information;
- covered VINs and VIN structure;
- internal-combustion engine make/type, displacement, fuel, fuel-supply type and ignition type;
- vehicle mass, driven-wheel formula, suspension and steering descriptions;
- a full approval PDF reference/file.

The important distinction is that the OTTS engine field is **make/type**, not a guaranteed VAG factory engine code. The OTTS attribute list does not provide a dedicated gearbox-code field. The VIN list describes the approval's covered vehicles; it does not, by itself, prove the exact engine, gearbox or ECU fitted to a particular VIN.

The separate SBKTS/ЭСБКТС attribute list includes engine make/type and, at field 68, gearbox make/type. SBKTS is an individual-vehicle safety certificate, not an OTTS type-approval record. Its individual-vehicle context and possible personal data require a separate privacy and rights review. Do not merge SBKTS gearbox descriptions into OTTS fitment or factory gearbox-code fields.

## EAEU Open Data Portal

- Resource catalog: https://opendata.eaeunion.org/opendata/ru/resourses
- REST API / OData guidance: https://opendata.eaeunion.org/opendata/ru/api/restapi

The catalog search result reports 117 resources and 7 in the technical-regulation section. The portal says machine-readable reuse is available through OData with minimal organizational and other access restrictions. However, no dedicated OTTS bulk dataset was confirmed in the searchable catalog during this review. A future importer must first identify the exact resource, its record-level provenance, market scope, update policy, and dataset-specific reuse terms. The portal's general statement must not be treated as a license for an unidentified dataset.

## HPT.SU

- API documentation: https://hpt.su/api/v1/docs/swagger/
- Public offer: https://hpt.su/p/oferta/
- API terms: https://hpt.su/p/api-terms/

The API terms effective 2026-05-27 require an active subscription to an API tariff. They permit the subscriber to integrate and process materials for internal purposes. Without separate written consent, they prohibit providing third parties equivalent access to the site's database, creating substantially reproducing derived databases for third parties, and systematic copying of the full current database. The public offer also prohibits mass automated downloads outside the documented interface or beyond permitted limits.

This is not sufficient permission for an offline VAG database distributed to third parties. HPT.SU is therefore marked **restricted_for_product_distribution**. A separate written agreement would need to explicitly cover offline caching, local SQLite storage, commercial display, redistribution, derivative database use, and retention after subscription expiry. No paid terms were accepted.

## Import policy

1. Do not scrape FGIS, HPT.SU, or other aggregators.
2. Do not call undocumented endpoints or imitate browser sessions.
3. Do not import an OTTS PDF or metadata record until commercial use, display, offline cache, and any required redistribution rights are confirmed in writing or by an applicable open-data license.
4. Store the exact source revision, source-file SHA-256, license-text SHA-256, retrieval date, market scope, approval validity, and record-level applicability precision for every imported record.
5. Keep OTTS engine make/type separate from factory engine code. Keep SBKTS gearbox make/type separate from factory gearbox code.
6. Treat covered VINs and VIN structure as approval evidence only; do not infer a vehicle's exact engine/gearbox/ECU from them without a matching, independently verified configuration source.
7. Keep all unlicensed source candidates in the source registry with data_ingested=false and permission_required / restricted_for_product_distribution status.

## Source registry

Machine-readable rights and field metadata are stored in:

- data/source-manifests/russian-eaeu-otts-sources.json

No source snapshot hash is claimed for sources that were not downloaded. Their source_snapshot_sha256 remains null and hash_status records why.

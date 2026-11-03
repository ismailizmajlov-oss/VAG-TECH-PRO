# Russian / EAEU OTTS source and rights review — 2026-11-03

## Decision

No Russian/EAEU OTTS records or PDFs were copied into the product database in this review. The official register is the highest-priority source, but public search/publication is not the same as a confirmed license for bulk extraction, commercial display, offline caching, or redistribution. Those rights remain unconfirmed. The source register records this as **permission_required**.

HPT.SU has a documented API, but its current API terms require an active API subscription and restrict equivalent third-party access, substantially reproducing derived databases, and full database mirroring without separate written consent. No subscription, account, API key, payment, or acceptance of paid terms was created.

The EAEU Open Data Portal offers an OData interface and describes reuse with minimal organizational restrictions. Its searchable catalog lists 117 resources, including 7 under technical regulation. No dedicated bulk OTTS dataset was confirmed in this review; this is not proof that no related resource exists. Dataset-specific metadata and license terms must be checked before import.

Two additional commercial aggregators were reviewed. Their terms do not grant the rights required for an offline VAG catalogue:
- OTTS.BOT allows free search but charges for document retrieval. Its terms prohibit automated scraping/mass requests and resale, publication or other distribution of documents and database information as the user's own information product.
- АВТОРЕГИСТР / otts-baza.ru sells subscription access to PDF documents. Its terms permit the subscriber's own professional work but prohibit systematic extraction of a substantial part of the database for publication, resale or a competing catalogue. No offline redistribution license is granted.

Neither aggregator was scraped, queried through undocumented endpoints, registered with, paid, or used to download documents. Both are marked **restricted_for_product_distribution**.

## Official Russian register

The FBU «КВФ «Интерстандарт» page describes FGIS «Реестры КТС» as a set of Rosstandart-maintained databases for vehicle type approvals, chassis type approvals, SBKTS, and cancellation notices. It also describes collection of data from certification bodies and testing laboratories.

- Register overview: https://www.interstandart.ru/page/fgis_01
- Rosstandart Order No. 2038 dated 2025-09-24: https://law.tks.ru/document/779154

Order No. 2038 defines the attribute structure and the fields to be published/searchable on the Rosstandart site. It does not, in the text reviewed, grant a blanket license to bulk-copy the database, commercially redistribute the records, cache the full corpus offline, or redistribute the PDFs. Therefore no bulk import is enabled.

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

## OTTS.BOT

- Website: https://www.otts.bot/
- Terms: https://www.otts.bot/terms

The terms state that search is free while document retrieval is paid. They prohibit automated scraping/mass requests, bypassing technical limits, and resale, publication or other distribution of received documents and database information as the user's own information product. Documents are provided for the user's own use, including submission to authorities. This is not a license to cache or redistribute the database or PDFs inside VAG TECH PRO.

## АВТОРЕГИСТР / otts-baza.ru

- Website: https://otts-baza.ru/
- Terms: https://otts-baza.ru/offer/
- Pricing: https://otts-baza.ru/pricing/

The offer dated 2026-10-04 provides paid subscription access to available PDF files. It permits the user's own tasks and internal professional work, but without separate agreement does not allow systematic extraction of a substantial part of the database for publication, resale or creation of a competing catalogue. The terms do not grant offline distribution or PDF redistribution rights. No subscription or download was made.

## Import policy

1. Do not scrape FGIS, HPT.SU, OTTS.BOT, АВТОРЕГИСТР or other aggregators.
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

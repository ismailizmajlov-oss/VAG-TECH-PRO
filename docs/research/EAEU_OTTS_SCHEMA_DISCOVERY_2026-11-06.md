# EAEU OTTS registry schema discovery — 2026-11-06

## Finding

The EAEU unified register of vehicle type-approval documents has a richer underlying XML data model than the public Annex 2 search fields used by the Russian FGIS importer. EEC Collegium Decision No. 88 of 2016-07-26 defines registry message structure **R.TR.TS.07.001**, version **1.0.0**, with root element **ConformityVehicleDocsRegistryDetails** and namespace:

    urn:EEC:R:TR:TS:07:ConformityVehicleDocsRegistryDetails:v1.0.0

The schema description identifies fields that could be valuable for VAG vehicle identification if, and only if, those fields are actually exposed in a lawfully obtained registry export:

- VehicleTypeDetails: manufacturer make, commercial name, manufacturer-assigned vehicle type ID and technical category.
- VehicleVariantDetails: manufacturer-assigned variant ID and variant-scoped technical details.
- EngineDetails.VehicleComponentModelCode: manufacturer-assigned engine type code; the schema does not guarantee that this is the familiar VAG three-letter engine code.
- EngineDetails: component make/description, cylinder quantity/arrangement, displacement, compression, maximum power and torque.
- TransmissionUnitDetails.VehicleUnitKindCode: code 05 means gearbox; 10 transfer case; 15 final drive; 20 power take-off.
- TransmissionUnitDetails.VehicleComponentModelCode: manufacturer-assigned transmission-unit model code, not automatically a VAG gearbox code.
- ECUModelCode: manufacturer-assigned engine ECU model designation.

The registry document-kind codes are 30 = OTTS, 35 = OTSH and 40 = SBKTS. The proposed importer accepts OTTS/OTSH records and deliberately skips SBKTS records because the SBKTS structure can contain an individual VIN and personal/applicant details.

## Critical boundary: schema is not a data-reuse grant
The EEC's 2022 procurement technical specification for open-data portal modernization defines “open data” as machine-readable public information that may be reused and republished for lawful purposes without copyright, patent or other control mechanisms (https://eec.eaeunion.org/upload/iblock/aad/K_1026.pdf). This is a portal-level definition in a procurement specification, not a dataset-specific license or a written grant for the OTTS register. It does not change the rights decision below: no OTTS-specific resource, bulk-export permission, offline-cache permission, third-party display right or redistribution right has been established.


Decision No. 225 of 2014-12-02 is the public-access and publication basis: the unified register consists of national parts; those parts must be accessible from official websites of authorized bodies and the EEC; the specified registry fields must be published within five working days; and requests from interested persons are handled by authorized bodies. Decision No. 88 of 2016-07-26 defines the R.TR.TS.07.001 technical information-exchange schema, not the public-access basis. Neither decision grants VAG TECH PRO bulk extraction, offline caching, commercial display or redistribution rights.

The public portal observation remains bounded:

- https://portal.eaeunion.org/ redirected to the EAEU open-data portal during the 2026-11-06 review. This is not the only access route: Decision No. 225 requires national parts to be available from official websites of authorized bodies.
- The reviewed open-data catalogue showed 117 resources overall and 7 under technical regulation; no dedicated OTTS dataset or OTTS-specific OData/REST endpoint was identified.
- Russia's national part is identified as FGIS Reestr KTS, maintained by FBU KVF Interstandart: https://www.interstandart.ru/page/fgis_01. The exact public search endpoint is not yet resolved. The technical-regulation portal https://tech.eaeunion.org/tech/ru/registers/ lists certificates/declarations and conformity-assessment bodies; it is a different registry and must not be treated as the OTTS register.
- Kazakhstan's national OTTS/OTSH registry is officially listed by the Committee of Technical Regulation and Metrology on gov.kz (published 2022-09-20, updated 2024-03-20): https://www.gov.kz/org/mti-ktrm/documents/details/350253?lang=ru. The official directory links the legacy portal https://techreg.gov.kz/index/; the current interface is https://techreg.kezekte.kz/ru/cert/ot-registry/list. The legacy list page showed 273 records, while the current list's indexed text showed zero and direct retrieval timed out on 2026-11-06; the zero is not treated as a current corpus count. The government listing confirms the registry reference and authority, not the current portal operator or data-reuse rights. No dataset license, API contract, bulk extraction, offline caching, display or redistribution permission was found.
- The EAEU electronic-document structure registry https://rseds.eaeunion.org/ru/ advertises batch export and XML validation in its indexed landing-page content. Direct retrieval timed out in this review; the actual XSD package was not downloaded or hash-pinned.
- Kyrgyzstan's Single Window portal https://cert.trade.kg/ links the public OTTS registry at https://sbkts.trade.kg/otts. The registry identifies itself as the state vehicle type-approval register and supports VIN/number search, but explicitly requires robot verification before records can be viewed. The portal summary lists one OTTS record; this is not treated as a complete/current corpus count. No documented API, dataset-specific licence, bulk export, offline-cache, display or redistribution right was identified. No CAPTCHA was bypassed and no records were downloaded or imported.

Accordingly, public_field_exposure_verified=false remains in the source register. The schema fields above are confirmed as fields in the Decision No. 88 data model, not confirmed as fields returned by the currently visible public query UI.

Decision No. 225 paragraph 8 lists OTTS/OTSH register fields such as make, commercial name, type, modification, category and ecological class, and refers to information in approval attachments. Paragraph 9 lists detailed SBKTS characteristics including engine make/type, displacement, compression, power, transmission and gearbox make/type, but also VIN and applicant information. The importer deliberately skips SBKTS and does not store VIN or applicant/entity names.

The EEC's 2023 report on the temporary registry pilot also records that the earlier XML-submission mechanism did not provide machine-readable export from the unified register. This is historical evidence, not proof that no newer endpoint exists: https://eec.eaeunion.org/upload/files/deptexreg/KK/KK-49.pdf.

## Import and applicability rules

The new scripts/import_eaeu_otts_registry_export.py parser is a fail-closed path for a future authorized XML export:

1. It accepts only R.TR.TS.07.001 v1.0.0 with the exact namespace and root element.
2. It does not scrape the portal, call undocumented endpoints or download documents.
3. Persistent SQLite staging is blocked unless the source register contains explicit owner-reviewed permission for commercial use, bulk reuse, offline caching, display and redistribution, plus a matching permission-evidence file SHA-256.
4. It never writes into the production vehicle catalogue. The output is a separate staging SQLite with distribution_eligible=0.
5. It skips SBKTS code 40 and does not store applicant, conformity-authority or vehicle-manufacturer entity names (which can contain a natural person's name), contact details, VINs or embedded binary documents.
6. Engine and transmission component codes retain their EAEU field namespace. They are not relabelled as VAG engine/gearbox codes without independent evidence.
7. A powertrain pair is emitted only as an unverified candidate when exactly one coded engine and one coded gearbox (unit kind 05) occur under the same approval variant. Multiple engines or gearboxes are never cross-joined.
8. The schema rule populates VehicleManufacturingYear for SBKTS; this importer skips SBKTS, so model_year remains NULL for OTTS/OTSH. Approval dates are never used as model years.
9. All imported values carry source ID/revision, market scope, retrieval timestamp, input SHA-256, normalized-record SHA-256, schema version and verification status.

The importer stores the issuing country separately from the EAEU market scope. It omits business-entity names from the manufacturer and conformity-authority sections because the schema permits a natural person to appear in those fields. The importer has only synthetic test fixtures. No real EAEU vehicle records have been downloaded, cached or imported.

## Next evidence required

- Resolve the current official Russian national-part search route for FGIS Reestr KTS and obtain a representative OTTS/OTSH record through the normal public workflow.
- Determine whether the public response exposes the engine, transmission and ECU fields defined in the schema.
- Obtain written permission or a dataset-specific open licence covering the exact VAG TECH PRO use case, including offline caching, commercial use, display and redistribution.
- Retrieve the official XSD package from the EAEU structure registry and pin its SHA-256 before treating the parser as schema-validated.
- Review each VAG record and its variant-level engine/transmission relationship before any exact fitment promotion.

## References

- EEC Collegium Decision No. 225, 2014-12-02 (registry access/publication rules): https://www.alta.ru/tamdoc/14kr0225/
- EEC Collegium Decision No. 88, 2016-07-26 (technical exchange schema): https://www.alta.ru/tamdoc/16kr0088/
- Official EAEU electronic-document structure registry: https://rseds.eaeunion.org/ru/
- EAEU open-data catalogue: https://opendata.eaeunion.org/opendata/ru/resourses
- EAEU technical-regulation registers: https://tech.eaeunion.org/tech/ru/registers/
- EAEU portal root: https://portal.eaeunion.org/
- EEC 2023 report on the registry pilot and machine-readable export limitation: https://eec.eaeunion.org/upload/files/deptexreg/KK/KK-49.pdf

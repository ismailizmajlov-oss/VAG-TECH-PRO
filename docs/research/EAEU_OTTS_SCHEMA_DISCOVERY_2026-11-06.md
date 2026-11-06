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

Decision No. 88 defines access for an interested person through the Union information portal and the structure used in the EAEU registry process. It does not grant VAG TECH PRO bulk extraction, offline caching, third-party display, commercial reuse or redistribution rights.

The public portal observation remains bounded:

- https://portal.eaeunion.org/ redirected to the EAEU open-data portal during the 2026-11-06 review.
- The reviewed open-data catalogue showed 117 resources overall and 7 under technical regulation; no dedicated OTTS dataset or OTTS-specific OData/REST endpoint was identified.
- The technical-regulation portal https://tech.eaeunion.org/tech/ru/registers/ lists certificates/declarations and conformity-assessment bodies; it is a different registry and must not be treated as the OTTS register.
- The EAEU electronic-document structure registry https://rseds.eaeunion.org/ru/ advertises batch export and XML validation in its indexed landing-page content. Direct retrieval timed out in this review; the actual XSD package was not downloaded or hash-pinned.

Accordingly, public_field_exposure_verified=false remains in the source register. The schema fields above are confirmed as fields in the Decision No. 88 data model, not confirmed as fields returned by the currently visible public query UI.

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

- Resolve the current official individual-query route for the OTTS register and obtain a representative record through that normal public workflow.
- Determine whether the public response exposes the engine, transmission and ECU fields defined in the schema.
- Obtain written permission or a dataset-specific open licence covering the exact VAG TECH PRO use case, including offline caching, commercial use, display and redistribution.
- Retrieve the official XSD package from the EAEU structure registry and pin its SHA-256 before treating the parser as schema-validated.
- Review each VAG record and its variant-level engine/transmission relationship before any exact fitment promotion.

## References

- EEC Collegium Decision No. 88, 2016-07-26 (published text copy): https://www.alta.ru/tamdoc/16kr0088/
- Official EAEU electronic-document structure registry: https://rseds.eaeunion.org/ru/
- EAEU open-data catalogue: https://opendata.eaeunion.org/opendata/ru/resourses
- EAEU technical-regulation registers: https://tech.eaeunion.org/tech/ru/registers/
- EAEU portal root: https://portal.eaeunion.org/

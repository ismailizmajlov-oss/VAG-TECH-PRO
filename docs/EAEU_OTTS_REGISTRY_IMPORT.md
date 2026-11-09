# Authorized EAEU OTTS/OTSH registry export import

The EAEU registry schema in Decision No. 88 defines **R.TR.TS.07.001 v1.0.0**. The importer in **scripts/import_eaeu_otts_registry_export.py** is a local fail-closed parser for an XML export that has already been obtained lawfully. It does not scrape the EAEU portal, discover undocumented endpoints, download PDFs or access restricted services.

## Current source status

The source **eaeu-otts-unified-register-public-portal** remains blocked for bulk reuse and product distribution. Decision No. 225 of 2014-12-02 establishes public access to national register parts from official websites and requests to authorized bodies; Decision No. 88 of 2016-07-26 defines the technical exchange schema. Neither decision grants bulk reuse, offline caching, commercial display or redistribution rights. The central portal root redirects to the EAEU open-data catalogue, but Decision No. 225 requires national parts to be accessible from official websites. Russia's national part is identified as FGIS Reestr KTS maintained by Interstandart (https://www.interstandart.ru/page/fgis_01); its exact public search endpoint and any bulk export remain unresolved. No real EAEU record is currently imported or cached.

## Validate-only mode

Validate an authorized XML file's root, namespace and structural fields without writing a database:

    python scripts/import_eaeu_otts_registry_export.py --input ./authorized-export/registry.xml --source-manifest ./data/source-manifests/vag-factory-source-register.json --retrieved-at 2026-11-06T07:19:20+07:00 --validate-only

Validate-only does not write or cache records. Use it only with a synthetic schema fixture or an export whose processing is already authorized.

## Persistent staging mode

Persistent staging requires all of the following in the source register entry:

- permission_status = approved_for_offline_distribution;
- review_status = approved_by_owner and a review date/reference;
- commercial_use_allowed = true;
- bulk_reuse_allowed = true;
- offline_cache_allowed = true;
- display_and_redistribution_allowed = true;
- a permission-evidence HTTPS URL and SHA-256, plus the matching local evidence file.

Example, after the rights evidence has been reviewed and the source register has been updated:

    python scripts/import_eaeu_otts_registry_export.py --input ./authorized-export/registry.xml --source-manifest ./data/source-manifests/vag-factory-source-register.json --retrieved-at 2026-11-06T07:19:20+07:00 --permission-evidence ./authorized-export/permission.pdf --output ./data/local-staging/eaeu-otts-staging.sqlite

The tool checks the permission file's SHA-256 against the source register, refuses to overwrite an existing database/sidecar, writes transactionally to a new SQLite file, and runs SQLite integrity and foreign-key checks. A matching file hash proves integrity of the supplied evidence file, not its authenticity or legal scope. The recorded rights status therefore remains owner_attested_not_independently_verified.

## OTTS/OTSH Annex 1 technical fields (Decision No. 232)

Decision No. 232's current consolidated OTTS/OTSH form contains a separate technical-characteristics attachment (Appendix No. 1 to the OTTS form; the corresponding Appendix No. 1 to the OTSH form). It lists, among other fields:

- internal-combustion engine make/type, cylinder count and arrangement, displacement, maximum power and torque;
- fuel and fuel-supply system;
- ECU marking and selected fuel-system component markings;
- transmission, clutch make/type, gearbox make/type, gear count and ratios, transfer-case and final-drive data.

These are **homologation-form fields**, not proof that the current public summary/search endpoint exposes the filled attachment. The current public field exposure remains unverified. The Decision No. 88 XML schema separately exposes manufacturer-assigned component make/model/text fields and ECUModelCode; those raw values must stay in their own namespaces.

Decision No. 52 of 2026-05-12 amended Decision No. 232; the relevant form amendments became effective 2026-10-08 and add hybrid-powertrain description details. The engine/gearbox fields listed above are present in the consolidated form, but this review does not claim they were newly introduced by Decision No. 52.

For any future authorized OTTS/OTSH attachment import:

- retain the exact approval number, document kind, annex/page, modification/variant scope, source revision and source hash with every extracted value;
- store manufacturer engine/gearbox make/type as raw homologation attributes, not as VAG three-letter engine or gearbox codes;
- create only an unverified same-annex/same-variant candidate when both values are explicitly tied to that scope; never cross-join variants;
- do not infer model year from approval dates or convert homologation attributes into ECU, DTC, wiring or repair applicability.

References: [Decision No. 232 consolidated form](https://www.alta.ru/tamdoc/14kr0232/), [Decision No. 52 of 2026-05-12](https://www.alta.ru/tamdoc/26kr0052/), [EEC official 2026 decisions index](https://docs.eaeunion.org/documents/463/).

This form/schema evidence does **not** grant bulk extraction, offline caching, product display, commercial reuse or redistribution rights for filled OTTS/OTSH documents.

## XML parser safety

The root must use the exact R.TR.TS.07.001 namespace. Each recognized field is checked against its field-specific imported namespace prefix from Decision No. 88, tables 12–13 (for example, trcdo for complex vehicle records and trsdo for vehicle component codes). Foreign or unqualified lookalike fields are rejected; unrelated extension elements such as XMLDSig signatures are ignored; every observed element namespace is recorded. The field map is based on the published structure description, not a retrieved XSD, so full XSD validation is still not claimed. It also rejects DTD/entity declarations after removing interleaved NUL bytes so UTF-16/UTF-32 encoded declarations cannot bypass the pre-parse guard. These checks are structural safeguards; they do not validate a real registry export against an official XSD, which has not yet been retrieved.

## Data semantics

- Only document kinds 30 (OTTS) and 35 (OTSH) are staged. Code 40 (SBKTS) is skipped.
- VehicleComponentModelCode is stored as an EAEU manufacturer-assigned component model code. It is not automatically a VAG three-letter engine code or a VAG gearbox code.
- VehicleUnitKindCode=05 is a gearbox. Transfer cases, final drives and power take-off units remain separate unit types.
- Engine and transmission candidates remain scoped to their source approval variant.
- A pair candidate is created only when one coded engine and one coded gearbox appear under the same variant. It is still candidate_unverified; the importer never confirms fitment.
- When a document contains multiple variants, every variant must carry VehicleTypeVariantId, following Decision No. 88, table 6, rule 34. A single unlabelled variant remains a candidate with explicitly reduced precision.
- Each variant may contain at most one VehicleTypeVariantId, and non-empty variant IDs must be unique within the approval document. Repeated ID elements or duplicate IDs are rejected because they make the engine/gearbox observation scope ambiguous.
- Pair-candidate precision is explicit: `same_approval_variant_id_single_pair_candidate` when `VehicleTypeVariantId` is present, and `same_unlabelled_approval_variant_single_pair_candidate` when the XML variant element has no ID. Both remain `candidate_unverified`; the XML element boundary is evidence only and is not factory-fitment confirmation.
- If multiple engine or gearbox candidates occur under a variant, the importer does not create a cross-product.
- The Decision No. 88 rule populates VehicleManufacturingYear for SBKTS; because SBKTS is skipped, model_year remains NULL for OTTS/OTSH. Approval issue/start dates are not model years.
- Applicant, conformity-authority and vehicle-manufacturer entity names (which can contain a natural person's name), contact, VIN and embedded binary-document fields are not stored.
- Document-level VehicleV2Details VIN and manufacturing-year fields are also not promoted into variant applicability; they are not nested under a specific VehicleVariantDetails.
- The output is a staging database only and is never merged into production automatically.

Decision No. 225 paragraph 9 describes SBKTS registry fields and includes engine/gearbox characteristics together with VIN and applicant data; this importer skips SBKTS. Separately, Decision No. 232's current consolidated OTTS/OTSH form lists detailed engine, ECU-marking, transmission, clutch and gearbox fields in the homologation attachment. That normative blank-form schema is not evidence that the current public query exposes filled attachments. Neither Decision No. 225, No. 232 nor the Decision No. 88 exchange schema grants VAG TECH PRO bulk extraction, offline caching, display or redistribution rights. See docs/research/EAEU_OTTS_SCHEMA_DISCOVERY_2026-11-06.md and the source register for the public-access basis, schema evidence and remaining legal/technical blockers.

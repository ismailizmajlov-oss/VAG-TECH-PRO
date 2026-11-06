# Authorized EAEU OTTS/OTSH registry export import

The EAEU registry schema in Decision No. 88 defines **R.TR.TS.07.001 v1.0.0**. The importer in **scripts/import_eaeu_otts_registry_export.py** is a local fail-closed parser for an XML export that has already been obtained lawfully. It does not scrape the EAEU portal, discover undocumented endpoints, download PDFs or access restricted services.

## Current source status

The source **eaeu-otts-unified-register-public-portal** remains blocked for bulk reuse and product distribution. The public-query legal basis under Decision No. 88 is not a bulk-reuse licence. The current portal root redirects to the EAEU open-data catalogue; no OTTS-specific public API or dataset was resolved in the 2026-11-06 review. No real EAEU record is currently imported or cached.

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

## Data semantics

- Only document kinds 30 (OTTS) and 35 (OTSH) are staged. Code 40 (SBKTS) is skipped.
- VehicleComponentModelCode is stored as an EAEU manufacturer-assigned component model code. It is not automatically a VAG three-letter engine code or a VAG gearbox code.
- VehicleUnitKindCode=05 is a gearbox. Transfer cases, final drives and power take-off units remain separate unit types.
- Engine and transmission candidates remain scoped to their source approval variant.
- A pair candidate is created only when one coded engine and one coded gearbox appear under the same variant. It is still candidate_unverified; the importer never confirms fitment.
- If multiple engine or gearbox candidates occur under a variant, the importer does not create a cross-product.
- The Decision No. 88 rule populates VehicleManufacturingYear for SBKTS; because SBKTS is skipped, model_year remains NULL for OTTS/OTSH. Approval issue/start dates are not model years.
- Applicant, conformity-authority and vehicle-manufacturer entity names (which can contain a natural person's name), contact, VIN and embedded binary-document fields are not stored.
- The output is a staging database only and is never merged into production automatically.

See docs/research/EAEU_OTTS_SCHEMA_DISCOVERY_2026-11-06.md for the schema evidence and remaining legal/technical blockers.

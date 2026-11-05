# Authorized Russian FGIS OTTS metadata import

This importer is a **local, offline, fail-closed staging tool** for a source export that the owner has already obtained lawfully. It does not scrape FGIS, imitate browser sessions, call an undocumented API, download PDFs, or infer VAG engine/gearbox/ECU fitment.

## Current source status

The FGIS source remains `permission_required` in the source register. Public-site search requirements under Rosstandart Orders 2038/2335 do not themselves authorize commercial reuse, third-party display, persistent SQLite caching, bulk export, or PDF redistribution. No real FGIS export is currently available or imported. The test suite uses explicitly synthetic fixtures only.

## Inputs

- `--input export.json`: JSON with `schema_version: 1`, `package_type: "rosstandart_fgis_annex2_export"`, and `records`.
- `--manifest source-manifest.json`: source ID/revision, publisher, source URL, retrieval timestamp, RU/EAEU market scope, and an owner-reviewed rights statement.
- `--license-text LICENSE.txt`: required for `rights.basis="open_license"`.
- `--permission-document permission.pdf`: required for `rights.basis="written_permission"`.
- `--output staging.sqlite`: new output path. Existing DBs/manifests are never overwritten.

Example:

```powershell
npm run prepare:authorized-fgis-otts -- `
  --input .\authorized-export\export.json `
  --manifest .\authorized-export\source-manifest.json `
  --license-text .\authorized-export\LICENSE.txt `
  --output .\data\local-staging\fgis-otts-2026-11.sqlite
```

For written permission, replace `--license-text` with `--permission-document`.

## Rights gate

The manifest must explicitly include:

- `source_id="rosstandart-fgis-kts"`, a source revision, HTTPS source URL, retrieval timestamp, and both `RU` and `EAEU_TR_TS_018_2011` market scopes;
- the manifest and every record source URL must use `rst.gov.ru`, `gost.ru` or `interstandart.ru` (or a subdomain); lookalike hosts, URL credentials and non-default ports are rejected. License/permission evidence URLs are separate HTTPS references.
- `rights.review_status="approved_by_owner"`, reviewer, review date, approval reference, and either a license identifier/URL/hash or permission-document URL/hash;
- `commercial_use_allowed=true`, `display_allowed=true`, `offline_cache_allowed=true`, and `bulk_export_allowed=true`;
- an explicit `pdf_redistribution_allowed` boolean. This metadata-only importer never includes PDF binaries, even when PDF rights are true.

The importer verifies only that the supplied license/permission file bytes match the SHA-256 declared in the manifest. This proves file integrity, not the authenticity of the reviewer, the authority of the person who approved the rights, or the legal scope of the document. The SQLite `rights_status` is therefore always `owner_attested_not_independently_verified`; it must never be interpreted as a legal clearance or as proof that VAG TECH PRO has redistribution rights. A project owner must separately inspect the complete evidence, confirm that it covers this exact application and distribution model, and record that decision through the project's controlled source-rights review before any production promotion.

## Data semantics and safety

- The input field namespace must be `annex_2_publication_fields`; field numbers are checked against the 28-field public Annex 2 map.
- The reviewed public-search obligation is limited to electronically issued records; field 20 (`electronically_issued_flag`) must be present and true for every staged row.
- Public Annex 2 is document/vehicle identity metadata only. It contains no engine or gearbox technical designation/code, engine/gearbox pairing, ECU, DTC, repair, wiring, pinout, torque, adaptation or service-interval fields. A field-19 Annex 1 PDF reference is not a PDF binary or a reuse grant.
- Annex 1 internal FGIS field numbers are rejected if presented as Annex 2 field numbers.
- Only Volkswagen, Audi, Škoda, SEAT and CUPRA make names are accepted.
- Engine codes, gearbox codes, ECU identifiers, PR codes, VIN patterns and exact configuration claims are rejected. They are not public Annex 2 fields.
- Every row is stored with source URL, source revision, source-field numbers, market scope, a stable canonical-JSON row SHA-256 and `type_approval_document_metadata_only` applicability precision. The full export's SHA-256 identifies the exact original input bytes; the per-row hash is over canonicalized parsed JSON, not a claim about original byte offsets.
- Every row remains `needs_review` and `blocked_pending_technical_review`; exact engine, transmission and ECU fitment claims are hard-coded to zero.
- The SQLite write uses a transaction, temporary files, integrity and foreign-key checks, and refuses to overwrite an existing output. A sidecar manifest records source URL/revision, market scope, license/permission identifiers and hashes, owner-review metadata, rights flags, and the database hash. The original export and rights-evidence files remain with the owner; their exact hashes are pinned in the database and sidecar.

This staging database is not merged into the production vehicle catalogue. A separate technical review and a separately authorized mapping step are required before any record can become a verified vehicle configuration.
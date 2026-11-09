# OpenVAG DTC repository review — 2026-11-09

## Repository and claimed scope

- Repository: https://github.com/riz4d/OpenVAG
- Pinned revision reviewed: `407d5e042cf46d55087ed4ae4e056605f2b04f08`
- Repository reports an MIT licence for tracked files.
- README claims 995 DTC codes, 1,103 variants, 341 component identifiers, 712 code/component links and 276 related-code links.

## What is actually available

The tracked repository contains an API implementation, SQL schema and schema documentation. It does **not** contain `db/openvag.db`; `.gitignore` explicitly excludes that file under “Database (regenerated from scripts)”. No database-generation script or GitHub Release artifact is present in the tracked tree. The API documentation describes a local `http://localhost:8000` service, not a hosted public dataset endpoint.

The database README describes the tables and repeats the row counts, but it does not identify the upstream sources for the DTC titles, variants, symptoms, causes, solutions, component mappings or related-code text. No per-row source URL, source revision, evidence locator or content hash is documented.

## Rights decision

The MIT licence file is evidence for the tracked repository code and files to the extent the author has rights to license them. It does not establish provenance or third-party rights for a database that is absent from the repository. In particular, it is not enough to approve caching or redistribution of the README-claimed DTC descriptions and repair text.

## VAG TECH PRO decision

- Keep the repository as a schema/API design lead only.
- Do not download, recreate, infer or import the claimed DTC dataset.
- Do not treat the README counts as independently verified data.
- Require the actual database bytes, a pinned data revision, per-record provenance, and a data-specific licence or written permission before any data review.
- No production or research DTC rows are added from this repository.

No database bytes were retrieved, so no database SHA-256 exists. No external account, maintainer contact, paid access or permission request was made.

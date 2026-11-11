# OpenVAG DTC database rights and file-presence recheck — 2026-11-11

## Scope

Recheck the public default branch of [riz4d/OpenVAG](https://github.com/riz4d/OpenVAG) before considering it as a source for the VAG TECH PRO local DTC catalog. This review is a source-rights and availability check only; it does not import or copy any DTC, component, repair or mapping content.

## Observed repository state

- Repository: `riz4d/OpenVAG`; default branch: `main`.
- Revision checked: `407d5e042cf46d55087ed4ae4e056605f2b04f08`.
- GitHub repository metadata reported a repository size of 147 KB at review time.
- The README claims a SQLite database containing 995 DTC code/title rows, 1,103 variants and 341 component identifiers.
- `db/README.md` describes a database of approximately 2.1 MB.
- The advertised path `db/openvag.db` is not present in the current default branch (GitHub contents lookup returned 404).
- The repository `.gitignore` explicitly excludes `db/openvag.db` with the comment `Database (regenerated from scripts)`.

The review did not obtain database bytes, did not compute a database SHA-256 and did not inspect historical release assets. Therefore this finding is limited to the current default-branch tree; it is not a claim that no copy has ever existed elsewhere.

## License and provenance

The root `LICENSE` is MIT and names the repository author. It licenses the software and accompanying files to which the licensor has rights. The README and `db/README.md` do not provide a separate database license, row-level provenance, source-document revision, rights statement for the underlying DTC/repair text, or evidence that the repository maintainer can relicense every upstream record.

A software license badge is not evidence that the maintainer owns or can redistribute third-party database content. The database schema documentation and headline row counts do not establish source authority or technical applicability.

## VAG TECH PRO decision

- Keep `riz4d-openvag-dtc-quarantine` in quarantine.
- Do not import, display, cache, bundle or redistribute DTC definitions, fault variants, repair solutions, component mappings or cross-references from this source.
- Do not infer exact model, generation, year, engine, gearbox or ECU applicability from the README's aggregate counts.
- Preserve the existing separate generic SAE/ISO DTC namespace; do not use this source to populate VAG-specific production records.

Reconsider only after the actual database bytes are made available with a pinned revision and SHA-256, the source owner supplies a separate dataset license or written reuse permission covering commercial display/offline caching/redistribution, and record-level source provenance and applicability can be audited.

No external account, paid access, credential, database download or production import was used.

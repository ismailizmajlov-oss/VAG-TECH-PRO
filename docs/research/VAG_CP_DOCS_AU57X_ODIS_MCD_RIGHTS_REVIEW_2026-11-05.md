# VAG-CP-Docs AU57X ODIS MCD material — rights and closed-catalogue exclusion (2026-11-05)

## Decision

Do not ingest or display the AU57X ODIS MCD findings from `dspl1236/VAG-CP-Docs`. The repository declares CC0 1.0 for its documentation, but the reviewed technical document explicitly identifies its source as a Volkswagen Group ODIS MCD project (DVR 72) built from a PDX source on a VW internal server. It describes extraction of ODIS MCD string databases and DIDB fault-code data. VAG TECH PRO has no evidence that the uploader owns or may sublicense the underlying OEM diagnostic database.

The repository README says the work was obtained from publicly observable vehicle behavior and does not contain unauthorized material. That statement is recorded, but it does not independently establish the acquisition authority or the right to redistribute OEM-derived ODIS MCD database content. Under the project's explicit no-leaks/no-closed-catalogues rule, this source remains **restricted and excluded** until VW AG permission or independently verifiable source rights are supplied.

No technical data from this repository has been copied into VAG TECH PRO. No ODIS MCD project, PDX, DIDB database, PDF, binary or diagnostic package was downloaded or cached.

## Evidence reviewed

- Repository: https://github.com/dspl1236/VAG-CP-Docs
- Repository README: https://github.com/dspl1236/VAG-CP-Docs/blob/main/README.md
- CC0 licence claim: https://github.com/dspl1236/VAG-CP-Docs/blob/main/LICENSE
- AU57X findings: https://github.com/dspl1236/VAG-CP-Docs/blob/main/technical/au57x-mcd-project-findings.md
- Last reviewed document commit: https://github.com/dspl1236/VAG-CP-Docs/commit/1d6948369cdaf6acc013907b5f35591f236ca649

The reviewed AU57X document states:

- Platform family: Audi A6 C7 / A7 4G / A8 D4 (AU57X).
- Source project: AU57X ODIS MCD Project, DVR 72 / revision 072102, dated 2022-09-22.
- Build host: `VWAGWOSOB127`; converter: `VW-MCD 19.0.2.0`.
- The project was built on a VW internal Tomcat server from a PDX source and converted to the PBL runtime format used by ODIS-S clients.
- The findings were extracted from `AStringData.data.gz` and a DIDB HSQLDB database; the document describes proprietary `.bv.db` / `.sd.db` project files and a PBL decoder.
- The document lists three CP-related DTC candidates: U110100, B1B0400 and B1B0300, plus diagnostic channel/DID identifiers.

The repository's `LICENSE` file declares CC0 1.0 for repository content. The CC0 declaration is not evidence that the author owns the underlying VW ODIS MCD/PDX/DIDB material or has authority to waive Volkswagen's rights in it.

## Applicability limits

Even if rights were later established, the published findings are not a complete vehicle configuration database:

- model family is stated, but exact model years and market are not;
- per-record ECU part number and HW/SW revision are not established;
- no exact engine/gearbox linkage is provided;
- the DTCs are platform-family candidates, not verified fitment for an exact configuration;
- DIDs and adaptation identifiers are not enough to create a safe executable test plan or repair procedure.

No candidate is promoted to verified VAG-specific DTC or technical content.

## Required before reconsideration

1. Written permission from VW AG or another party demonstrably authorized to license the underlying ODIS MCD/PDX/DIDB material, covering commercial use, offline caching, display and redistribution in VAG TECH PRO; or
2. a reproducible provenance statement showing that the specific data was independently collected from lawfully owned vehicles without copying closed ODIS MCD/PDX/DIDB content, together with a valid data licence from the rights holder.

Until then, keep the source quarantined. The source register records repository/document commit identifiers and Git blob SHA-1 values only; no local snapshot was created and no SHA-256 data snapshot is claimed.

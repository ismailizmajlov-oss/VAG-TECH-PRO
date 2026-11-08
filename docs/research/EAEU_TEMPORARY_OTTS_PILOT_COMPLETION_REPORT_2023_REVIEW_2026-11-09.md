# EAEU temporary OTTS pilot completion and current-route status — 2026-11-09

## Executive finding

The official EEC page still publishes a navigation link to the electronic OTTS register, but the underlying temporary electronic-register pilot was reported by the EEC as completed in 2023. The historical pilot did provide a machine-readable export service **on request by an interested person while the pilot operated**. That is not evidence that the service remains active, that a public bulk API exists today, or that VAG TECH PRO may persistently cache, display, commercially reuse or redistribute the records.

The current electronic OTTS destination returned HTTP 502 on 2026-11-09. No vehicle records, attachments, exports or source files were downloaded. No source snapshot SHA-256 is claimed.

## Primary EEC evidence

1. The EEC's current temporary-register page remains visible and separately links to electronic OTTS, OTSH and SBKTS routes:
   - EEC page: https://eec.eaeunion.org/comission/department/deptexreg/tr/temprorary_otts.php
   - Electronic OTTS destination: https://portal.elpts.ru/ncher/otts
   - Rechecked: 2026-11-09; destination response: HTTP 502 Bad Gateway.

2. EEC Collegium Order No. 18 of 2022-02-08 approved a pilot for electronic conformity documents and a temporary register through 2022-12-31. The order identifies Russia and Belarus as the initial participants, with possible accession by Armenia, Kazakhstan and Kyrgyzstan if they were ready:
   - Official EEC legal-portal record: https://docs.eaeunion.org/documents/398/6429/
   - Official PDF: https://docs.eaeunion.org/upload/iblock/7f0/ccpz6isinr3h134zlbw6tffs2nyo3xz6/err_14022022_18_doc.pdf

3. The EEC's materials for the 49th meeting of the Consultative Committee (2023-04-18), agenda item 12, contain an explanatory report on the pilot's results:
   - Official EEC report PDF: https://eec.eaeunion.org/upload/files/deptexreg/KK/KK-49.pdf
   - The report states that the temporary register was hosted by the electronic-passport administrator and duplicated on Belarus's infrastructure.
   - Historical totals during the pilot: 2,491 OTTS approvals and revisions (74 issued in Belarus), 111 OTSH approvals (11 issued in Belarus), and 313,123 SBKTS certificates (14,640 issued in Belarus).
   - During the pilot, the service developed by the authorized bodies allowed an interested person to request machine-readable information from documents in the temporary register.
   - The report records that the authorized bodies of Armenia, Kazakhstan and Kyrgyzstan did not express a wish to join at the 2023-01-27 meeting. It concludes that the pilot should be considered completed; further continuation was considered appropriate only if those states joined.

These counts are historical pilot statistics, not a verified current register size, not a VAG count and not a list of records available for download.

## Consequences for VAG TECH PRO

- Treat the 2026 EEC page link as a historical navigation route to a pilot register, not as proof of an active export service.
- Keep the current official OTTS route in discovery-only status until its live service, record fields, export mechanism and legal basis are independently reverified.
- The pilot's request-based machine-readable export does not grant a general right to bulk extraction, automated scraping, local persistent SQLite caching, offline display, commercial use, third-party display or redistribution.
- Decision No. 225 remains the legal basis for national-register publication and interested-person requests. Decision No. 88 defines an information-exchange schema; neither decision by itself supplies a VAG TECH PRO bulk-reuse licence.
- Do not treat the historical counts as current coverage, and do not infer exact VAG engine/gearbox codes or pairings from the pilot statistics.
- The schema-aware XML importer remains validate-only unless written source-specific reuse permission is obtained. Even after permission, parsed engine/gearbox relationships remain candidates until same-variant primary evidence and independent technical review support promotion.
- Keep SBKTS excluded from the importer because its schema can contain VIN and applicant/personal information; the existing importer tests assert those fields are not retained.
- No raw report bytes were downloaded in this review, so no SHA-256 is asserted. The official URL, review date and source revision are recorded as provenance; a file hash may be added only after an authorized raw file is actually retrieved.

## Source and rights decision

The source manifests record the 2023 EEC report, historical pilot period, request-based export mode and completed status. They continue to record:

- permission_status = not_obtained
- bulk reuse = not established
- offline cache = not established / not confirmed
- display and redistribution = not established / not confirmed
- data_ingested = false
- source_snapshot_sha256 = null

No account, paid access, external request or permission application was created or submitted.

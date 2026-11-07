# KBA Germany vehicle identity and type-approval open-data review

Review date: 2026-11-07

## Sources reviewed

### 1. KBA whole-vehicle type-approval list

- Dataset: [Liste der erteilten Typgenehmigungen (Gesamtfahrzeug)](https://www.govdata.de/suche/daten/liste-der-erteilten-typgenehmigungen-gesamtfahrzeug?ids=1cb74abc-7356-49bf-bb07-ef5dd9d7abfb)
- Publisher: Kraftfahrt-Bundesamt (KBA), published via GovData/Mobilithek.
- Scope described by the catalogue: KBA-issued whole-vehicle approvals for M1/N1 under Directive 2007/46/EC and Regulation (EU) 2018/858; the list also identifies the EU Member State that issued the related emissions type approval. The catalogue says the series begins on 2019-01-01 and is updated at intervals.
- Catalogue metadata: published 2023-03-17; last modified 2024-04-11.
- Resource: XLSX, linked from the GovData page to the KBA publication page.
- Acquisition result on 2026-11-07: the official XLSX resource returned HTTP 503. No bytes were acquired; no file hash or data-row count is claimed for this dataset.

### 2. KBA passenger-car manufacturer/trade-name and HSN/TSN reference

- Dataset: [FZ Hersteller Handelsnamen Pkw](https://www.govdata.de/suche/daten/fz-hersteller-handelsnamen-pkw?ids=638594fd-195a-4e03-b91c-f5ea2eacfa39)
- Publisher: Kraftfahrt-Bundesamt (KBA), published via GovData/Mobilithek.
- Description: manufacturer and trade-name overview intended to resolve HSN/TSN values from German vehicle registration documents; the reference date is 1 January of the relevant year.
- Catalogue metadata: published and last modified 2026-01-26. The European Data Portal catalogue reports temporal coverage from 2023-01-01.
- Resource: CSV through the KBA Statistikportal ArcGIS Hub.
- Acquisition result on 2026-11-07: the official ArcGIS Hub legacy download endpoint returned a 65,366,675-byte CSV snapshot. SHA-256: 03bd9f85e384b2b8bcd0e7d80b5f755eca568e9ad1c45e7fb3fe512e7fedc468.
- Exact source columns: Berichtszeitpunkt, Hersteller, Handelsname, Typschlüssel, Bundesland, Anzahl, ZS Anzahl, ObjectId.
- The acquired file has 1,047,991 source rows. An exact manufacturer-value allowlist retains 264,847 VAG-group observations across eight labels: VOLKSWAGEN (D), AUDI (D), AUDI (H), SKODA (CZ), SEAT (E), PORSCHE, BENTLEY (UK) and LAMBORGHINI (I).
- The observed CSV has no HSN column. Typschlüssel is retained verbatim as an unclassified raw KBA type-key field; it is not promoted to HSN or confirmed TSN.
- The live CSV contains annual observations for 2023-01-01, 2024-01-01, 2025-01-01 and 2026-01-01, although the catalogue's temporal-coverage field reports only 2023-01-01. Berichtszeitpunkt is a stock reference date, not a vehicle model year.
- The source-row hash method is SHA-256 over canonical JSON of the original parsed CSV field strings without trimming; source column names are preserved.

## Reuse rights

The GovData dataset pages mark the datasets as freie Nutzung under **Datenlizenz Deutschland – Namensnennung – Version 2.0 (DL-DE BY 2.0)**. The [official licence text](https://www.govdata.de/dl-de/by-2-0) permits commercial and non-commercial copying, display, modification, processing, transfer to third parties, combining with other datasets and integration into products, subject to attribution and a notice where data has been modified.

For the acquired HSN/TSN reference CSV, the source register records commercial use, display, offline caching, bulk reuse and redistribution as allowed under the published licence, with attribution required. No account, paid access or separate permission was obtained or required by that published licence. The licence does not convert the dataset's German registration identity fields into factory fitment evidence.

## Research pack build and independent verification

The separate DE-only pack was built by [KBA research workflow run 7](https://github.com/ismailizmajlov-oss/VAG-TECH-PRO/actions/runs/42328320491), which completed successfully on 2026-11-07.

- Artifact ZIP: 27,883,868 bytes; SHA-256 fd75f0e2c0dd260cf95540f7bcf6cda7d4bfc79948cd332ff2ac3402461281bd.
- Pack manifest SHA-256: 0322d9acc4236e89702377a1c8a90daea253f4b14f86d996fd28bbf505e4c8e2.
- Source-manifest SHA-256: 3aab2daa3c03914001f8b80c92b0e47c1883e3e1ec6eb8589ac3065d2e1c04da.
- SQLite SHA-256: 879ff1f66d3615ee2324b98d4d2defdcfae8018f48fe78f865fc1d3f13a5f4b9.
- Source CSV SHA-256: 03bd9f85e384b2b8bcd0e7d80b5f755eca568e9ad1c45e7fb3fe512e7fedc468.

An independent read-only audit of the downloaded artifact reproduced the ZIP, source CSV, source-manifest, pack-manifest and SQLite hashes. SQLite returned PRAGMA integrity_check=ok, no foreign-key violations and nine expected tables. The database contains 264,847 stock observations, eight manufacturers, 794 trade names, 2,225 raw type keys, 17 federal states and four reference dates. It contains 802 make/trade-name pairs, 4,155 make/type-key pairs and 16,301 make/trade/type/reference-date tuples.

The pack is marked verified_research_only. It is separate from the production vehicle catalog: research_pack_ingested=true, data_ingested=false, product_database_ingested=false and product_import_allowed=false. The source CSV is retained in the CI research artifact; the desktop integration is designed to package the normalized SQLite and licence/provenance material, not a duplicate raw CSV.

## Import and applicability decision

- Market scope is Germany (DE) only. Neither dataset supports Russian/EAEU applicability.
- The KBA stock dataset is an aggregate population count by exact manufacturer label, trade name, raw type key, federal state and annual reference date. It is not a list of individual vehicles or build sheets.
- Typschlüssel is not promoted to HSN or confirmed TSN. It is not an engine code or gearbox code.
- The annual report date is not model year or generation.
- No engine code, gearbox code, engine/gearbox pair, ECU, DTC, wiring, repair procedure, torque value, adaptation, service interval or OEM parts applicability is supplied.
- No exact vehicle fitment, diagnostic execution or repair applicability is inferred.
- The KBA whole-vehicle type-approval XLSX remains unacquired and has no source snapshot hash.
- No production fitment import was performed.

Windows desktop validation run 474 successfully integrated the run-7 KBA pack into the staging desktop source and emitted a verified research-only integration report. The subsequent verifier-patch step failed because its JavaScript replacement string contained an unescaped newline. The patch script was corrected in commit d86c65bb320903ab3f4fb5b7131e5ea9eb66f5e3 and a regression assertion was added in commit 52673aed8e7dc6c21eb551e81bb98c7a2e6d867f. The source register and per-source manifest now agree on the built-but-not-yet-validated desktop-integration status. A fresh successful Windows build/lifecycle is still required; no installer is claimed to contain this KBA pack until that run succeeds.

## Evidence URLs

- [GovData KBA type-approval dataset and licence](https://www.govdata.de/suche/daten/liste-der-erteilten-typgenehmigungen-gesamtfahrzeug?ids=1cb74abc-7356-49bf-bb07-ef5dd9d7abfb)
- [GovData KBA HSN/TSN dataset and licence](https://www.govdata.de/suche/daten/fz-hersteller-handelsnamen-pkw?ids=638594fd-195a-4e03-b91c-f5ea2eacfa39)
- [KBA ArcGIS Hub CSV resource](https://hub.arcgis.com/api/download/v1/items/d277ec18ff1e442597c9411d7c1aaeaa/csv?layers=0)
- [DL-DE BY 2.0 licence text](https://www.govdata.de/dl-de/by-2-0)
- [GovData usage FAQ](https://www.govdata.de/informationen/faq)
- [European Data Portal record for HSN/TSN dataset](https://data.europa.eu/data/datasets/https-www-arcgis-com-home-item-html-id-d277ec18ff1e442597c9411d7c1aaeaa-sublayer-0)

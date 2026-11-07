# KBA Germany vehicle identity and type-approval open-data review

Review date: 2026-11-07

## Sources reviewed

### 1. KBA whole-vehicle type-approval list

- Dataset: [Liste der erteilten Typgenehmigungen (Gesamtfahrzeug)](https://www.govdata.de/suche/daten/liste-der-erteilten-typgenehmigungen-gesamtfahrzeug?ids=1cb74abc-7356-49bf-bb07-ef5dd9d7abfb)
- Publisher: Kraftfahrt-Bundesamt (KBA), published via GovData/Mobilithek.
- Scope described by the catalogue: KBA-issued whole-vehicle approvals for M1/N1 under Directive 2007/46/EC and Regulation (EU) 2018/858; the list also identifies the EU Member State that issued the related emissions type approval. The catalogue says the series begins on 2019-01-01 and is updated at intervals.
- Catalogue metadata: published 2023-03-17; last modified 2024-04-11.
- Resource: XLSX, linked from the GovData page to the KBA publication page.
- Acquisition result on 2026-11-07: the official XLSX resource returned HTTP 503. No bytes were acquired; no file hash or data-row count is claimed.

### 2. KBA passenger-car manufacturer/trade-name and HSN/TSN reference

- Dataset: [FZ Hersteller Handelsnamen Pkw](https://www.govdata.de/suche/daten/fz-hersteller-handelsnamen-pkw?ids=638594fd-195a-4e03-b91c-f5ea2eacfa39)
- Publisher: Kraftfahrt-Bundesamt (KBA), published via GovData/Mobilithek.
- Description: manufacturer and trade-name overview intended to resolve HSN/TSN values from German vehicle registration documents; the reference date is 1 January of the relevant year.
- Catalogue metadata: published and last modified 2026-01-26. The European data portal record identifies temporal coverage 2023-01-01; this is not a model year.
- Resource: CSV, linked through the KBA Statistikportal ArcGIS Hub.
- Acquisition result on 2026-11-07: the CSV download endpoint returned HTTP 400 through the available retrieval path. No bytes were acquired; no file hash or data-row count is claimed.
- European Data Portal cross-check on 2026-11-07: the same ArcGIS item ID is listed under KBA as publisher, with annual frequency, temporal coverage from 2023-01-01, eight distributions including one CSV, and distribution metadata dated 22 May 2026. The catalogue record was added on 29 January 2026 and updated on 26 July 2026. The access URL was not retrievable in this session; this is metadata corroboration only, not a successful download.

## Reuse rights

Both GovData dataset pages explicitly mark the datasets as *freie Nutzung* under **Datenlizenz Deutschland – Namensnennung – Version 2.0 (DL-DE BY 2.0)**. The [official licence text](https://www.govdata.de/dl-de/by-2-0) permits commercial and non-commercial copying, display, modification, processing, transfer to third parties, combining with other datasets and integration into products. Required conditions are attribution to the provider, identification of DL-DE BY 2.0 and the dataset URI, plus a notice where data has been modified.

The source register records those rights as cleared under the published licence. No account, paid access or separate permission was obtained or required by the published licence.

## Import and applicability decision

- Both sources are registered as rights-cleared metadata candidates, but **no data has been imported** because neither source file was retrieved and its exact schema could not be checked.
- `source_snapshot_sha256` and file SHA-256 are deliberately null. A metadata page or URL is not a downloaded data snapshot.
- Market scope is Germany (`DE`) only. Neither source supports Russian/EAEU applicability.
- The KBA approval list is an approval-identity source, not a vehicle build sheet. It does not establish an individual vehicle's factory configuration.
- HSN/TSN are German registration identity keys. They are not engine codes, gearbox codes, or model-year/generation proof.
- Do not infer VAG engine/gearbox pairs, ECU fitment, DTC applicability, repair procedures, or exact model generation from either dataset.
- After the official resources become retrievable, validate the CSV/XLSX columns, filter VAG makes only by exact source values, preserve source-row hashes and temporal coverage, and keep all matches in a separate DE research namespace until independently corroborated.

## Evidence URLs

- [GovData KBA type-approval dataset and licence](https://www.govdata.de/suche/daten/liste-der-erteilten-typgenehmigungen-gesamtfahrzeug?ids=1cb74abc-7356-49bf-bb07-ef5dd9d7abfb)
- [GovData KBA HSN/TSN dataset and licence](https://www.govdata.de/suche/daten/fz-hersteller-handelsnamen-pkw?ids=638594fd-195a-4e03-b91c-f5ea2eacfa39)
- [DL-DE BY 2.0 licence text](https://www.govdata.de/dl-de/by-2-0)
- [GovData usage FAQ](https://www.govdata.de/informationen/faq)
- [European data portal record for HSN/TSN dataset](https://data.europa.eu/data/datasets/https-www-arcgis-com-home-item-html-id-d277ec18ff1e442597c9411d7c1aaeaa-sublayer-0)

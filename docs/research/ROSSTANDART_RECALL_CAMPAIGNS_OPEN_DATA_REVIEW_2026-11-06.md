# Rosstandart recall-campaign open-data source review — 2026-11-06

## Decision

**Register as a high-priority Russian-market candidate; do not import yet.** The official Rosstandart dataset route is identifiable and historical public statements support non-commercial service use, but the current official landing page, archive, file schema, dataset-linked terms and source snapshot could not be retrieved during this review. No file was downloaded, no VIN was copied, and no SQLite rows were added.

If the current dataset page links the applicable Open Government Commission Typical Open Data Terms, those terms may permit reproduction, distribution and adaptation (including commercial use) with the required attribution. That link must be verified on the actual dataset page; a general terms page or a third-party report is not enough to approve offline packaging.

## Source and reported content

- Official landing page: https://easy.gost.ru/opendata/7706406291-recallcampaigns/
- Official archive: https://easy.gost.ru/opendata/7706406291-recallcampaigns/archive/
- Official Rosstandart open-data portal: https://www.gost.ru/opendata
- The source is reported as a machine-readable register of wheel vehicles participating in recall campaigns. Reported fields include VIN, manufacturer, make, commercial name, recall reason, remedial work, official news link, repair-completion date and place.
- A 2019 report quotes Rosstandart Deputy Head Alexey Kuleshov describing the register as open data available for non-commercial services: https://www.afanasy.biz/news/road_newsn/143585
- A 2023 report of a Rosstandart/Polylog webinar describes the open dataset as reusable by business services and intended to support recall information services: https://www.normacs.info/news/73140
- An independent 2026-08-30 review reports 7,044,734 rows, 5,387,610 unique VINs and 79 makes in the observed snapshot. These are third-party counts, not a verified current official snapshot: https://glav-auto.ru/news/kak-proverit-otzyvnuyu-kampaniyu

## Rights analysis

The Open Government Commission Typical Open Data Terms were approved by protocol No. 6 dated 2016-09-19. The published text describes rights to reproduce, distribute and adapt open data, including commercial use, subject to attribution and conditions against distortion. Reference: https://data.gov.ru/information-usage

However, the current Rosstandart dataset page was not retrievable, so the presence of a dataset-specific hyperlink to those terms could not be verified. Historical statements about non-commercial use are useful evidence but do not prove that the current dataset page grants offline caching and redistribution rights for a packaged SQLite database. Accordingly:

- non-commercial service use is historically supported by a public statement attributed to Rosstandart;
- commercial use, offline caching, bulk extraction and redistribution in a Windows installer are **not approved by this review**;
- no data is to be downloaded, cached, displayed or packaged until the current official page and its linked terms are verified;
- no permission request, account creation or paid access was initiated.

## Applicability and safe future extraction

The dataset is a recall-campaign source, not a VAG factory workshop manual. Its reported fields do not establish exact VAG engine codes, gearbox codes, engine/gearbox pairs, ECU identities, DTC applicability, wiring, pinouts, torque values, adaptations or service schedules.

If rights and the actual schema are later confirmed, evaluate a separate RU recall-campaign layer only. Exclude VIN-level rows and repair-completion/dealer-location fields. Do not convert campaign remedy text into a generic or OEM repair procedure. Any model/year scope must remain at the precision explicitly supported by the source; free-text descriptions are not exact configuration evidence.

## Snapshot and provenance

- Review date: 2026-11-06
- Official file retrieved: no
- Source revision: not verified
- Source file size: unknown
- Source snapshot SHA-256: null (not downloaded; no hash fabricated)
- Data ingested: false
- Product import decision: blocked pending current official terms, schema and snapshot verification

## Evidence links

- Official dataset: https://easy.gost.ru/opendata/7706406291-recallcampaigns/
- Official archive: https://easy.gost.ru/opendata/7706406291-recallcampaigns/archive/
- Rosstandart portal: https://www.gost.ru/opendata
- 2019 Rosstandart statement report: https://www.afanasy.biz/news/road_newsn/143585
- 2023 Rosstandart webinar report: https://www.normacs.info/news/73140
- 2026 independent schema/snapshot review: https://glav-auto.ru/news/kak-proverit-otzyvnuyu-kampaniyu
- Typical open-data terms: https://data.gov.ru/information-usage

# ELPTS electronic SBKTS public UI review — 10 November 2026

## Decision

Register the electronic SBKTS search page as a separate **discovery-only** source. Do not treat it as an OTTS/OTSH source, do not import records, and do not download certificates or PDFs. No bulk-reuse, commercial-use, offline-cache, third-party display or redistribution rights have been established.

The source is not added to the Russian/EAEU OTTS importer manifest. SBKTS is an individual-vehicle safety certificate; it must not be joined to OTTS type-approval data or used to infer factory engine/gearbox fitment.

## Official page and observation

- Public page: https://docs.elpts.ru/ncher/esbkts
- Page title: «Реестр свидетельств о безопасности конструкции транспортного средства, оформленных в электронном виде».
- Review date: 2026-11-10.
- The search-indexed preview available on the review date showed 2,799,410 total certificates and 155 results for the displayed 2026-11-04 date filter.
- One non-personal example in that preview showed make `VOLKSWAGEN` and vehicle type `FV6462HADCG`.
- The indexed preview listed certificate number, make, vehicle type, status, issue date, applicant, manufacturer, testing laboratory, environmental class, blank numbers and a PDF link.

The page is dynamic. Direct page inspection returned the interface template and dynamic placeholders rather than a complete record export. The counts and example above are therefore recorded only as **search-indexed discovery observations**, not as a pinned source snapshot, a complete dataset, or independently captured registry records.

## Privacy boundary

SBKTS records concern individual vehicles. The public interface exposes an applicant field, and linked certificate PDFs may contain personal or vehicle-identifying information. This project did not retrieve any personal values, VINs, registration plates, owner identities, addresses, contact details or PDF contents.

Any future review must exclude at minimum:
- applicant names and other personal identifiers;
- VINs and registration plates;
- owner identity, postal addresses and contact details;
- certificate PDF contents unless separately authorized and privacy-reviewed.

No individual-vehicle data should be retained in the VAG TECH PRO offline database under this discovery entry.

## Technical applicability boundary

The preview's make and vehicle-type fields are document metadata only. They do not establish:
- an OTTS/OTSH type, variant or version;
- a VAG factory engine code or gearbox code;
- an exact engine/gearbox pair;
- model generation or production-year applicability;
- ECU, DTC, test-plan, repair, wiring, pinout, torque, adaptation or service applicability.

The Volkswagen type string `FV6462HADCG` is preserved only as a non-personal example of a public UI field. It is not normalized to a VAG platform, model, generation or factory type code.

## Rights and acquisition state

A publicly reachable search interface does not itself grant rights to bulk extraction, persistent SQLite storage, offline caching, third-party display, commercial use or redistribution. No dataset-specific licence or written permission was found during this review.

- Raw registry records downloaded: 0.
- Certificate PDFs downloaded: 0.
- Personal values retrieved or retained: 0.
- Records imported: 0.
- Source snapshot SHA-256: intentionally null; no raw source bytes were retrieved.
- Permission request sent: no.
- External account, paid service or API access created: no.

## References

- Official electronic SBKTS search page: https://docs.elpts.ru/ncher/esbkts
- ELPTS homepage and register navigation: https://elpts.ru/
- EEC explanatory report on TR TS 018/2011: https://eec.eaeunion.org/upload/iblock/33d/_Otch-o-NIR-2-etap_itog_T-1-i-T-2.pdf (describes SBKTS as confirming an individual vehicle).
- ELPTS tariff-plan amendment notice (software-use terms, not a dataset licence): https://elpts.ru/uvedomlenie-o-vnesenii-izmenenij-v-tarifnyj-plan-k-oferte-pravo-ispolzovaniya-po/

## Product decision

Keep `elpts-esbkts-public-query` in the central source register as `data_ingested=false`, `product_import_allowed=false`, rights `not_established`, and no source hash. Reconsider only after written permission from the appropriate rights holder explicitly covers the intended data fields, bulk retrieval, privacy-safe processing, local storage, offline display and redistribution. Even then, SBKTS must remain a separate document namespace and cannot independently confirm factory VAG fitment.

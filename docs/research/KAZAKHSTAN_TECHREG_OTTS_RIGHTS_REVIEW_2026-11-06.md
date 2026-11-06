# Kazakhstan TechReg OTTS public registry — rights and coverage review (2026-11-06)

## Finding

A Kazakhstan technical-regulation portal exposes a public OTTS/OTSH search route:

- Legacy list: https://techreg.kezekte.kz/ru/cert/ot-registry/old/list
- Current list: https://techreg.kezekte.kz/ru/cert/ot-registry/list
- Project information: https://techreg.kezekte.kz/kz/cert/info

The public pages identify the Committee of Technical Regulation and Metrology of the Ministry of Trade and Integration of the Republic of Kazakhstan and National Accreditation Center contact information. The exact portal operator and legal ownership were not independently established.

## Observed coverage

- The legacy list page shows 273 records and fields including approval number, issue/registry dates, validity, make, commercial name, certification body and applicant/address.
- A search-index snapshot of the new list showed zero records, but its crawl was about three weeks old; this is not a current or authoritative corpus count.
- A legacy detail page (record 269) demonstrates additional fields such as assembly plant, vehicle equipment and a VIN section. It does not establish VAG applicability.
- No VAG-specific record, exact engine code, gearbox code, ECU mapping or repair applicability was independently identified.

## Rights and decision

No dataset-specific open licence, API contract, bulk-export permission, offline-cache permission, commercial display right or redistribution permission was found in this review. Public search visibility is not treated as permission to copy records into VAG TECH PRO.

**Decision:** discovery-only / permission required. No data were downloaded, cached or imported. Do not automate, bulk extract, bundle, display or redistribute records until the operator and applicable reuse rights are confirmed in writing. Detailed records may contain VIN-related and applicant/contact information; any future processing also requires privacy and data-minimisation review.

The source is recorded in both the central VAG source-rights register and the Russian/EAEU source register with `data_ingested=false`.

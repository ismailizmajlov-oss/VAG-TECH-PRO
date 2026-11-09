# ELPTS paid-report forms and eligibility review — 2026-11-09

## Official access route

The official [ELPTS homepage](https://elpts.ru/) states that AS SEP paid statistical reports are supplied to system participants under service agreements. For AS SEP reports, the page says a separate additional agreement is concluded after a request through the Help Center under the category «АС СЭП – Платные отчеты». For AS EOTTS, it describes reports for certification bodies or applicant organizations under an invoice-contract after a request; availability is subject to prior approval, and the operator may return a negative response.

The official [paid-report forms page](https://elpts.ru/formy-platnyh-otchetov-2/) links a 20-page appendix to AO «Электронный паспорт» Order No. 10/81-26 dated 2026-10-02:
https://elpts.ru/wp-content/uploads/2026/10/prilozhenie-k-prikazu-ot-02.10.2026-%E2%84%96-10_81-26.pdf

The appendix was inspected in the browser on 2026-11-09. The PDF bytes were not downloaded to the project and no file SHA-256 is claimed.

## Report forms relevant to VAG source discovery

| Form | Frequency | Eligibility / scope | Relevant fields | Price per row incl. VAT |
|---|---|---|---|---:|
| R | Daily | Participant is the manufacturer, foreign-manufacturer representative, or acts under that organization's authorization | Make, commercial name, fuel, gearbox make/type, registration-action details | 15 RUB |
| R3 | Weekly | Same participant restriction | Base/final vehicle descriptors, VIN, EPTS number, manufacturer, OTTS number and registry-entry date, category and purpose | 180 RUB |
| R4 | Weekly | Same participant restriction | Base/final vehicle descriptors, EPTS number, manufacturer, OTTS number and registry-entry date, category and purpose | 120 RUB |

The report R form's gearbox field is only «make/type»; it does not establish a VAG factory gearbox code or an exact engine/gearbox pair. The R3 and R4 forms contain OTTS identity and vehicle-description fields, but no engine code, gearbox code, ECU identity or exact powertrain pairing.

R3 and R4 are not a general bulk export of the national OTTS register. The appendix limits the reports to vehicles whose electronic passports identify the participant as manufacturer, foreign-manufacturer representative, or an organization acting under that party's authorization. The homepage separately states that report delivery is contract-based.

## Rights and product decision

The published report form, eligibility terms and per-row fees are evidence of a paid participant-scoped service, not a data-reuse licence. They do not grant VAG TECH PRO permission for third-party display, persistent SQLite caching, offline distribution, bulk reuse or redistribution. Any such rights would need to be stated explicitly in a separate written agreement covering this product and its intended distribution.

The route may be relevant only if the owner can establish the required manufacturer/representative authorization and decides to request a quote. No request was sent, no account was created, no agreement or paid terms were accepted, and no report data were acquired. All source rights remain not established; permission_status=not_obtained; data_ingested=false; product_import_allowed=false.

## Sources

- ELPTS homepage: https://elpts.ru/
- ELPTS paid-report forms: https://elpts.ru/formy-platnyh-otchetov-2/
- Appendix to Order No. 10/81-26, dated 2026-10-02: https://elpts.ru/wp-content/uploads/2026/10/prilozhenie-k-prikazu-ot-02.10.2026-%E2%84%96-10_81-26.pdf

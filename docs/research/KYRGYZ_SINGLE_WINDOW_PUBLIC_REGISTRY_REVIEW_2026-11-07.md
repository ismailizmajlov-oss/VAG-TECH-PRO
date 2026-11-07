# Kyrgyz Single Window public vehicle-approval registry review — 2026-11-07

## Decision

Register the new State Enterprise «Single Window» public registry as an **EAEU-member-state discovery source only**. The operator describes a no-login public registry pilot that includes OTTS and OTSH, but no dataset-specific reuse licence, documented API or bulk-export contract was found. Do not import or cache records.

This source is distinct from the older `sbkts.trade.kg/otts` interface, which was previously observed behind a CAPTCHA. No CAPTCHA bypass was attempted.

## What the official operator confirms

- The [official portal](https://trade.kg/) says its public registers are open without registration. Its current homepage describes the OTTS/OTSH registry search by approval number, make and model.
- The [public-registry project page](https://trade.kg/projects/public-registry) describes a pilot, says no login is required, and says personal data are not displayed. It links to [smart.trade.kg/registry](https://smart.trade.kg/registry?lng=ru) for public lookup by document number or VIN.
- The separate [cert.trade.kg landing page](https://cert.trade.kg/) displays UI counters of one OTTS document and zero OTSH documents. These are portal counters only; they are not verified, complete or stable public-register corpus counts.
- The [vehicle-approval project page](https://trade.kg/projects/vehicles) identifies [car.trade.kg](https://car.trade.kg/) as the application system for certification bodies and experts. It describes application fields for the vehicle/chassis, engine and other characteristics, and says issued documents are published to the public registry.
- The [24 August 2026 announcement](https://trade.kg/news/24-avgusta-2026-goda-v-promyshlennoj-srede-zapuskaetsya-informaczionnaya-sistema) describes the OTTS/OTSH issuance workflow and publication of approved documents into an electronic register.

## Important separation of scopes

The engine fields described on the certification application form are input fields for a restricted professional workflow. They are **not evidence that the public registry exposes engine designations or factory codes**. The public record schema was not retrieved. No exact VAG engine code, gearbox code, engine/gearbox pair, ECU, DTC or repair applicability was established.

The register is Kyrgyz national data in the EAEU TR TS 018/2011 context. It is not Russian-market evidence and must not be promoted to RU applicability.

## Rights and acquisition

- No dataset-specific open licence or written permission for automated extraction, bulk export, offline caching, third-party display or redistribution was identified.
- The no-login public search interface is not treated as permission to scrape or mirror the registry.
- No documented API, bulk export contract, reproducible snapshot or dataset revision was identified.
- No records were downloaded. No source-file hash or snapshot SHA-256 is claimed.
- No VIN, applicant, address, owner or other personal data were collected.
- The source remains `permission_required`, `data_ingested=false`, and `product_import_allowed=false`.


## Statutory access and reuse review — Digital Code of Kyrgyzstan (2026-11-07)

The legal position is more nuanced than simply "no legal basis found". The official State Agency for Personal Data Protection publishes the **Digital Code of the Kyrgyz Republic, No. 178 of 31 July 2025**. The enabling Law No. 179 of the same date was published in the official newspaper *Erkin-Too* on 5 August 2025, No. 58 (3714), and states that the Code enters into force six months after official publication. The calculated effective date is **5 February 2026**.

Relevant provisions reviewed:

- **Article 1(14)** defines a state/municipal digital resource as a digital resource created to provide state services by state or municipal bodies.
- **Article 1(39)** defines open data as machine-readable data available without restrictions on reuse.
- **Article 25** distinguishes digital data from digital records and preserves the digital rights of the record owner.
- **Article 26** gives the digital-resource owner rights to control access and distribute data from the resource.
- **Article 59** permits use of digital data by any person subject to intellectual-property rights and statutory restrictions; digital records are presumed publicly accessible unless metadata restricts access, and record metadata may require attribution.
- **Article 60** says access to digital records is on conditions set by the record owner or resource owner; record metadata must identify the owner.
- **Article 62** says records from state and municipal digital resources are provided free and without restrictions unless otherwise established by law.

The official Single Window portal identifies its operator as a state enterprise under the State Customs Service and advertises six public registers without registration. That establishes a real public-lookup route. It does **not** by itself establish that this specific register is formally a state/municipal digital resource under Article 1(14), that its records are machine-readable open data under Article 1(39), or that a third party may make a bulk copy, keep an offline cache, display the records in another product or redistribute the records. The actual record metadata, record owner and any attribution condition were not retrieved. The JavaScript lookup page did not expose a documented API, bulk export or machine-readable schema in this review.

**Decision unchanged:** statutory public-access and data-use provisions are now recorded, but product reuse is not cleared. Keep `permission_status=not_obtained`, `product_import_allowed=false`, `data_ingested=false`, and the source in discovery-only status. Do not automate extraction, cache or package records until the operator confirms the register's legal classification, record-owner/metadata terms and the exact reuse scope, or a formal legal review clears those points. No VIN or personal data were collected.

Official legal evidence:
1. [Digital Code of the Kyrgyz Republic, No. 178 — State Agency for Personal Data Protection](https://reestr.dpa.gov.kg/ru/npa/59), reviewed 7 November 2026; definitions 1(14), 1(39), Articles 25, 26, 59, 60 and 62.
2. [Law No. 179 on Enactment of the Digital Code — State Agency for Personal Data Protection](https://reestr.dpa.gov.kg/ru/npa/60), reviewed 7 November 2026; official publication date and six-month commencement rule.

## Evidence reviewed

1. [Official Single Window homepage](https://trade.kg/) — reviewed 2026-11-07; public registers without login and OTTS/OTSH search fields.
2. [CertTrade landing page](https://cert.trade.kg/) — reviewed 2026-11-07; one-OTTS and zero-OTSH UI counters, not verified corpus counts.
3. [Public registry project page](https://trade.kg/projects/public-registry) — reviewed 2026-11-07; pilot status, no-login lookup and personal-data display statement.
4. [Public registry application](https://smart.trade.kg/registry?lng=ru) — identified from the official link; JavaScript page did not expose a readable record schema in this review.
5. [SBKTS/OTTS/OTSH application system description](https://trade.kg/projects/vehicles) — reviewed 2026-11-07; professional user scope, application workflow and engine/vehicle form fields.
6. [Official 24 August 2026 launch announcement](https://trade.kg/news/24-avgusta-2026-goda-v-promyshlennoj-srede-zapuskaetsya-informaczionnaya-sistema) — reviewed 2026-11-07; electronic issuance and registry publication workflow.

## Re-entry criteria

Reconsider ingestion only after the operator provides (a) a documented public-record schema or supported API, (b) a reproducible dataset or authorized export method, and (c) explicit rights covering bulk retrieval, offline caching, third-party display and redistribution. Any future import must field-allowlist document-level non-personal data, retain source and row hashes, and keep OTTS/OTSH/SBKTS document types separate.

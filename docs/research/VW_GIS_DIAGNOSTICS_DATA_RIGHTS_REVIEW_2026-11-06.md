# Volkswagen Group Info Services — Diagnostics Data (OEM ODX) rights review

Review date: 2026-11-06

## Source identity and technical value

- Provider/operator: Volkswagen Group Info Services AG (GIS), Wolfsburg, Germany.
- Product: **Diagnostics Data**.
- Official product page: https://www.drivesomethinggreater.com/solutions/all-solutions/Diagnostics-Data
- API documentation and protected ZIP download page: https://www.drivesomethinggreater.com/developer-hub/api-specifications/diagnostics-data-api-downloads
- Data Hub terms: https://www.drivesomethinggreater.com/service/terms-of-use
- Provider imprint: https://www.drivesomethinggreater.com/service/Imprint

GIS states that the DTC descriptions originate directly from the R&D departments of Volkswagen Group brands. The product covers Volkswagen Passenger Cars, Volkswagen Commercial Vehicles, Audi, Škoda, SEAT, CUPRA, Bentley and Lamborghini. The Europe package covers 70 EU-approved platforms; a worldwide package is stated to cover 75 platforms. Each ECU is delivered as an individual ODX file with potential DTCs, plain-text descriptions and reference values. Updates are published twice a year, in May and November.

This is the strongest official route identified so far for VAG-specific OEM DTC/ECU data. It is not a public open dataset.

## Access and eligibility restrictions

The published product page states:

- The product is intended for commercial providers in the vehicle diagnostics/service market.
- Customer headquarters must be in the EEA, Switzerland or the UK.
- An SFD agreement is required.
- A second agreement with Volkswagen AG is required for encryption keys.
- The Data Hub currently provides static ZIP downloads; an automated API is under development.
- The download page requires an API key.

The Data Hub terms state that:

- Access requires registration with a VW AG ONE Business ID and company information/proof of incorporation.
- Data subscriptions require a separate Data Distribution Agreement (DDA); subscription pricing is set out in that agreement.
- Data Hub use rights are non-exclusive, non-sublicensable and non-transferable, limited to the registered customer/users and contract purpose.
- Downloading, reproducing, transmitting, selling or distributing Data Hub contents without specific and express written permission is prohibited.
- The terms do not grant a general public licence to cache or redistribute the ODX/DTC data.

The product page says authorized customers may use the data in their own products/tools under the applicable regulatory and contractual framework, while further use and remarketing are not permitted. The precise scope of offline embedding and distribution to VAG TECH PRO users must therefore be stated expressly in the DDA or a separate written permission.

## Rights decision

**No import, no account creation, no subscription, no API-key request, no download and no payment.**

The source is recorded as `official_source_identified_contractual_access_not_obtained`, not as an approved data source. No data files, DTC rows, ODX content, encryption keys or logos were copied.

The public product page does not establish:
- eligibility of a Russian-headquartered or non-commercial project;
- permission to cache the ODX files in an offline SQLite database;
- permission to redistribute DTC descriptions or reference values inside an installer;
- Russian/EAEU market coverage for the Europe package;
- whether a worldwide package can be licensed for this project and territory.

## Owner-controlled action required

Reconsider only if the owner independently confirms an eligible contracting entity and explicitly approves the commercial/legal terms. Before any import, obtain written confirmation from GIS/VW AG covering:

1. VAG TECH PRO as an authorized product and its intended distribution model;
2. persistent offline storage and packaging of ODX-derived DTC/reference data;
3. display to end users and redistribution in installers or database updates;
4. allowed territories, especially RU/EAEU;
5. retention and deletion obligations after contract termination;
6. SFD/SFD2 and encryption-key obligations, if diagnostic execution is ever added.

Do not create a ONE Business ID, accept terms, sign a DDA/SFD agreement, request API keys, pay or download data on the owner's behalf.

## Project status

The source is registered in `data/source-manifests/vag-factory-source-register.json` as `vw-gis-diagnostics-data-oem-odx`. It remains unavailable for product import, display or offline caching. This is an external licensing/eligibility blocker, not a technical import failure.

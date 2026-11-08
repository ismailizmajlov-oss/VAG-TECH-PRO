# Volkswagen OKAPI — rights, scope and market review (2026-11-09)

## Decision

**Status: metadata-only candidate; no data ingestion or offline bundling.**

Volkswagen AG's OKAPI is a potentially valuable primary source for official market-specific VAG model, vehicle-type and option identity. It is not a general repair-data licence and is not yet an approved source for VAG TECH PRO. The published contract restricts the purpose to creating vehicle configurations, checking configuration buildability and determining WLTP values. Access is company-only, requires a written access request and Volkswagen approval, and can be refused at Volkswagen's discretion.

No account, client credentials, access token, API request, paid access or contract acceptance was created or performed for this review. No Product Data was downloaded, cached or imported. No source snapshot SHA-256 exists.

## Official data surface

The public overview identifies these supported Volkswagen Group brands:

- Audi
- SEAT
- ŠKODA
- Volkswagen Commercial Vehicles
- Volkswagen

The overview describes the API as exposing current product data, configurations, buildability and WLTP values. It states that only officially type-approved data is available. It also warns that product data is customer information, not binding, and that a configurable vehicle is not necessarily available in production.

The documented catalog endpoints provide country-specific:

- countries;
- brands;
- models;
- vehicle types;
- options.

The example type payload includes fields such as `base_type`, `model_year`, `version` and a type code. Type descriptions may contain engine/transmission wording (for example, displacement, fuel type, power and gear-count text), but those descriptions are not factory engine codes, factory gearbox codes, or proof of an exact engine/gearbox pairing. No public schema evidence was found for ECU identifiers, DTC definitions, repair procedures, wiring diagrams, pinouts, tightening specifications, adaptations or service schedules.

## Market scope

The public overview's displayed, explicitly non-exhaustive market list is:

`AR, AU, BH, BE, BR, IC, CN, CY, CZ, DK, EE, FI, FR, DE, GR, IS, IE, IT, JP, JO, KW, LV, LB, LT, LU, MT, MX, MD, NL, NO, OM, PL, PT, QA, RS, ZA, ES, SE, CH, TW, TR, UA, AE, GB`.

The EAEU member identifiers `AM`, `BY`, `KZ`, `KG` and `RU` are not displayed in that public list. Because Volkswagen explicitly says the list is not complete, this is **not** evidence that those markets are unsupported. The authenticated `/countries` response must be checked after access is approved. Until then, the source's effective market scope remains `UNKNOWN`; no RU/EAEU coverage is claimed.

## Contract and rights

The current published terms were rechecked on 2026-11-09:

1. The contract is between Volkswagen AG and a company using OKAPI. It begins only after Volkswagen approves the access request.
2. The applicant must provide company name, address, contact person and purpose by email. Volkswagen may reject an application at its discretion.
3. Access requires a Client ID, Client Secret and OAuth access token.
4. Volkswagen retains ownership of OKAPI and Product Data.
5. The grant is non-exclusive, non-transferable, revocable and non-sublicensable, for the sole purpose stated in the terms and through registered applications.
6. Registered applications may display and evaluate Product Data; the terms expressly permit disclosure of Product Data and derived results to third parties, subject to the contract.
7. The current service is described as free, but Volkswagen reserves the right to introduce a reasonable fee and later price changes.
8. The caching guide documents ETags, conditional requests and catalog-update timestamps for refreshing a cache in the user's application. It does not expressly grant redistribution of a pre-populated offline SQLite database inside a third-party Windows installer.

The terms therefore do not establish the rights needed to bundle a persistent offline VAG identity database with VAG TECH PRO, nor do they authorize repurposing configurator data as repair guidance. Written clarification is required for offline retention, installer redistribution, end-user access after the API contract ends, and use outside the stated configurator/buildability/WLTP purpose.

## VAG TECH PRO handling

- Keep the source in `permission_required` / metadata-only status.
- Keep `data_ingested=false`, `product_import_allowed=false`, and `source_snapshot_sha256=null`.
- Do not create accounts, request credentials, call the API, accept paid terms or contact Volkswagen on the owner's behalf.
- Do not use the public market list as proof of RU/EAEU absence or presence.
- Do not turn type-description text into factory engine/gearbox codes.
- Do not infer exact pairings, ECU applicability or repair applicability from a model/type label.
- If the owner later obtains company access and explicit written permission, pin the authenticated country list, API revision, response ETags and content-update headers; hash actual response bytes; retain market, model, type, option and revision provenance; and import only fields whose use and offline distribution are expressly authorized.
- Any exact powertrain relationship must be supported by the same official type/variant evidence or separate primary evidence and reviewed independently.

## Owner action required

If this source is to be pursued, the owner must decide whether a qualifying legal entity can apply. The request must disclose the intended application and ask Volkswagen to confirm, in writing, whether the proposed use includes a repair-workshop reference application, offline caching, inclusion of selected data in a Windows installer, end-user redistribution, and retention of cached data after access termination. No request has been sent.

## Official evidence

- [OKAPI Terms and Conditions of Use](https://productdata.volkswagenag.com/condition-of-use.html) — company access and approval, permitted purpose, registered application, ownership, third-party disclosure, pricing and revocable/non-sublicensable grant.
- [OKAPI overview](https://productdata.volkswagenag.com/overview.html) — supported brands, public market list and official type-approval scope.
- [Product data catalog](https://productdata.volkswagenag.com/product-catalog.html) — countries, brands, models, types and options.
- [Caching and update guide](https://productdata.volkswagenag.com/data-update.html) — ETag and catalog-content update mechanism.
- [Quick start](https://productdata.volkswagenag.com/quick-start.html) — company-only access request and credentials.
- [Tutorial](https://productdata.volkswagenag.com/tutorial.html) — country-specific catalog flow.

**Conclusion:** OKAPI is a high-value official identity/configuration lead for markets that Volkswagen confirms, but it does not currently fill the Russian/EAEU or repair-data gap. No data are admitted to production SQLite.

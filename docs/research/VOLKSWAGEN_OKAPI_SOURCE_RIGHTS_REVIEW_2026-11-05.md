# Volkswagen OKAPI — source rights and offline-cache review

Review date: 2026-11-05  
Publisher: Volkswagen AG  
Source: https://productdata.volkswagenag.com/

## What the public documentation establishes

- OKAPI is an official Volkswagen product-data API for companies. Registered applications may display and evaluate product data for configuration, buildability checks and WLTP calculations. The terms say the contractual relationship starts only after Volkswagen approves an access request: [Terms, §§ I–II](https://productdata.volkswagenag.com/condition-of-use.html).
- Access requires a company request containing the company's full name/address, a contact person and purpose. Volkswagen may reject a request at its discretion. A Client ID and Client Secret are required; no credentials or account were created and no API call was made: [Terms, § III](https://productdata.volkswagenag.com/condition-of-use.html).
- Volkswagen retains ownership of OKAPI and Product Data. The contractual right is non-exclusive, non-transferable, revocable and non-sublicensable for the duration of the contract. The terms do allow the user to disclose Product Data or results to third parties, but do not expressly define distribution of a bundled offline SQLite database or post-termination retention: [Terms, § IV](https://productdata.volkswagenag.com/condition-of-use.html).
- The public guide explicitly documents caching product data on the user's side and provides ETag and content-last-update headers to refresh caches: [Data update guide](https://productdata.volkswagenag.com/data-update.html). This establishes a cache mechanism, not an unambiguous perpetual/offline redistribution licence.
- OKAPI is currently free, but Volkswagen reserves the right to introduce fees: [Terms, § V](https://productdata.volkswagenag.com/condition-of-use.html).
- The catalog exposes markets, brands, models, types and options. Type records can contain model year, base type and type code; sample descriptions contain engine/gearbox descriptions such as displacement, power and number of gears. The documentation does not establish that these text labels are factory engine codes or gearbox codes: [Product catalog guide](https://productdata.volkswagenag.com/product-catalog.html).
- The public market list includes Germany, Ukraine, Moldova and Turkey but does not list Russia, Kazakhstan or Belarus in the reviewed list. Volkswagen says the displayed list is not exhaustive; without credentials the authenticated `/countries` endpoint could not be checked. RU/EAEU coverage therefore remains UNKNOWN, not confirmed absent.

## Product decision

Keep OKAPI as a high-value official-source lead with `permission_required`. Do not create an external account, send an access request, accept terms, pay fees or download product data in this automation run.

Before importing or bundling any OKAPI data, the owner must obtain credentials and written confirmation covering:
1. use in the registered VAG TECH PRO Windows desktop application;
2. persistent offline caching in local SQLite;
3. distribution of the cached data inside an autonomous installer/database to third-party users;
4. retention and continued display after contract termination or credential revocation;
5. supported Russian/EAEU markets and the exact fields returned for vehicle type, engine and transmission identifiers.

Even after access is granted, treat model/type descriptions as descriptive product data. Do not infer factory engine or gearbox codes from free-text descriptions or type/option codes without explicit field-level evidence.

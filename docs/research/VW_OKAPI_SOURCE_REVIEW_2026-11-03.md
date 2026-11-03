# Volkswagen OKAPI source review — 2026-11-03

## Decision

Register Volkswagen OKAPI as an **official OEM product-configuration source candidate**, not as an approved repair-data source. The source is promising for a future market-aware, VIN-optional model/type selector, but it is not currently importable: no company access request has been approved, no credentials have been supplied, no authenticated country list has been inspected, and offline distribution rights for a cached database are not explicit.

No account, API key, subscription, request, or external contact was created or made.

## Verified official terms

The official Volkswagen terms state that:

- OKAPI gives registered applications access to Volkswagen product data for vehicle configurations and permits those applications to display and evaluate that data.
- The stated purpose is creating configurations, checking buildability, and determining WLTP values.
- Volkswagen retains ownership of OKAPI and the product data.
- The grant is non-exclusive, non-transferable, revocable, and non-sublicensable.
- A company must request access by email with its company details, contact person, and purpose; Volkswagen may reject the request at its discretion.
- Credentials consist of a Client ID and Client Secret and must be kept confidential.
- Product data and evaluations may be disclosed to third parties, subject to the terms.
- The API is currently free, but Volkswagen reserves the right to introduce a fee.

Official terms: https://productdata.volkswagenag.com/condition-of-use.html

## Caching and offline limitations

Volkswagen's official caching guide documents ETag, conditional requests (If-None-Match), and catalog last-update headers. It describes caching product data on the user's side and refreshing it when the ETag or catalog timestamp changes.

Official caching guide: https://productdata.volkswagenag.com/data-update.html

This is evidence that caching is a supported integration pattern for an approved application. It is **not treated here as an unambiguous grant to redistribute a prebuilt offline database to unrelated third parties**. The contract also says the license is non-transferable and non-sublicensable. Before shipping a cached pack, obtain written confirmation that the specific Windows desktop application may retain the relevant fields offline and distribute those cached fields to its end users after the user has fetched them through its registered application.

## What the documented API can and cannot establish

The public documentation describes country, brand, model, vehicle-type, and option endpoints, plus buildability, WLTP, and order information. Model records include model name and year; vehicle types have a name that may include engine/trim designation.

The public schema does not establish factory engine codes, gearbox codes, ECU identities, PR-code decoding, workshop procedures, wiring diagrams, torque values, DTCs, or OEM parts applicability. A new-car configuration's buildability is not proof of the original configuration of an existing used vehicle.

Official tutorial: https://productdata.volkswagenag.com/tutorial.html

## Market scope

The API's country list is authenticated. Since no credentials were available, no country list was retrieved. RU and EAEU coverage are therefore **unknown**, not assumed. Do not create RU/EAEU fitment rows from this source until the returned country list and the relevant market catalog are observed and preserved with retrieval timestamp, response hash, and API revision.

## Integration gate

The source manifest at data/source-manifests/vw-okapi-product-catalog.json keeps the source in permission_required and records:

- ownership and contract scope;
- the access-approval and credential requirements;
- the documented caching mechanism and the unresolved offline redistribution question;
- unknown RU/EAEU market coverage;
- the exact limits of model/type identity precision;
- explicit prohibitions against inferring engine, gearbox, ECU, PR-code, repair, or parts fitment.

When the owner obtains an approved company integration and written confirmation of offline end-user distribution rights, implement a separate market-scoped source adapter. Store ETag, catalog last-update headers, API version, market, retrieval timestamp, canonical response hash, and source record key. Import into candidate tables first; never promote to confirmed fitment without independent evidence for the exact field.

## Release effect

No product SQLite rows were added. No existing data was modified. No credentials or external accounts were created. This review does not remove the separate Russian/EAEU OTTS rights blocker and does not provide workshop repair data.

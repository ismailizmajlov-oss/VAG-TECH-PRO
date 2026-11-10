# ELPTS public electronic OTTS UI — discovery review

Review date: 2026-11-10. This review records only publicly rendered/search-indexed page metadata. No API, undocumented endpoint, record download, PDF download, scraping or SQLite import was performed.

## Observed route

- Public UI: https://docs.elpts.ru/ncher/otts
- Official operator homepage: https://elpts.ru/
- The homepage identifies АО «Электронный паспорт» and links the national part of the unified OTTS/OTSH/SBKTS register to the Rosstandart site: https://www.rst.gov.ru/portal/gost/home/activity/compliance/evaluationcompliance/AcknowledgementCorrespondence
- The docs.elpts.ru route is on an ELPTS subdomain but was discovered independently; the homepage's national-register link points to rst.gov.ru, not this route. The exact relationship between the two endpoints is not asserted.

## UI observations

The page title identifies a registry of electronically issued vehicle type approvals. Search-indexed page content exposed these columns: approval registration number, vehicle make, vehicle type, status, validity dates, applicant, manufacturer, certification body, environmental class, accounting numbers for the title form/annexes/supplementary sheets, and a printable OTTS form.

The search-indexed page showed:
- date range 2026-11-09 through 2026-11-10;
- zero rows for that selected range;
- a UI counter of 14,822 total issued approvals;
- manufacturer filter values including AUDI AG, Volkswagen AG, and Skoda Auto a.s.

The counter is a provider UI value surfaced by search indexing, not an independently verified database count, not a VAG-specific count, and not proof of complete coverage. Manufacturer filter values are dropdown options, not evidence of matching approval records. No result rows were returned for the observed date range.

## Technical applicability boundary

The visible table columns are document and registry metadata. They do not expose a factory engine code, gearbox code, exact engine/gearbox pair, ECU identity, DTC, wiring, pinout, torque or repair procedure. An OTTS search result, manufacturer filter or type-approval number must not be converted into exact powertrain or repair applicability.

## Rights and ingestion decision

The page is publicly reachable, but no dataset-specific licence or written permission was identified for commercial reuse, bulk extraction, persistent offline caching, third-party desktop display or redistribution in a VAG TECH PRO installer. Public visibility is not a reuse licence.

- No source bytes or documents were downloaded; no source SHA-256 is claimed.
- No undocumented endpoint was queried and no automated extraction was attempted.
- No records were added to any SQLite database.
- The source remains discovery-only with rights unconfirmed; product import is blocked pending written permission and a verified acquisition method.

## Additional operator terms

The currently linked ELPTS offer is titled “ОФЕРТА (право использования ПО)”. It governs use of the operator's software and requires formal acceptance and payment for the specified software rights; it is not a dataset-specific open-data licence or permission to reproduce the public register. The offer also contains intellectual-property restrictions relating to the operator's software and materials. No offer was accepted.

Reference: https://elpts.ru/articles/oferta-pravo-ispolzovaniya-po/

# Volkswagen erWin rights recheck — 2026-11-11

## Sources reviewed

- [Official erWin General Terms and Conditions](https://erwin.vwgroup-datahub.com/en-DE/simplecontent/terms-and-conditions-MCR6ZPIVA5SNFZ3KJ7TAQAMQWIQQ), status 2026-08-14, reviewed 2026-11-11.
- [Official erWin product-use notice](https://erwin.vwgroup-datahub.com/disclaimer-info), reviewed 2026-11-11.

## Findings

The current erWin GTC is for electronic service information delivered through the erWin workshop system. Section 7.1 reserves publication, reproduction, editing, design and exploitation rights in the service information. Section 7.4 grants a simple, non-exclusive right to use the information for the user's own use only; that right is non-transferable, and protective notices must be retained.

The official product-use notice says dissemination, distribution and reproduction of technical information are prohibited. It describes narrow exceptions for internal-company printouts within the same service number and for specified maintenance tables, working hours and measurement protocols. Those exceptions do not authorize copying erWin content into a third-party, pre-populated offline SQLite database or distributing that database to VAG TECH PRO users.

## Storage limit

Section 5.8 of the official GTC limits storage of downloaded erWin service information to a maximum of 24 hours from availability. Further storage is allowed only to the extent and for the duration necessary to comply with statutory retention, documentation or evidentiary obligations. This is not a general offline-cache licence and does not permit retaining a pre-populated VAG TECH PRO database.

## Product decision

- Direct erWin access remains a paid, time-based workshop service, not a bulk data feed.
- Individual workshop use under the applicable erWin terms is distinct from VAG TECH PRO's proposed offline database distribution.
- No rights to bulk extraction, automated ingestion, third-party display, pre-populated offline caching or redistribution are established for VAG TECH PRO.
- Individual downloaded service information is subject to the GTC's 24-hour storage limit, with only the narrow statutory retention/documentation/evidence exception.
- The separate Volkswagen Group third-party RMI product licence is a different contractual product; its eligibility and rights must be assessed under that contract. Its current reviewed scope excludes Russia.
- No account, API key, subscription, agreement, source document or technical data was obtained. No source-data hash is claimed.
- `product_import_allowed=false` and `data_ingested=false` remain unchanged.

This review strengthens the rights boundary only. It does not add DTC, ECU, repair, wiring, pinout, torque, adaptation, service-interval or vehicle-fitment records.

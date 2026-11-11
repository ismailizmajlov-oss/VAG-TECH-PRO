# Volkswagen erWin rights recheck — 2026-11-11

## Sources reviewed

- [Official erWin General Terms and Conditions](https://erwin.vwgroup-datahub.com/en-DE/simplecontent/terms-and-conditions-MCR6ZPIVA5SNFZ3KJ7TAQAMQWIQQ), status 2026-08-14, reviewed 2026-11-11.
- [Official erWin product-use notice](https://erwin.vwgroup-datahub.com/disclaimer-info), reviewed 2026-11-11.

## Findings

The current erWin GTC is for electronic service information delivered through the erWin workshop system. Section 7.1 reserves publication, reproduction, editing, design and exploitation rights in the service information. Section 7.4 grants a simple, non-exclusive right to use the information for the user's own use only; that right is non-transferable, and protective notices must be retained.

The official product-use notice says dissemination, distribution and reproduction of technical information are prohibited. It describes narrow exceptions for internal-company printouts within the same service number and for specified maintenance tables, working hours and measurement protocols. Those exceptions do not authorize copying erWin content into a third-party, pre-populated offline SQLite database or distributing that database to VAG TECH PRO users.

## Product decision

- Direct erWin access remains a paid, time-based workshop service, not a bulk data feed.
- Individual workshop use under the applicable erWin terms is distinct from VAG TECH PRO's proposed offline database distribution.
- No rights to bulk extraction, automated ingestion, third-party display, pre-populated offline caching or redistribution are established for VAG TECH PRO.
- The separate Volkswagen Group third-party RMI product licence is a different contractual product; its eligibility and rights must be assessed under that contract. Its current reviewed scope excludes Russia.
- No account, API key, subscription, agreement, source document or technical data was obtained. No source-data hash is claimed.
- `product_import_allowed=false` and `data_ingested=false` remain unchanged.

This review strengthens the rights boundary only. It does not add DTC, ECU, repair, wiring, pinout, torque, adaptation, service-interval or vehicle-fitment records.

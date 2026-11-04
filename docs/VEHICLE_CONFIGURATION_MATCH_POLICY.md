# Vehicle configuration match policy

## Manual selection is supported; VIN is not mandatory

A saved garage entry may be created from manually entered make, model, generation, market, year, engine, gearbox, ECU and PR-code details. Manual values remain user-declared and are never promoted to independent factory verification merely because a catalogue row is selected.

## Exact technical lookup gate

Before a vehicle can be linked to a rights-cleared exact configuration and used for technical lookup:

1. The saved vehicle make and model must match the catalogue configuration.
2. The user must enter the engine code and transmission code observed on the vehicle or in its documents. Both must match the exact configuration.
3. Any declared generation, model year and market must match.
4. Any declared ECU identifiers and PR codes must be present in the selected configuration.
5. The source and snapshot must still have approved display, offline-cache, bulk-reuse and redistribution rights.

A mismatch or missing engine/gearbox code blocks linking. A technical-record request must include the saved vehicle ID as well as the configuration ID; the local database rechecks the match server-side before returning records.

## Status language

The application reports that the user-declared engine and gearbox codes match a selected catalogue configuration. It does **not** claim that the physical vehicle has been independently verified. Selecting a catalogue row does not overwrite the user's entered values and does not establish VIN-level or document-level proof.

If source rights are revoked, the saved link becomes ineligible and exact technical lookup is blocked. Generic OBD-II DTC records remain in a separate namespace and are not used as VAG-specific repair applicability.

## Safety rationale

This gate prevents a model-only selection from exposing the wrong engine, transmission, ECU, wiring, torque or repair procedure. It also preserves the no-VIN workflow while keeping candidate data and user assertions distinct from verified source records.

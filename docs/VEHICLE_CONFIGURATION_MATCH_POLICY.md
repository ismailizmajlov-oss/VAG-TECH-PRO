# Vehicle configuration match policy

## Manual selection is supported; VIN is not mandatory

A saved garage entry may be created from manually entered make, model, generation, market, year, engine, gearbox, ECU and PR-code details. Manual values remain user-declared and are never promoted to independent factory verification merely because a catalogue row is selected.

## Exact technical lookup gate

Before a vehicle can be linked to a rights-cleared exact configuration and used for VAG-specific technical lookup, all of the following are required:

1. Make and model must match the catalogue configuration.
2. Generation must be explicitly selected and match.
3. Market scope must be explicitly selected; UNKNOWN is not eligible. A configuration scope may cover the selected market through an explicit ALL or multi-market declaration.
4. Model year must be entered and match the catalogue configuration.
5. The user must enter the engine code and transmission code observed on the vehicle or in its documents. Both must match the exact configuration.
6. Any declared ECU identifiers and PR codes must be present in the selected configuration.
7. Exactly one rights-cleared exact configuration must match the complete declared identity. If multiple configurations remain possible, linking and technical lookup are blocked until ECU, PR-code or another supported production-boundary identifier reduces the match to one.
8. The source and snapshot must still have approved display, offline-cache, bulk-reuse and redistribution rights.

A mismatch or missing required identity field blocks linking. A technical-record request must include the saved vehicle ID as well as the configuration ID; the local database rechecks the declared identity, rights and uniqueness before returning records. The uniqueness check is repeated on every lookup so a later catalogue update cannot silently widen applicability for an already linked vehicle.

## Status language

The application reports that the user's declared vehicle identity matches one unique catalogue configuration. It does **not** claim that the physical vehicle has been independently verified. Selecting a catalogue row does not overwrite the user's entered values and does not establish VIN-level or document-level proof.

If multiple exact configurations match, the garage entry is marked ambiguous and VAG-specific technical lookup is blocked. If source rights are revoked, the saved link becomes ineligible and exact technical lookup is blocked. Generic OBD-II DTC records remain in a separate namespace and are not used as VAG-specific repair applicability.

## Safety rationale

This gate prevents a model-only or engine/gearbox-only selection from exposing the wrong engine, transmission, ECU, wiring, torque or repair procedure. It preserves the no-VIN workflow while requiring enough manual identity detail to select one exact, rights-cleared configuration. Candidate data and user assertions remain distinct from verified source records.

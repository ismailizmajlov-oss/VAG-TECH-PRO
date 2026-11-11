# OwnerSpecs VAG dataset snapshot drift review — 2026-11-11

## Decision

**Quarantine the newly acquired JSON snapshot. Retain the previous verified CC BY-SA 4.0 pack only as a dated research snapshot. Do not rebuild, replace, or promote the pack until the publisher reconciles the public HTML count with the JSON contents.**

This is a data-consistency failure, not a license revocation. The current JSON still declares CC BY-SA 4.0 and attribution. It is nevertheless not accepted as a replacement because its contents no longer reconcile with the publisher's public page and the pinned research manifest.

## Evidence

- Public HTML page: https://ownerspecs.com/data — reviewed 2026-11-11; its headline still states **111 generations, 27 brands, 2,369 verified datapoints** and says the dataset was last generated 2026-11-10.
- Public JSON: https://ownerspecs.com/data/dataset.json — reviewed 2026-11-11; it still declares 111 generations and CC BY-SA 4.0, but the sum of per-generation `verified_datapoints` is **2,273**, not 2,369.
- Windows acquisition run: https://github.com/ismailizmajlov-oss/VAG-TECH-PRO/actions/runs/42968938274
- Acquisition evidence artifact: `ownerspecs-vag-source-acquisition-evidence`, artifact ID `13833035466`.
- Previous verified source snapshot: SHA-256 `6ed73e4cd634e64501edd3b0e03405afa0aad3b8d1a103f78b839c87c8588c95`, 683,533 bytes.
- Newly acquired JSON: SHA-256 `d702e4572a4e640c0295c40970ef3c0da2db3703c829c5e3d96cebb4acccacc9`, 659,973 bytes.

The builder rejected the new snapshot with the exact error: `OwnerSpecs datapoint count mismatch: expected 2369, got 2273.` No replacement SQLite pack was built.

## Exact content delta

| Measure | Last verified snapshot | Current JSON | Change |
|---|---:|---:|---:|
| Generations | 111 | 111 | 0 |
| All datapoints | 2,369 | 2,273 | -96 |
| VAG generation candidates | 20 | 20 | 0 |
| VAG facts | 233 | 186 | -47 |
| Other-brand datapoints | 2,136 | 2,087 | -49 |

Eight generation records changed. No generation was added or removed. The 96 datapoint reduction consists of removed facts; the current JSON also changes three BMW X5 mass values.

| Brand / model / generation | Previous | Current | Delta |
|---|---:|---:|---:|
| Porsche Cayenne (E3) | 17 | 0 | -17 |
| Kia EV6 | 12 | 0 | -12 |
| Mercedes-Benz GLE (V167) | 15 | 0 | -15 |
| Tesla Model Y | 12 | 0 | -12 |
| Audi Q7 (4M) | 12 | 7 | -5 |
| Audi Q8 (4MN) | 13 | 8 | -5 |
| Volkswagen Touareg (CR) | 20 | 0 | -20 |
| BMW X5 (G05) | 14 | 4 | -10 |

The VAG subset includes Audi, Skoda, Volkswagen and Porsche in this dataset. The 47 removed VAG facts are from Porsche Cayenne (-17), Audi Q7 (-5), Audi Q8 (-5) and Volkswagen Touareg (-20). The current Touareg and Cayenne generation entries remain present but have zero verified datapoints.

The current BMW X5 mass values differ from the previous snapshot:

| Field | Previous | Current |
|---|---:|---:|
| Permissible maximum laden mass | 2,835 kg | 2,800 kg |
| Mass in running order | 2,211 kg | 2,135 kg |
| Braked trailer towing capacity | 3,270 kg | 3,500 kg |

The unbraked trailer value remains 750 kg. These changes are non-VAG, but they are recorded because the source snapshot is versioned as a whole.

## Applicability and rights boundary

- License remains CC BY-SA 4.0 with attribution; Share-Alike remains mandatory for the separate adapted research database.
- Market scope remains UNKNOWN.
- The dataset does not supply a primary-document URL and revision for each value.
- Generation/year spans remain publisher candidates, not verified VAG generation or model-year applicability.
- No exact factory engine code, gearbox code, engine/gearbox pair, ECU, DTC, wiring, pinout, adaptation, service interval or repair procedure is established.
- Critical technical values remain non-publishable for repair decisions.
- No data from either snapshot is imported into the production vehicle catalog or technical library.

## Handling

1. Keep the previous verified pack (run 115, artifact 13742090427) intact and identify it as the last verified dated research snapshot.
2. Record the new JSON hash and count discrepancy in the central source register as a quarantined acquisition attempt.
3. Do not update the pinned pack manifest or its source hash to the unreviewed JSON.
4. Do not build or publish a replacement SQLite pack from the mismatched snapshot.
5. Re-attempt acquisition only after the publisher page and JSON count reconcile, or the publisher supplies an explanation and a versioned correction.

**Status:** latest public JSON quarantined; previous verified research pack retained; production import remains disabled.

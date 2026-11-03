# Wal33D Volkswagen P1 DTC candidate review — 2026-11-03

## Decision

**Quarantined; not integrated into the Windows product.** The upstream repository declares MIT at repository level, but does not provide a separate data license or primary-source provenance for the DTC descriptions. Do not expose, cache or redistribute this candidate pack in VAG TECH PRO until the data-specific rights and source lineage are confirmed.

## Pinned source and reproducible evidence

- Repository: https://github.com/Wal33D/dtc-database
- Pinned commit: `04c43d72e7db7197658b6f72fe582c5076d9eee8`
- Input: `data/source-data/volkswagen_codes.txt`
- Source file SHA-256: `fd6bf267f1db3a1a44279a21b1c69cba19ee96d2b2821e0b238cdf54b3a71579`
- Repository `LICENSE` SHA-256: `5106ad327a989f9f864f55f9111d055530af80c3109e9f26026bc2cd486087f5`
- Repository `README.md` SHA-256: `60526631da85d81a8c9100709b0ac13cc270c4380ba055a95f38cedff70b6aa7`
- README declares MIT; no separate dataset-specific license file is present.
- A candidate-only SQLite was generated and passed `PRAGMA integrity_check=ok`.
- Candidate SQLite SHA-256: `d87369ddfac724250ccab39865864d781eb247c003d3fbff38c6c7f00f54fbff`
- Candidate pack manifest SHA-256: `49cf199765e766c6c6aafd40e21b8d611b6ba22be8e42980a1b9f22ea373b3b7`
- Internal artifact ZIP SHA-256: `53e376ea33f0fecf5dc7f8fb94075d4af65fd91533d94e2738729b8a7a189c2e`
- Acquisition run: [41713373245](https://github.com/ismailizmajlov-oss/VAG-TECH-PRO/actions/runs/41713373245)

## Namespace and applicability controls

The source file yielded 528 unique `P1xxx` rows. The candidate builder imports only the manufacturer-controlled P1 range into a separate `manufacturer_controlled_candidate` namespace. It rejects duplicates and does not import generic rows.

Every row is explicitly marked:

- make label: Volkswagen; status: `community_reference_unverified`
- market: `UNKNOWN`
- precision: `manufacturer_make_candidate`
- exact vehicle, model-year, generation, engine, gearbox, ECU, PR-code and VIN fitment: **not established**
- diagnostic execution, test plans, repair procedures, wiring/pinouts, torque values and OEM parts: **not allowed / not included**

A P1 range indicates a manufacturer-controlled code range; it does **not** prove that a particular description is OEM-confirmed or applicable to a specific Volkswagen model or ECU.

## Product boundary

The candidate artifact is not part of the offline Windows research-pack manifest and is not returned by the diagnostic API. The separate Supabase draft document remains unverified and has no exact configuration fitment. Generic SAE/ISO DTC definitions remain in their own document and namespace.

## Required clearance before integration

1. Obtain the maintainer's written confirmation that the DTC dataset itself (not merely the software) is licensed for commercial use, display, offline caching and redistribution.
2. Obtain the primary source references or a statement of authorship for the descriptions and verify third-party rights.
3. Independently review the code descriptions and keep any approved rows as manufacturer-make candidates until model/generation/ECU applicability is independently proven.
4. Only then stage a new immutable SQLite pack with source revision, source-file and per-line SHA-256, license notice, market scope and review status.

Until these conditions are met, the source remains `permission_required` and the pack remains quarantined.

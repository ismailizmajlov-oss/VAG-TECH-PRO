# Windows offline data-pack rights — 2026-11-04

The Windows offline bundle contains exactly three separate research databases:

1. **OBDex generic OBD-II** — CC0-1.0 data, generic SAE/ISO namespace only, no manufacturer-specific codes and no VAG fitment claim.
2. **OBDb VAG signal candidates** — CC BY-SA 4.0, six pinned upstream repositories, attribution and share-alike notices retained. Community UDS 0x22 signal candidates only; execution disabled.
3. **VehiclesDB identity candidates** — CC BY 4.0 with upstream notices and attribution retained. Foreign-market make/model name evidence only; no Russian evidence, generation/year, engine, gearbox, ECU or exact fitment. In the pinned v2026.10.3 upstream manifest, 14 source registries are approved and 4 present source registries are excluded; the Romanian ID `ro_drpciv` is absent from that release and is recorded separately as a negative presence check, not as an excluded upstream source.

Each SQLite database remains separate under its own license. No records are merged across packs.

## Explicit exclusions

- **gor3a/vehicle-makes-models (ODbL-1.0 downstream declaration):** excluded from the bundle. Its declared upstream is Autoevolution. Autoevolution's Terms of Use (sections 4, 5 and 8) reserve rights in site content/data and require express written permission for reuse; no permission covering offline cache, display, bulk reuse and redistribution has been obtained. The downstream ODbL declaration is not treated as proof of upstream rights.
- **Wal33D manufacturer DTC candidate data:** excluded. The repository-level MIT declaration does not establish data-specific rights or provenance for manufacturer DTC records.

MechanicDB and AutoDiag2 remain separate research-only candidate packs in their own independently licensed workflows; neither is a verified VAG DTC catalogue and neither establishes exact vehicle/ECU applicability.

## Product boundary

- Generic OBD-II data is never relabelled as VAG-specific.
- Candidate identity and UDS signal records are not verified vehicle fitment.
- No manufacturer-specific DTC pack is included until data-specific reuse, display, offline-cache and redistribution rights are confirmed.
- No pack in this bundle supplies verified VAG repair procedures, factory wiring diagrams, pinouts, torque values, adaptations or service schedules.
- This bundle is a data-pack artifact, not an installer and not a production database.

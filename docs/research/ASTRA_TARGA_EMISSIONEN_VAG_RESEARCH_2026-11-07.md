# ASTRA / FEDRO TARGA emissions VAG research pack — 2026-11-07

## Decision and scope

The official Swiss Federal Roads Office (FEDRO / ASTRA) TARGA `emissionen.txt` source is approved for a separately namespaced, read-only CH research pack under the published Swiss Open Government Data reuse terms, with mandatory attribution. It is not a Russian/EAEU OTTS source, not a VAG factory vehicle-fitment database, and not repair documentation.

The source is a tab-delimited 65-column file with one row per Swiss type-approval gearbox variant. The current source revision is `Thu, 30 Jul 2026 09:22:59 GMT`; the 70,829,020-byte source file SHA-256 is `a11c1727440d6d587a1bd0b37eaeb011afc050b8f356ef746fdd6e18898fdd92`.

## Rights and attribution

- Publisher: Federal Roads Office (FEDRO / ASTRA), Swiss Confederation.
- Source: https://opendata.astra.admin.ch/ivzod/2000-Typengenehmigungen_TG_TARGA/2200-Basisdaten_TG_ab_1995/emissionen.txt
- Official product description: https://www.astra.admin.ch/dam/de/sd-web/7fPLSFMqD6JR/informationsprodukte_typengenehmigungsdaten.pdf
- Official ASTRA vehicle-data information: https://www.astra.admin.ch/de/fahrzeugdaten
- Swiss OGD policy: https://www.bk.admin.ch/en/open-government-data-ogd-2
- Reuse terms: https://opendata.swiss/en/terms-of-use
- Legal basis: https://www.fedlex.admin.ch/eli/cc/2023/682/en

The publisher does not assign a separate SPDX identifier in the reviewed ASTRA publication. Reuse is allowed under the Swiss OGD terms, subject to attribution. Paid holder/location data, registration-plate mappings, eDatenblatt portal output and non-public type-approval documents are excluded.

Required attribution:

> Source: Federal Roads Office (FEDRO / ASTRA), TARGA emissions data (emissionen.txt), third-generation type-approval data, source revision 2026-07-30; https://opendata.astra.admin.ch/ivzod/2000-Typengenehmigungen_TG_TARGA/2200-Basisdaten_TG_ab_1995/emissionen.txt. Swiss Open Government Data (OGD). VAG-only research extraction; source field values are retained as raw approval classifications and are not promoted to OEM VAG codes.

## Data and applicability boundary

The pack contains 53,240 VAG-make rows retained from 280,993 scanned source rows, across AUDI, BENTLEY, BUGATTI, CUPRA, LAMBORGHINI, PORSCHE, SEAT, SKODA and VW.

- Market scope: CH only.
- Applicability precision: source-defined Swiss type-approval gearbox-variant row.
- Engine fields are raw ASTRA approval designations; they are not independently confirmed VAG factory engine codes.
- Gearbox fields are raw Swiss approval classifications; they are not confirmed VAG gearbox codes.
- The source-defined row relation is retained as published; no inferred cross-join is used.
- No exact VAG factory engine/gearbox code pair, exact vehicle fitment, production fitment, RU/EAEU applicability, model year or generation is asserted.
- No ECU, DTC, diagnostic test plan, repair procedure, wiring diagram, pinout, torque value, adaptation or service interval is supplied.

The pack is a read-only research namespace. It is not imported into the product vehicle-configuration database and must never be promoted into Russian/EAEU production fitment.

## Latest verified pack build — run 25, 2026-11-07

The Windows source acquisition and SQLite build completed successfully in [workflow run 25](https://github.com/ismailizmajlov-oss/VAG-TECH-PRO/actions/runs/42389267213), source commit `db6df4c6955289ba0f08c12ae08f1eaae75f1018`. The source file revision is unchanged from 2026-07-30; this run rebuilds the pack with the current source manifest and attribution metadata.

- 280,993 source rows scanned; 53,240 exact VAG-make rows retained; zero malformed rows.
- 53,240 source-defined approval/gearbox-variant rows; **zero** exact VAG factory code pairs.
- Zero exact vehicle-fitment rows; zero RU/EAEU applicability rows.
- SQLite `integrity_check=ok`; no foreign-key violations.
- Database SHA-256: `408980e7a8923223b5f7f4fe5120be961b65317d8e96abb25e2b9e4965ccd926` (28,864,512 bytes).
- Inner research-pack archive SHA-256: `6029405c986aca792fba66084938508bfa47fd8e39d9a55fbcef95d8d4bacee1` (5,683,005 bytes).
- Pack-manifest SHA-256: `89c4f9f865ac212ffeb29eb1c52f817693ee25fd8a817fc617e4dc98e7ced996`.
- Source-manifest SHA-256: `1c92ab5b80ac2c95a95f853f82c09c1070928d16961b1a8c0dea27c7b6ac15ec`.
- Outer CI artifact ID `13581110826`, 11,229,087 bytes, SHA-256 `58f5867cf4fb504eba328ad68f0f2fc874bb5d83f7f3062a6a1d1fca7a866e7e`.

The per-gearbox source row is a source-defined CH approval variant link. Engine designation and gearbox classification remain raw source fields; they are not promoted to a confirmed VAG factory code pair. The pack is research-only, separately namespaced, attribution-required and not imported into production fitment or RU/EAEU data. Desktop inclusion is recorded only after the corresponding Windows CI installer and lifecycle complete successfully.

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

## Latest verified pack build — run 16, 2026-11-07

The Windows source acquisition and SQLite build completed successfully in [workflow run 16](https://github.com/ismailizmajlov-oss/VAG-TECH-PRO/actions/runs/42388349228), source commit `d228c5158fc2056abf3d016a55ead952d1973c19`.

- 280,993 source rows scanned; 53,240 exact VAG-make rows retained; zero malformed rows.
- 53,240 source-defined approval/gearbox-variant rows; **zero** exact VAG factory code pairs.
- Zero exact vehicle-fitment rows; zero RU/EAEU applicability rows.
- SQLite `integrity_check=ok`; no foreign-key violations.
- Database SHA-256: `408980e7a8923223b5f7f4fe5120be961b65317d8e96abb25e2b9e4965ccd926` (28,864,512 bytes).
- Inner research-pack archive SHA-256: `5bf0a552cfc057b52c66640db36d6c671e9994a613f4c6d7b5d296948be33be3` (5,683,005 bytes).
- Pack-manifest SHA-256: `6699777df7619ad9394d52471b2b34c494b0089fac46d55c260a7a9a2ff5506c`.
- Source-manifest SHA-256: `fb3a594436c3c17be1eb7b27a05af2e0b3006c619a200343317342b42d3843e3`.
- Outer CI artifact ID `13580905833`, 11,229,081 bytes, SHA-256 `fac173f744dcd5d7acb47702371771d684034c8a5141251ec1eb685dfe71d51c`.

The subsequent desktop CI run 657 resolved run 16, downloaded the artifact, and completed the separate CH-only desktop integration and staging-audit steps successfully. The final NSIS build and lifecycle for run 657 were still running when this evidence was recorded; do not claim the run 657 installer/lifecycle complete until its final result is successful.

## Reproduction and verification

The Windows pack workflow runs parser, exact-make filter and SQLite applicability tests before downloading the official source. It deletes the raw source file before artifact upload. The pack manifest and final-verification report pin source, pack, database, counts and boundary flags. The desktop reader rechecks the database hash, manifest, SQLite integrity, counts, market scope and zero-pair flags at runtime.

The next refresh must re-download the official source and reproduce the source hash, row counts, schema and rights boundary before the pack is accepted. A changed source snapshot must generate a new review and new hashes; it must not silently reuse the old pack.


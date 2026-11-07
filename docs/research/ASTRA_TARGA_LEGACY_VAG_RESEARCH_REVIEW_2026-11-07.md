# ASTRA TARGA legacy VAG source review — 2026-11-07

## Decision

The third-generation ASTRA TARGA automobile dataset is approved for a **separate Switzerland-only, read-only research pack**. It is not a Russian/EAEU source, not a production fitment source, and not an OEM repair-data source.

The official ASTRA publication identifies the TARGA type-approval datasets as freely available Open Government Data. The reviewed third-generation source is a tab-delimited file containing approval-level vehicle identity and technical fields. A bounded Windows CI probe confirmed the published 223-column layout and found VAG-branded rows in the first 2 MiB. A full snapshot build is separately gated by the pinned file size, ETag and Last-Modified value.

## Rights and data-protection evidence

- ASTRA's official *Newsletter Fahrzeugzulassung* page states that type-approval factual data are freely available as Open Data and lists the three generations: scanned PDFs to approximately 1985, Excel data for 1985–1995, and TXT data from 1995 onward: https://www.astra.admin.ch/de/news-homologation
- ASTRA's *Fahrzeugdaten* page identifies free products as Open Government Data, says these are anonymised or factual data, and explicitly distinguishes them from fee-based datasets containing holder-location data or the mapping of vehicle-type data to registration plates. The page also states that no personal data are disclosed: https://www.astra.admin.ch/de/fahrzeugdaten
- The official Swiss Federal Chancellery OGD policy says OGD may be reused freely subject to statutory source-disclosure obligations: https://www.bk.admin.ch/en/open-government-data-ogd-2
- Swiss OGD portal terms and FAQ: https://opendata.swiss/en/terms-of-use and https://opendata.swiss/en/faq
- Legal framework: EMBAG/EMOTA, Article 10: https://www.fedlex.admin.ch/eli/cc/2023/682/en

The selected product is the freely published factual type-approval file under ASTRA's OGD directory. Paid standard datasets, holder/location data, registration-plate mappings, and eDatenblatt portal output are excluded. Attribution is mandatory in the product and in every redistributed pack. No separate Creative Commons identifier is assigned by the reviewed ASTRA publication; the source is recorded as Swiss OGD rather than mislabelled CC0.

## Exact source and revision

- Publisher: Federal Roads Office (FEDRO / ASTRA), Swiss Confederation.
- Source file: `TG-Automobil.txt`.
- URL: https://opendata.astra.admin.ch/ivzod/2000-Typengenehmigungen_TG_TARGA/2200-Basisdaten_TG_ab_1995/TG-Automobil.txt
- Schema/documentation: https://opendata.astra.admin.ch/ivzod/2000-Typengenehmigungen_TG_TARGA/2200-Basisdaten_TG_ab_1995/2220-Datenbeschreibung/Basisdaten_TG_ab_1995.pdf
- Observed Last-Modified: `Thu, 30 Jul 2026 09:22:48 GMT`.
- Observed ETag: `"133ef745-657d09d960472"`.
- Observed full file size from HTTP Content-Range: `322,893,637` bytes.
- Format from bounded probe: CP1252, tab-delimited, 223 columns, header row present.
- The builder pins the size, ETag and Last-Modified and fails closed if any of them changes. The full source SHA-256 is generated only after a complete download; a preview hash is never substituted for a full-file hash.

## Bounded schema probe

Windows CI run: https://github.com/ismailizmajlov-oss/VAG-TECH-PRO/actions/runs/42334866409

- HTTP 206 confirmed a byte-range response for bytes 0–2,097,151.
- 1,557 complete data rows in the bounded preview; all 1,557 had 223 columns.
- 618 exact `AUDI` make values appeared in that preview.
- Sample approval record: `1AB701`, AUDI A6 Quattro, C4/C4B, approval date `19950918`; source fields show engine type/marking `AEL`, gearbox field `m6`, final-drive ratio `4,11`.
- This sample is an approval-level source record, not proof of a model-year range, a production vehicle configuration, or a complete factory engine/gearbox pairing.

## Field interpretation and hard boundaries

The builder uses zero-based positions from ASTRA's published data description:

- approval number/date: columns 1–2;
- vehicle class, make, type and variant/version: columns 10–13;
- EU whole-vehicle approval: column 18;
- raw gearbox classifications 1–4, ratios and assignments: columns 27–38;
- engine make/type, construction, fuel, displacement, power and torque: columns 60–68;
- stamped engine marking (`Motorkennzeichen`) and its location: columns 76–77.

The values are stored as raw source fields. In particular:

1. `Motorkennzeichen` is a source engine-marking candidate. It is not automatically promoted to a confirmed VAG factory engine code.
2. `Getriebe 1..4` are raw Swiss approval classifications. A value such as `m6` is not a VAG gearbox code.
3. Engine markings and gearbox classifications are stored in separate child tables. There is no engine/gearbox pair table and no Cartesian or co-occurrence pairing.
4. Variant/version strings remain unchanged. Embedded lists, wildcard-like values and combined labels are not expanded.
5. Approval date is not treated as model year. No generation is inferred from a type name or approval number.
6. Applicability precision is `CH_type_approval_record`. No VIN, individual-vehicle fitment, production fitment, ECU, DTC, test-plan, repair procedure, wiring, pinout, torque or adaptation applicability is claimed.
7. No field from this source can establish RU/EAEU approval or Russian/EAEU market applicability.

## Emissionen bounded probe result

Windows CI run: https://github.com/ismailizmajlov-oss/VAG-TECH-PRO/actions/runs/42335907326

- Source: `emissionen.txt`.
- HTTP 206 confirmed the first 2 MiB range; total file size is `70,829,020` bytes.
- Last-Modified: `Thu, 30 Jul 2026 09:22:59 GMT`.
- ETag: `"438c3dc-657d09e3d7852"`.
- Preview SHA-256: `9397822e766f9ae262c8db5021c2ef978f264958caa11291b7423846ce7ba1f7` (preview only, not the full file).
- The live file has 65 columns, not the 42-column core list shown in the older PDF table. The probe therefore resolves fields by exact normalized header names and pins the current 65-column schema.
- 8,437 complete data rows in the 2 MiB preview; all 65 columns; 7,160 exact `AUDI` make values in that preview.
- Sample row: `TG-Code=1AB701`, `Marke=AUDI`, `Typ=A6 Quattro`, `Motortyp=AEL`, `Getriebe=m6`, `iAchse='4.11`, `Homologationsdatum=19950918`.
- The source has no separate variant/version field in this file; the raw `Typ` field is retained without expanding it. Applicability is therefore `CH_type_approval_gearbox_variant_row`, not an exact model-year or variant/version assertion.
- The leading apostrophe in the raw final-drive value is preserved; no numeric coercion is applied.

The pack builder stores one row per source-defined gearbox variant with both raw engine type and raw gearbox classification. This supports a **source-defined approval-row association**, not a confirmed VAG factory code pair. It must not be shown as an OEM gearbox code or used for parts/repair selection without independent VAG evidence.

## Product boundary

- Allowed: offline display and search in a separately namespaced ASTRA TARGA research section with source attribution, source revision, full source SHA-256, row SHA-256, market and explicit candidate status.
- Not allowed: import into the production vehicle/engine/gearbox fitment tables; promotion to confirmed OEM codes; cross-market transfer to RU/EAEU; repair or diagnostic recommendations.
- `data_ingested=false` remains the production-register value even after the separate research pack is built.
- The source is never mixed with generic OBD-II or VAG-specific DTC datasets.

## Related third-generation per-gearbox emissions dataset

The same official OGD directory also publishes `emissionen.txt` (directory listing: 68 MB, Last-Modified 2026-07-30 11:22 UTC): https://opendata.astra.admin.ch/ivzod/2000-Typengenehmigungen_TG_TARGA/2200-Basisdaten_TG_ab_1995/emissionen.txt

ASTRA's TARGA documentation says this dataset is for motor vehicles (not trailers) and **one row is emitted for each gearbox variant**. Its 42-field schema includes approval code (`TG-Code`), make, raw type, gearbox classification, final-drive ratio, engine make/type, fuel, displacement, power, torque, emissions and homologation date (documentation pages 5–6). The live 65-column file has no separate variant/version column. This is stronger than the multi-slot gearbox fields in `TG-Automobil.txt`: a row preserves a source-defined approval-type/gearbox-variant engine-type/gearbox-classification association.

It still does not provide a confirmed VAG factory gearbox code. The raw `Motortyp` and `Getriebe` values must remain source labels; a row is not a production-vehicle fitment, and the exact VAG factory code pair is not confirmed. A separate bounded probe and hash-pinned SQLite pack are required before this product can be used. The schema calls these `approval_powertrain_variant_rows`, not `vag_engine_gearbox_pairs`, and records `source_defined_variant_link=true` alongside `exact_vag_factory_code_pair=false`.

## Other TARGA generations

ASTRA's official page also lists a second-generation 1985–1995 Excel dataset and first-generation pre-1985 scanned approval sheets. They are separate products and are not included in this third-generation pack. The second-generation workbook is a candidate for a subsequent schema probe; scanned PDFs require a separate quality and OCR review.

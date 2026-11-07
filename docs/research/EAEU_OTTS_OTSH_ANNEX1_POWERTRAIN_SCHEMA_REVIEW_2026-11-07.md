# EAEU OTTS/OTSH Annex 1 powertrain fields review — 2026-11-07

## Decision

A current normative form schema for vehicle powertrain characteristics has been identified. It is useful for designing a future document-level importer, but it is **not a data acquisition authorization** and does not change any source-rights status.

- No filled OTTS/OTSH document was downloaded in this review.
- No vehicle record or powertrain value was imported.
- No source snapshot or SHA-256 for filled approval documents is claimed.
- Bulk extraction, offline caching, product display, commercial reuse and redistribution rights remain **not established**.
- The EAEU source remains discovery-only; `data_ingested=false`.

## Legal and form references

1. EEC Collegium Decision No. 232 of 2014-12-09, current consolidated text amended by Decision No. 52 of 2026-05-12:
   - [Official EEC 2026 decisions index](https://docs.eaeunion.org/documents/463/)
   - [Decision No. 52 amendment text](https://www.alta.ru/tamdoc/26kr0052/)
   - [Current consolidated Decision No. 232 and OTTS/OTSH forms](https://www.kontur-extern.ru/info/normativ/document/1/507167-reshenie-kollegii-evraziyskoy-ekonomicheskoy-komissii-ot-09-12-2014-n-232)
2. EEC Collegium Decision No. 225 of 2014-12-02 — national-part publication and public-access basis, not a dataset reuse licence:
   - https://www.alta.ru/tamdoc/14kr0225/
3. EEC Collegium Decision No. 88 of 2016-07-26 — technical information-exchange schema R.TR.TS.07.001, not the public-access or data-reuse basis:
   - https://www.alta.ru/tamdoc/16kr0088/

Decision No. 52 was adopted on 2026-05-12 and published on 2026-05-15. Its general entry-into-force date is 2026-06-14; the relevant changes to the vehicle-approval form rules take effect from 2026-10-08. The current consolidated Decision No. 232 page identifies the form revision as 2026-05-12 and its relevant effective date as 2026-10-08. The amendment's relevant wording updates the hybrid-powertrain description. This review does **not** claim that the engine/gearbox fields below were newly introduced by Decision No. 52; it records their presence in the current consolidated form.

## Fields in the OTTS/OTSH Annex 1 blank form

The current consolidated form's Appendix No. 1, headed "Общие характеристики транспортного средства" (and the corresponding OTSH chassis form), includes these powertrain fields:

- Internal-combustion engine: make/type, cylinder count and layout, displacement, maximum power, maximum torque, fuel and other equipment/markings.
- ECU/control-unit marking.
- Transmission type.
- Clutch make/type.
- Gearbox make/type.
- Number of gears and gear ratios.
- Transfer-case type, gear count and ratios.
- Final-drive type and ratios, including an intermediate ratio where applicable.

These are **attachment-level form fields**. They are distinct from the short public registry-summary fields observed on the ELPTS page on 2026-11-06. That visible table included a "Печатная форма ОТТС (ОТШ)" column but did not expose engine code, gearbox code, an engine/gearbox pair or ECU fields. No filled attachment was retrieved, so the actual availability, completeness and access terms for individual documents remain unresolved.

## EEC Order No. 126 — unified-register implementation plan

The official six-page PDF for Collegium Order No. 126 of 2026-08-11 includes the approved implementation plan (pages 3–6 of the PDF). The order was published and entered into force on 2026-08-14. The plan contains four milestones:

| Item | Target | Planned measure | Expected result |
|---|---|---|---|
| 1 | Q4 2026 | Draft amendments to the rules for filling OTTS/OTSH and related vehicle-approval forms under Decision No. 232 | Electronic form rules for approval documents and cancellation notices under TR TS 018/2011 |
| 2 | Q4 2026 | Draft amendments to the regulation on the unified register under Decision No. 225 | Formation from electronic information in national parts and the ability to transfer information from the unified register |
| 3 | Q1 2027 | Draft amendments to Decisions No. 88 (2016-07-26), No. 81 (2016-07-12) and No. 122 (2015-09-22) | Legal support for the unified register based on electronic national-part information and information transfer |
| 4 | Q1 2027 | Agree mechanisms for providing customs-release information to the national electronic-passport operator and the Russian administrator | Define the information composition and provision procedure; implementation may be by protocol or Customs Code amendments |

Primary source: [official EEC Order No. 126 PDF, including the plan](https://docs.eaeunion.org/upload/iblock/db6/3ecew1lvopjk2zx2raf66047bn274ofu/Rasporyazhenie-Kollegii-_-126-ot-11-avgusta-2026-g.pdf). The official EEC index is https://docs.eaeunion.org/en/documents/464/.

These are **planned legal/administrative milestones**, not evidence that the amendments or registry are already implemented. The plan points to electronic information in national parts and a future ability to transfer information; it does not itself expose a live OTTS API, publish records, define the final public fields, or grant rights to bulk extract, cache, display or redistribute data. The existing source remains `permission_required`, `data_ingested=false`, and `product_import_allowed=false`. No importer or data mapping is enabled on the basis of this roadmap. Monitor the Q4 2026 and Q1 2027 acts and re-review their actual text, endpoint, fields and reuse terms before any acquisition.

## Required interpretation for VAG TECH PRO

1. Store the document's raw values exactly as printed. Do not silently normalize or translate a manufacturer "make/type" label into a VAG three-letter engine code or gearbox code.
2. Preserve document number, document kind (OTTS versus OTSH), issuing country, revision/status, annex and page locator, exact modification/variant scope, source URL, retrieval time and SHA-256 of the actual downloaded document.
3. A possible engine/gearbox relationship is only a **candidate** if both fields are explicitly tied to the same Annex 1 row and the same modification/variant scope. Never cross-join values from different variants, pages or documents.
4. Promote a VAG engine code, gearbox code or exact pair only after independent manufacturer-code mapping and technical review. A type-approval form alone does not prove ECU software/hardware fitment, DTC applicability, wiring, repair procedures or parts supersession.
5. Keep SBKTS separate from OTTS/OTSH. SBKTS is an individual-vehicle document and may contain VIN, registration and owner information; this project importer continues to exclude SBKTS and personal/vehicle-identifying fields.
6. Do not ingest or redistribute filled approval attachments until the source owner or a dataset-specific licence confirms bulk extraction, offline caching, display and redistribution rights.

## Source-register effect

The central source register now records the current normative attachment schema under `eaeu-otts-unified-register-public-portal` and notes the same boundary on the ELPTS national query entry. No source was promoted to approved, no rights flags were changed, no source count was changed, and no data were imported.

The EAEU public-access basis remains Decision No. 225. Decision No. 88 remains a technical exchange-schema reference only. Neither decision, nor the blank form in Decision No. 232, grants VAG TECH PRO rights to bulk copy, cache, display or redistribute filled registry records.

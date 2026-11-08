# EAEU temporary OTTS register route recheck — 2026-11-09

## Finding

The official Eurasian Economic Commission website has a dedicated page for the temporary electronic register under TR TS 018/2011:

- EEC page: https://eec.eaeunion.org/comission/department/deptexreg/tr/temprorary_otts.php
- Page title: «Временный реестр документов об оценке соответствия требованиям технического регламента Таможенного союза “О безопасности колесных транспортных средств” (ТР ТС 018/2011)…»
- The page exposes separate links for electronic OTTS, OTSH and SBKTS registers.
- The OTTS link is explicitly labelled «Реестр одобрений типа транспортного средства, оформленных в электронном виде» and points to https://portal.elpts.ru/ncher/otts.

This is a more precise official navigation route than the previously reviewed EAEU portal root. It does not establish that the temporary register is complete, current, machine-readable, or licensed for reuse.

## Endpoint check

On 2026-11-09 the linked OTTS destination returned HTTP 502 Bad Gateway in the web retrieval attempt. The destination content was therefore not verified. No search result rows, attachments, export endpoints, API methods, raw bytes or database records were retrieved.

The EEC page itself is accessible and its link labels distinguish OTTS from OTSH and SBKTS. Do not collapse these document classes. A link to the register is not a record count and is not proof that a particular VAG approval exists.

## Rights and product boundary

The new observation does not change any rights decision:

- bulk extraction: not established;
- automated collection: not established;
- persistent SQLite caching: not established;
- offline end-user display: not established;
- installer/update redistribution: not established;
- commercial reuse: not established;
- written permission: not obtained.

No API or export endpoint was guessed. No data were downloaded or imported. No source snapshot SHA-256 is claimed. `data_ingested=false`, `product_import_allowed=false`, and `source_snapshot_sha256=null` remain mandatory.

The official EEC temporary-register page and its linked portal route are recorded in `data/source-manifests/vag-factory-source-register.json` under `eaeu-otts-unified-register-public-portal`. The regression test `tests/test_elpts_otts_source_rights.py` asserts that the official link cannot bypass the rights gate.

## Technical applicability

Even a future licensed OTTS record would establish only the approval scope explicitly contained in that document. Do not infer:

- an individual vehicle's factory build;
- a VAG three-letter engine or gearbox code from a raw manufacturer component designation;
- an exact engine/gearbox pairing unless both are tied to the same exact variant/annex scope;
- model year from approval issue dates;
- ECU, DTC, wiring, repair, torque or adaptation applicability.

Any approved future import must retain the original document identifier, document class, revision/status, exact type/variant/version, annex/page, raw values, market scope, source bytes SHA-256, licence evidence and independent technical-review status.

## Primary sources

- EEC temporary electronic vehicle-approval register page: https://eec.eaeunion.org/comission/department/deptexreg/tr/temprorary_otts.php
- Linked electronic OTTS register: https://portal.elpts.ru/ncher/otts
- EEC Decision No. 225 public-access framework: https://www.alta.ru/tamdoc/14kr0225/
- ELPTS public OTTS page previously reviewed: https://docs.elpts.ru/ncher/otts

Review date: 2026-11-09.

## Additional public page-shell observation — 2026-11-09

The separate `https://docs.elpts.ru/ncher/otts` page was opened successfully. The rendered page shell displayed the title «РЕЕСТР ОДОБРЕНИЙ ТИПА ТРАНСПОРТНОГО СРЕДСТВА, ОФОРМЛЕННЫХ В ЭЛЕКТРОННОМ ВИДЕ», document-class navigation (`ОТШ`, `ЭСБКТС`, `ЗОЕТС`) and unresolved dynamic placeholders `{{ totalFiltered }}` / `{{ totalNotFiltered }}`. No record rows, API endpoint, export endpoint, raw page bytes or document attachments were exposed in the retrieved rendering. This page is recorded as a separate observation; it is not assumed to be the same host/endpoint as the EEC-linked `portal.elpts.ru/ncher/otts` URL, which returned HTTP 502. No rights changed and no source hash is claimed.

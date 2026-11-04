# ELPTS public vehicle-approval register route — rights review (2026-11-05)

## Decision

The official public ELPTS site now provides a useful discovery route for the Russian national part of the unified EAEU vehicle-approval register. The site lists a section named **“Национальная часть единого реестра выданных ОТТС, ОТШ, СБКТС”**. Its linked public document page at `https://docs.elpts.ru/ncher/esbkts` is titled as an electronic SBKTS register and visibly exposes filter labels **ОТТС / ОТШ / ЗОЕТС**.

This is a newly recorded source lead, **not an approved import source**. No resource-specific licence or written permission was found that grants VAG TECH PRO commercial reuse, systematic extraction, persistent SQLite caching, offline third-party display, PDF redistribution or distribution of a derived register. No records or PDFs were downloaded, copied, cached or imported.

## Evidence reviewed

1. ELPTS official public site: https://elpts.ru/
   - The public page identifies AO “Electronic Passport” as the administrator and lists a “Реестры” section with the national part of the unified register of issued OTTS, OTSH and SBKTS.
   - The same site states that additional statistical reports for SEP/EOTTS participants are supplied under a separate agreement; access to EOTTS training materials requires an organization profile in the request centre.
2. Public document-register page: https://docs.elpts.ru/ncher/esbkts
   - Page heading: “РЕЕСТР СВИДЕТЕЛЬСТВ О БЕЗОПАСНОСТИ КОНСТРУКЦИИ ТРАНСПОРТНОГО СРЕДСТВА, ОФОРМЛЕННЫХ В ЭЛЕКТРОННОМ ВИДЕ”.
   - Visible filter labels: “ОТТС”, “ОТШ”, “ЗОЕТС”.
   - The page does not expose a dataset licence, bulk export contract, API documentation, offline-cache permission or redistribution grant in the reviewed public content.
3. Official Rosstandart / FBU Interstandart FGIS overview: https://www.interstandart.ru/page/fgis_01
   - Confirms the national FGIS vehicle-compliance register's document classes and the role of Rosstandart/Interstandart.
   - Describes specialized registry software for accredited certification bodies and testing laboratories; this does not grant VAG TECH PRO reuse rights.
4. EAEU public-data portal: https://opendata.eaeunion.org/opendata/ru/api/restapi
   - The portal is a general OData/REST catalogue; no specific OTTS resource with a matching reuse licence was established in this review.

## Rights and acquisition boundary

| Capability | Current status |
|---|---|
| Public page visibility | Observed |
| Exact OTTS dataset coverage and completeness | Not established |
| Resource-specific open licence | Not found |
| Commercial use | Not confirmed |
| Bulk export / automated extraction | Not established |
| Persistent local SQLite cache | Not confirmed |
| Offline third-party display | Not confirmed |
| PDF redistribution | Not confirmed |
| Product import | Blocked pending written permission or a resource-specific open licence |

Do not infer that a publicly reachable search page is an open-data licence. Do not scrape the page, enumerate hidden endpoints, automate queries, bulk-download records or PDFs, or place the data into the installer until the operator confirms the exact permitted scope in writing.

## Document-type and technical applicability controls

- Keep **OTTS**, **OTSH**, **SBKTS** and **ZOETS** in distinct document namespaces. The page title is SBKTS while the visible filter labels include other document classes; the labels alone do not establish the page's completeness or exact semantics for each class.
- An OTTS is evidence of type/variant homologation only to the extent explicitly stated in the approval and its annexes.
- Do not treat an OTTS as an individual VIN build sheet.
- Do not infer a factory engine code from a free-text engine make/type field.
- Do not infer an exact engine/gearbox pairing unless the primary approval explicitly binds those exact values to the same approved type/variant.
- Do not derive ECU, DTC, wiring, pinout, torque, adaptation, maintenance or repair applicability from registry metadata alone.
- Every future permitted record must retain the issuing authority, document type/number, revision/supplement, validity dates, market, source URL, snapshot hash, licence/permission hash, extracted field evidence and applicability precision.

## Project action

The source has been added to:

- `data/source-manifests/vag-factory-source-register.json`
- `data/source-manifests/russian-eaeu-otts-sources.json`

Status is `permission_required`; `data_ingested=false`; `source_snapshot_sha256=null`. The registry is a discovery lead only. No external account, subscription, API key, paid access, automated request or download was used.

To unlock ingestion, the project needs written permission from AO “Electronic Passport” or the relevant register operator that explicitly covers commercial use, bulk extraction, persistent SQLite caching, offline third-party display, updates/retention and redistribution in VAG TECH PRO. If the permission is internal-use-only, the data must not be bundled in the Windows installer.

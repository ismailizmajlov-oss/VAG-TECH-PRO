# Kyrgyz Single Window public OTTS registry — source and rights review (2026-11-06)

## Finding

The Kyrgyz Republic's State Enterprise «Single Window» Center, operating under the State Customs Service at the Cabinet of Ministers, documents a pilot public registry for issued conformity and vehicle documents. The official portal describes checks by document number or VIN without login and says personal data are not shown in the public registry.

Official sources:

- Main operator portal: https://trade.kg/
- OTTS/OTSH registry landing route: https://trade.kg/registry?tab=OTTS.otts
- Linked public registry application: https://smart.trade.kg/registry?lng=ru
- Public-registry project description: https://trade.kg/projects/public-registry
- Vehicle approval system description: https://trade.kg/projects/vehicles
- Vehicle-system launch notice dated 2026-08-24: https://trade.kg/news/24-avgusta-2026-goda-v-promyshlennoj-srede-zapuskaetsya-informaczionnaya-sistema
- Website privacy policy: https://trade.kg/privacy
- Previously observed legacy route: https://sbkts.trade.kg/otts

The operator's home page lists OTTS/OTSH search by approval number, make and model. The public-registry project page separately describes checking issued documents by number or VIN without login. The new smart.trade.kg record page did not return readable record content during this review; therefore its actual record fields and CAPTCHA behavior were not independently inspected. The older sbkts.trade.kg route was previously observed to require robot verification; no CAPTCHA bypass was attempted.

## Scope and applicability

The separate car.trade.kg vehicle-approval workflow is described for certification bodies and experts. Its application process includes vehicle, chassis, engine and other characteristics. Those are application/workflow fields and are **not** evidence that the public registry exposes the same fields.

The portal's landing-page summary showed one OTTS record in the indexed snapshot. This is not treated as a current, complete or authoritative corpus count.

No VAG-specific engine code, gearbox code, exact engine/gearbox pair, ECU identity, DTC, test plan or repair applicability was established. An OTTS/OTSH record, even if later licensed, is type-approval evidence only and cannot by itself establish individual VIN build data or repair applicability.

## Rights and decision

The public-registry page establishes a public query route without login, but public visibility is not a dataset reuse licence. The website privacy policy describes visitor analytics and search handling; it does not grant rights to bulk extract, automate, cache offline, display in a third-party product or redistribute registry records.

No dataset-specific open licence, documented API contract, bulk export method or written permission for automated extraction, local caching, commercial display or redistribution was identified.

**Decision:** keep the source at `permission_required`. No records were downloaded, cached, imported or displayed. `data_ingested=false`, `product_import_allowed=false`, and `source_snapshot_sha256=null`. No hash is claimed for data that were not obtained.

Before any future product import, obtain written permission from the operator covering the exact fields, bulk extraction, local offline storage, third-party display, redistribution and update cadence; separately verify the public record schema and exclude VIN, applicant/contact and other personal data.

## Evidence reviewed

- https://trade.kg/ — state-enterprise operator, public-register overview and OTTS/OTSH search fields.
- https://trade.kg/registry?tab=OTTS.otts — official registry landing route.
- https://smart.trade.kg/registry?lng=ru — linked public registry application; no readable record payload obtained.
- https://trade.kg/projects/public-registry — pilot status, no-login query by number/VIN, personal-data statement.
- https://trade.kg/projects/vehicles — separate certification workflow and its application fields.
- https://trade.kg/privacy — website privacy policy; not a data licence.
- https://sbkts.trade.kg/otts — legacy route with previously observed robot verification.

The source remains in both the central VAG source-rights register and the Russian/EAEU source register with import disabled.

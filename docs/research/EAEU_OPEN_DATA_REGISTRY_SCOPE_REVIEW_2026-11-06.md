# EAEU public registry scope review — 2026-11-06

## Decision

The EAEU technical-regulation portal exposes an official open-data resource for the **Unified Register of Conformity Assessment Bodies** at:

- Resource page: https://tech.eaeunion.org/tech/ru/registers/36
- Open-data REST API guidance: https://opendata.eaeunion.org/opendata/ru/api/restapi
- Portal resource catalogue: https://opendata.eaeunion.org/opendata/ru/resourses

The resource is **not** the Unified Register of Vehicle Type Approvals (OTTS/OTSH) and must not be treated as one.

## What the page establishes

The resource page identifies the dataset as the EAEU Unified Register of Conformity Assessment Bodies, based on EEC Council Decision No. 100 of 2018-12-05. The page displayed 3,236 records when checked on 2026-11-06 and exposes data access options labelled ODATA (GET), REST (POST), and S3 (full archive and daily changes). The visible record fields include country, national unique identifier, organization name, register/accreditation status, accreditation certificate number and dates, address, head/contact details, product scope, and technical regulation. The page says the published information was current as of 2024-09-01.

The page's filter and sample records include TR TS 018/2011 scopes, which can help a human reviewer check whether a certification body or testing laboratory's declared scope includes vehicle-related conformity assessment.

## Rights and ingestion boundary

The EAEU open-data portal's general REST API page states that portal data are available for reuse with minimal organizational and other restrictions. However, this review did not establish a dataset-specific license identifier, exact attribution terms, offline-caching permission, redistribution conditions, or a versioned downloadable snapshot hash for this particular resource.

Therefore:
- source status: `candidate_rights_review_required`;
- bulk acquisition: `not_authorized_for_this_project_yet`;
- offline cache: `not_established`;
- redistribution: `not_established`;
- no records were downloaded, copied, cached, or imported by this review.

Before any import, obtain the resource card's explicit reuse terms and attribution requirements, pin the exact ODATA/S3 endpoint and schema, preserve the source snapshot and SHA-256, and add a separate source entry. Do not infer a reuse grant for this resource solely from the portal-wide wording.

## Permitted product role after rights clearance

If the resource-specific reuse terms are confirmed, the dataset may support a separate **accreditation-body verification** table. It must not be merged with:
- OTTS/OTSH documents or vehicle variants;
- VAG model/generation taxonomy;
- engine or gearbox codes and pairings;
- ECU identities or DTC applicability;
- repair procedures, wiring diagrams, pinouts, torque values, adaptations, or service intervals.

A body's accreditation scope is evidence about the body, not proof that a particular vehicle type approval exists or that a particular VAG configuration is approved.

## References checked

- EAEU resource page: https://tech.eaeunion.org/tech/ru/registers/36
- EAEU portal REST API guidance: https://opendata.eaeunion.org/opendata/ru/api/restapi
- EAEU portal catalogue: https://opendata.eaeunion.org/opendata/ru/resourses
- EEC Council Decision No. 100 (2018-12-05), cited by the resource page as the register's basis.

Checked: 2026-11-06.

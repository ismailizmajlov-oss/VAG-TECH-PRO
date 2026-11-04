# Upstream rights review — gor3a/vehicle-makes-models

Review date: 2026-11-04

## Scope

The pinned `gor3a/vehicle-makes-models` snapshot declares `autoevolution.com` as its upstream source and declares ODbL-1.0 for the downstream database. The downstream ODbL declaration does not, by itself, establish that the repository maintainer had authority to license all upstream material or database rights contained in that snapshot.

## Primary-source terms reviewed

- Autoevolution Terms of Use: https://www.autoevolution.com/static/terms.html
- Reviewed sections: 4 (Intellectual property protection), 5 (Non-commercial use), 8 (Prohibited activities).
- The terms identify SoftNews NET as the rights holder for Autoevolution content and data related to the website, require express written permission for unauthorized use, and limit service use to personal use unless commercial use is approved.

## Project decision

`gor3a/vehicle-makes-models` remains quarantined. Do not import, cache, bundle, display, redistribute, or derive product records from this dataset until written permission from the relevant upstream rights holder expressly covers the exact data snapshot and the required uses (display, offline caching, bulk reuse, and redistribution). Preserve the pinned revision and prior hash evidence only as an audit record; do not use its model, generation, engine-variant or transmission-description rows as product data.

The downstream ODbL notice remains relevant to the downstream database's own rights and share-alike obligations, but it is not treated as proof of rights in the upstream Autoevolution material. No engine code, gearbox code, ECU mapping, market applicability, or repair applicability may be inferred from this dataset in any event.

## Evidence captured

- Source repository: https://github.com/gor3a/vehicle-makes-models
- Pinned revision: `ee99776470a45214bf524cdfe22e5dbf4bd67f93`
- Upstream Terms of Use: https://www.autoevolution.com/static/terms.html
- Terms page identifies SoftNews Net SRL in its site footer and states the relevant content/data restrictions in sections 4, 5, and 8.

This is a conservative source-rights gate for the project, not a legal opinion. Reconsider only after written authorization or a replacement source with independently verified rights and provenance is supplied.

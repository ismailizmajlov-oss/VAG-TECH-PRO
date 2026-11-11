# OwnerSpecs open vehicle-spec dataset — rights and applicability review

Reviewed: 2026-11-10  
Publisher: [ownerspecs.com](https://ownerspecs.com)  
Dataset: [Open vehicle-spec dataset](https://ownerspecs.com/data)  
Machine-readable descriptor: [dataset.json](https://ownerspecs.com/data/dataset.json)  
Licence: [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/)

## Decision

The publisher's published CC BY-SA 4.0 licence permits commercial reuse, display, offline caching, bulk reuse and redistribution with attribution. Adapted database material must remain under the same Share-Alike licence and be separately packaged from differently licensed production data.

A fresh live review on 2026-11-10 confirms that the HTML dataset page and JSON descriptor both report **111 generations**. The HTML page also reports **27 brands and 2,369 verified datapoints**. The earlier 112-generation observation came from a stale indexed response and is superseded by the current live page/JSON pair.

## Exact retained snapshot and change review

Windows x64 CI re-acquired the exact JSON snapshot on 2026-11-10 at 06:28:05 UTC:
- Raw source.json SHA-256: **6ed73e4cd634e64501edd3b0e03405afa0aad3b8d1a103f78b839c87c8588c95**. The source snapshot SHA-256 is pinned in the source manifest and build evidence.
- Raw file size: **683,533 bytes**.
- 111 generations and 2,369 datapoints; VAG subset: 20 generation candidates and 233 facts.
- Market scope remains UNKNOWN.

Comparison with the retained run 64 source snapshot **7b39e1183bd2a7617d43fdbe1f2ae64662520cb62f89ba8fec4dadbcce79204d** found no generation or datapoint membership changes. Five records changed across four generations:
- Four specification values changed. Three are VAG: Audi A1 CO2, Audi A1 fuel consumption, and Volkswagen Polo CO2. One is non-VAG: Mercedes-Benz A-Class CO2. Each changed specification value was previously represented as a range and is now represented by its upper bound alone.
- One non-VAG unit-only normalization: Hyundai i10 engine-oil capacity changed unit spelling from L to l; the numeric range did not change.

The earlier 05:51 acquisition note reported SHA-256 **f29c0e49e71b4c1def0c0159d2fa7617ed4d9724078a241d5ce81c7edfb8b9c4**, but the raw bytes from that acquisition were not retained in the available artifact. That hash is preserved in review history as an intermediate, unverified claim. No exact byte-level delta between that unretained snapshot and the 06:28 snapshot is asserted.

The source JSON does not provide a primary-document locator or revision per value. The dataset is not independently reviewed for repair accuracy. These records remain generation/model candidates only and must not be promoted to factory engine/gearbox fitment, ECU applicability, repair procedures or critical workshop values.

## Verified separate research pack — run 115

- Workflow run: **115 / 42770457166**.
- Artifact ID: **13742090427**.
- Artifact SHA-256: **93c4050130a8d372888ffd3126e18d4ef03de434558adfc98f7bb51e0a6918d1**.
- Research SQLite SHA-256: **572455b8054bd93600fb5ef25d38c6aa478a5bc98a0d26d678a220b008d4d683**.
- Database size: **323,584 bytes**.
- Pack manifest SHA-256: **35bbe697d046891c1f49e8f5a318fa2f6f1afab087a7c20d8718ab4c02c9f6dd**.
- SQLite integrity check: **ok**; foreign-key violations: **0**.
- Counts: 111 generations, 2,369 source datapoints, 20 VAG generations and 233 VAG facts.

The pack was subsequently integrated into the offline Windows desktop research catalog in PR #91, validated by Windows x64 CI run 1264 on 2026-11-10. It remains a separate read-only CC BY-SA research artifact; production import remains disabled and no critical repair values are publishable from this source.


## Desktop integration verification — 2026-11-10

The exact pinned OwnerSpecs research artifact was integrated into the offline desktop build by PR #91, Windows x64 workflow run **1264** (run ID `42813922741`), source revision `f5f005a04e1dc715aae1fb48899592ff5f1009c2`. The integration workflow resolved and verified the pinned run-115 artifact, downloaded it, integrated the read-only SQLite reader and research UI, and ran the pack verifier. Steps 69–71 completed successfully. The full Windows x64 build/lifecycle job and separate Windows Server 2022 installer-compatibility lifecycle both passed; PR #91 was subsequently merged to main.

The desktop pack retains the original CC BY-SA 4.0 attribution and Share-Alike boundary. It is visible only as a separate research dataset and does not seed the production vehicle catalog, engine/transmission fitment, OEM DTC index, ECU applicability or technical repair library. The 20 generation labels and 233 facts remain UNKNOWN-market candidates; the source JSON still lacks a primary-document locator and revision per value. Native Windows 10/11 client lifecycle remains unverified because the owner-controlled runner gate is disabled.

## Current publisher snapshot refresh — 2026-11-11

A fresh live review of the [public dataset page](https://ownerspecs.com/data) on 2026-11-11 reports **111 generations, 27 brands and 2,273 verified datapoints**, with last generated date 2026-11-11. The [machine-readable JSON](https://ownerspecs.com/data/dataset.json) reports 111 generations; the retained exact JSON from Windows x64 acquisition run [141](https://github.com/ismailizmajlov-oss/VAG-TECH-PRO/actions/runs/42968938274) contains 111 generation records and 2,273 nested facts.

The exact source file retained in artifact **13833035466** has:
- Raw source JSON SHA-256: **d702e4572a4e640c0295c40970ef3c0da2db3703c829c5e3d96cebb4acccacc9**.
- Source JSON size: **659,973 bytes**.
- Acquisition evidence ZIP SHA-256: **ee801173419bf17b8610f7eac80b813f24a9456633138a96078cfbc494ca5c85** (33,501 bytes).
- Acquisition log SHA-256: **7c559297e0884939cf8ac33a05978e0835beeb5ea933e6fb84c6e4513ed82c77**.

An exact row-level comparison with the previous verified 2026-11-10 snapshot (SHA-256 `6ed73e4cd634e64501edd3b0e03405afa0aad3b8d1a103f78b839c87c8588c95`, 111 generations / 2,369 facts) found:
- No generation membership changes.
- 99 facts removed, 3 replacement facts added and 3 BMW X5 mass values changed; net reduction: 96 facts.
- The VAG subset remains 20 generation candidates but falls from 233 to **186 facts**: 47 VAG facts were removed. The affected VAG generations are Audi Q7 (5 mass facts), Audi Q8 (5 mass facts), Porsche Cayenne (17 specification/mass facts) and Volkswagen Touareg (20 specification/mass facts).
- The three changed values are non-VAG BMW X5 mass values: running order 2,211→2,135 kg; permissible maximum laden mass 2,835→2,800 kg; braked towing capacity 3,270→3,500 kg.

The first acquisition workflow correctly failed closed because the prior manifest still expected 2,369 datapoints. The fresh publisher HTML now confirms 2,273, so the failure was a stale snapshot pin, not a reason to discard the new source. A versioned 2026-11-11 manifest and a dedicated Windows x64 refresh workflow now pin the exact source bytes and reconcile the live HTML, JSON counts, VAG subset and hashes before building a new pack.

The previously verified 233-fact research pack remains a dated prior snapshot. It is not silently relabelled as current and will not be replaced in the desktop until the 2026-11-11 pack is independently built, verified, and its SQLite/artifact hashes are recorded. The new pack remains a separate read-only CC BY-SA 4.0 research database with attribution and Share-Alike; market UNKNOWN; no primary-document locator/revision per value; no exact engine/gearbox pair, ECU, DTC, RU/EAEU or repair applicability; no production import.

The 20 VAG generation labels and 186 facts in the current snapshot remain **candidate-only**: market scope is UNKNOWN, no per-value primary-document locator/revision is supplied, and no exact engine/gearbox, ECU, DTC, RU/EAEU or repair applicability is established. They are not factory fitment or critical repair data.


## Exact source reacquisition — 2026-11-11 06:33 UTC

Windows x64 acquisition workflow [run 158](https://github.com/ismailizmajlov-oss/VAG-TECH-PRO/actions/runs/42973238985) retained the exact publisher JSON in artifact **13834540968**:
- Raw source JSON SHA-256: **835fe7452b3370dbf921049a72ca365d6f69b6b63ef8a3a37b5714265272814c**.
- Raw source JSON size: **659,973 bytes**.
- Acquisition evidence ZIP SHA-256: **81360d348655f3fe84ccfd926c026120677848ffff4e9f03cfad404158f7c803** (34,193 bytes).
- Acquisition snapshot SHA-256: **93bd94338641703d4a1a3cb47870fbf0a3782d65738dc382444e6e4060b10904**.
- Acquisition log SHA-256: **5aed7971c3ff23321202a33483f2bd732c5f2ee319e8b15aba13f4b84a748fd8**.

A direct row-level comparison with the preceding exact 06:19 snapshot (**d702e4572a4e640c0295c40970ef3c0da2db3703c829c5e3d96cebb4acccacc9**) found exactly two non-VAG unit-case changes in Hyundai i10 III (AC3): coolant capacity L to l (5.53–5.89) and engine-oil capacity l to L (3.1–3.4). No generation or datapoint membership changed, and the VAG subset remains exactly 20 generation candidates / 186 facts. The numeric values and ranges are unchanged.

The acquisition step itself completed and retained the source bytes. The subsequent pack-build call rejected the new bytes because the manifest still pinned the preceding d702e4572a4e640c0295c40970ef3c0da2db3703c829c5e3d96cebb4acccacc9 hash; **no SQLite pack was built by run 158**. The prior pack remains the last independently verified artifact and is explicitly tied to d702e4572a4e640c0295c40970ef3c0da2db3703c829c5e3d96cebb4acccacc9. Its exact source manifest is preserved at `data/source-manifests/history/ownerspecs-verified-vehicle-specs-cc-by-sa-4.0-pack3-2026-11-11.json`; the current publisher manifest is updated to 835fe7452b3370dbf921049a72ca365d6f69b6b63ef8a3a37b5714265272814c. A separate pack rebuild and verification are still required before replacing the desktop research pack.

The latest facts remain CC BY-SA 4.0 research-only material: market UNKNOWN, no per-value primary-document locator/revision, no exact engine/gearbox, ECU, DTC, RU/EAEU or repair applicability, and no production import.


The acquisition evidence also records a stale free-text source_revision label in the run-158 acquisition-snapshot.json: it was copied from the pre-refresh manifest that still pinned d702e4572a4e640c0295c40970ef3c0da2db3703c829c5e3d96cebb4acccacc9. That label is explicitly marked stale; the raw source JSON SHA-256 **835fe7452b3370dbf921049a72ca365d6f69b6b63ef8a3a37b5714265272814c** and byte count are authoritative. The updated manifest now pins those exact bytes, and the acquisition-only CLI has been separated from pack building so the next refresh can record the correct revision metadata before SQLite generation.

No VAG fact changes were observed in the exact 835fe745 re-acquisition delta; only two non-VAG Hyundai i10 unit-label case changes were found.

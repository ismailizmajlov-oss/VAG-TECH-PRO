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

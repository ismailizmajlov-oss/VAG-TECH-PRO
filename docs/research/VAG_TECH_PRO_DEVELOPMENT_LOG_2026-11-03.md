# VAG TECH PRO engineering journal — 2026-11-03

## Run scope

Branch: `automation/rdw-eu-type-approval-research-run19`

Target remains Windows 10/11 x64. No Linux/macOS build work, production deployment, account creation, paid subscription or payment integration was performed.

## Baseline re-check

- Reviewed the latest available Windows offline data-pack artifact from workflow run `41569514426`.
- Re-opened all five SQLite databases read-only; each returned `PRAGMA integrity_check = ok`.
- Confirmed that the bundle keeps licenses separate and does not merge records across datasets.
- Rechecked that generic SAE/ISO DTCs are isolated from manufacturer-controlled DTC candidates.
- Supabase remains outside the first-delivery local SQLite path; no cloud writes or migrations were made in this run.

## Existing offline SQLite evidence

The inspected bundle contains five separate SQLite databases:

| Pack | Rows / evidence | Boundary |
|---|---:|---|
| OBDex | 9,533 generic DTCs; 132 PIDs | CC0 generic SAE/ISO only; no VAG fitment |
| VehiclesDB | 260 model candidates; 1,524 market-presence records | CC BY 4.0; foreign-market model names only |
| VAG engine research | 823 generation candidates; 5,081 engine-variant candidates | ODbL research-only; upstream provenance still requires review |
| OBDb VAG signals | 2,480 signal candidates; 2,315 command candidates; 15 ECU candidates; 32 generation candidates | CC BY-SA research-only; no confirmed ECU/vehicle fitment and no command execution |
| Wal33D DTC candidates | 530 manufacturer-controlled code candidates | Repository-level MIT notice, but rights and record provenance not confirmed; research-only |

The pack counts are from the downloaded workflow artifact, not estimates. These datasets are not represented as verified repair data.

## RDW CC0 type-approval acquisition

Added:

- `data/source-manifests/rdw-eu-type-approval-cc0.json`
- `scripts/build_rdw_type_approval_pack.py`
- `scripts/test_rdw_type_approval_pack.py`
- `.github/workflows/acquire-rdw-eu-type-approval.yml`
- `docs/research/RDW_EU_TYPE_APPROVAL_CC0_REVIEW_2026-11-03.md`

The source set is five RDW datasets: TGK Basis Uitvoering, TGK Merk Uitvoering, TGK Aandrijving Uitvoering, TGK Handelsbenaming Fabrikant and TGK Versnelling Uitvoering. Each selected government-catalogue record declares CC0-1.0. The acquisition stores dataset-specific license evidence, CC0 legal text, Socrata metadata, query URLs/text, raw filtered CSV pages, source revisions and SHA-256 hashes.

The first full export attempt was correctly rejected because the unfiltered TGK Basis export exceeded the configured safe response size. The builder was changed to discover RDW make codes first and retrieve only VAG make rows and related approval-number rows through paginated SoQL queries.

Applicability is deliberately limited:

- market: Netherlands RDW register / European type approvals recorded by RDW;
- precision: type-approval variant;
- status: source-published candidate;
- no Russian/EAEU fitment;
- no exact production-vehicle/VIN fitment;
- RDW `Motorcode` is not promoted to a VAG factory engine code;
- RDW gearbox-type code is not promoted to a VAG factory gearbox code;
- no generation/year, ECU, PR-code or repair-data claim.

### Windows CI status at journal time

- The initial Windows run `41571138506` passed all 10 offline regression tests and then failed on the oversized unfiltered export.
- The filtered SoQL acquisition run `41571524577` was still executing its acquisition step.
- The six-pack Windows bundle runs `41571731692` and `41571789988` were queued/pending.
- Therefore no RDW SQLite artifact or six-pack bundle is marked verified in this journal entry.

## DTC source-rights triage

Added `docs/research/VAG_SPECIFIC_DTC_SOURCE_TRIAGE_2026-11-03.md`.

- OpenVAG is excluded: the repository contains schema/API code but no reviewable SQLite data snapshot or row-level source provenance.
- AutoDiag2 is excluded unless individual source rights are established: the inspected Audi record attributes content to OBDCodeX without a commercial redistribution license.
- OBDex remains generic-only and isolated.
- OBDb remains a separately licensed community signal candidate pack.
- Wal33D remains research-only; repository-level MIT is not treated as proof of rights over every underlying record.

## Windows bundle integration

The offline bundle assembler now expects six independent SQLite packs and independently verifies the RDW pack, including source revisions and applicability boundaries. The bundle workflow is Windows x64 only. The separate licensed databases remain separate; no cross-license merge is performed.

## Next engineering gate

1. Complete the filtered RDW Windows acquisition and inspect the actual make-code inventory and row counts.
2. Correct any RDW alias/schema/query mismatch found by CI; do not loosen the applicability boundary.
3. Complete and independently verify the six-pack offline bundle.
4. Build a metadata-only SQLite pack registry/index that points to the separate licensed databases without merging their contents.
5. Continue Russian/EAEU OTTS discovery only where dataset-specific commercial display/cache rights can be demonstrated.
6. Only after the data layer is stable, implement the Windows desktop technical modules and the NSIS install/update/backup/restore/uninstall tests.

No application-ready or repair-accuracy claim is made by this journal entry.

# MechanicDB Audi/VW DTC candidates and community repair leads — audit (2026-11-05)

## Decision

Keep this dataset in a separate, read-only ODbL research namespace. It contains two make-labelled DTC candidates, six community-authored repair leads and six generic part-name candidates. It is **not** an OEM-confirmed VAG repair database and does not establish exact vehicle applicability.

The app may display the leads as community research references, but must not:
- promote them to factory repair procedures or verified VAG-specific DTC data;
- create executable test plans or diagnostic commands from them;
- infer model, generation, year, engine, gearbox, ECU, PR-code, VIN or market fitment;
- treat generic part names as OEM part numbers.

## Provenance

- Publisher: MechanicDB / MechanicDB-public.
- Immutable upstream revision: \`c788dfe9ed1517d4cd0be27f5aacb4776abf4864\`.
- Acquisition workflow run: \`41956857684\`.
- Acquisition commit: \`5f4f42c6660bee92f13f7950d9677aadc76f03cc\`.
- Artifact ID: \`13383726909\`.
- Artifact SHA-256: \`aaabbb30cc3c616e8136ad31d6371073e42d8ae1c5461b67e80f921a8724d490\`.
- Source snapshot SHA-256: \`3e1357acba252f4aa1f49b94438540b1448fb23663f5a6be5cdfd4e74f2f0eb2\`.
- SQLite SHA-256: \`b0708f055c485018b69263904f60f66124f90f758da9bc597f2145d46ffe5c7d\`.
- Desktop-pack manifest SHA-256 after provenance binding: \`d957d8031857ffb8a053281e33164f0b0530c2619c181cd5409ed75e40b1f294\`.

## Rights

- Data database: Open Database License (ODbL) v1.0.
- Documentation: CC BY 4.0.
- Upstream DTC code-spine notice: MIT; preserved in the pack.
- Published terms allow commercial use, display, offline caching and redistribution subject to attribution, share-alike and open-reuse obligations.
- No paid/full-dataset content is included.
- The ODbL database remains a separate distributable database; it is not merged into proprietary or differently licensed data.

## Included data

| Namespace | Count | Status |
|---|---:|---|
| Make-labelled DTC candidates | 2 | \`community_reference_unverified\` |
| Community repair leads | 6 | \`community_reference_unverified\`, not factory procedures |
| Generic part-name candidates | 6 | \`community_reference_unverified\`, not OEM part numbers |
| Verified OEM repair procedures | 0 | None |
| OEM part numbers | 0 | None |
| Generic SAE/ISO DTC rows in this pack | 0 | Separate namespace |

The two DTC candidates are Audi P3000 and Volkswagen P1128. The six repair leads map only to those two candidate rows. Generic DTC definitions and the generic repair-guidance pack remain separate.

## Source-file hashes

| File | SHA-256 |
|---|---|
| \`upstream/dtc_codes.csv\` | \`796fa2b18bdbff311f15eb4943b68adbf7241e564ce8eff32023a2d297694bff\` |
| \`upstream/diagnostic_fixes.csv\` | \`4a751b24b1c094249e5beacc7117e40e7c14774969b5b1d3be07f46eedd31fbc\` |
| \`upstream/replacement_parts.csv\` | \`634b9aa658af85123992e9f05cacf035c65a83675cd5a2c0db0a22c780fbd59c\` |
| \`upstream/LICENSE-ODbL.txt\` | \`fe0faf3171a95b59dc606677657bd9743e76f4e1e66276fd86aa3cd193ba05bf\` |
| \`upstream/LICENSE-MIT.txt\` | \`cb4a2aba542fa28da9a59e39ae65c92ac0065e995bd275d2e529b49778b46eb0\` |
| \`upstream/SOURCES.md\` | \`9c8ca6ad6ce74b6475e533ef3351723206327db12a85b86b22acdad004444b8a\` |
| \`upstream/DATA_DICTIONARY.md\` | \`0fc3e5a73a229d17c1544b3f90c3a7c71b7eece1d34e078a2c4d117db89b08f0\` |

## Physical source-line evidence

### DTC candidates

| Make | Code | Line | SHA-256 |
|---|---|---:|---|
| Audi | P3000 | 77 | \`e253da2d9d245e39bc7da4e7ca578b1634d5aeb4ad0f793e04128220633ea965\` |
| Volkswagen | P1128 | 91 | \`f97df50476af7b0d4bdeb13628396349bd4199fe75620fd2fd313b2f9e919a38\` |

### Community repair leads

| Fix ID | Candidate code ID | Line | SHA-256 |
|---:|---:|---:|---|
| 33105 | 9344 | 271 | \`ae658e3579a8c115db0e8be849d515870f87fc707fcb3ebeacc3651fe9224e47\` |
| 33106 | 9344 | 272 | \`34815a42a6f5593439c7be1556da4840a732738665737b17ef0a35bc2091995e\` |
| 33107 | 9344 | 273 | \`89493fe4d97c5438d3b662795b666a9c8c1a0e1dfce692bc9a3669056ab6a245\` |
| 54784 | 15386 | 319 | \`0ab2dd574f26d656780d79b2901716d33d11b55c8892a507904fdfefa8c50f28\` |
| 54785 | 15386 | 320 | \`830737f5787ea8180df8d067568248100b04417d5035c772effe05cf37b3a250\` |
| 54786 | 15386 | 321 | \`51a5074ce78b8b396bf143a717e7b2a8ae6876026ebfc7c432d49e54f0a5ff56\` |

### Generic part-name candidates

| Part ID | Fix ID | Line | SHA-256 |
|---:|---:|---:|---|
| 45037 | 33105 | 376 | \`9df3f322808a2972a5a38e270fc1c407bbe1cbec9b64638f907092cd842280cf\` |
| 45038 | 33106 | 377 | \`1deed4b63147f22635c368e26c951c312c3e501a525de17e36d3790234a3f623\` |
| 45039 | 33107 | 378 | \`0a77a2af0c712698fa9bad81c3f0c3eb37b06c68e9d9a569c4cb6c73e5f6595a\` |
| 72741 | 54784 | 448 | \`8d45e85a88029f4fb44e2daf417febc4645824d6964c762a92e8165f9750247d\` |
| 72742 | 54785 | 449 | \`4d1ddcdfe6074bf0e48af0fe4d63525ca123065959c6e1dad81b3cee65f9bdc3\` |
| 72743 | 54786 | 450 | \`65cc5f43d02a5c304adb85e66d35b00a5603db5b502bbd054cf70213784a5730\` |

## Safety and display rules

- Market scope: \`UNKNOWN\`.
- Applicability precision: \`manufacturer_make_candidate\`.
- Exact vehicle, ECU and PR-code fitment: false.
- Diagnostic execution: disabled.
- Repair-procedure status: \`community_authored_not_factory_not_verified\`.
- Consideration order is not a probability or success likelihood.
- Difficulty labels are publisher editorial labels, not OEM safety classifications.
- US cost/labour estimates and external Amazon search URLs are excluded.
- The Audi P3000 community leads concern a high-voltage system. The UI must show a qualified-technician warning and state that OEM isolation/zero-voltage procedures govern; the community text is not a safety procedure.

## Promotion requirements

Promotion requires independent authoritative evidence for the DTC definition and exact vehicle/ECU applicability, plus separate technical review of every repair lead and part mapping. Until then, the data remains read-only research reference material under ODbL.

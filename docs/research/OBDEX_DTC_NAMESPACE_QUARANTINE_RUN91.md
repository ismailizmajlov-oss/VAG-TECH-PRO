# OBDex DTC namespace presentation quarantine — run91

## Decision

Keep OBDex as a separate, read-only CC0 research pack. Do not import its rows into the production VAG-specific DTC index. The desktop research UI must not trust an upstream generic_sae_iso_obd2 label when the local DTC namespace policy classifies the code as manufacturer-controlled, unresolved/reserved or unknown.

The run91 patch changes only the research result projection and presentation. It does not modify the OBDex SQLite file, production SQLite, vehicle configuration records, DTC import batches or user data.

## Pinned source evidence

- Publisher/repository: https://github.com/foerbsnavi/OBDex
- Upstream revision: 9ba1ffa095f3140d9e21b985b322ddea3134bb60
- Snapshot generated: 2026-11-09T12:24:17.1172910Z
- Data licence: CC0-1.0, explicitly applied by upstream to YAML/JSON/schema data files. Upstream code has a separate MIT licence and is not copied into the desktop application.
- Data licence file SHA-256: 2f0d80d2bf20d5637b0077983b503efec8ed943222d8ca14cc1b1295f9eaab3c
- Source manifest SHA-256: ef116c6f453b222083ed88b7ecd2e5a641934420b7f1b3c4ac9c250406e154c6
- Isolated SQLite SHA-256: 4195b3ebc3301e117de5c21729f448c8dce4345bc2554548f906fab95850b3a8
- Acquired source-artifact ZIP SHA-256: ef51a325751edf7d0c5873bedb4832a4850de869f8be857dd476eafb7a7e8647
- Acquisition workflow run: https://github.com/ismailizmajlov-oss/VAG-TECH-PRO/actions/runs/42616568015, artifact ID 13673640228
- Local DTC namespace policy: data/policies/dtc-namespace-ranges.json, revision run87-2026-11-08

The acquired database was independently opened read-only. PRAGMA integrity_check returned ok; PRAGMA foreign_key_check returned zero rows. The source snapshot contains 9,533 DTC identifiers and 132 generic PIDs.

## Range counts from the pinned SQLite

| Local policy class | Rows | Treatment |
|---|---:|---|
| P0xxx, P2xxx, B0xxx, C0xxx, U0xxx | 9,204 | Generic code-range research only; descriptions/categories remain unreviewed |
| P34xx-P39xx | 155 | Unknown/reserved quarantine; not normalized generic or VAG-specific |
| U3xxx | 174 | Unknown/reserved quarantine |
| B3xxx | 0 | Reserved-range quarantine policy; no rows in this snapshot |
| C3xxx | 0 | Reserved-range quarantine policy; no rows in this snapshot |
| Total DTC identifiers | 9,533 | Research-only; no vehicle or ECU fitment |

The 9,204 generic-range count is derived from the pinned SQLite: P0xxx 3,705; P2xxx 3,495; B0xxx 323; C0xxx 626; U0xxx 1,055. It is a code-range count, not a count of independently verified definitions or repair instructions.

## Run91 desktop behavior

- Classify each OBDex DTC against the canonical local namespace policy, not only the upstream namespace label.
- Preserve the upstream namespace label separately as provenance.
- Show generic-range rows as GENERIC SAE/ISO RANGE / RESEARCH ONLY.
- Show unresolved/reserved, manufacturer-controlled and unknown ranges as DTC RANGE QUARANTINE / QUARANTINE.
- Label OBDex titles, categories, descriptions, components and possible causes as unverified source content.
- Suppress source-provided component/cause lists for quarantined rows.
- Do not render embedded third-party references from OBDex; the CC0 data grant does not relicense those external documents.
- Include the policy revision, market scope UNKNOWN, applicability precision generic_code_only, source snapshot, source-record SHA-256 and source-manifest SHA-256 in the result.
- Keep fitmentClaim=false and diagnosticExecutionAllowed=false for every row.

The local regression suite was run against the actual pinned OBDex SQLite: 5/5 tests passed. The run91 patch also adds data/policies to the packaged app runtime at app-runtime/data/policies so offline namespace classification does not depend on the development checkout. The patch script also passed a clean-apply and second-run idempotence check. The Windows CI integration is pending; no production import or installer release is claimed by this research note.

## Cross-layer acceptance matrix

The Windows pull-request workflow must verify the same classification at the policy, SQLite-reader, renderer and package-resource layers:

| Test input | Expected namespace | Expected UI state | Permitted use |
|---|---|---|---|
| P0xxx, P2xxx, B0xxx, C0xxx, U0xxx | `generic_sae_iso_obd2` | `GENERIC SAE/ISO RANGE` / `RESEARCH ONLY` | Read-only generic reference; no vehicle/ECU fitment |
| P1xxx, P30xx–P33xx, B1xxx–B2xxx, C1xxx–C2xxx, U1xxx–U2xxx | `manufacturer_controlled_candidate` | `DTC RANGE QUARANTINE` / `QUARANTINE` | Unattributed manufacturer-controlled research only; never infer VAG authorship |
| P34xx–P39xx, U3xxx, B3xxx, C3xxx | `unknown_reserved` | `DTC RANGE QUARANTINE` / `QUARANTINE` | Retain source row for audit only; suppress source component/cause/symptom lists |
| Malformed or unclassified identifier | `unknown` | `DTC RANGE QUARANTINE` / `QUARANTINE` | No normalized DTC lookup or diagnostic execution |

For every returned row, acceptance also requires: the upstream namespace label is preserved separately; the source-record and source-snapshot SHA-256 values are present; the canonical policy revision is shown; market remains `UNKNOWN`; applicability remains `generic_code_only`; `fitmentClaim=false`; `diagnosticExecutionAllowed=false`; and external references are not rendered.

The Windows package-resource check must open the packaged policy from the Electron runtime resource directory with external networking blocked. The OBDex SQLite snapshot must remain byte-for-byte unchanged, the production catalog and user database must remain untouched, and a failed policy/resource/test check must fail the build before NSIS packaging. This matrix is a validation contract, not a claim that the upstream descriptions are technically verified.

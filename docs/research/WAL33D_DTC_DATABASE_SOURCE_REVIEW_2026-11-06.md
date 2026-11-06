# Wal33D DTC database — source-lineage and namespace review (2026-11-06)

## Decision

The Volkswagen-labelled file from `Wal33D/dtc-database` remains a quarantined research candidate. It is **not approved** for the VAG TECH PRO production DTC namespace, Windows offline pack, technical search, or redistribution. No records from this source were imported or exposed as confirmed VAG-specific definitions.

## Pinned candidate snapshot

- Repository: https://github.com/Wal33D/dtc-database
- Pinned revision already recorded in the source manifest: `04c43d72e7db7197658b6f72fe582c5076d9eee8`
- Candidate file: `data/source-data/volkswagen_codes.txt`
- Candidate file SHA-256: `fd6bf267f1db3a1a44279a21b1c69cba19ee96d2b2821e0b238cdf54b3a71579`
- Git blob SHA-1 observed for that file: `a8afd432644e8cad718e42cdd18cc1931a75bb08`
- Root licence file: `LICENSE`; repository README declares MIT, but no separate data licence or per-record rights statement was found in the reviewed material.
- Upstream README states that `data/source-data/` contains 37 source text files.

## Reviewed upstream implementation

The repository README describes the source files as `CODE - Description` text. The reviewed `build_database.py` assigns the manufacturer by uppercasing the file stem and removing `_codes`. Only the four generic stems `p_codes`, `b_codes`, `c_codes`, and `u_codes` are treated as generic; every other file is marked manufacturer-specific.

This is a filename-based classification rule. It does not prove that a description was authored or approved by the named manufacturer, and it does not establish a VAG-specific namespace for each row.

The reviewed Volkswagen file contains code/description pairs. It does not include row-level source URLs, source revisions, market scope, model, generation, model year, engine code, gearbox code, ECU identity, hardware/software revision, or vehicle applicability. A five-character P1 code and a filename labelled Volkswagen are insufficient evidence of exact OEM origin or fitment.

The adjacent Audi file contains broad PCM/OBD troubleshooting language. This reinforces the need for row-level provenance and independent technical review; it is not evidence that the Volkswagen file is OEM-authored.

## Rights boundary

The repository has a root MIT licence and a README-level MIT declaration. The reviewed upstream material does not separately identify the origin and rights holder for each imported description or provide a source index mapping each file/row to a primary source. A repository-level software licence is not treated as independent proof that the repository author holds redistribution rights to every third-party description.

No project-specific written permission was obtained. Commercial use, product display, persistent offline caching, bulk reuse and redistribution of the Volkswagen DTC content therefore remain unapproved for this project.

## Applicability boundary

The candidate has:
- market scope: `UNKNOWN`;
- applicability precision: `manufacturer_make_candidate`;
- exact model/generation/year fitment: not established;
- exact engine/gearbox pairing: not established;
- ECU/HW/SW fitment: not established;
- diagnostic execution: prohibited;
- test plans and repair procedures: not supplied as traceable OEM records.

The data must not be merged with generic SAE/ISO DTCs or represented as factory VAG DTCs. Any description must remain outside technician-facing repair guidance until its provenance, rights and technical applicability are independently established.

## Evidence reviewed on 2026-11-06

| File | Observed Git blob SHA-1 | Finding |
|---|---|---|
| `README.md` | `1ab235040508244db114e7cafc6c6afe973425d7` | Repository-level MIT declaration; 37 source text files; no per-file source index in the reviewed README |
| `LICENSE` | `9cbfaae3f07b8daa1685b4587e36c604a7a4ded1` | Root MIT text; no separate dataset-specific licence located |
| `build_database.py` | `d4d8ff47eff67fa6d450ae99546e5c6dc483b6d4` | Manufacturer inferred from filename; no row-level provenance or fitment |
| `data/source-data/volkswagen_codes.txt` | `a8afd432644e8cad718e42cdd18cc1931a75bb08` | Code/description pairs only |
| `data/source-data/audi_codes.txt` | `96cac4cd186eae8b7b74d151c5a3dc36c9cb8870` | Broad PCM/OBD language; no row-level OEM provenance |

The source manifest `data/source-manifests/wal33d-dtc-candidate.json` contains the corresponding candidate-pack hash, source-file SHA-256, review evidence, rights boundary and quarantine decision.

## Reconsideration requirements

The publisher would need to supply:
1. per-file primary-source lineage and per-record source attribution;
2. evidence that the publisher controls the rights in the imported descriptions;
3. a data-specific licence or written permission covering commercial use, display, offline caching, bulk reuse and redistribution;
4. a reproducible acquisition/build process with immutable source revisions and SHA-256 snapshots;
5. clear separation of generic and manufacturer-specific namespaces; and
6. independent technical review binding each accepted definition to an exact ECU and applicable vehicle scope before repair or diagnostic execution is enabled.

No account, paid access, API key, bulk download, or maintainer contact was initiated.

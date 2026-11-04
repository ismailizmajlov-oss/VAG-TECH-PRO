# Owner-controlled source rights approval

This workflow records a human rights decision. It is not legal advice, automated license interpretation, or a technical-data approval.

## Required evidence

For an existing source candidate, the owner or an authorized operator must review the actual terms and provide:

1. The exact license text or license document.
2. The applicable written permission or official terms evidence.
3. The exact source snapshot that will be imported.

The desktop computes SHA-256 locally for all three files. File contents are not uploaded by the approval form; only hashes and metadata are written to the local SQLite audit trail. Keep the original evidence files in a controlled location.

## Rights that must be explicitly granted

The evidence must permit all five actions for the intended VAG TECH PRO distribution:

- commercial use;
- display in the application;
- offline caching;
- bulk reuse;
- redistribution with the application.

The operator must also record whether attribution and Share-Alike obligations apply, and the exact attribution text where required. If any permission is missing, ambiguous, limited to online lookup, or limited to a named individual/account, leave the source in `permission_required` status.

## What approval does not mean

Approving source rights changes only the source's rights status. It does **not** approve the accuracy of imported technical records, establish vehicle applicability, or authorize a repair instruction. Imported records remain candidates until a separate technical review validates their source, revision, market, model/generation/year, engine/transmission/ECU links, and applicability precision.

Generic SAE/ISO OBD-II DTCs remain in their own namespace and must never be represented as VAG-specific. Manufacturer-labelled candidates without exact model/ECU evidence remain separate and unverified.

## EAEU / Russian registries and OEM sources

Public search access to an OTTS or FGIS registry is not, by itself, evidence of permission for bulk extraction, offline caching, or redistribution. A source must remain a candidate until the applicable terms or written authorization explicitly cover those uses. The same rule applies to OEM portals and user-specific subscriptions: do not package or redistribute cached material unless the relevant terms expressly allow it.

## Import matching

The later import package must match the approved source ID, revision, market scope, source snapshot SHA-256, license SHA-256, and rights-evidence SHA-256. A mismatch must fail closed and leave the live database unchanged.
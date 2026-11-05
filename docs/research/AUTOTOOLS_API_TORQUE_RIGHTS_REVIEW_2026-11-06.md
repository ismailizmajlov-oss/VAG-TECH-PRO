# AutoTools public API — torque-data rights and provenance review (2026-11-06)

## Decision

AutoTools is a potentially relevant third-party source for generic torque references and vehicle/OBD API data. It is **not approved for VAG TECH PRO import or offline distribution**.

The API documentation states that endpoints are free for personal and commercial use with attribution and says consumers may cache results on their side. The published Terms of Use separately state: "Do not copy substantial parts of the content for commercial reuse." Those statements do not provide an unambiguous grant for bulk extraction, a bundled offline SQLite dataset, or redistribution inside a third-party Windows application.

The torque page calls its values common workshop figures from technical documentation and says they must be checked against the official service manual. The About page likewise describes the figures as estimates. No per-row primary document, revision, model-year, engine, gearbox, market or exact VAG fitment evidence was identified in the reviewed public documentation.

## Evidence reviewed

- API documentation: https://autotools.brightcoding.dev/docs
  - commercial-use-with-attribution statement;
  - torque, OBD, vehicle and maintenance API endpoint descriptions;
  - statement that consumers may cache results;
  - documented vehicle-data sources include NHTSA, Transport Canada and EPA for specific fields.
- Published Terms of Use: https://autotools.brightcoding.dev/terms
  - educational/diagnostic-aid disclaimer;
  - torque values are indicative;
  - clause under Acceptable Use prohibits copying substantial parts of the content for commercial reuse.
- About page: https://autotools.brightcoding.dev/about
  - values are estimates; torque specifications and oil quantities are described as common workshop documentation and must be verified against the official manual.
- Torque reference page: https://autotools.brightcoding.dev/tools/torque-specs
  - generic example ranges are labelled typical/common, not tied to a named VAG model, engine, gearbox or model year.

## Applicability and quality limits

- No Russian/EAEU market scope is established.
- The public torque page does not supply exact VAG vehicle/engine/gearbox applicability or a source revision for each fastener.
- A general torque value is not safe to promote as an OEM critical specification.
- Generic OBD endpoints are not VAG-specific factory DTC definitions.
- The API documentation identifies NHTSA, Transport Canada and EPA as sources for some vehicle information; those fields are US/Canada scope and do not establish RU/EAEU fitment.
- The reviewed public documentation does not identify row-level primary sources for torque records.

## Rights and ingestion boundary

The API documentation's client-side caching statement is not treated as permission to package and redistribute substantial datasets. The Terms restriction is applied conservatively until the publisher provides written clarification.

No API calls were made, no records or PDFs were downloaded, no account was created, no payment was made, and no data was imported. The source remains quarantined. Reconsideration requires:
1. a written clarification covering commercial use in a third-party Windows application;
2. explicit permission for the intended offline caching and redistribution scope;
3. row-level source, revision, market and exact vehicle/engine/gearbox applicability for every critical torque value.

## Project action

The source register and regression tests now ensure this API cannot silently become a torque-data source. It remains a research lead only, with zero imported rows and zero approved critical torque values.

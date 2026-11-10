"use strict";

const fs = require("node:fs");
const path = require("node:path");

const root = path.join(__dirname, "desktop-source");
const dbFile = path.join(root, "lib", "local-research-db.cjs");
const testFile = path.join(root, "tests", "local-research-db.test.cjs");
for (const file of [dbFile, testFile]) {
  if (!fs.existsSync(file)) throw new Error("Required desktop source file is missing: " + file);
}

function replaceOnce(source, before, after, label) {
  if (source.includes(after)) return source;
  const first = source.indexOf(before);
  if (first < 0 || first !== source.lastIndexOf(before)) {
    throw new Error("Expected " + label + " block exactly once; refusing unsafe patch.");
  }
  return source.slice(0, first) + after + source.slice(first + before.length);
}


function ensureVehiclesDbCandidateGate(source) {
  const gateStart = source.indexOf("if (!vehiclesDbProvenance");
  const gateEnd = gateStart >= 0 ? source.indexOf(") {", gateStart) : -1;
  if (gateStart >= 0 && gateEnd > gateStart) {
    const gate = source.slice(gateStart, gateEnd + 3);
    const requiredDynamicMarkers = [
      "vehiclesDbProvenance.dataset_id !== PACKS.vehiclesdb.id ||",
      "vehiclesDbProvenance.dataset_license !== PACKS.vehiclesdb.license ||",
      "vehiclesDbProvenance.upstream_tag !== vehiclesDbPackManifest.upstream_tag ||",
      "vehiclesDbProvenance.upstream_manifest_sha256 !== vehiclesDbPackManifest.source_manifest_sha256 ||",
      "vehiclesDbProvenance.source_catalog_sha256 !== vehiclesDbPackManifest.source_catalog_sha256 ||",
      "vehiclesDbProvenance.attribution_sha256 !== vehiclesDbPackManifest.source_snapshot_sha256?.[\"ATTRIBUTION.md\"] ||",
      "vehiclesDbProvenance.license_sha256 !== vehiclesDbPackManifest.source_snapshot_sha256?.[\"LICENSE\"] ||",
      "vehiclesDbProvenance.lock_sha256 !== vehiclesDbPackManifest.lock_sha256 ||",
      "vehiclesDbCounts.models !== vehiclesDbPackManifest.counts?.models ||",
      "vehiclesDbCounts.marketEvidence !== vehiclesDbPackManifest.counts?.market_evidence ||",
      "vehiclesDbCounts.russianEvidence !== 0 ||",
      "vehiclesDbPackManifest.identity_only_use !== true ||",
      "vehiclesDbPackManifest.safety_critical_reliance !== false ||",
      "vehiclesDbPackManifest.repair_decision_use !== false ||",
      "vehiclesDbPackManifest.fitment_claim !== false ||",
      "vehiclesDbPackManifest.ru_evidence_present !== false ||",
      "vehiclesDbPackManifest.attribution?.required !== true ||",
      "vehiclesDbPackManifest.counts?.models !== vehiclesDbCounts.models ||",
      "vehiclesDbPackManifest.counts?.market_evidence !== vehiclesDbCounts.marketEvidence ||",
      "vehiclesDbPackManifest.open_data_policy_notice.includes(",
      "!/Vehicle data by VehiclesDB/i.test(vehiclesDbAttribution)",
      "!/UNCONDITIONAL/i.test(vehiclesDbAttribution)"
    ];
    if (requiredDynamicMarkers.every((marker) => gate.includes(marker))) {
      if (/vehiclesDbCounts\.models\s*!==\s*\d+/.test(gate) ||
          /vehiclesDbCounts\.marketEvidence\s*!==\s*\d+/.test(gate)) {
        throw new Error("VehiclesDB candidate gate mixes manifest-driven counts with stale fixed model/evidence counts.");
      }
      return source;
    }
  }

  const legacyGate = `if (!vehiclesDbProvenance || vehiclesDbProvenance.dataset_license !== PACKS.vehiclesdb.license || vehiclesDbProvenance.attribution_required !== 1 ||
        vehiclesDbProvenance.ru_evidence_present !== 0 || vehiclesDbProvenance.fitment_claim !== 0 ||
        vehiclesDbCounts.sources !== 14 || vehiclesDbCounts.models !== 260 || vehiclesDbCounts.marketEvidence !== 1524 || vehiclesDbCounts.russianEvidence !== 0 ||
        vehiclesDbPackManifest.dataset_license !== PACKS.vehiclesdb.license || vehiclesDbPackManifest.fitment_claim !== false ||
        vehiclesDbPackManifest.ru_evidence_present !== false || vehiclesDbPackManifest.attribution?.required !== true ||
        vehiclesDbPackManifest.counts?.models !== vehiclesDbCounts.models || vehiclesDbPackManifest.counts?.market_evidence !== vehiclesDbCounts.marketEvidence ||
        !/Vehicle data by VehiclesDB/i.test(vehiclesDbAttribution) || !/UNCONDITIONAL/i.test(vehiclesDbAttribution)) {`;
  const currentGate = `if (!vehiclesDbProvenance || vehiclesDbProvenance.dataset_id !== PACKS.vehiclesdb.id ||
        vehiclesDbProvenance.dataset_license !== PACKS.vehiclesdb.license ||
        vehiclesDbProvenance.upstream_tag !== vehiclesDbPackManifest.upstream_tag ||
        vehiclesDbProvenance.upstream_manifest_sha256 !== vehiclesDbPackManifest.source_manifest_sha256 ||
        vehiclesDbProvenance.source_catalog_sha256 !== vehiclesDbPackManifest.source_catalog_sha256 ||
        vehiclesDbProvenance.attribution_sha256 !== vehiclesDbPackManifest.source_snapshot_sha256?.["ATTRIBUTION.md"] ||
        vehiclesDbProvenance.license_sha256 !== vehiclesDbPackManifest.source_snapshot_sha256?.["LICENSE"] ||
        vehiclesDbProvenance.lock_sha256 !== vehiclesDbPackManifest.lock_sha256 ||
        vehiclesDbCounts.sources !== 14 || vehiclesDbCounts.models !== 260 || vehiclesDbCounts.marketEvidence !== 1524 || vehiclesDbCounts.russianEvidence !== 0 ||
        vehiclesDbPackManifest.dataset_license !== PACKS.vehiclesdb.license || vehiclesDbPackManifest.fitment_claim !== false ||
        vehiclesDbPackManifest.ru_evidence_present !== false || vehiclesDbPackManifest.attribution?.required !== true ||
        vehiclesDbPackManifest.counts?.models !== vehiclesDbCounts.models || vehiclesDbPackManifest.counts?.market_evidence !== vehiclesDbCounts.marketEvidence ||
        !/Vehicle data by VehiclesDB/i.test(vehiclesDbAttribution) || !/UNCONDITIONAL/i.test(vehiclesDbAttribution)) {`;
  return replaceOnce(source, legacyGate, currentGate, "VehiclesDB provenance and candidate-only gate");
}

let source = fs.readFileSync(dbFile, "utf8");
source = replaceOnce(
  source,
  'const vehiclesDbProvenance = vehiclesDb.prepare("SELECT dataset_id, publisher, repository_url, upstream_tag, dataset_version, dataset_license, attribution_required, attribution_text, attribution_url, catalog_sqlite_sha256, upstream_manifest_sha256, license_sha256, attribution_sha256, ru_evidence_present, fitment_claim FROM dataset_provenance WHERE provenance_id=1").get();',
  'const vehiclesDbProvenance = vehiclesDb.prepare("SELECT dataset_id, publisher, repository, upstream_tag, dataset_version, dataset_license, license_url, upstream_manifest_sha256, source_catalog_sha256, attribution_sha256, license_sha256, lock_sha256, imported_at_utc FROM dataset_provenance WHERE dataset_id=?").get(PACKS.vehiclesdb.id);',
  "VehiclesDB provenance query"
);
source = ensureVehiclesDbCandidateGate(source);
source = replaceOnce(source, "attributionUrl: safeHttpsUrl(vehiclesDbProvenance.attribution_url),", "attributionUrl: safeHttpsUrl(vehiclesDbPackManifest.attribution?.url),", "VehiclesDB attribution URL");
source = replaceOnce(source, "upstreamRevision: vehiclesDbProvenance.upstream_tag,", "upstreamRevision: vehiclesDbPackManifest.upstream_tag,", "VehiclesDB upstream revision");
source = replaceOnce(source, "snapshotGeneratedAt: vehiclesDbProvenance.built_at_utc,", "snapshotGeneratedAt: vehiclesDbPackManifest.built_at_utc,", "VehiclesDB snapshot timestamp");

const functionStart = source.indexOf("function searchVehiclesDbCandidates(query, limit = 25, root) {");
const nextFunction = source.indexOf("\nfunction searchUdsSignals(", functionStart);
const functionEnd = nextFunction >= 0 ? nextFunction : source.indexOf("\nmodule.exports = {", functionStart);
if (functionStart < 0 || functionEnd < 0) throw new Error("VehiclesDB search function boundaries not found");
const newFunction = String.raw`function searchVehiclesDbCandidates(query, limit = 25, root) {
  const q = validateQuery(query);
  const pack = verifyPackDatabaseHash(root, PACKS.vehiclesdb.id, PACKS.vehiclesdb.file);
  for (const [fileField, hashField] of [["license_file", "license_file_sha256"], ["source_manifest_file", "source_manifest_sha256"], ["upstream_manifest_file", "upstream_manifest_sha256"], ["attribution_file", "attribution_sha256"]]) {
    verifyPackFileHash(root, PACKS.vehiclesdb.id, fileField, hashField);
  }
  const packManifest = JSON.parse(fs.readFileSync(path.join(getResearchRoot(root), PACKS.vehiclesdb.manifest), "utf8"));
  const db = openReadOnly(root, PACKS.vehiclesdb.file);
  try {
    const pattern = likePattern(q);
    const models = db.prepare(
      "SELECT model_id, kind, make_slug, make_name, model_slug, model_name,\n" +
      "  body_types_json, regions_json, market_scope_json, applicability_precision,\n" +
      "  verification_status, fitment_status, year_start, year_end, source_ids_json\n" +
      "FROM model_candidates\n" +
      "WHERE applicability_precision='make_model_name_only'\n" +
      "  AND verification_status='identity_candidate' AND fitment_status='not_established'\n" +
      "  AND (make_name LIKE ? ESCAPE '\\' OR model_name LIKE ? ESCAPE '\\')\n" +
      "ORDER BY make_name, model_name\n" +
      "LIMIT ?"
    ).all(pattern, pattern, clampLimit(limit));
    if (!models.length) return [];
    const ids = models.map((row) => row.model_id);
    const placeholders = ids.map(() => "?").join(",");
    const evidence = db.prepare(
      "SELECT me.model_id, me.country_code, me.evidence_type,\n" +
      "  sr.source_id, sr.source_name, sr.source_url, sr.source_license,\n" +
      "  sr.source_license_url, sr.evidence_type AS source_evidence_type\n" +
      "FROM model_market_evidence me\n" +
      "JOIN source_registry sr ON sr.source_id=me.source_id\n" +
      "WHERE me.model_id IN (" + placeholders + ")\n" +
      "  AND me.country_code!='ru'\n" +
      "  AND me.applicability_precision='market_presence_only'\n" +
      "  AND me.verification_status='source_published_presence_evidence'\n" +
      "ORDER BY me.model_id, me.country_code, sr.source_name"
    ).all(...ids);
    const byModel = new Map(ids.map((id) => [id, []]));
    for (const row of evidence) byModel.get(row.model_id)?.push({
      countryCode: row.country_code,
      evidenceType: row.evidence_type,
      sourceId: row.source_id,
      sourceName: row.source_name,
      sourceUrl: safeHttpsUrl(row.source_url),
      sourceLicense: row.source_license,
      sourceLicenseUrl: safeHttpsUrl(row.source_license_url),
      evidenceScope: "market_presence_only",
      attributionRequired: true,
    });
    return models.map((row) => {
      const marketEvidence = byModel.get(row.model_id) || [];
      const markets = [...new Set(marketEvidence.map((item) => item.countryCode))].sort();
      const parseJsonArray = (value) => {
        try {
          const parsed = JSON.parse(value || "[]");
          return Array.isArray(parsed) ? parsed : [];
        } catch {
          return [];
        }
      };
      const sourceRecord = {
        model_id: row.model_id,
        kind: row.kind,
        make_slug: row.make_slug,
        make_name: row.make_name,
        model_slug: row.model_slug,
        model_name: row.model_name,
        body_types_json: row.body_types_json,
        regions_json: row.regions_json,
        market_scope_json: row.market_scope_json,
        source_ids_json: row.source_ids_json,
        year_start: row.year_start,
        year_end: row.year_end,
        applicability_precision: row.applicability_precision,
        verification_status: row.verification_status,
        fitment_status: row.fitment_status,
      };
      const candidateRecordSha256 = crypto.createHash("sha256").update(JSON.stringify(sourceRecord)).digest("hex");
      return {
        sourceModelId: row.model_id,
        brand: row.make_name,
        brandKey: row.make_slug,
        model: row.model_name,
        modelKey: row.model_slug,
        vehicleKind: row.kind,
        bodyTypes: parseJsonArray(row.body_types_json),
        regions: parseJsonArray(row.regions_json),
        marketScope: markets,
        declaredMarketScope: parseJsonArray(row.market_scope_json),
        sourceIds: parseJsonArray(row.source_ids_json),
        marketEvidence,
        marketEvidenceCount: marketEvidence.length,
        applicabilityPrecision: row.applicability_precision,
        reviewStatus: row.verification_status,
        verificationStatus: row.verification_status,
        fitmentStatus: row.fitment_status,
        modelYearStart: row.year_start ?? null,
        modelYearEnd: row.year_end ?? null,
        engineCode: null,
        gearboxCode: null,
        ecuFitment: false,
        exactFitment: false,
        ruEvidencePresent: false,
        identityOnlyUse: packManifest.identity_only_use === true,
        safetyCriticalReliance: packManifest.safety_critical_reliance === true,
        repairDecisionUse: packManifest.repair_decision_use === true,
        openDataPolicyNotice: packManifest.open_data_policy_notice,
        sourceRevision: packManifest.upstream_tag,
        sourceUrl: safeHttpsUrl(packManifest.source_repository),
        sourceLicense: PACKS.vehiclesdb.license,
        attributionRequired: true,
        attribution: typeof packManifest.attribution === "string" ? packManifest.attribution : "Vehicle data by VehiclesDB (vehiclesdb.com)",
        attributionUrl: safeHttpsUrl(packManifest.attribution?.url),
        sourceSha256: packManifest.source_catalog_sha256,
        candidateRecordSha256,
        recordHashKind: "normalized_candidate_row",
        sourceManifestSha256: pack.source_manifest_sha256,
        upstreamManifestSha256: pack.upstream_manifest_sha256,
        databaseSha256: pack.database_sha256,
        sourceCatalogSha256: packManifest.source_catalog_sha256,
        warning: "Только наличие названия модели в зарубежных источниках. В наборе нет данных RU; это не подтверждает российскую/ЕАЭС применимость, поколение, год, двигатель, КПП, ECU или комплектацию автомобиля.",
      };
    });
  } finally {
    db.close();
  }
}`;
source = source.slice(0, functionStart) + newFunction + source.slice(functionEnd);
const vehiclesFunctionStart = source.indexOf("function searchVehiclesDbCandidates");
const vehiclesFunctionEnd = source.indexOf("\nfunction searchUdsSignals", vehiclesFunctionStart) > 0 ? source.indexOf("\nfunction searchUdsSignals", vehiclesFunctionStart) : source.indexOf("\nmodule.exports = {", vehiclesFunctionStart);
const patchedVehiclesFunction = source.slice(vehiclesFunctionStart, vehiclesFunctionEnd);
if (/repository_url|provenance_id|model_candidate_id|source_model_id|body_types_raw|regions_raw|market_scope_summary_json|upstream_license|evidence_kind|upstream_attribution_required/.test(patchedVehiclesFunction)) {
  throw new Error("Legacy VehiclesDB column names remain in the candidate search function");
}
fs.writeFileSync(dbFile, source, "utf8");

const verifierFile = path.join(root, "scripts", "verify-local-research-packs.cjs");
if (!fs.existsSync(verifierFile)) throw new Error("Required research-pack verifier is missing: " + verifierFile);
let verifier = fs.readFileSync(verifierFile, "utf8");
verifier = replaceOnce(
  verifier,
  'assert(vehiclesDbSnapshot.dataset_id === "vehiclesdb-vag-identity-cc-by-4.0" && vehiclesDbSnapshot.dataset_license === vehiclesdb.license, "VehiclesDB dataset manifest identity/license mismatch");',
  'assert(vehiclesDbSnapshot.pack_id === vehiclesdb.id && vehiclesDbSnapshot.dataset_license === vehiclesdb.license, "VehiclesDB dataset manifest identity/license mismatch");',
  "VehiclesDB current pack identity"
);
verifier = replaceOnce(
  verifier,
  'assert(vehiclesDbSnapshot.attribution?.required === true && /Vehicle data by VehiclesDB/i.test(vehiclesDbAttribution) && /UNCONDITIONAL/i.test(vehiclesDbAttribution), "VehiclesDB attribution and upstream notices are incomplete");',
  'assert(vehiclesDbSnapshot.attribution_required === true && /Vehicle data by VehiclesDB/i.test(vehiclesDbAttribution) && /UNCONDITIONAL/i.test(vehiclesDbAttribution), "VehiclesDB attribution and upstream notices are incomplete");',
  "VehiclesDB current attribution flag"
);
verifier = replaceOnce(
  verifier,
  'const vehiclesDbProvenance = vehiclesDb.prepare("SELECT dataset_id, publisher, repository_url, upstream_tag, dataset_version, dataset_license, attribution_required, attribution_text, attribution_url, catalog_sqlite_sha256, upstream_manifest_sha256, license_sha256, attribution_sha256, ru_evidence_present, fitment_claim FROM dataset_provenance WHERE provenance_id=1").get();',
  'const vehiclesDbProvenance = vehiclesDb.prepare("SELECT dataset_id, publisher, repository, upstream_tag, dataset_version, dataset_license, license_url, upstream_manifest_sha256, source_catalog_sha256, attribution_sha256, license_sha256, lock_sha256, imported_at_utc FROM dataset_provenance WHERE dataset_id=?").get(vehiclesdb.id);',
  "VehiclesDB verifier provenance query"
);
verifier = replaceOnce(
  verifier,
  'assert(vehiclesDbProvenance && vehiclesDbProvenance.dataset_license === "CC-BY-4.0" && vehiclesDbProvenance.attribution_required === 1 && vehiclesDbProvenance.ru_evidence_present === 0 && vehiclesDbProvenance.fitment_claim === 0, "VehiclesDB embedded provenance failed");',
  'assert(vehiclesDbProvenance && vehiclesDbProvenance.dataset_id === vehiclesdb.id && vehiclesDbProvenance.dataset_license === "CC-BY-4.0", "VehiclesDB embedded provenance failed");',
  "VehiclesDB verifier embedded provenance"
);
verifier = replaceOnce(
  verifier,
  'assert(vehiclesDbProvenance.catalog_sqlite_sha256 === vehiclesDbSnapshot.source_snapshot_sha256["catalog.sqlite"] && vehiclesDbProvenance.upstream_manifest_sha256 === vehiclesdb.upstream_manifest_sha256 && vehiclesDbProvenance.license_sha256 === vehiclesdb.license_file_sha256 && vehiclesDbProvenance.attribution_sha256 === vehiclesdb.attribution_sha256, "VehiclesDB embedded source hashes mismatch");',
  'assert(vehiclesDbProvenance.upstream_manifest_sha256 === vehiclesdb.upstream_manifest_sha256 && vehiclesDbProvenance.source_catalog_sha256 === vehiclesDbSnapshot.source_catalog_sha256 && vehiclesDbProvenance.license_sha256 === vehiclesdb.license_file_sha256 && vehiclesDbProvenance.attribution_sha256 === vehiclesdb.attribution_sha256 && vehiclesDbProvenance.lock_sha256 === vehiclesDbSnapshot.lock_sha256, "VehiclesDB embedded source hashes mismatch");',
  "VehiclesDB verifier embedded source hashes"
);
const sourceArtifactBefore = [
  'const sourceArtifacts = vehiclesDb.prepare("SELECT relative_path, sha256 FROM source_file_artifacts ORDER BY relative_path").all();',
  '    for (const artifact of sourceArtifacts) {',
  '      const expected = vehiclesDbSnapshot.source_snapshot_sha256[artifact.relative_path === "catalog.sqlite" ? "catalog.sqlite" : artifact.relative_path === "manifest.json" ? "manifest.json" : artifact.relative_path === "LICENSE" ? "LICENSE" : "ATTRIBUTION.md"];',
  '      assert(expected === artifact.sha256, `VehiclesDB source artifact hash mismatch for ${artifact.relative_path}`);',
  '    }',
].join("\n");
const sourceArtifactAfter = [
  'const sourceArtifacts = vehiclesDb.prepare("SELECT source_path, sha256, source_role FROM source_file_artifacts ORDER BY source_path").all();',
  '    for (const artifact of sourceArtifacts) {',
  '      const expected = vehiclesDbSnapshot.source_snapshot_sha256[artifact.source_role];',
  '      assert(expected === artifact.sha256, `VehiclesDB source artifact hash mismatch for ${artifact.source_path}`);',
  '    }',
].join("\n");
verifier = replaceOnce(verifier, sourceArtifactBefore, sourceArtifactAfter, "VehiclesDB source file artifact schema");
fs.writeFileSync(verifierFile, verifier, "utf8");

let tests = fs.readFileSync(testFile, "utf8");
tests = replaceOnce(
  tests,
  '  assert.deepEqual(vehiclesDb.counts, { sources: 14, models: 260, marketEvidence: 1524, russianEvidence: 0 });',
  '  const vehiclesDbManifest = JSON.parse(fs.readFileSync(path.join(root, "vehiclesdb-vag-identity", "manifest.json"), "utf8"));\\n  assert.equal(vehiclesDb.counts.sources, vehiclesDbManifest.counts.sources);\\n  assert.equal(vehiclesDb.counts.models, vehiclesDbManifest.counts.models);\\n  assert.equal(vehiclesDb.counts.marketEvidence, vehiclesDbManifest.counts.market_evidence);\\n  assert.equal(vehiclesDb.counts.russianEvidence, 0);',
  "VehiclesDB manifest-driven summary counts"
);
tests = replaceOnce(
  tests,
  '  assert.equal(rows[0].snapshotGeneratedAt, "2026-11-03T07:21:36.7901580Z");',
  '  const rootManifest = JSON.parse(fs.readFileSync(path.join(root, "manifest.json"), "utf8"));\n  const obdexPack = rootManifest.packs.find((pack) => pack.id === "obdex-generic-cc0");\n  assert.equal(rows[0].snapshotGeneratedAt, obdexPack.snapshot_generated_at_utc);',
  "dynamic OBDex snapshot timestamp assertion"
);
tests = replaceOnce(
  tests,
  '  assert.throws(() => vehiclesDb.exec("DELETE FROM model_candidates WHERE model_candidate_id=1"), /readonly|read-only|query only/i);',
  "  assert.throws(() => vehiclesDb.exec(\"DELETE FROM model_candidates WHERE model_id='car/audi/100'\"), /readonly|read-only|query only/i);",
  "VehiclesDB read-only mutation assertion"
);
const golfHashBefore = '  assert.match(golf.sourceSha256, /^[a-f0-9]{64}$/);';
const golfHashAfter = [
  '  assert.match(golf.sourceSha256, /^[a-f0-9]{64}$/);',
  '  assert.match(golf.candidateRecordSha256, /^[a-f0-9]{64}$/);',
  '  assert.equal(golf.recordHashKind, "normalized_candidate_row");',
  '  assert.ok(Array.isArray(golf.sourceIds) && golf.sourceIds.length > 0);',
  '  assert.equal(golf.verificationStatus, "identity_candidate");',
  '  assert.match(golf.sourceCatalogSha256, /^[a-f0-9]{64}$/);',
  '  assert.equal(golf.sourceSha256, golf.sourceCatalogSha256);',
].join("\n");
tests = replaceOnce(tests, golfHashBefore, golfHashAfter, "VehiclesDB record and source catalog fingerprints");
fs.writeFileSync(testFile, tests, "utf8");

process.stdout.write(JSON.stringify({
  status: "patched",
  databaseFile: path.relative(root, dbFile),
  testFile: path.relative(root, testFile),
  changes: [
    "use the current VehiclesDB dataset_provenance schema and manifest for rights/attribution fields",
    "align the independent research-pack verifier with current pack_id and attribution_required fields",
    "update verifier SQL and hash assertions to the current VehiclesDB provenance schema",
    "expose the pinned attribution text and source repository URL",
    "query model_id and current source_registry/model_market_evidence columns",
    "decode source JSON arrays, retain source IDs, and hash normalized candidate rows without mislabelling them as upstream record hashes",
    "derive snapshot timestamp from the pinned manifest instead of a stale hard-coded date",
    "test query-only protection using the current model_id primary key"
  ]
}, null, 2) + "\n");

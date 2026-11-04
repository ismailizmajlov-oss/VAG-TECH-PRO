"use strict";

const fs = require("node:fs");
const path = require("node:path");
const crypto = require("node:crypto");
const { DatabaseSync } = require("node:sqlite");

const ROOT = __dirname;
const PACK_ID = "wikidata-vag-model-taxonomy-cc0";
const ARTIFACT = {
  workflowRunId: 41875660206,
  artifactId: 13346487773,
  artifactSha256: "5b6ec0423ceaab6dcd7f2ba69cc968fc38c19cf868b9c5eb277a18ec85966b03",
  sourceCommit: "5d7069d180db626ea0d10ef7292900a12b4a82e1",
  sourceBranch: "research/wikidata-live-run67",
};

function fail(message) { throw new Error("[run68] " + message); }
function sha256(bytes) { return crypto.createHash("sha256").update(bytes).digest("hex"); }
function sha256File(file) { return sha256(fs.readFileSync(file)); }
function readText(file) {
  if (!fs.existsSync(file)) fail("Required file missing: " + path.relative(ROOT, file));
  return fs.readFileSync(file, "utf8").replace(/\r\n/g, "\n");
}
function readJson(file) {
  try { return JSON.parse(readText(file)); }
  catch (error) { fail("Invalid JSON " + path.relative(ROOT, file) + ": " + error.message); }
}
function writeText(file, value) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, value.replace(/\r\n/g, "\n"), "utf8");
}
function atomicWriteJson(file, value) {
  const dir = path.dirname(file);
  const temp = path.join(dir, ".manifest-staging-" + process.pid + "-" + crypto.randomBytes(6).toString("hex"));
  const backup = path.join(dir, ".manifest-backup-" + process.pid + "-" + crypto.randomBytes(6).toString("hex"));
  fs.writeFileSync(temp, JSON.stringify(value, null, 2) + "\n", { flag: "wx" });
  let movedOld = false;
  try {
    if (fs.existsSync(file)) { fs.renameSync(file, backup); movedOld = true; }
    fs.renameSync(temp, file);
    if (movedOld) fs.rmSync(backup, { force: true });
  } catch (error) {
    if (movedOld && !fs.existsSync(file) && fs.existsSync(backup)) fs.renameSync(backup, file);
    fs.rmSync(temp, { force: true });
    throw error;
  }
}
function safeJoin(root, relative) {
  if (typeof relative !== "string" || !relative || path.isAbsolute(relative) || relative.includes("\\")) fail("Unsafe relative path: " + String(relative));
  const base = path.resolve(root);
  const target = path.resolve(base, relative);
  const rel = path.relative(base, target);
  if (rel === ".." || rel.startsWith(".." + path.sep) || path.isAbsolute(rel)) fail("Path escaped root: " + relative);
  return target;
}
function replaceExactly(file, before, after, label) {
  let source = readText(file);
  if (source.includes(after)) return false;
  const count = source.split(before).length - 1;
  if (count !== 1) fail(label + ": expected exactly one anchor, found " + count);
  writeText(file, source.replace(before, after));
  return true;
}
function parseArgs(argv) {
  const result = {};
  for (let i = 2; i < argv.length; i += 1) {
    const key = argv[i];
    if (key !== "--pack-dir" && key !== "--research-dir") fail("Unknown argument: " + key);
    const value = argv[i + 1];
    if (!value || value.startsWith("--")) fail("Missing value for " + key);
    result[key] = value;
    i += 1;
  }
  if (!result["--pack-dir"] || !result["--research-dir"]) fail("Usage: node apply-wikidata-vag-taxonomy-run68.cjs --pack-dir <dir> --research-dir <dir>");
  return { packDir: path.resolve(result["--pack-dir"]), researchDir: path.resolve(result["--research-dir"]) };
}
function count(db, sql, ...params) { return Number(db.prepare(sql).get(...params).n); }
function openReadOnly(file) {
  const db = new DatabaseSync(file, { readOnly: true });
  db.exec("PRAGMA query_only=ON; PRAGMA trusted_schema=OFF;");
  const integrity = db.prepare("PRAGMA integrity_check").get().integrity_check;
  if (integrity !== "ok") fail("Wikidata SQLite integrity_check failed: " + integrity);
  const foreignKeys = db.prepare("PRAGMA foreign_key_check").all();
  if (foreignKeys.length) fail("Wikidata SQLite has " + foreignKeys.length + " foreign-key violations");
  return db;
}
function copyRegularFile(sourceRoot, relative, targetRoot) {
  const source = safeJoin(sourceRoot, relative);
  const stat = fs.lstatSync(source);
  if (!stat.isFile() || stat.isSymbolicLink()) fail("Source pack entry is not a regular file: " + relative);
  const target = safeJoin(targetRoot, relative);
  fs.mkdirSync(path.dirname(target), { recursive: true });
  if (fs.existsSync(target)) {
    if (!fs.lstatSync(target).isFile() || sha256File(target) !== sha256File(source)) fail("Refusing to overwrite a different existing pack file: " + relative);
  } else {
    fs.copyFileSync(source, target);
  }
  if (sha256File(target) !== sha256File(source)) fail("Copied pack file hash mismatch: " + relative);
  return sha256File(target);
}

function validatePack(packDir) {
  const manifest = readJson(safeJoin(packDir, "manifest.json"));
  if (manifest.schema_version !== 1 || manifest.pack_id !== "wikidata-vag-model-taxonomy-cc0-" + manifest.snapshot_id) fail("Unexpected Wikidata pack identity/schema");
  if (manifest.publisher !== "Wikidata / Wikimedia Foundation" ||
      manifest.source_id !== "wikidata-vag-model-taxonomy" ||
      manifest.source_repository !== "https://www.wikidata.org/" ||
      manifest.source_endpoint !== "https://query.wikidata.org/sparql") fail("Wikidata source identity mismatch");
  if (manifest.data_license !== "CC0-1.0" || manifest.license_url !== "https://creativecommons.org/publicdomain/zero/1.0/" ||
      manifest.rights_status !== "approved_by_published_license") fail("Wikidata CC0 rights declaration is incomplete");
  for (const field of ["commercial_use_allowed", "display_allowed", "offline_cache_allowed", "bulk_reuse_allowed", "redistribution_allowed"]) {
    if (manifest[field] !== true) fail("Wikidata reuse right is not explicitly allowed: " + field);
  }
  if (manifest.attribution_required !== false || manifest.attribution_recommended !== true || manifest.share_alike_required !== false) fail("Wikidata attribution/share-alike terms are inconsistent");
  for (const field of ["source_snapshot_sha256", "source_query_sha256", "logical_content_sha256", "database_sha256"]) {
    if (!/^[a-f0-9]{64}$/.test(manifest[field] || "")) fail("Invalid Wikidata hash field: " + field);
  }
  if (!manifest.scope || manifest.scope.market_scope !== "UNKNOWN" ||
      manifest.scope.applicability_precision !== "candidate_identity_only" ||
      manifest.scope.review_status !== "candidate" ||
      manifest.scope.exact_vehicle_fitment !== false ||
      manifest.scope.generation_verified !== false ||
      manifest.scope.engine_code_fitment !== false ||
      manifest.scope.transmission_code_fitment !== false ||
      manifest.scope.ecu_fitment !== false ||
      manifest.scope.dtc_fitment !== false ||
      manifest.scope.repair_procedure_fitment !== false ||
      manifest.scope.diagnostic_execution_allowed !== false ||
      manifest.scope.production_years_inferred !== false ||
      manifest.scope.generation_entities !== 0 ||
      manifest.completeness_status !== "unknown" ||
      manifest.scope.completeness_status !== "unknown" ||
      manifest.completeness_status !== "unknown") fail("Wikidata candidate-only applicability/completeness boundary failed");
  const expectedCounts = { model_entities: 376, source_bindings: 376, manufacturers: 5, russian_labels: 171, date_statements: 21 };
  for (const [key, expected] of Object.entries(expectedCounts)) {
    if (manifest.counts?.[key] !== expected) fail("Wikidata expected count mismatch for " + key);
  }
  if (!manifest.pack_files || typeof manifest.pack_files !== "object") fail("Wikidata per-file provenance map is missing");
  const requiredFiles = ["snapshot.json", "query.rq", "LICENSE-NOTICE.txt", "ATTRIBUTION.md", "wikidata-vag-taxonomy.sqlite"];
  for (const relative of requiredFiles) {
    const item = manifest.pack_files[relative];
    if (!item || !/^[a-f0-9]{64}$/.test(item.sha256 || "") || !Number.isInteger(item.byte_size) || item.byte_size < 1) fail("Wikidata per-file hash/size metadata missing for " + relative);
    const file = safeJoin(packDir, relative);
    const stat = fs.lstatSync(file);
    if (!stat.isFile() || stat.isSymbolicLink() || stat.size !== item.byte_size || sha256File(file) !== item.sha256) fail("Wikidata source file hash/size mismatch: " + relative);
  }
  if (sha256File(safeJoin(packDir, "snapshot.json")) !== manifest.source_snapshot_sha256) fail("Wikidata snapshot hash mismatch");
  if (sha256File(safeJoin(packDir, "query.rq")) !== manifest.source_query_sha256) fail("Wikidata query hash mismatch");
  if (sha256File(safeJoin(packDir, "wikidata-vag-taxonomy.sqlite")) !== manifest.database_sha256) fail("Wikidata SQLite hash mismatch");
  const license = readText(safeJoin(packDir, "LICENSE-NOTICE.txt"));
  const attribution = readText(safeJoin(packDir, "ATTRIBUTION.md"));
  if (!/CC0 1\.0 Universal/i.test(license) || !/creativecommons\.org\/publicdomain\/zero\/1\.0/i.test(license)) fail("Wikidata structured-data CC0 notice is missing");
  if (!/Wikidata structured data/i.test(attribution) || !/CC0 1\.0 Universal/i.test(attribution) ||
      !/not an authoritative Volkswagen Group model register/i.test(attribution)) fail("Wikidata attribution/scope notice is incomplete");

  const db = openReadOnly(safeJoin(packDir, "wikidata-vag-taxonomy.sqlite"));
  let counts;
  try {
    const tables = db.prepare("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name").all().map((row) => row.name);
    if (JSON.stringify(tables) !== JSON.stringify(["model_date_statements", "source_bindings", "source_registry", "vehicle_model_entities"])) fail("Unexpected Wikidata SQLite table set: " + JSON.stringify(tables));
    const source = db.prepare("SELECT * FROM source_registry WHERE source_id=?").get(manifest.source_id);
    if (!source || source.publisher !== manifest.publisher || source.source_url !== manifest.source_repository ||
        source.endpoint_url !== manifest.source_endpoint || source.license_id !== "CC0-1.0" ||
        source.license_url !== manifest.license_url || source.rights_status !== "approved_by_published_license" ||
        source.commercial_use_allowed !== 1 || source.display_allowed !== 1 || source.offline_cache_allowed !== 1 ||
        source.bulk_reuse_allowed !== 1 || source.redistribution_allowed !== 1 ||
        source.attribution_required !== 0 || source.attribution_recommended !== 1 || source.share_alike_required !== 0 ||
        source.source_revision !== manifest.source_revision ||
        source.source_snapshot_sha256 !== manifest.source_snapshot_sha256 ||
        source.source_query_sha256 !== manifest.source_query_sha256 ||
        source.market_scope !== "UNKNOWN" || source.applicability_precision !== "candidate_identity_only" ||
        source.review_status !== "candidate") fail("Wikidata SQLite source registry failed its CC0/provenance gate");

    counts = {
      models: count(db, "SELECT count(*) AS n FROM vehicle_model_entities"),
      sourceBindings: count(db, "SELECT count(*) AS n FROM source_bindings"),
      manufacturers: count(db, "SELECT count(DISTINCT manufacturer_qid) AS n FROM vehicle_model_entities"),
      russianLabels: count(db, "SELECT count(*) AS n FROM vehicle_model_entities WHERE model_label_ru IS NOT NULL AND trim(model_label_ru)!=''"),
      dateStatements: count(db, "SELECT count(*) AS n FROM model_date_statements"),
      invalidRows: count(db, "SELECT count(*) AS n FROM vehicle_model_entities WHERE market_scope!='UNKNOWN' OR applicability_precision!='candidate_identity_only' OR review_status!='candidate' OR exact_vehicle_fitment!=0 OR generation_verified!=0 OR engine_code_fitment!=0 OR transmission_code_fitment!=0 OR ecu_fitment!=0 OR dtc_fitment!=0 OR repair_procedure_fitment!=0"),
      invalidBindings: count(db, "SELECT count(*) AS n FROM source_bindings WHERE length(source_binding_sha256)!=64 OR source_revision!=? OR source_snapshot_sha256!=? OR source_query_sha256!=?", manifest.source_revision, manifest.source_snapshot_sha256, manifest.source_query_sha256),
      invalidDates: count(db, "SELECT count(*) AS n FROM model_date_statements WHERE property_id NOT IN ('P571','P576')"),
      badEntityBindingCounts: count(db, "SELECT count(*) AS n FROM vehicle_model_entities v WHERE v.source_binding_count != (SELECT count(*) FROM source_bindings b WHERE b.model_qid=v.model_qid AND b.manufacturer_qid=v.manufacturer_qid)"),
    };
    if (counts.models !== expectedCounts.model_entities || counts.sourceBindings !== expectedCounts.source_bindings ||
        counts.manufacturers !== expectedCounts.manufacturers || counts.russianLabels !== expectedCounts.russian_labels ||
        counts.dateStatements !== expectedCounts.date_statements || counts.invalidRows || counts.invalidBindings ||
        counts.invalidDates || counts.badEntityBindingCounts) fail("Wikidata SQLite row-count/provenance/candidate-only gate failed: " + JSON.stringify(counts));
    const orphanBindings = count(db, "SELECT count(*) AS n FROM source_bindings b LEFT JOIN vehicle_model_entities v ON v.model_qid=b.model_qid AND v.manufacturer_qid=b.manufacturer_qid WHERE v.model_qid IS NULL");
    if (orphanBindings) fail("Wikidata SQLite has orphan source bindings");
  } finally {
    db.close();
  }
  return { manifest, counts, sourceManifestSha256: sha256File(safeJoin(packDir, "manifest.json")) };
}

function updateResearchManifest(researchDir, verified) {
  const manifestPath = safeJoin(researchDir, "manifest.json");
  const rootManifest = readJson(manifestPath);
  if (rootManifest.schema_version !== 1 || !Array.isArray(rootManifest.packs)) fail("Desktop research manifest schema mismatch");
  const base = PACK_ID;
  const sourceManifestRelative = base + "/manifest.json";
  const licenseRelative = base + "/LICENSE-NOTICE.txt";
  const attributionRelative = base + "/ATTRIBUTION.md";
  const queryRelative = base + "/query.rq";
  const snapshotRelative = base + "/snapshot.json";
  const databaseRelative = base + "/wikidata-vag-taxonomy.sqlite";
  const reportRelative = base + "/integration-verification.json";
  const sourceManifestSha = sha256File(safeJoin(researchDir, sourceManifestRelative));
  const licenseSha = sha256File(safeJoin(researchDir, licenseRelative));
  const attributionSha = sha256File(safeJoin(researchDir, attributionRelative));
  const querySha = sha256File(safeJoin(researchDir, queryRelative));
  const snapshotSha = sha256File(safeJoin(researchDir, snapshotRelative));
  const databaseSha = sha256File(safeJoin(researchDir, databaseRelative));
  if (sourceManifestSha !== verified.sourceManifestSha256 ||
      databaseSha !== verified.manifest.database_sha256 ||
      snapshotSha !== verified.manifest.source_snapshot_sha256 ||
      querySha !== verified.manifest.source_query_sha256) fail("Copied Wikidata pack failed final source hash verification");

  const report = {
    schema_version: 1,
    status: "verified_candidate_identity_only",
    pack_id: PACK_ID,
    source_revision: verified.manifest.source_revision,
    source_snapshot_sha256: verified.manifest.source_snapshot_sha256,
    source_query_sha256: verified.manifest.source_query_sha256,
    source_manifest_sha256: sourceManifestSha,
    database_sha256: databaseSha,
    artifact_sha256: ARTIFACT.artifactSha256,
    workflow_run_id: ARTIFACT.workflowRunId,
    artifact_id: ARTIFACT.artifactId,
    source_commit: ARTIFACT.sourceCommit,
    counts: {
      models: verified.counts.models,
      sourceBindings: verified.counts.sourceBindings,
      manufacturers: verified.counts.manufacturers,
      russianLabels: verified.counts.russianLabels,
      dateStatements: verified.counts.dateStatements,
    },
    candidate_only: true,
    exact_vehicle_fitment: false,
    generation_verified: false,
    engine_code_fitment: false,
    transmission_code_fitment: false,
    ecu_fitment: false,
    dtc_fitment: false,
    repair_procedure_fitment: false,
    diagnostic_execution_allowed: false,
    production_years_inferred: false,
  };
  writeText(safeJoin(researchDir, reportRelative), JSON.stringify(report, null, 2) + "\n");
  const reportSha = sha256File(safeJoin(researchDir, reportRelative));
  const entry = {
    id: PACK_ID,
    kind: "vehicle_model_identity_candidates",
    database: databaseRelative,
    database_sha256: databaseSha,
    license_file: licenseRelative,
    license_file_sha256: licenseSha,
    license: "CC0-1.0",
    license_status: "approved_by_published_license",
    source_manifest_file: sourceManifestRelative,
    source_manifest_sha256: sourceManifestSha,
    attribution_file: attributionRelative,
    attribution_sha256: attributionSha,
    query_file: queryRelative,
    query_sha256: querySha,
    snapshot_file: snapshotRelative,
    snapshot_sha256: snapshotSha,
    integration_report_file: reportRelative,
    integration_report_sha256: reportSha,
    publisher: verified.manifest.publisher,
    dataset: "Wikidata VAG model identity candidate snapshot",
    source_url: verified.manifest.source_repository,
    source_endpoint: verified.manifest.source_endpoint,
    upstream_revision: verified.manifest.source_revision,
    snapshot_generated_at_utc: verified.manifest.built_at_utc,
    source_snapshot_sha256: verified.manifest.source_snapshot_sha256,
    source_query_sha256: verified.manifest.source_query_sha256,
    logical_content_sha256: verified.manifest.logical_content_sha256,
    counts: {
      models: verified.counts.models,
      source_bindings: verified.counts.sourceBindings,
      manufacturers: verified.counts.manufacturers,
      russian_labels: verified.counts.russianLabels,
      date_statements: verified.counts.dateStatements,
    },
    market_scope: "UNKNOWN",
    applicability_precision: "candidate_identity_only",
    review_status: "candidate",
    fitment_claim: false,
    execution_allowed: false,
    generation_verified: false,
    generation_entities: 0,
    engine_code_fitment: false,
    transmission_code_fitment: false,
    ecu_fitment: false,
    dtc_fitment: false,
    repair_procedure_fitment: false,
    diagnostic_execution_allowed: false,
    production_years_inferred: false,
    attribution_required: false,
    attribution_recommended: true,
    share_alike_required: false,
    commercial_use_allowed: true,
    display_allowed: true,
    cache_allowed: true,
    offline_cache_allowed: true,
    bulk_reuse_allowed: true,
    redistribution_allowed: true,
    rights_status: "approved_by_published_license",
    manufacturer_whitelist: verified.manifest.manufacturer_whitelist,
    scope: verified.manifest.scope,
    limitations: verified.manifest.exclusions,
    source_workflow: {
      repository: "ismailizmajlov-oss/VAG-TECH-PRO",
      branch: ARTIFACT.sourceBranch,
      commit: ARTIFACT.sourceCommit,
      run_id: ARTIFACT.workflowRunId,
      artifact_id: ARTIFACT.artifactId,
      artifact_sha256: ARTIFACT.artifactSha256,
    },
  };
  const existing = rootManifest.packs.find((pack) => pack.id === PACK_ID);
  if (existing) {
    if (existing.database_sha256 !== databaseSha || existing.source_snapshot_sha256 !== verified.manifest.source_snapshot_sha256) fail("A different Wikidata snapshot is already registered; refusing to overwrite it");
    Object.assign(existing, entry);
  } else {
    rootManifest.packs.push(entry);
  }
  if (rootManifest.packs.length !== 6) fail("Expected six separately licensed desktop research packs; found " + rootManifest.packs.length);
  rootManifest.integration_revision = "run68";
  rootManifest.integrated_artifacts = Array.isArray(rootManifest.integrated_artifacts) ? rootManifest.integrated_artifacts : [];
  rootManifest.integrated_artifacts = rootManifest.integrated_artifacts.filter((item) => item.pack_id !== PACK_ID);
  rootManifest.integrated_artifacts.push({
    pack_id: PACK_ID,
    artifact_zip_sha256: ARTIFACT.artifactSha256,
    source_snapshot_sha256: verified.manifest.source_snapshot_sha256,
    source_query_sha256: verified.manifest.source_query_sha256,
    database_sha256: databaseSha,
    source_revision: verified.manifest.source_revision,
    workflow_run_id: ARTIFACT.workflowRunId,
    artifact_id: ARTIFACT.artifactId,
    source_commit: ARTIFACT.sourceCommit,
  });
  atomicWriteJson(manifestPath, rootManifest);
  return entry;
}

function patchDesktopSource(desktopRoot) {
  const dbFile = path.join(desktopRoot, "lib", "local-research-db.cjs");
  const typesFile = path.join(desktopRoot, "lib", "local-research-db.d.cts");
  const routeFile = path.join(desktopRoot, "app", "api", "local-research", "route.ts");
  const uiFile = path.join(desktopRoot, "components", "local-research-catalog.tsx");
  const dbTestFile = path.join(desktopRoot, "tests", "local-research-db.test.cjs");
  const packTestFile = path.join(desktopRoot, "tests", "local-research-packs.test.cjs");
  const uiTestFile = path.join(desktopRoot, "tests", "local-research-ui-contract.test.cjs");
  const verifierFile = path.join(desktopRoot, "scripts", "verify-local-research-packs.cjs");
  const readmeFile = path.join(desktopRoot, "data", "research", "README.md");
  const docsFile = path.join(desktopRoot, "docs", "RESEARCH_DATA_PACKS.md");
  for (const file of [dbFile, typesFile, routeFile, uiFile, dbTestFile, packTestFile, uiTestFile, verifierFile, readmeFile, docsFile]) {
    if (!fs.existsSync(file)) fail("Required desktop integration file is missing: " + path.relative(desktopRoot, file));
  }

  let source = readText(dbFile);
  const descriptor = [
    '  wikidata: Object.freeze({',
    '    id: "wikidata-vag-model-taxonomy-cc0",',
    '    file: "wikidata-vag-model-taxonomy-cc0/wikidata-vag-taxonomy.sqlite",',
    '    manifest: "wikidata-vag-model-taxonomy-cc0/manifest.json",',
    '    attribution: "wikidata-vag-model-taxonomy-cc0/ATTRIBUTION.md",',
    '    licenseFile: "wikidata-vag-model-taxonomy-cc0/LICENSE-NOTICE.txt",',
    '    verificationFile: "wikidata-vag-model-taxonomy-cc0/integration-verification.json",',
    '    license: "CC0-1.0",',
    '    source: "Wikidata structured data",',
    '    sourceUrl: "https://www.wikidata.org/",',
    '    scope: "VAG-group model identity candidates; market UNKNOWN; no generation or exact vehicle fitment",',
    '  }),',
    ''
  ].join("\n");
  if (!source.includes('id: "wikidata-vag-model-taxonomy-cc0"')) {
    const anchor = "\n});\n\nfunction getResearchRoot";
    if (source.split(anchor).length - 1 !== 1) fail("Wikidata PACKS insertion anchor is missing or ambiguous");
    source = source.replace(anchor, "\n" + descriptor + anchor);
  }
  function replaceSource(before, after, label) {
    if (source.includes(after)) return;
    const count = source.split(before).length - 1;
    if (count !== 1) fail(label + ": expected exactly one anchor, found " + count);
    source = source.replace(before, after);
  }
  replaceSource(
    '  const mechanicDbManifest = manifest.packs.find((pack) => pack.id === PACKS.mechanicdb.id);',
    '  const mechanicDbManifest = manifest.packs.find((pack) => pack.id === PACKS.mechanicdb.id);\n  const wikidataManifest = manifest.packs.find((pack) => pack.id === PACKS.wikidata.id);',
    "Wikidata root manifest lookup"
  );
  replaceSource(
    'if (!obManifest || !vagManifest || !udsManifest || !vehiclesDbManifest || !mechanicDbManifest) throw new Error("A required local research pack is missing from the manifest");',
    'if (!obManifest || !vagManifest || !udsManifest || !vehiclesDbManifest || !mechanicDbManifest || !wikidataManifest) throw new Error("A required local research pack is missing from the manifest");',
    "Wikidata required-pack gate"
  );
  replaceSource(
    '  verifyPackDatabaseHash(root, PACKS.mechanicdb.id, PACKS.mechanicdb.file);',
    '  verifyPackDatabaseHash(root, PACKS.mechanicdb.id, PACKS.mechanicdb.file);\n  verifyPackDatabaseHash(root, PACKS.wikidata.id, PACKS.wikidata.file);',
    "Wikidata database hash verification"
  );
  replaceSource(
    '    [PACKS.mechanicdb.id, [["license_file", "license_file_sha256"], ["upstream_license_file", "upstream_license_file_sha256"], ["source_manifest_file", "source_manifest_sha256"], ["attribution_file", "attribution_sha256"], ["source_file", "source_file_sha256"], ["sources_file", "sources_file_sha256"], ["data_dictionary_file", "data_dictionary_sha256"], ["sha256sums_file", "sha256sums_sha256"]]],',
    '    [PACKS.mechanicdb.id, [["license_file", "license_file_sha256"], ["upstream_license_file", "upstream_license_file_sha256"], ["source_manifest_file", "source_manifest_sha256"], ["attribution_file", "attribution_sha256"], ["source_file", "source_file_sha256"], ["sources_file", "sources_file_sha256"], ["data_dictionary_file", "data_dictionary_sha256"], ["sha256sums_file", "sha256sums_sha256"]]],\n    [PACKS.wikidata.id, [["license_file", "license_file_sha256"], ["source_manifest_file", "source_manifest_sha256"], ["attribution_file", "attribution_sha256"], ["query_file", "query_sha256"], ["snapshot_file", "snapshot_sha256"], ["integration_report_file", "integration_report_sha256"]]],',
    "Wikidata provenance hash verification"
  );
  replaceSource(
    '  const mechanicDb = openReadOnly(root, PACKS.mechanicdb.file);',
    '  const mechanicDb = openReadOnly(root, PACKS.mechanicdb.file);\n  const wikidataDb = openReadOnly(root, PACKS.wikidata.file);',
    "Wikidata SQLite open"
  );

  const summaryStart = source.indexOf("function getResearchSummary(root) {");
  const summaryEnd = source.indexOf("\nfunction searchGenericDtcs(", summaryStart);
  if (summaryStart < 0 || summaryEnd < 0) fail("Wikidata summary function boundaries are missing");
  if (!source.slice(summaryStart, summaryEnd).includes("const wikidataCounts")) {
    const anchor = "\n    return {\n      mode: \"offline_read_only\",";
    const index = source.indexOf(anchor, summaryStart);
    if (index < 0 || index > summaryEnd) fail("Wikidata summary validation insertion anchor is missing");
    const validation = [
      '',
      '    const wikidataPackManifest = JSON.parse(fs.readFileSync(path.join(getResearchRoot(root), PACKS.wikidata.manifest), "utf8"));',
      '    const wikidataAttribution = fs.readFileSync(path.join(getResearchRoot(root), PACKS.wikidata.attribution), "utf8");',
      '    const wikidataLicense = fs.readFileSync(path.join(getResearchRoot(root), PACKS.wikidata.licenseFile), "utf8");',
      '    const wikidataSource = wikidataDb.prepare("SELECT * FROM source_registry WHERE source_id=?").get(wikidataPackManifest.source_id);',
      '    const wikidataCounts = {',
      '      models: wikidataDb.prepare("SELECT count(*) AS n FROM vehicle_model_entities").get().n,',
      '      sourceBindings: wikidataDb.prepare("SELECT count(*) AS n FROM source_bindings").get().n,',
      '      manufacturers: wikidataDb.prepare("SELECT count(DISTINCT manufacturer_qid) AS n FROM vehicle_model_entities").get().n,',
      '      russianLabels: wikidataDb.prepare("SELECT count(*) AS n FROM vehicle_model_entities WHERE model_label_ru IS NOT NULL AND trim(model_label_ru)!=\'\'").get().n,',
      '      dateStatements: wikidataDb.prepare("SELECT count(*) AS n FROM model_date_statements").get().n,',
      '      invalidRows: wikidataDb.prepare("SELECT count(*) AS n FROM vehicle_model_entities WHERE market_scope!=\'UNKNOWN\' OR applicability_precision!=\'candidate_identity_only\' OR review_status!=\'candidate\' OR exact_vehicle_fitment!=0 OR generation_verified!=0 OR engine_code_fitment!=0 OR transmission_code_fitment!=0 OR ecu_fitment!=0 OR dtc_fitment!=0 OR repair_procedure_fitment!=0").get().n,',
      '      invalidBindings: wikidataDb.prepare("SELECT count(*) AS n FROM source_bindings WHERE length(source_binding_sha256)!=64 OR source_revision!=? OR source_snapshot_sha256!=? OR source_query_sha256!=?").get(wikidataPackManifest.source_revision, wikidataPackManifest.source_snapshot_sha256, wikidataPackManifest.source_query_sha256).n,',
      '      invalidDates: wikidataDb.prepare("SELECT count(*) AS n FROM model_date_statements WHERE property_id NOT IN (\'P571\',\'P576\')").get().n,',
      '      badEntityBindingCounts: wikidataDb.prepare("SELECT count(*) AS n FROM vehicle_model_entities v WHERE v.source_binding_count != (SELECT count(*) FROM source_bindings b WHERE b.model_qid=v.model_qid AND b.manufacturer_qid=v.manufacturer_qid)").get().n,',
      '    };',
      '    if (!wikidataSource || wikidataSource.source_url !== "https://www.wikidata.org/" || wikidataSource.endpoint_url !== "https://query.wikidata.org/sparql" ||',
      '        wikidataSource.license_id !== "CC0-1.0" || wikidataSource.rights_status !== "approved_by_published_license" ||',
      '        wikidataSource.commercial_use_allowed !== 1 || wikidataSource.display_allowed !== 1 || wikidataSource.offline_cache_allowed !== 1 ||',
      '        wikidataSource.bulk_reuse_allowed !== 1 || wikidataSource.redistribution_allowed !== 1 || wikidataSource.attribution_required !== 0 ||',
      '        wikidataSource.attribution_recommended !== 1 || wikidataSource.share_alike_required !== 0 || wikidataSource.market_scope !== "UNKNOWN" ||',
      '        wikidataSource.applicability_precision !== "candidate_identity_only" || wikidataSource.review_status !== "candidate" ||',
      '        wikidataSource.source_revision !== wikidataPackManifest.source_revision ||',
      '        wikidataSource.source_snapshot_sha256 !== wikidataPackManifest.source_snapshot_sha256 || wikidataSource.source_query_sha256 !== wikidataPackManifest.source_query_sha256 ||',
      '        wikidataPackManifest.source_repository !== "https://www.wikidata.org/" || wikidataPackManifest.data_license !== "CC0-1.0" ||',
      '        wikidataPackManifest.rights_status !== "approved_by_published_license" || wikidataPackManifest.commercial_use_allowed !== true ||',
      '        wikidataPackManifest.display_allowed !== true || wikidataPackManifest.offline_cache_allowed !== true || wikidataPackManifest.bulk_reuse_allowed !== true ||',
      '        wikidataPackManifest.redistribution_allowed !== true || wikidataPackManifest.attribution_required !== false ||',
      '        wikidataPackManifest.attribution_recommended !== true || wikidataPackManifest.share_alike_required !== false ||',
      '        wikidataPackManifest.scope?.market_scope !== "UNKNOWN" || wikidataPackManifest.scope?.applicability_precision !== "candidate_identity_only" ||',
      '        wikidataPackManifest.scope?.review_status !== "candidate" || wikidataPackManifest.scope?.exact_vehicle_fitment !== false ||',
      '        wikidataPackManifest.scope?.generation_verified !== false || wikidataPackManifest.scope?.engine_code_fitment !== false ||',
      '        wikidataPackManifest.scope?.transmission_code_fitment !== false || wikidataPackManifest.scope?.ecu_fitment !== false ||',
      '        wikidataPackManifest.scope?.dtc_fitment !== false || wikidataPackManifest.scope?.repair_procedure_fitment !== false ||',
      '        wikidataPackManifest.scope?.diagnostic_execution_allowed !== false || wikidataPackManifest.scope?.production_years_inferred !== false || wikidataPackManifest.scope?.generation_entities !== 0 || wikidataPackManifest.completeness_status !== "unknown" ||',
      '        wikidataCounts.models !== 376 || wikidataCounts.sourceBindings !== 376 || wikidataCounts.manufacturers !== 5 ||',
      '        wikidataCounts.russianLabels !== 171 || wikidataCounts.dateStatements !== 21 || wikidataCounts.invalidRows ||',
      '        wikidataCounts.invalidBindings || wikidataCounts.invalidDates || wikidataCounts.badEntityBindingCounts || !/Wikidata structured data/i.test(wikidataAttribution) ||',
      '        !/CC0 1\\.0 Universal/i.test(wikidataLicense)) throw new Error("Wikidata model identity pack failed its CC0 provenance, rights or candidate-only gate");',
      ''
    ].join("\n");
    source = source.slice(0, index) + "\n" + validation.join("\n") + source.slice(index);
  }

  const summaryObject = [
    '        {',
    '          id: PACKS.wikidata.id,',
    '          kind: "vehicle_model_identity_candidates",',
    '          license: PACKS.wikidata.license,',
    '          source: PACKS.wikidata.source,',
    '          sourceUrl: PACKS.wikidata.sourceUrl,',
    '          scope: PACKS.wikidata.scope,',
    '          status: "identity_candidate",',
    '          marketScope: "UNKNOWN",',
    '          applicabilityPrecision: "candidate_identity_only",',
    '          fitmentClaim: false,',
    '          executionAllowed: false,',
    '          attributionRequired: false,',
    '          attributionRecommended: true,',
    '          counts: { models: wikidataCounts.models, sourceBindings: wikidataCounts.sourceBindings, manufacturers: wikidataCounts.manufacturers, russianLabels: wikidataCounts.russianLabels, dateStatements: wikidataCounts.dateStatements },',
    '          upstreamRevision: wikidataPackManifest.source_revision,',
    '          snapshotGeneratedAt: wikidataPackManifest.built_at_utc,',
    '          sourceManifestSha256: wikidataManifest.source_manifest_sha256,',
    '          sourceSnapshotSha256: wikidataPackManifest.source_snapshot_sha256,',
    '          sourceQuerySha256: wikidataPackManifest.source_query_sha256,',
    '          databaseSha256: wikidataManifest.database_sha256,',
    '          note: "Structured model/manufacturer identity candidates only. Russian-language labels are not Russian-market evidence. Date statements are not production-year ranges. No generation, engine, gearbox, ECU, DTC or repair applicability.",',
    '        },'
  ].join("\n");
  if (!source.slice(summaryStart, summaryEnd).includes("id: PACKS.wikidata.id")) {
    const currentSummaryEnd = source.indexOf("\nfunction searchGenericDtcs(", summaryStart);
    const arrayEnd = source.lastIndexOf("\n      ],\n    };", currentSummaryEnd);
    if (arrayEnd < 0 || arrayEnd < summaryStart) fail("Wikidata summary pack-array insertion point is missing");
    source = source.slice(0, arrayEnd) + "\n" + summaryObject + source.slice(arrayEnd);
  }
  replaceSource(
    '    mechanicDb.close();',
    '    mechanicDb.close();\n    wikidataDb.close();',
    "Wikidata SQLite close"
  );

  if (!source.includes("function searchWikidataCandidates(")) {
    const searchFunction = [
      "function searchWikidataCandidates(query, limit = 25, root) {",
      "  const q = validateQuery(query);",
      "  const pack = verifyPackDatabaseHash(root, PACKS.wikidata.id, PACKS.wikidata.file);",
      "  for (const [fileField, hashField] of [[\"license_file\", \"license_file_sha256\"], [\"source_manifest_file\", \"source_manifest_sha256\"], [\"attribution_file\", \"attribution_sha256\"], [\"query_file\", \"query_sha256\"], [\"snapshot_file\", \"snapshot_sha256\"], [\"integration_report_file\", \"integration_report_sha256\"]]) verifyPackFileHash(root, PACKS.wikidata.id, fileField, hashField);",
      "  const researchRoot = getResearchRoot(root);",
      "  const packManifest = JSON.parse(fs.readFileSync(path.join(researchRoot, PACKS.wikidata.manifest), \"utf8\"));",
      "  const report = JSON.parse(fs.readFileSync(path.join(researchRoot, PACKS.wikidata.verificationFile), \"utf8\"));",
      "  if (pack.license !== \"CC0-1.0\" || pack.market_scope !== \"UNKNOWN\" || pack.applicability_precision !== \"candidate_identity_only\" || pack.review_status !== \"candidate\" ||",
      "      report.status !== \"verified_candidate_identity_only\" || report.candidate_only !== true || report.exact_vehicle_fitment !== false ||",
      "      report.generation_verified !== false || report.engine_code_fitment !== false || report.transmission_code_fitment !== false ||",
      "      report.ecu_fitment !== false || report.dtc_fitment !== false || report.repair_procedure_fitment !== false ||",
      "      report.diagnostic_execution_allowed !== false || report.production_years_inferred !== false ||",
      "      packManifest.data_license !== \"CC0-1.0\" || packManifest.scope?.market_scope !== \"UNKNOWN\" ||",
      "      packManifest.scope?.applicability_precision !== \"candidate_identity_only\" || packManifest.scope?.exact_vehicle_fitment !== false || packManifest.scope?.generation_verified !== false || packManifest.scope?.engine_code_fitment !== false || packManifest.scope?.transmission_code_fitment !== false || packManifest.scope?.ecu_fitment !== false || packManifest.scope?.dtc_fitment !== false || packManifest.scope?.repair_procedure_fitment !== false || packManifest.scope?.diagnostic_execution_allowed !== false || packManifest.scope?.production_years_inferred !== false) {",
      "    throw new Error(\"Wikidata search failed its candidate-only runtime gate\");",
      "  }",
      "  const db = openReadOnly(root, PACKS.wikidata.file);",
      "  try {",
      "    const source = db.prepare(\"SELECT * FROM source_registry WHERE source_id=?\").get(packManifest.source_id);",
      "    if (!source || source.license_id !== \"CC0-1.0\" || source.market_scope !== \"UNKNOWN\" || source.applicability_precision !== \"candidate_identity_only\" || source.review_status !== \"candidate\" || source.commercial_use_allowed !== 1 || source.display_allowed !== 1 || source.offline_cache_allowed !== 1 || source.bulk_reuse_allowed !== 1 || source.redistribution_allowed !== 1 || source.attribution_required !== 0 || source.share_alike_required !== 0) throw new Error(\"Wikidata SQLite source registry rights gate failed\");",
      "    const pattern = \"%\" + q.replace(/[!%_]/g, \"!$&\") + \"%\";",
      "    const rows = db.prepare(",
      "      \"SELECT model_qid, manufacturer_qid, model_label_en, model_label_ru, manufacturer_label_en, inception_dates_json, dissolution_dates_json, modified_dates_json, source_record_sha256, source_revision, source_snapshot_sha256, source_query_sha256, source_binding_count \" +",
      "      \"FROM vehicle_model_entities WHERE market_scope='UNKNOWN' AND applicability_precision='candidate_identity_only' AND review_status='candidate' \" +",
      "      \"AND exact_vehicle_fitment=0 AND generation_verified=0 AND engine_code_fitment=0 AND transmission_code_fitment=0 AND ecu_fitment=0 AND dtc_fitment=0 AND repair_procedure_fitment=0 \" +",
      "      \"AND (model_label_en LIKE ? ESCAPE '!' OR model_label_ru LIKE ? ESCAPE '!' OR manufacturer_label_en LIKE ? ESCAPE '!') ORDER BY manufacturer_label_en, model_label_en LIMIT ?\"",
      "    ).all(pattern, pattern, pattern, clampLimit(limit));",
      "    const parseDates = (value) => { try { const parsed = JSON.parse(value || \"[]\"); return Array.isArray(parsed) ? parsed : []; } catch { return []; } };",
      "    return rows.map((row) => ({",
      "      modelQid: row.model_qid, manufacturerQid: row.manufacturer_qid,",
      "      manufacturer: row.manufacturer_label_en, model: row.model_label_en, modelRu: row.model_label_ru || null,",
      "      modelUrl: \"https://www.wikidata.org/wiki/\" + encodeURIComponent(row.model_qid),",
      "      inceptionDateStatements: parseDates(row.inception_dates_json), dissolutionDateStatements: parseDates(row.dissolution_dates_json), modifiedDateStatements: parseDates(row.modified_dates_json),",
      "      sourceBindingCount: row.source_binding_count, sourceRevision: row.source_revision, sourceUrl: safeHttpsUrl(PACKS.wikidata.sourceUrl),",
      "      sourceLicense: PACKS.wikidata.license, attributionRequired: false, attributionRecommended: true,",
      "      sourceRecordSha256: row.source_record_sha256, sourceSnapshotSha256: row.source_snapshot_sha256, sourceQuerySha256: row.source_query_sha256,",
      "      sourceManifestSha256: pack.source_manifest_sha256, databaseSha256: pack.database_sha256,",
      "      marketScope: \"UNKNOWN\", applicabilityPrecision: \"candidate_identity_only\", reviewStatus: \"candidate\",",
      "      exactFitment: false, generationVerified: false, engineCode: null, gearboxCode: null,",
      "      ecuFitment: false, dtcFitment: false, repairProcedureFitment: false,",
      "      warning: \"Wikidata structured identity candidate only. A Russian-language label does not establish Russian/EAEU market applicability. Date statements are not model-year ranges. Generation, year, engine code, gearbox code, ECU, DTC and exact vehicle fitment are not confirmed.\",",
      "    }));",
      "  } finally { db.close(); }",
      "}",
      ""
    ].join("\n");
    const searchAnchor = "\nfunction searchVehiclesDbCandidates(";
    if (source.split(searchAnchor).length - 1 !== 1) fail("Wikidata search-function insertion anchor is missing or ambiguous");
    source = source.replace(searchAnchor, "\n" + searchFunction + searchAnchor);
  }
  if (!source.includes("  searchWikidataCandidates,")) {
    const exportAnchor = "  validateQuery,";
    if (source.split(exportAnchor).length - 1 !== 1) fail("Wikidata search export anchor is missing or ambiguous");
    source = source.replace(exportAnchor, "  searchWikidataCandidates,\n  validateQuery,");
  }
  writeText(dbFile, source);

  let types = readText(typesFile);
  if (!types.includes("export function searchWikidataCandidates(")) {
    const anchor = "export function searchUdsSignals(query: string, limit?: number, root?: string): Array<Record<string, unknown>>;\n";
    replaceExactly(typesFile, anchor, anchor + "export function searchWikidataCandidates(query: string, limit?: number, root?: string): Array<Record<string, unknown>>;\n", "Wikidata TypeScript declaration");
    types = readText(typesFile);
  }
  if (!types.includes("attributionRecommended?: boolean;")) {
    replaceExactly(typesFile, "    attributionRequired?: boolean;\n", "    attributionRequired?: boolean;\n    attributionRecommended?: boolean;\n    sourceSnapshotSha256?: string;\n    sourceQuerySha256?: string;\n", "Wikidata summary type fields");
  }

  let route = readText(routeFile);
  if (!route.includes('dataset === "wikidata"')) {
    const anchor = '    else if (dataset === "vehiclesdb") rows = localResearch.searchVehiclesDbCandidates(query, limit);\n';
    replaceExactly(routeFile, anchor, anchor + '    else if (dataset === "wikidata") rows = localResearch.searchWikidataCandidates(query, limit);\n', "Wikidata API route");
    route = readText(routeFile);
  }

  let ui = readText(uiFile);
  const datasetMatch = ui.match(/type Dataset = ([^;]+);/);
  if (!datasetMatch) fail("Local research Dataset type is missing");
  if (!datasetMatch[1].split("|").some((part) => part.trim() === '"wikidata"')) ui = ui.replace(datasetMatch[0], "type Dataset = " + datasetMatch[1] + ' | "wikidata";');
  if (!ui.includes("attributionRecommended?: boolean;")) ui = ui.replace("attributionRequired?: boolean;", "attributionRequired?: boolean; attributionRecommended?: boolean; sourceSnapshotSha256?: string; sourceQuerySha256?: string;");
  if (!ui.includes('id: "wikidata"')) {
    const anchor = '  { id: "vehiclesdb", label: "Модели · рыночные данные", hint: "VehiclesDB · зарубежные рынки only" },\n';
    if (ui.split(anchor).length - 1 !== 1) fail("Wikidata research tab insertion anchor is missing");
    ui = ui.replace(anchor, anchor + '  { id: "wikidata", label: "Wikidata · модели VAG", hint: "CC0 · кандидаты идентичности · рынок UNKNOWN" },\n');
  }
  if (!ui.includes('const wikidata = summary.find((pack) => pack.id === "wikidata-vag-model-taxonomy-cc0");')) {
    const anchor = '  const mechanicDb = summary.find((pack) => pack.id === "mechanicdb-vag-dtc-candidates-odbl");\n';
    if (ui.split(anchor).length - 1 !== 1) fail("Wikidata UI summary lookup anchor is missing");
    ui = ui.replace(anchor, anchor + '  const wikidata = summary.find((pack) => pack.id === "wikidata-vag-model-taxonomy-cc0");\n');
  }
  if (!ui.includes("Модели Wikidata")) {
    const anchor = '      <article className="research-stat"><small>Модели VehiclesDB</small><strong>{formatNumber(vehiclesDb?.counts?.models)}</strong><span>{formatNumber(vehiclesDb?.counts?.marketEvidence)} зарубежных свидетельств · RU отсутствует</span></article>\n';
    if (ui.split(anchor).length - 1 !== 1) fail("Wikidata UI statistics insertion anchor is missing");
    ui = ui.replace(anchor, anchor + '      <article className="research-stat"><small>Модели Wikidata</small><strong>{formatNumber(wikidata?.counts?.models)}</strong><span>{formatNumber(wikidata?.counts?.russianLabels)} русских названий · CC0 · рынок UNKNOWN</span></article>\n');
  }
  if (!ui.includes("Русскоязычная метка не доказывает российский рынок")) {
    const anchor = '      {mechanicDb && <p>';
    const index = ui.indexOf(anchor);
    if (index < 0) fail("Wikidata boundary-note insertion anchor is missing");
    const paragraph = '      <p>Wikidata добавляет только структурированные названия моделей и производителей. Русскоязычная метка не доказывает российский рынок; даты P571/P576 не являются годами выпуска. Поколения, двигатели, КПП, ECU и точная применимость не подтверждены.</p>\n';
    ui = ui.slice(0, index) + paragraph + ui.slice(index);
  }
  if (!ui.includes('dataset === "wikidata" ?')) {
    const anchor = ': dataset === "vehiclesdb" ? "Марка или модель… например Golf" :';
    if (ui.split(anchor).length - 1 !== 1) fail("Wikidata search placeholder insertion anchor is missing");
    ui = ui.replace(anchor, ': dataset === "wikidata" ? "Марка или модель… например Golf" : dataset === "vehiclesdb" ? "Марка или модель… например Golf" :');
  }
  if (!ui.includes('dataset === "wikidata" && rows.map')) {
    const anchor = '      {dataset === "vehiclesdb" && rows.map((row) => <article className="research-result" key={row.sourceModelId}>';
    const card = [
      '      {dataset === "wikidata" && rows.map((row) => <article className="research-result" key={row.modelQid + "-" + row.manufacturerQid}>',
      '        <div className="research-result-top"><div><small>{row.manufacturer} · WIKIDATA · CC0 1.0</small><h3>{row.model}{row.modelRu ? " · " + row.modelRu : ""}</h3></div><span className="research-candidate">IDENTITY CANDIDATE</span></div>',
      '        <div className="research-data-grid">',
      '          <div><small>Wikidata model ID</small><b>{row.modelQid}</b></div>',
      '          <div><small>Даты P571 / P576</small><b>{[...(row.inceptionDateStatements || []), ...(row.dissolutionDateStatements || [])].join(" · ") || "Не указаны"}</b></div>',
      '          <div><small>Источник / ревизия</small><b>{row.sourceRevision}</b></div>',
      '          <div><small>Поколение / годы выпуска</small><b>Не подтверждены</b></div>',
      '          <div><small>Двигатель / КПП / ECU</small><b>Не предоставлены</b></div>',
      '        </div>',
      '        <div className="research-warning-line">{row.warning} Рынок: {row.marketScope}; точность: {row.applicabilityPrecision}; статус: {row.reviewStatus}.</div>',
      '        <div className="research-source"><span>Wikidata structured data · CC0-1.0 · attribution recommended, not required · SHA записи {String(row.sourceRecordSha256).slice(0, 12)}… · SHA snapshot {String(row.sourceSnapshotSha256).slice(0, 12)}… · SHA query {String(row.sourceQuerySha256).slice(0, 12)}… · SHA БД {String(row.databaseSha256).slice(0, 12)}… · SHA манифеста {String(row.sourceManifestSha256).slice(0, 12)}…</span><a href={row.modelUrl} target="_blank" rel="noopener noreferrer">Открыть Wikidata</a></div>',
      '      </article>)}',
      '',
      ''
    ].join("\n");
    if (ui.split(anchor).length - 1 !== 1) fail("Wikidata research result insertion anchor is missing");
    ui = ui.replace(anchor, card + anchor);
  }
  if (!ui.includes("Wikidata structured data — CC0 1.0 Universal")) {
    const anchor = '      <p>VAG identity — ODbL-1.0:';
    if (ui.split(anchor).length - 1 !== 1) fail("Wikidata attribution insertion anchor is missing");
    ui = ui.replace(anchor, '      <p>Wikidata structured data — CC0 1.0 Universal: <a href="https://www.wikidata.org/" target="_blank" rel="noopener noreferrer">Wikidata</a>. Атрибуция рекомендуется, но не обязательна; лицензия не распространяется на статьи, изображения, логотипы и OEM-материалы Wikimedia.</p>\n' + anchor);
  }
  if (!ui.includes("SQLite SHA-256 · Wikidata")) {
    const anchor = '      <p>SQLite SHA-256 · VehiclesDB identity:';
    if (ui.split(anchor).length - 1 !== 1) fail("Wikidata UI hash-summary anchor is missing");
    ui = ui.replace(anchor, '      <p>SQLite SHA-256 · Wikidata identity: {wikidata?.databaseSha256 || "недоступен"} · snapshot SHA-256: {wikidata?.sourceSnapshotSha256 || "недоступен"} · query SHA-256: {wikidata?.sourceQuerySha256 || "недоступен"} · manifest SHA-256: {wikidata?.sourceManifestSha256 || "недоступен"}</p>\n' + anchor);
  }
  writeText(uiFile, ui);

  replaceExactly(dbTestFile,
    'test("VehiclesDB model evidence is foreign-market-only, attributed, and never promoted to exact fitment", () => {',
    'test("Wikidata model labels are CC0 identity candidates and never establish Russian-market or exact fitment", () => {\n' +
    '  const summary = local.getResearchSummary(root);\n' +
    '  const wikidata = summary.packs.find((x) => x.id === "wikidata-vag-model-taxonomy-cc0");\n' +
    '  assert.deepEqual(wikidata.counts, { models: 376, sourceBindings: 376, manufacturers: 5, russianLabels: 171, dateStatements: 21 });\n' +
    '  assert.equal(wikidata.license, "CC0-1.0");\n' +
    '  assert.equal(wikidata.marketScope, "UNKNOWN");\n' +
    '  assert.equal(wikidata.applicabilityPrecision, "candidate_identity_only");\n' +
    '  assert.equal(wikidata.fitmentClaim, false);\n' +
    '  assert.equal(wikidata.executionAllowed, false);\n' +
    '  assert.equal(wikidata.attributionRequired, false);\n' +
    '  assert.equal(wikidata.attributionRecommended, true);\n' +
    '  assert.match(wikidata.sourceManifestSha256, /^[a-f0-9]{64}$/);\n' +
    '  assert.match(wikidata.sourceSnapshotSha256, /^[a-f0-9]{64}$/);\n' +
    '  assert.match(wikidata.sourceQuerySha256, /^[a-f0-9]{64}$/);\n' +
    '  assert.match(wikidata.databaseSha256, /^[a-f0-9]{64}$/);\n' +
    '  const rows = local.searchWikidataCandidates("Volkswagen", 10, root);\n' +
    '  assert.ok(rows.length > 0);\n' +
    '  assert.ok(rows.every((row) => row.marketScope === "UNKNOWN" && row.reviewStatus === "candidate" && row.applicabilityPrecision === "candidate_identity_only" && row.exactFitment === false && row.generationVerified === false && row.engineCode === null && row.gearboxCode === null && row.ecuFitment === false && row.dtcFitment === false && row.repairProcedureFitment === false));\n' +
    '});\n\n' +
    'test("VehiclesDB model evidence is foreign-market-only, attributed, and never promoted to exact fitment", () => {',
    "Wikidata local research DB test");

  replaceExactly(packTestFile,
    '  assert.equal(result.mechanicdb_vag_dtc_candidates.unsafeRows, 0);',
    '  assert.equal(result.mechanicdb_vag_dtc_candidates.unsafeRows, 0);\n' +
    '  assert.deepEqual(result.wikidata_vag_taxonomy, { models: 376, sourceBindings: 376, manufacturers: 5, russianLabels: 171, dateStatements: 21 });',
    "Wikidata pack verification test");

  replaceExactly(uiTestFile,
    'test("desktop opens the local SQLite workspace when Supabase is not configured and keeps research packs separate", () => {',
    'test("Wikidata CC0 identity candidates have their own tab and never claim market or technical fitment", () => {\n' +
    '  assert.match(component, /Wikidata · модели VAG/);\n' +
    '  assert.match(component, /dataset === "wikidata"/);\n' +
    '  assert.match(component, /Русскоязычная метка не доказывает российский рынок/);\n' +
    '  assert.match(component, /даты P571 \\/ P576/);\n' +
    '  assert.match(component, /candidate_identity_only/);\n' +
    '  assert.match(component, /CC0-1\\.0/);\n' +
    '  const route = fs.readFileSync(path.join(__dirname, "..", "app", "api", "local-research", "route.ts"), "utf8");\n' +
    '  assert.match(route, /dataset === "wikidata"/);\n' +
    '  assert.match(route, /searchWikidataCandidates/);\n' +
    '});\n\n' +
    'test("desktop opens the local SQLite workspace when Supabase is not configured and keeps research packs separate", () => {',
    "Wikidata UI contract test");

  let verifier = readText(verifierFile);
  if (verifier.includes("manifest.packs.length === 5")) verifier = verifier.replace('manifest.packs.length === 5, "Expected five separately licensed research packs"', 'manifest.packs.length === 6, "Expected six separately licensed research packs"');
  if (!verifier.includes('const wikidata = byId["wikidata-vag-model-taxonomy-cc0"];')) {
    const anchor = '  const mechanicdb = byId["mechanicdb-vag-dtc-candidates-odbl"];\n';
    if (verifier.split(anchor).length - 1 !== 1) fail("Wikidata verifier manifest lookup anchor is missing");
    verifier = verifier.replace(anchor, anchor + '  const wikidata = byId["wikidata-vag-model-taxonomy-cc0"];\n');
  }
  if (verifier.includes('assert(ob && vag && obdb && vehiclesdb && mechanicdb, "All five research packs must be registered");')) {
    verifier = verifier.replace('assert(ob && vag && obdb && vehiclesdb && mechanicdb, "All five research packs must be registered");', 'assert(ob && vag && obdb && vehiclesdb && mechanicdb && wikidata, "All six research packs must be registered");');
  }
  if (!verifier.includes("const wikidataSummary = localResearch.getResearchSummary(RESEARCH);")) {
    const anchor = '  const manifestHash = sha256(fs.readFileSync(manifestPath));\n';
    if (verifier.split(anchor).length - 1 !== 1) fail("Wikidata verifier summary insertion anchor is missing");
    verifier = verifier.replace(anchor, anchor +
      '  const localResearch = require(path.join(ROOT, "lib", "local-research-db.cjs"));\n' +
      '  const wikidataSummary = localResearch.getResearchSummary(RESEARCH).packs.find((pack) => pack.id === "wikidata-vag-model-taxonomy-cc0");\n' +
      '  assert(wikidataSummary && wikidataSummary.counts?.models === 376 && wikidataSummary.counts?.russianLabels === 171 && wikidataSummary.marketScope === "UNKNOWN" && wikidataSummary.fitmentClaim === false, "Wikidata runtime pack verification failed");\n');
  }
  if (!verifier.includes("wikidata_vag_taxonomy: wikidataSummary.counts")) {
    const anchor = '      mechanicdb_vag_dtc_candidates: mechanicCounts,\n';
    if (verifier.split(anchor).length - 1 !== 1) fail("Wikidata verifier result insertion anchor is missing");
    verifier = verifier.replace(anchor, anchor + '      wikidata_vag_taxonomy: wikidataSummary.counts,\n');
  }
  writeText(verifierFile, verifier);

  let readme = readText(readmeFile);
  readme = readme.replace("Five separately licensed", "Six separately licensed");
  if (!readme.includes("| Wikidata VAG model identity | CC0-1.0 |")) {
    const anchor = '| VehiclesDB | CC BY 4.0 | 260 model names; 1,524 market-presence evidence rows across 14 non-RU countries | No RU evidence, generation/year, engine, gearbox, ECU or exact fitment; visible attribution and upstream notices required |\n';
    replaceExactly(readmeFile, anchor, anchor + '| Wikidata VAG model identity | CC0-1.0 | 376 model entities; 171 Russian-language labels; 5 manufacturer labels | Market UNKNOWN; candidate identity only; no generation verification, model years, engine/gearbox/ECU codes or exact fitment |\n', "Wikidata README table row");
    readme = readText(readmeFile);
  }
  if (!readme.includes("Wikidata Russian-language labels do not establish Russian/EAEU market applicability")) {
    const anchor = '- VehiclesDB is only a foreign-market identity aid; it cannot establish Russian or EAEU applicability.\n';
    replaceExactly(readmeFile, anchor, anchor + '- Wikidata Russian-language labels do not establish Russian/EAEU market applicability; P571/P576 statements are not converted into production-year ranges.\n', "Wikidata README boundary");
  }
  if (!readme.includes("Wikidata structured-data snapshot is acquired")) {
    const anchor = "The MechanicDB artifact is integrated with";
    const index = readme.indexOf(anchor);
    if (index < 0) fail("Wikidata README integration-note anchor is missing");
    const note = "The Wikidata structured-data snapshot is acquired from the official SPARQL endpoint by a bounded, pinned query. The CC0 pack preserves the raw snapshot, query, per-binding hashes, SQLite source registry, license notice and attribution note. All records remain identity candidates with market UNKNOWN; Russian labels and P571/P576 date statements are not converted into Russian-market fitment or production years.\n\n";
    readme = readme.slice(0, index) + note + readme.slice(index);
    writeText(readmeFile, readme);
  }

  let docs = readText(docsFile).replace("Five separately licensed", "Six separately licensed");
  if (!docs.includes("| Wikidata VAG model identity |")) {
    const anchor = "## Critical limits\n";
    if (docs.split(anchor).length - 1 !== 1) fail("Wikidata research docs table anchor is missing");
    docs = docs.replace(anchor, "| Wikidata VAG model identity | CC0-1.0 | 376 model entities; 171 Russian-language labels; 5 manufacturer labels | Market UNKNOWN; candidate identity only; no generation, model-year, engine, gearbox, ECU or exact fitment |\n\n## Critical limits\n");
  }
  if (!docs.includes("Wikidata Russian-language labels do not establish Russian/EAEU market applicability")) {
    docs = docs.replace("- VehiclesDB is only a foreign-market identity aid; it cannot establish Russian or EAEU applicability.\n", "- VehiclesDB is only a foreign-market identity aid; it cannot establish Russian or EAEU applicability.\n- Wikidata Russian-language labels do not establish Russian/EAEU market applicability; P571/P576 statements are not converted into production-year ranges.\n");
  }
  writeText(docsFile, docs);
}

function main() {
  const args = parseArgs(process.argv);
  const desktopRoot = path.resolve(ROOT, "desktop-source");
  const researchDir = path.resolve(args.researchDir);
  if (!fs.existsSync(path.join(desktopRoot, "package.json")) || !fs.existsSync(path.join(researchDir, "manifest.json"))) fail("Desktop source or research manifest is missing");
  const verified = validatePack(args.packDir);
  const targetDir = safeJoin(researchDir, PACK_ID);
  fs.mkdirSync(targetDir, { recursive: true });
  copyRegularFile(args.packDir, "manifest.json", targetDir);
  for (const relative of Object.keys(verified.manifest.pack_files).sort()) copyRegularFile(args.packDir, relative, targetDir);
  updateResearchManifest(researchDir, verified);
  patchDesktopSource(desktopRoot);

  const rootManifest = readJson(path.join(researchDir, "manifest.json"));
  const rootPack = rootManifest.packs.find((pack) => pack.id === PACK_ID);
  if (!rootPack || rootPack.database_sha256 !== verified.manifest.database_sha256 ||
      sha256File(safeJoin(researchDir, rootPack.database)) !== rootPack.database_sha256) fail("Final desktop Wikidata pack manifest/database verification failed");
  const local = require(path.join(desktopRoot, "lib", "local-research-db.cjs"));
  const summary = local.getResearchSummary(researchDir);
  const packSummary = summary.packs.find((pack) => pack.id === PACK_ID);
  const sample = local.searchWikidataCandidates("Volkswagen", 5, researchDir);
  if (!packSummary || packSummary.counts.models !== 376 || packSummary.counts.russianLabels !== 171 ||
      !sample.length || sample.some((row) => row.marketScope !== "UNKNOWN" || row.exactFitment !== false || row.engineCode !== null || row.gearboxCode !== null)) fail("Wikidata local search/summary smoke test failed");
  const verification = {
    status: "integrated_verified_candidate_only",
    pack_id: PACK_ID,
    source_revision: verified.manifest.source_revision,
    source_snapshot_sha256: verified.manifest.source_snapshot_sha256,
    source_query_sha256: verified.manifest.source_query_sha256,
    database_sha256: verified.manifest.database_sha256,
    source_manifest_sha256: rootPack.source_manifest_sha256,
    root_manifest_sha256: sha256File(path.join(researchDir, "manifest.json")),
    counts: packSummary.counts,
    search_sample_count: sample.length,
    market_scope: "UNKNOWN",
    applicability_precision: "candidate_identity_only",
    exact_vehicle_fitment: false,
    generation_verified: false,
    engine_code_fitment: false,
    transmission_code_fitment: false,
    ecu_fitment: false,
    dtc_fitment: false,
    repair_procedure_fitment: false,
    diagnostic_execution_allowed: false,
    production_years_inferred: false,
  };
  writeText(path.join(researchDir, PACK_ID, "desktop-integration-verification.json"), JSON.stringify(verification, null, 2) + "\n");
  console.log(JSON.stringify(verification, null, 2));
}

main();

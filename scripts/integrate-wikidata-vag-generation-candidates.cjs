"use strict";
const fs = require("node:fs");
const path = require("node:path");
const crypto = require("node:crypto");
const { DatabaseSync } = require("node:sqlite");

const ROOT = path.resolve(__dirname, "..");
const ID = "wikidata-vag-generation-candidates-cc0";
const SOURCE_ID = "wikidata-vag-generation-candidates";
const ARTIFACT = {
  workflowRunId: 41906770429,
  artifactId: 13361576024,
  artifactSha256: "0171d7775e9ad8c98ff564be1dd5729c85b031f67cd063521e5a9f4989ca3989",
  sourceCommit: "5fc952cfe117152e522740809c2a1d70e1bf01a3",
  sourceBranch: "main",
  snapshotCommit: "576cf983d195c51c8984ad46acdcab6ed1725800"
};
const EXPECTED = {
  snapshotId: "5c1c7c37593b",
  sourceSnapshotSha256: "5c1c7c37593b5a86c7497153c4b29307f1c26922e21d3fabe08e6929c66d4495",
  sourceQuerySha256: "bedc320b0181a5682c99b50b9b648bf85e5ba3adb619f39c07a7b31bf44acb5b",
  databaseSha256: "866807139e33365997c402809f4ce2dba64e9cbadcd685d40db4ac309b2f93a5",
  counts: { member_entities: 9, model_member_links: 10, source_bindings: 14, models_with_members: 6, manufacturers: 3, russian_labels: 5, date_statements: 2 }
};

function fail(message) { throw new Error("[run70] " + message); }
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
function writeJson(file, value) { writeText(file, JSON.stringify(value, null, 2) + "\n"); }
function safeJoin(root, relative) {
  if (typeof relative !== "string" || !relative || path.isAbsolute(relative) || relative.includes("\\")) fail("Unsafe relative path: " + String(relative));
  const base = path.resolve(root);
  const target = path.resolve(base, relative);
  const rel = path.relative(base, target);
  if (rel === ".." || rel.startsWith(".." + path.sep) || path.isAbsolute(rel)) fail("Path escaped root: " + relative);
  return target;
}
function exact(source, before, after, label) {
  if (source.includes(after)) return source;
  const count = source.split(before).length - 1;
  if (count !== 1) fail(label + ": expected one anchor, found " + count);
  return source.replace(before, after);
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
  if (!result["--pack-dir"] || !result["--research-dir"]) fail("Usage: node integrate-wikidata-vag-generation-candidates.cjs --pack-dir <dir> --research-dir <dir>");
  return { packDir: path.resolve(result["--pack-dir"]), researchDir: path.resolve(result["--research-dir"]) };
}
function copyAs(sourceRoot, relative, targetFile) {
  const source = safeJoin(sourceRoot, relative);
  const stat = fs.lstatSync(source);
  if (!stat.isFile() || stat.isSymbolicLink()) fail("Source is not a regular file: " + relative);
  fs.mkdirSync(path.dirname(targetFile), { recursive: true });
  if (fs.existsSync(targetFile)) {
    if (!fs.lstatSync(targetFile).isFile() || sha256File(targetFile) !== sha256File(source)) fail("Refusing to overwrite different immutable file: " + relative);
  } else fs.copyFileSync(source, targetFile);
  if (sha256File(targetFile) !== sha256File(source)) fail("Copied file hash mismatch: " + relative);
  return sha256File(targetFile);
}
function copyRegularFile(sourceRoot, relative, targetRoot) {
  const source = safeJoin(sourceRoot, relative);
  const stat = fs.lstatSync(source);
  if (!stat.isFile() || stat.isSymbolicLink()) fail("Pack entry is not a regular file: " + relative);
  const target = safeJoin(targetRoot, relative);
  fs.mkdirSync(path.dirname(target), { recursive: true });
  if (fs.existsSync(target)) {
    if (!fs.lstatSync(target).isFile() || sha256File(target) !== sha256File(source)) fail("Refusing to overwrite different immutable pack file: " + relative);
  } else fs.copyFileSync(source, target);
  if (sha256File(target) !== sha256File(source)) fail("Copied pack file SHA-256 mismatch: " + relative);
  return sha256File(target);
}
function openReadOnly(file) {
  const db = new DatabaseSync(file, { readOnly: true });
  db.exec("PRAGMA query_only=ON; PRAGMA trusted_schema=OFF;");
  const integrity = db.prepare("PRAGMA integrity_check").get().integrity_check;
  if (integrity !== "ok") fail("SQLite integrity_check failed: " + integrity);
  if (db.prepare("PRAGMA foreign_key_check").all().length) fail("SQLite foreign-key check failed");
  return db;
}
function count(db, sql, ...params) { return Number(db.prepare(sql).get(...params).n); }

function validatePack(packDir, researchDir) {
  const manifest = readJson(safeJoin(packDir, "manifest.json"));
  const sourceManifestPath = safeJoin(ROOT, "data/source-manifests/wikidata-vag-generation-candidates.json");
  const sourceRegisterPath = safeJoin(ROOT, "data/source-manifests/vag-factory-source-register.json");
  const sourceManifest = readJson(sourceManifestPath);
  const register = readJson(sourceRegisterPath);
  const sourceRecord = register.sources.find((item) => item.source_id === SOURCE_ID);
  if (manifest.schema_version !== 1 || manifest.source_id !== SOURCE_ID || manifest.snapshot_id !== EXPECTED.snapshotId ||
      manifest.source_snapshot_sha256 !== EXPECTED.sourceSnapshotSha256 ||
      manifest.source_query_sha256 !== EXPECTED.sourceQuerySha256 || manifest.database_sha256 !== EXPECTED.databaseSha256) {
    fail("Pinned generation snapshot identity/hash mismatch");
  }
  if (manifest.data_license !== "CC0-1.0" || manifest.rights_status !== "approved_by_published_license" ||
      manifest.commercial_use_allowed !== true || manifest.display_allowed !== true ||
      manifest.offline_cache_allowed !== true || manifest.bulk_reuse_allowed !== true ||
      manifest.redistribution_allowed !== true || manifest.attribution_required !== false ||
      manifest.attribution_recommended !== true || manifest.share_alike_required !== false) fail("CC0 rights gate failed");
  if (manifest.scope?.market_scope !== "UNKNOWN" || manifest.scope?.applicability_precision !== "series_member_candidate" ||
      manifest.scope?.review_status !== "candidate" || manifest.scope?.generation_verified !== false ||
      manifest.scope?.exact_vehicle_fitment !== false || manifest.scope?.engine_code_fitment !== false ||
      manifest.scope?.transmission_code_fitment !== false || manifest.scope?.ecu_fitment !== false ||
      manifest.scope?.dtc_fitment !== false || manifest.scope?.repair_procedure_fitment !== false ||
      manifest.scope?.diagnostic_execution_allowed !== false || manifest.scope?.production_years_inferred !== false ||
      manifest.completeness_status !== "unknown" || manifest.limit_reached !== false ||
      manifest.query_limit !== 5000 ||
      manifest.query_batch_size !== 50 || manifest.query_batches !== 8) fail("Candidate-only scope or bounded-query gate failed");
  if (JSON.stringify(manifest.counts) !== JSON.stringify(EXPECTED.counts)) fail("Generation pack row counts differ from pinned release");
  if (sourceManifest.source_id !== SOURCE_ID || sourceManifest.license?.id !== "CC0-1.0" ||
      sourceManifest.applicability?.market_scope !== "UNKNOWN" ||
      sourceManifest.applicability?.precision !== "series_member_candidate" ||
      sourceManifest.applicability?.generation_verified !== false ||
      sourceManifest.applicability?.exact_vehicle_fitment !== false ||
      sourceManifest.applicability?.production_years_inferred !== false) fail("Static source manifest rights/scope mismatch");
  if (!sourceRecord || sourceRecord.provenance?.source_manifest !== "data/source-manifests/wikidata-vag-generation-candidates.json" ||
      sourceRecord.provenance?.snapshot_manifest_pattern !== "data/research/wikidata-vag-generations/<snapshot-id>/manifest.json" ||
      sourceRecord.access?.query_batch_size !== 50 || sourceRecord.access?.query_limit !== 5000 ||
      sourceRecord.access?.query_limit_scope !== "per_batch") fail("Source register provenance/query limits mismatch");
  for (const [relative, info] of Object.entries(manifest.pack_files || {})) {
    const file = safeJoin(packDir, relative);
    if (!fs.existsSync(file) || fs.statSync(file).size !== info.size_bytes || sha256File(file) !== info.sha256) fail("Pack file SHA-256/size mismatch: " + relative);
  }
  const parentManifest = readJson(safeJoin(researchDir, "wikidata-vag-model-taxonomy-cc0/manifest.json"));
  if (manifest.parent_model_pack?.source_snapshot_sha256 !== parentManifest.source_snapshot_sha256 ||
      manifest.parent_model_pack?.database_sha256 !== parentManifest.database_sha256 ||
      manifest.parent_model_pack?.source_revision !== parentManifest.source_revision ||
      manifest.parent_model_pack?.snapshot_id !== parentManifest.snapshot_id) fail("Generation pack parent does not match the installed model identity pack");

  const db = openReadOnly(safeJoin(packDir, "wikidata-vag-generations.sqlite"));
  try {
    const source = db.prepare("SELECT * FROM source_registry WHERE source_id=?").get(SOURCE_ID);
    if (!source || source.license_id !== "CC0-1.0" || source.rights_status !== "approved_by_published_license" ||
        source.parent_model_source_revision !== parentManifest.source_revision ||
        source.parent_model_source_snapshot_sha256 !== parentManifest.source_snapshot_sha256 ||
        source.parent_model_database_sha256 !== parentManifest.database_sha256 ||
        source.source_revision !== manifest.source_revision || source.source_snapshot_sha256 !== manifest.source_snapshot_sha256 ||
        source.source_query_sha256 !== manifest.source_query_sha256 || source.market_scope !== "UNKNOWN" ||
        source.applicability_precision !== "series_member_candidate" || source.review_status !== "candidate" ||
        source.generation_verified !== 0 || source.exact_vehicle_fitment !== 0 ||
        source.engine_code_fitment !== 0 || source.transmission_code_fitment !== 0 ||
        source.ecu_fitment !== 0 || source.dtc_fitment !== 0 || source.repair_procedure_fitment !== 0 ||
        source.diagnostic_execution_allowed !== 0 || source.production_years_inferred !== 0 ||
        source.attribution_required !== 0 || source.attribution_recommended !== 1 ||
        source.share_alike_required !== 0 || source.commercial_use_allowed !== 1 ||
        source.display_allowed !== 1 || source.offline_cache_allowed !== 1 ||
        source.bulk_reuse_allowed !== 1 || source.redistribution_allowed !== 1) fail("SQLite source_registry rights/applicability gate failed");
    const counts = {
      member_entities: count(db, "SELECT count(DISTINCT member_qid) AS n FROM model_series_member_candidates"),
      model_member_links: count(db, "SELECT count(*) AS n FROM model_series_member_candidates"),
      source_bindings: count(db, "SELECT count(*) AS n FROM series_member_source_bindings"),
      models_with_members: count(db, "SELECT count(DISTINCT model_qid) AS n FROM model_series_member_candidates"),
      manufacturers: count(db, "SELECT count(DISTINCT manufacturer_qid) AS n FROM model_series_member_candidates"),
      russian_labels: count(db, "SELECT count(DISTINCT member_qid) AS n FROM model_series_member_candidates WHERE member_label_ru IS NOT NULL AND trim(member_label_ru)!=''"),
      date_statements: count(db, "SELECT count(*) AS n FROM series_member_date_statements")
    };
    if (JSON.stringify(counts) !== JSON.stringify(EXPECTED.counts)) fail("SQLite row counts do not match pinned manifest");
    const invalid = count(db, "SELECT count(*) AS n FROM model_series_member_candidates WHERE market_scope!='UNKNOWN' OR applicability_precision!='series_member_candidate' OR review_status!='candidate' OR generation_verified!=0 OR exact_vehicle_fitment!=0 OR engine_code_fitment!=0 OR transmission_code_fitment!=0 OR ecu_fitment!=0 OR dtc_fitment!=0 OR repair_procedure_fitment!=0 OR diagnostic_execution_allowed!=0 OR production_years_inferred!=0");
    if (invalid !== 0) fail("One or more candidate rows cross the applicability boundary");
    const badBindings = count(db, "SELECT count(*) AS n FROM series_member_source_bindings WHERE length(source_binding_sha256)!=64 OR source_revision!=? OR source_snapshot_sha256!=? OR source_query_sha256!=?", manifest.source_revision, manifest.source_snapshot_sha256, manifest.source_query_sha256);
    if (badBindings !== 0) fail("Source binding hashes/revisions are incomplete");
    const badDates = count(db, "SELECT count(*) AS n FROM series_member_date_statements d JOIN series_member_source_bindings b USING(source_binding_index) WHERE d.source_binding_sha256!=b.source_binding_sha256");
    if (badDates !== 0) fail("Date statement source binding hashes mismatch");
    return { manifest, sourceManifest, sourceRecord, parentManifest, counts };
  } finally { db.close(); }
}

function updateResearchManifest(researchDir, packDir, verified) {
  const targetDir = safeJoin(researchDir, ID);
  fs.mkdirSync(targetDir, { recursive: true });
  copyRegularFile(packDir, "manifest.json", targetDir);
  for (const relative of Object.keys(verified.manifest.pack_files).sort()) copyRegularFile(packDir, relative, targetDir);
  copyAs(ROOT, "data/source-manifests/wikidata-vag-generation-candidates.json", safeJoin(targetDir, "source-manifest.json"));
  copyAs(ROOT, "data/source-manifests/vag-factory-source-register.json", safeJoin(targetDir, "source-register.json"));

  const rootPath = safeJoin(researchDir, "manifest.json");
  const rootManifest = readJson(rootPath);
  const sourceManifestSha = sha256File(safeJoin(targetDir, "source-manifest.json"));
  const sourceRegisterSha = sha256File(safeJoin(targetDir, "source-register.json"));
  const snapshotManifestSha = sha256File(safeJoin(targetDir, "manifest.json"));
  const report = {
    schema_version: 1, status: "integrated_verified_series_member_candidates_only",
    pack_id: ID, source_id: SOURCE_ID, snapshot_id: verified.manifest.snapshot_id,
    source_revision: verified.manifest.source_revision,
    source_snapshot_sha256: verified.manifest.source_snapshot_sha256,
    source_query_sha256: verified.manifest.source_query_sha256,
    logical_content_sha256: verified.manifest.logical_content_sha256,
    database_sha256: verified.manifest.database_sha256,
    source_manifest_sha256: sourceManifestSha, source_register_sha256: sourceRegisterSha,
    snapshot_manifest_sha256: snapshotManifestSha,
    artifact_sha256: ARTIFACT.artifactSha256, workflow_run_id: ARTIFACT.workflowRunId,
    artifact_id: ARTIFACT.artifactId, source_commit: ARTIFACT.sourceCommit,
    snapshot_commit: ARTIFACT.snapshotCommit, parent_model_pack: verified.manifest.parent_model_pack,
    counts: verified.manifest.counts, market_scope: "UNKNOWN",
    applicability_precision: "series_member_candidate", review_status: "candidate",
    generation_verified: false, exact_vehicle_fitment: false, engine_code_fitment: false,
    transmission_code_fitment: false, ecu_fitment: false, dtc_fitment: false,
    repair_procedure_fitment: false, diagnostic_execution_allowed: false,
    production_years_inferred: false
  };
  writeJson(safeJoin(targetDir, "integration-verification.json"), report);
  const entry = {
    id: ID, kind: "vehicle_model_series_member_candidates",
    database: ID + "/wikidata-vag-generations.sqlite",
    database_sha256: verified.manifest.database_sha256,
    license_file: ID + "/LICENSE-NOTICE.txt",
    license_file_sha256: verified.manifest.pack_files["LICENSE-NOTICE.txt"].sha256,
    license: "CC0-1.0", license_status: "approved_by_published_license",
    source_manifest_file: ID + "/source-manifest.json", source_manifest_sha256: sourceManifestSha,
    source_register_file: ID + "/source-register.json", source_register_sha256: sourceRegisterSha,
    snapshot_manifest_file: ID + "/manifest.json", snapshot_manifest_sha256: snapshotManifestSha,
    attribution_file: ID + "/ATTRIBUTION.md", attribution_sha256: verified.manifest.pack_files["ATTRIBUTION.md"].sha256,
    query_file: ID + "/generation-query.rq", query_sha256: verified.manifest.source_query_sha256,
    snapshot_file: ID + "/generation-snapshot.json", snapshot_sha256: verified.manifest.source_snapshot_sha256,
    integration_report_file: ID + "/integration-verification.json",
    publisher: verified.manifest.publisher, dataset: "Wikidata VAG model-series member candidates",
    source_url: "https://www.wikidata.org/", source_endpoint: "https://query.wikidata.org/sparql",
    upstream_revision: verified.manifest.source_revision, snapshot_generated_at_utc: verified.manifest.built_at_utc,
    source_snapshot_sha256: verified.manifest.source_snapshot_sha256,
    source_query_sha256: verified.manifest.source_query_sha256,
    logical_content_sha256: verified.manifest.logical_content_sha256,
    counts: verified.manifest.counts, parent_model_pack: verified.manifest.parent_model_pack,
    query_limit: verified.manifest.query_limit, query_batch_size: verified.manifest.query_batch_size,
    query_batches: verified.manifest.query_batches, limit_reached: verified.manifest.limit_reached,
    market_scope: "UNKNOWN", applicability_precision: "series_member_candidate",
    review_status: "candidate", completeness_status: "unknown",
    fitment_claim: false, generation_verified: false, exact_vehicle_fitment: false,
    engine_code_fitment: false, transmission_code_fitment: false, ecu_fitment: false,
    dtc_fitment: false, repair_procedure_fitment: false, diagnostic_execution_allowed: false,
    production_years_inferred: false, attribution_required: false,
    attribution_recommended: true, share_alike_required: false,
    commercial_use_allowed: true, display_allowed: true, offline_cache_allowed: true,
    bulk_reuse_allowed: true, redistribution_allowed: true,
    rights_status: "approved_by_published_license",
    scope: verified.manifest.scope, limitations: verified.manifest.exclusions,
    source_workflow: {
      repository: "ismailizmajlov-oss/VAG-TECH-PRO", branch: ARTIFACT.sourceBranch,
      commit: ARTIFACT.sourceCommit, snapshot_commit: ARTIFACT.snapshotCommit,
      run_id: ARTIFACT.workflowRunId, artifact_id: ARTIFACT.artifactId,
      artifact_sha256: ARTIFACT.artifactSha256
    }
  };
  const existing = rootManifest.packs.find((pack) => pack.id === ID);
  if (existing && existing.database_sha256 !== entry.database_sha256) fail("Refusing to overwrite a different immutable generation pack");
  if (existing) Object.assign(existing, entry); else rootManifest.packs.push(entry);
  if (rootManifest.packs.length !== 9) fail("Expected 9 separately licensed research packs; found " + rootManifest.packs.length);
  rootManifest.integration_revision = "run70";
  rootManifest.integrated_artifacts = Array.isArray(rootManifest.integrated_artifacts) ? rootManifest.integrated_artifacts : [];
  rootManifest.integrated_artifacts = rootManifest.integrated_artifacts.filter((item) => item.pack_id !== ID);
  rootManifest.integrated_artifacts.push({
    pack_id: ID, artifact_zip_sha256: ARTIFACT.artifactSha256,
    source_snapshot_sha256: verified.manifest.source_snapshot_sha256,
    source_query_sha256: verified.manifest.source_query_sha256,
    database_sha256: verified.manifest.database_sha256,
    source_revision: verified.manifest.source_revision,
    workflow_run_id: ARTIFACT.workflowRunId, artifact_id: ARTIFACT.artifactId,
    source_commit: ARTIFACT.sourceCommit, snapshot_commit: ARTIFACT.snapshotCommit
  });
  writeJson(rootPath, rootManifest);
  entry.integration_report_sha256 = sha256File(safeJoin(targetDir, "integration-verification.json"));
  writeJson(rootPath, rootManifest);
  return { targetDir, rootManifest, entry, report };
}

function patchDesktopSource(desktop) {
  const dbPath = path.join(desktop, "lib/local-research-db.cjs");
  const typesPath = path.join(desktop, "lib/local-research-db.d.cts");
  const routePath = path.join(desktop, "app/api/local-research/route.ts");
  const uiPath = path.join(desktop, "components/local-research-catalog.tsx");
  const verifierPath = path.join(desktop, "scripts/verify-local-research-packs.cjs");
  const dbTestPath = path.join(desktop, "tests/local-research-db.test.cjs");
  const packTestPath = path.join(desktop, "tests/local-research-packs.test.cjs");
  const uiTestPath = path.join(desktop, "tests/local-research-ui-contract.test.cjs");
  const lifecyclePath = path.join(desktop, "scripts/windows-installer-lifecycle.ps1");
  for (const file of [dbPath, typesPath, routePath, uiPath, verifierPath, dbTestPath, packTestPath, uiTestPath, lifecyclePath]) {
    if (!fs.existsSync(file)) fail("Required desktop file missing: " + path.relative(desktop, file));
  }

  let db = readText(dbPath);
  const descriptor = [
    '  wikidataGenerations: Object.freeze({',
    '    id: "wikidata-vag-generation-candidates-cc0",',
    '    file: "wikidata-vag-generation-candidates-cc0/wikidata-vag-generations.sqlite",',
    '    manifest: "wikidata-vag-generation-candidates-cc0/manifest.json",',
    '    sourceManifest: "wikidata-vag-generation-candidates-cc0/source-manifest.json",',
    '    sourceRegister: "wikidata-vag-generation-candidates-cc0/source-register.json",',
    '    attribution: "wikidata-vag-generation-candidates-cc0/ATTRIBUTION.md",',
    '    licenseFile: "wikidata-vag-generation-candidates-cc0/LICENSE-NOTICE.txt",',
    '    queryFile: "wikidata-vag-generation-candidates-cc0/generation-query.rq",',
    '    snapshotFile: "wikidata-vag-generation-candidates-cc0/generation-snapshot.json",',
    '    verificationFile: "wikidata-vag-generation-candidates-cc0/integration-verification.json",',
    '    license: "CC0-1.0", source: "Wikidata structured data", sourceUrl: "https://www.wikidata.org/",',
    '    scope: "P179/P527 series-member candidates only; not verified generations; market UNKNOWN; no exact technical fitment",',
    '  }),'
  ].join("\n");
  if (!db.includes('id: "wikidata-vag-generation-candidates-cc0"')) {
    const anchor = "\n});\n\nfunction getResearchRoot";
    if (db.split(anchor).length - 1 !== 1) fail("PACKS descriptor insertion anchor missing");
    db = db.replace(anchor, "\n" + descriptor + anchor);
  }
  const functions = [
    "function getWikidataGenerationSummary(root) {",
    "  verifyPackDatabaseHash(root, PACKS.wikidataGenerations.id, PACKS.wikidataGenerations.file);",
    "  for (const [fileField, hashField] of [[\"license_file\", \"license_file_sha256\"], [\"source_manifest_file\", \"source_manifest_sha256\"], [\"source_register_file\", \"source_register_sha256\"], [\"snapshot_manifest_file\", \"snapshot_manifest_sha256\"], [\"attribution_file\", \"attribution_sha256\"], [\"query_file\", \"query_sha256\"], [\"snapshot_file\", \"snapshot_sha256\"], [\"integration_report_file\", \"integration_report_sha256\"]]) verifyPackFileHash(root, PACKS.wikidataGenerations.id, fileField, hashField);",
    "  const base = getResearchRoot(root);",
    "  const pack = JSON.parse(fs.readFileSync(path.join(base, PACKS.wikidataGenerations.manifest), \"utf8\"));",
    "  const sourceManifest = JSON.parse(fs.readFileSync(path.join(base, PACKS.wikidataGenerations.sourceManifest), \"utf8\"));",
    "  const parentManifest = JSON.parse(fs.readFileSync(path.join(base, PACKS.wikidata.manifest), \"utf8\"));",
    "  const db = openReadOnly(root, PACKS.wikidataGenerations.file);",
    "  try {",
    "    const source = db.prepare(\"SELECT * FROM source_registry WHERE source_id=?\").get(pack.source_id);",
    "    const counts = { memberEntities: db.prepare(\"SELECT count(DISTINCT member_qid) AS n FROM model_series_member_candidates\").get().n, modelMemberLinks: db.prepare(\"SELECT count(*) AS n FROM model_series_member_candidates\").get().n, sourceBindings: db.prepare(\"SELECT count(*) AS n FROM series_member_source_bindings\").get().n, modelsWithMembers: db.prepare(\"SELECT count(DISTINCT model_qid) AS n FROM model_series_member_candidates\").get().n, manufacturers: db.prepare(\"SELECT count(DISTINCT manufacturer_qid) AS n FROM model_series_member_candidates\").get().n, russianLabels: db.prepare(\"SELECT count(DISTINCT member_qid) AS n FROM model_series_member_candidates WHERE member_label_ru IS NOT NULL AND trim(member_label_ru)!=''\").get().n, dateStatements: db.prepare(\"SELECT count(*) AS n FROM series_member_date_statements\").get().n };",
    "    const invalid = db.prepare(\"SELECT count(*) AS n FROM model_series_member_candidates WHERE market_scope!='UNKNOWN' OR applicability_precision!='series_member_candidate' OR review_status!='candidate' OR generation_verified!=0 OR exact_vehicle_fitment!=0 OR engine_code_fitment!=0 OR transmission_code_fitment!=0 OR ecu_fitment!=0 OR dtc_fitment!=0 OR repair_procedure_fitment!=0 OR diagnostic_execution_allowed!=0 OR production_years_inferred!=0\").get().n;",
    "    const badBindings = db.prepare(\"SELECT count(*) AS n FROM series_member_source_bindings WHERE length(source_binding_sha256)!=64 OR source_revision!=? OR source_snapshot_sha256!=? OR source_query_sha256!=?\").get(pack.source_revision,pack.source_snapshot_sha256,pack.source_query_sha256).n;",
    "    const badDates = db.prepare(\"SELECT count(*) AS n FROM series_member_date_statements d JOIN series_member_source_bindings b USING(source_binding_index) WHERE d.source_binding_sha256!=b.source_binding_sha256\").get().n;",
    "    if (!source || source.license_id!==\"CC0-1.0\" || source.rights_status!==\"approved_by_published_license\" || source.parent_model_source_revision!==parentManifest.source_revision || source.parent_model_source_snapshot_sha256!==parentManifest.source_snapshot_sha256 || source.parent_model_database_sha256!==parentManifest.database_sha256 || pack.parent_model_pack?.source_snapshot_sha256!==parentManifest.source_snapshot_sha256 || pack.parent_model_pack?.database_sha256!==parentManifest.database_sha256 || source.source_revision!==pack.source_revision || source.source_snapshot_sha256!==pack.source_snapshot_sha256 || source.source_query_sha256!==pack.source_query_sha256 || source.market_scope!==\"UNKNOWN\" || source.applicability_precision!==\"series_member_candidate\" || source.review_status!==\"candidate\" || source.generation_verified!==0 || source.exact_vehicle_fitment!==0 || source.engine_code_fitment!==0 || source.transmission_code_fitment!==0 || source.ecu_fitment!==0 || source.dtc_fitment!==0 || source.repair_procedure_fitment!==0 || source.diagnostic_execution_allowed!==0 || source.production_years_inferred!==0 || source.attribution_required!==0 || source.attribution_recommended!==1 || source.share_alike_required!==0 || source.commercial_use_allowed!==1 || source.display_allowed!==1 || source.offline_cache_allowed!==1 || source.bulk_reuse_allowed!==1 || source.redistribution_allowed!==1 || invalid!==0 || badBindings!==0 || badDates!==0 || sourceManifest.license?.id!==\"CC0-1.0\" || sourceManifest.applicability?.market_scope!==\"UNKNOWN\" || sourceManifest.applicability?.precision!==\"series_member_candidate\" || sourceManifest.applicability?.generation_verified!==false || sourceManifest.applicability?.exact_vehicle_fitment!==false || sourceManifest.applicability?.production_years_inferred!==false) throw new Error(\"Wikidata generation candidate source/parent/rights gate failed\");",
    "    const expected=pack.counts; if (counts.memberEntities!==expected.member_entities || counts.modelMemberLinks!==expected.model_member_links || counts.sourceBindings!==expected.source_bindings || counts.modelsWithMembers!==expected.models_with_members || counts.manufacturers!==expected.manufacturers || counts.russianLabels!==expected.russian_labels || counts.dateStatements!==expected.date_statements) throw new Error(\"Wikidata generation candidate counts mismatch\");",
    "    const rootManifest=JSON.parse(fs.readFileSync(path.join(base,\"manifest.json\"),\"utf8\")); const entry=rootManifest.packs.find((item)=>item.id===PACKS.wikidataGenerations.id);",
    "    return { id:PACKS.wikidataGenerations.id, kind:\"vehicle_model_series_member_candidates\", license:\"CC0-1.0\", source:PACKS.wikidataGenerations.source, sourceUrl:PACKS.wikidataGenerations.sourceUrl, status:\"series_member_candidate\", marketScope:\"UNKNOWN\", applicabilityPrecision:\"series_member_candidate\", reviewStatus:\"candidate\", generationVerified:false, exactVehicleFitment:false, engineCodeFitment:false, transmissionCodeFitment:false, ecuFitment:false, dtcFitment:false, repairProcedureFitment:false, diagnosticExecutionAllowed:false, productionYearsInferred:false, attributionRequired:false, attributionRecommended:true, shareAlikeRequired:false, counts, upstreamRevision:pack.source_revision, snapshotGeneratedAt:pack.built_at_utc, sourceManifestSha256:entry.source_manifest_sha256, sourceRegisterSha256:entry.source_register_sha256, snapshotManifestSha256:entry.snapshot_manifest_sha256, sourceSnapshotSha256:pack.source_snapshot_sha256, sourceQuerySha256:pack.source_query_sha256, logicalContentSha256:pack.logical_content_sha256, databaseSha256:pack.database_sha256, parentModelPack:pack.parent_model_pack, queryBatchSize:pack.query_batch_size, queryBatches:pack.query_batches, queryLimit:pack.query_limit, limitReached:pack.limit_reached, note:\"P179/P527 series-member candidates only. Not verified generations, production-year ranges, Russian/EAEU fitment or technical repair applicability.\" };",
    "  } finally { db.close(); }",
    "}",
    "",
    "function searchWikidataGenerationCandidates(query, limit=25, root) {",
    "  const q=validateQuery(query); const summary=getWikidataGenerationSummary(root); const base=getResearchRoot(root);",
    "  const db=openReadOnly(root,PACKS.wikidataGenerations.file); const parentDb=openReadOnly(root,PACKS.wikidata.file);",
    "  try {",
    "    const pattern=\"%\"+q.replace(/[\\\\%_]/g,\"\\\\$&\")+\"%\";",
    "    const rows=db.prepare(\"SELECT * FROM model_series_member_candidates WHERE member_label_en LIKE ? ESCAPE '\\\\' OR member_label_ru LIKE ? ESCAPE '\\\\' OR model_label_en LIKE ? ESCAPE '\\\\' OR member_qid LIKE ? OR model_qid LIKE ? ORDER BY model_label_en,member_label_en LIMIT ?\").all(pattern,pattern,pattern,pattern,pattern,clampLimit(limit));",
    "    return rows.map((row)=>{",
    "      const parent=parentDb.prepare(\"SELECT model_label_ru,manufacturer_label_en,manufacturer_qid FROM vehicle_model_entities WHERE model_qid=? LIMIT 1\").get(row.model_qid);",
    "      const dates=db.prepare(\"SELECT property_id,date_value,source_binding_index,source_binding_sha256 FROM series_member_date_statements WHERE member_qid=? AND model_qid=? ORDER BY property_id,date_value\").all(row.member_qid,row.model_qid);",
    "      return { memberQid:row.member_qid,modelQid:row.model_qid,manufacturerQid:row.manufacturer_qid,memberLabelEn:row.member_label_en,memberLabelRu:row.member_label_ru,modelLabelEn:row.model_label_en,modelLabelRu:parent?.model_label_ru||null,manufacturerLabelEn:parent?.manufacturer_label_en||null,memberUrl:\"https://www.wikidata.org/wiki/\"+encodeURIComponent(row.member_qid),modelUrl:\"https://www.wikidata.org/wiki/\"+encodeURIComponent(row.model_qid),relationProperties:JSON.parse(row.relation_properties_json),memberTypeQids:JSON.parse(row.member_type_qids_json),memberManufacturerQids:JSON.parse(row.member_manufacturer_qids_json),manufacturerRelationStatus:row.manufacturer_relation_status,startDates:JSON.parse(row.start_dates_json),endDates:JSON.parse(row.end_dates_json),inceptionDates:JSON.parse(row.inception_dates_json),dissolutionDates:JSON.parse(row.dissolution_dates_json),seriesOrdinals:JSON.parse(row.series_ordinals_json),dateStatements:dates.map((item)=>({propertyId:item.property_id,dateValue:item.date_value,sourceBindingIndex:item.source_binding_index,sourceBindingSha256:item.source_binding_sha256})),sourceBindingIndexes:JSON.parse(row.source_binding_indexes_json),sourceBindingSha256s:JSON.parse(row.source_binding_sha256s_json),sourceBindingCount:JSON.parse(row.source_binding_indexes_json).length,sourceRecordSha256:row.source_record_sha256,sourceRevision:row.source_revision,sourceSnapshotSha256:row.source_snapshot_sha256,sourceQuerySha256:row.source_query_sha256,databaseSha256:summary.databaseSha256,sourceManifestSha256:summary.sourceManifestSha256,sourceUrl:PACKS.wikidataGenerations.sourceUrl,sourceLicense:\"CC0-1.0\",marketScope:\"UNKNOWN\",applicabilityPrecision:\"series_member_candidate\",reviewStatus:\"candidate\",generationVerified:false,exactVehicleFitment:false,engineCodeFitment:false,transmissionCodeFitment:false,ecuFitment:false,dtcFitment:false,repairProcedureFitment:false,diagnosticExecutionAllowed:false,productionYearsInferred:false,warning:\"P179/P527 series-member candidate only; not a verified generation. Date statements are not production-year ranges. No Russian/EAEU or exact technical fitment.\" };",
    "    });",
    "  } finally { db.close(); parentDb.close(); }",
    "}"
  ].join("\n");
  if (!db.includes("function getWikidataGenerationSummary(")) {
    const exportIndex = db.lastIndexOf("\nmodule.exports");
    if (exportIndex < 0) fail("local research export block missing");
    db = db.slice(0, exportIndex) + "\n" + functions + "\n" + db.slice(exportIndex);
  }
  if (!db.includes("  getWikidataGenerationSummary,")) {
    db = exact(db, "  searchWikidataCandidates,\n  validateQuery,", "  searchWikidataCandidates,\n  getWikidataGenerationSummary,\n  searchWikidataGenerationCandidates,\n  validateQuery,", "generation DB exports");
  }
  writeText(dbPath, db);

  let types = readText(typesPath);
  if (!types.includes("getWikidataGenerationSummary")) {
    types += "\nexport function getWikidataGenerationSummary(root?: string): Record<string, unknown>;\n";
    types += "export function searchWikidataGenerationCandidates(query: string, limit?: number, root?: string): Array<Record<string, unknown>>;\n";
    writeText(typesPath, types);
  }

  let route = readText(routePath);
  route = exact(route,
    '    else if (dataset === "wikidata") rows = localResearch.searchWikidataCandidates(query, limit);',
    '    else if (dataset === "wikidata") rows = localResearch.searchWikidataCandidates(query, limit);\n    else if (dataset === "wikidata-generations-summary") summary = localResearch.getWikidataGenerationSummary();\n    else if (dataset === "wikidata-generations") rows = localResearch.searchWikidataGenerationCandidates(query, limit);',
    "generation API route");
  writeText(routePath, route);

  let ui = readText(uiPath);
  const dataset = ui.match(/type Dataset = ([^;]+);/);
  if (!dataset) fail("Research UI Dataset type missing");
  if (!dataset[1].includes('"wikidata-generations"')) ui = ui.replace(dataset[0], "type Dataset = " + dataset[1] + ' | "wikidata-generations";');
  if (!ui.includes("type WikidataGenerationRow")) {
    const rowType = [
      "type WikidataGenerationSummary = {",
      "  counts: { memberEntities: number; modelMemberLinks: number; sourceBindings: number; modelsWithMembers: number; manufacturers: number; russianLabels: number; dateStatements: number };",
      "  marketScope: string; applicabilityPrecision: string; reviewStatus: string; generationVerified: boolean;",
      "  exactVehicleFitment: boolean; diagnosticExecutionAllowed: boolean; sourceSnapshotSha256: string;",
      "  sourceQuerySha256: string; databaseSha256: string; sourceManifestSha256: string; note: string;",
      "};",
      "type WikidataGenerationRow = {",
      "  memberQid: string; modelQid: string; manufacturerQid: string | null;",
      "  memberLabelEn: string; memberLabelRu: string | null; modelLabelEn: string; modelLabelRu: string | null;",
      "  manufacturerLabelEn: string | null; memberUrl: string; modelUrl: string;",
      "  relationProperties: string[]; memberTypeQids: string[]; memberManufacturerQids: string[];",
      "  manufacturerRelationStatus: string; seriesOrdinals: string[];",
      "  dateStatements: Array<{ propertyId: string; dateValue: string; sourceBindingIndex: number; sourceBindingSha256: string }>;",
      "  sourceBindingIndexes: number[]; sourceBindingSha256s: string[]; sourceBindingCount: number;",
      "  sourceRecordSha256: string; sourceRevision: string; sourceSnapshotSha256: string; sourceQuerySha256: string;",
      "  databaseSha256: string; sourceManifestSha256: string; sourceUrl: string; sourceLicense: string;",
      "  marketScope: string; applicabilityPrecision: string; reviewStatus: string;",
      "  generationVerified: boolean; exactVehicleFitment: boolean; engineCodeFitment: boolean; transmissionCodeFitment: boolean;",
      "  ecuFitment: boolean; dtcFitment: boolean; repairProcedureFitment: boolean; diagnosticExecutionAllowed: boolean; productionYearsInferred: boolean; warning: string;",
      "};"
    ].join("\n");
    ui = ui.replace(dataset[0], dataset[0] + "\n" + rowType);
  }
  if (!ui.includes("wikidataGenerationSummary")) {
    const stateAnchor = '  const [genericGuidanceSummary, setGenericGuidanceSummary] = useState<GenericGuidanceSummary | null>(null);';
    ui = exact(ui, stateAnchor, stateAnchor + '\n  const [wikidataGenerationSummary, setWikidataGenerationSummary] = useState<WikidataGenerationSummary | null>(null);', "generation summary state");
  }
  if (!ui.includes('dataset !== "wikidata-generations"')) {
    const genericIndex = ui.indexOf("generic-guidance-summary");
    const effectEnd = ui.indexOf("  }, [dataset]);", genericIndex);
    if (genericIndex < 0 || effectEnd < 0) fail("Generic guidance summary effect missing");
    const insertAt = effectEnd + "  }, [dataset]);".length;
    const effect = [
      "",
      "  useEffect(() => {",
      '    if (dataset !== "wikidata-generations") return;',
      "    let active = true;",
      '    fetch("/api/local-research?dataset=wikidata-generations-summary")',
      "      .then((response) => response.json())",
      "      .then((payload) => { if (active && payload?.ok) setWikidataGenerationSummary(payload.summary); })",
      "      .catch(() => { if (active) setWikidataGenerationSummary(null); });",
      "    return () => { active = false; };",
      "  }, [dataset]);"
    ].join("\n");
    ui = ui.slice(0, insertAt) + effect + ui.slice(insertAt);
  }
  if (!ui.includes('id: "wikidata-generations"')) {
    const anchor = '  { id: "wikidata", label: "Wikidata · модели VAG", hint: "CC0 · кандидаты идентичности · рынок UNKNOWN" },\n';
    ui = exact(ui, anchor, anchor + '  { id: "wikidata-generations", label: "Поколения · кандидаты", hint: "P179/P527 · CC0 · рынок UNKNOWN" },\n', "generation research tab");
  }
  if (!ui.includes('dataset === "wikidata-generations" ?')) {
    const anchor = ': dataset === "wikidata" ? "Марка или модель… например Golf" :';
    ui = exact(ui, anchor, ': dataset === "wikidata-generations" ? "Модель, серия или QID… например Octavia" : ' + anchor, "generation search placeholder");
  }
  if (!ui.includes("Кандидаты серий Wikidata")) {
    const anchor = '      <article className="research-stat"><small>Модели Wikidata</small>';
    const index = ui.indexOf(anchor);
    if (index < 0) fail("Wikidata stats card anchor missing");
    const end = ui.indexOf("\n", index);
    ui = ui.slice(0, end + 1) + '      <article className="research-stat"><small>Кандидаты серий Wikidata</small><strong>{formatNumber(wikidataGenerationSummary?.counts?.memberEntities)}</strong><span>{formatNumber(wikidataGenerationSummary?.counts?.modelMemberLinks)} связей P179/P527 · CC0 · рынок UNKNOWN</span></article>\n' + ui.slice(end + 1);
  }
  if (!ui.includes("P179/P527 — только кандидаты серий")) {
    const anchor = '      <p>Wikidata добавляет только структурированные названия моделей и производителей.';
    const index = ui.indexOf(anchor);
    if (index < 0) fail("Wikidata boundary note anchor missing");
    const end = ui.indexOf("</p>", index) + 4;
    const note = '\n      <p>P179/P527 — только кандидаты серий, а не подтверждённые поколения. Рынок UNKNOWN; даты — исходные утверждения, не годы выпуска. Нет точной применимости к автомобилю, двигателю, КПП, ECU, DTC или ремонтным данным.</p>';
    ui = ui.slice(0, end) + note + ui.slice(end);
  }
  if (!ui.includes('dataset === "wikidata-generations" && rows.map')) {
    const anchor = '      {dataset === "wikidata" && rows.map((row) => <article className="research-result"';
    const index = ui.indexOf(anchor);
    if (index < 0) fail("Wikidata result card anchor missing");
    const card = [
      '      {dataset === "wikidata-generations" && (rows as unknown as WikidataGenerationRow[]).map((row) => <article className="research-result" key={row.memberQid + "-" + row.modelQid}>',
      '        <div className="research-result-top"><div><small>WIKIDATA SERIES MEMBER · CC0 1.0</small><h3>{row.memberLabelEn}{row.memberLabelRu ? " · " + row.memberLabelRu : ""}</h3></div><span className="research-candidate">UNVERIFIED CANDIDATE</span></div>',
      '        <div className="research-data-grid"><div><small>Parent model</small><b>{row.modelLabelEn} · {row.modelQid}</b></div><div><small>Member QID</small><b>{row.memberQid}</b></div><div><small>Relations</small><b>{row.relationProperties.join(", ")}</b></div><div><small>Manufacturer relation</small><b>{row.manufacturerLabelEn || row.manufacturerQid || "unknown"} · {row.manufacturerRelationStatus}</b></div><div><small>Raw date statements</small><b>{row.dateStatements.map((item) => item.propertyId + "=" + item.dateValue).join(" · ") || "none"}</b></div><div><small>Series ordinals / member types</small><b>{row.seriesOrdinals.join(", ") || "none"} · {row.memberTypeQids.join(", ")}</b></div></div>',
      '        <div className="research-warning-line">{row.warning} Market: {row.marketScope}; applicability: {row.applicabilityPrecision}; review: {row.reviewStatus}.</div>',
      '        <div className="research-source"><span>Revision {row.sourceRevision} · record SHA {String(row.sourceRecordSha256).slice(0,12)}… · snapshot SHA {String(row.sourceSnapshotSha256).slice(0,12)}… · query SHA {String(row.sourceQuerySha256).slice(0,12)}… · DB SHA {String(row.databaseSha256).slice(0,12)}… · manifest SHA {String(row.sourceManifestSha256).slice(0,12)}…</span><a href={row.memberUrl} target="_blank" rel="noopener noreferrer">Wikidata member</a> · <a href={row.modelUrl} target="_blank" rel="noopener noreferrer">model</a></div>',
      '      </article>)}',
      ''
    ].join("\n");
    ui = ui.slice(0, index) + card + ui.slice(index);
  }
  if (!ui.includes("Wikidata generation candidates — CC0-1.0")) {
    const anchor = "Wikidata structured data — CC0 1.0 Universal";
    const index = ui.indexOf(anchor);
    if (index >= 0) {
      const end = ui.indexOf("</p>", index) + 4;
      ui = ui.slice(0, end) + '\n      <p>Wikidata generation candidates — CC0-1.0. Атрибуция рекомендуется, но не обязательна; только структурированные утверждения, не статьи, изображения, логотипы или OEM-материалы.</p>' + ui.slice(end);
    }
  }
  writeText(uiPath, ui);

  let dbTest = readText(dbTestPath);
  if (!dbTest.includes("searchWikidataGenerationCandidates")) {
    dbTest += [
      "",
      'test("Wikidata series-member candidates remain candidate-only and preserve parent/source provenance", () => {',
      "  const summary = local.getWikidataGenerationSummary(root);",
      '  assert.equal(summary.license, "CC0-1.0"); assert.equal(summary.marketScope, "UNKNOWN");',
      '  assert.equal(summary.applicabilityPrecision, "series_member_candidate"); assert.equal(summary.generationVerified, false);',
      '  assert.equal(summary.exactVehicleFitment, false); assert.equal(summary.diagnosticExecutionAllowed, false);',
      '  assert.deepEqual(summary.counts, { memberEntities: 9, modelMemberLinks: 10, sourceBindings: 14, modelsWithMembers: 6, manufacturers: 3, russianLabels: 5, dateStatements: 2 });',
      '  const rows = local.searchWikidataGenerationCandidates("Octavia", 10, root); assert.ok(rows.length > 0);',
      '  assert.ok(rows.every((row) => row.marketScope === "UNKNOWN" && row.generationVerified === false && row.exactVehicleFitment === false && row.engineCodeFitment === false && row.transmissionCodeFitment === false && row.ecuFitment === false && row.dtcFitment === false && row.repairProcedureFitment === false && row.diagnosticExecutionAllowed === false && row.productionYearsInferred === false));',
      '  assert.deepEqual(local.searchWikidataGenerationCandidates("%%", 25, root), []);',
      "});",
      ""
    ].join("\n");
    writeText(dbTestPath, dbTest);
  }
  let packTest = readText(packTestPath);
  if (!packTest.includes("wikidata_vag_generation_candidates")) {
    const anchor = '  assert.deepEqual(result.wikidata_vag_taxonomy, { models: 376, sourceBindings: 376, manufacturers: 5, russianLabels: 171, dateStatements: 21 });';
    const addition = anchor + '\n  assert.deepEqual(result.wikidata_vag_generation_candidates, { memberEntities: 9, modelMemberLinks: 10, sourceBindings: 14, modelsWithMembers: 6, manufacturers: 3, russianLabels: 5, dateStatements: 2 });';
    packTest = exact(packTest, anchor, addition, "generation candidate pack test assertion");
    writeText(packTestPath, packTest);
  }
  let uiTest = readText(uiTestPath);
  if (!uiTest.includes("P179/P527 — только кандидаты серий")) {
    uiTest += [
      "",
      'test("Wikidata series-member UI labels candidates as unverified and non-actionable", () => {',
      '  assert.match(component, /Поколения · кандидаты/);',
      '  assert.match(component, /P179\\/P527 — только кандидаты серий/);',
      '  assert.match(component, /series_member_candidate/);',
      '  assert.match(component, /diagnosticExecutionAllowed/);',
      '  const route = fs.readFileSync(path.join(__dirname, "..", "app", "api", "local-research", "route.ts"), "utf8");',
      '  assert.match(route, /dataset === "wikidata-generations"/);',
      "});",
      ""
    ].join("\n");
    writeText(uiTestPath, uiTest);
  }

  let verifier = readText(verifierPath);
  verifier = verifier.replace(/manifest\.packs\.length\s*===\s*\d+/, "manifest.packs.length === 9");
  verifier = verifier.replace(/Expected eight separately licensed research packs/g, "Expected nine separately licensed research packs");
  if (!verifier.includes("wikidata-vag-generation-candidates-cc0")) {
    const anchor = '  const wikidata = byId["wikidata-vag-model-taxonomy-cc0"];\n';
    verifier = exact(verifier, anchor, anchor + '  const wikidataGenerations = byId["wikidata-vag-generation-candidates-cc0"];\n', "generation verifier pack lookup");
    verifier = verifier.replace('  const wikidataGenerations = byId["wikidata-vag-generation-candidates-cc0"];\n', '  const wikidataGenerations = byId["wikidata-vag-generation-candidates-cc0"];\n  assert(wikidataGenerations, "Wikidata generation candidate pack must be registered");\n');
    const summaryAnchor = '  const wikidataSummary = localResearch.getResearchSummary(RESEARCH).packs.find((pack) => pack.id === "wikidata-vag-model-taxonomy-cc0");';
    if (verifier.includes(summaryAnchor)) {
      verifier = verifier.replace(summaryAnchor, summaryAnchor + '\n  const wikidataGenerationSummary = localResearch.getWikidataGenerationSummary(RESEARCH);');
      verifier = verifier.replace('  assert(wikidataSummary &&', '  assert(wikidataGenerationSummary.counts.memberEntities === 9 && wikidataGenerationSummary.generationVerified === false, "Wikidata generation candidate runtime verification failed");\n  assert(wikidataSummary &&');
      verifier = verifier.replace('      wikidata_vag_taxonomy: wikidataSummary.counts,', '      wikidata_vag_taxonomy: wikidataSummary.counts,\n      wikidata_vag_generation_candidates: wikidataGenerationSummary.counts,');
    }
  }
  writeText(verifierPath, verifier);

  let lifecycle = readText(lifecyclePath);
  if (!lifecycle.includes("wikidata-generations-summary")) {
    const anchor = '  # generic_repair_guidance is a separate local SQLite pack and must remain readable with external network blocked.';
    const index = lifecycle.indexOf(anchor);
    if (index < 0) fail("Lifecycle generic offline research check anchor missing");
    const checks = [
      '  $generationSummary = Invoke-RestMethod -Uri "$baseUrl/api/local-research?dataset=wikidata-generations-summary" -TimeoutSec 20',
      '  if ($generationSummary.summary.marketScope -ne "UNKNOWN" -or $generationSummary.summary.applicabilityPrecision -ne "series_member_candidate" -or $generationSummary.summary.generationVerified -ne $false -or $generationSummary.summary.counts.memberEntities -ne 9) { throw "Wikidata generation candidate summary failed offline lifecycle verification." }',
      '  $generationRows = Invoke-RestMethod -Uri "$baseUrl/api/local-research?dataset=wikidata-generations&q=Octavia&limit=10" -TimeoutSec 20',
      '  if (@($generationRows.rows).Count -lt 1 -or @($generationRows.rows | Where-Object { $_.marketScope -ne "UNKNOWN" -or $_.generationVerified -ne $false -or $_.diagnosticExecutionAllowed -ne $false }).Count -gt 0) { throw "Wikidata generation candidate search crossed its candidate-only boundary." }',
      ''
    ].join("\n");
    lifecycle = lifecycle.slice(0, index) + checks + lifecycle.slice(index);
    writeText(lifecyclePath, lifecycle);
  }
}

function integrateGenerationPack(desktop, researchDir, packDir) {
  const verified = validatePack(packDir, researchDir);
  const updated = updateResearchManifest(researchDir, packDir, verified);
  const sourceManifestDir = path.join(desktop, "data/source-manifests");
  fs.mkdirSync(sourceManifestDir, { recursive: true });
  copyAs(ROOT, "data/source-manifests/wikidata-vag-generation-candidates.json", path.join(sourceManifestDir, "wikidata-vag-generation-candidates.json"));
  copyAs(ROOT, "data/source-manifests/vag-factory-source-register.json", path.join(sourceManifestDir, "vag-factory-source-register.json"));
  patchDesktopSource(desktop);
  const local = require(path.join(desktop, "lib/local-research-db.cjs"));
  const summary = local.getWikidataGenerationSummary(researchDir);
  const sample = local.searchWikidataGenerationCandidates("Octavia", 10, researchDir);
  if (summary.counts.memberEntities !== 9 || summary.marketScope !== "UNKNOWN" ||
      summary.generationVerified !== false || !sample.length ||
      sample.some((row) => row.marketScope !== "UNKNOWN" || row.generationVerified !== false || row.diagnosticExecutionAllowed !== false)) {
    fail("Final generation candidate desktop API smoke test failed");
  }
  const report = {
    status: "integrated_verified_series_member_candidates_only",
    pack_id: ID, snapshot_id: verified.manifest.snapshot_id,
    source_revision: verified.manifest.source_revision,
    source_snapshot_sha256: verified.manifest.source_snapshot_sha256,
    source_query_sha256: verified.manifest.source_query_sha256,
    database_sha256: verified.manifest.database_sha256,
    source_manifest_sha256: summary.sourceManifestSha256,
    artifact_sha256: ARTIFACT.artifactSha256,
    workflow_run_id: ARTIFACT.workflowRunId, artifact_id: ARTIFACT.artifactId,
    source_commit: ARTIFACT.sourceCommit, snapshot_commit: ARTIFACT.snapshotCommit,
    parent_model_pack: verified.manifest.parent_model_pack,
    counts: summary.counts, market_scope: "UNKNOWN",
    applicability_precision: "series_member_candidate",
    generation_verified: false, exact_vehicle_fitment: false,
    engine_code_fitment: false, transmission_code_fitment: false,
    ecu_fitment: false, dtc_fitment: false, repair_procedure_fitment: false,
    diagnostic_execution_allowed: false, production_years_inferred: false
  };
  writeJson(path.join(updated.targetDir, "desktop-integration-verification.json"), report);
  return report;
}

function main() {
  const args = parseArgs(process.argv);
  const desktop = path.resolve(ROOT, "desktop-source");
  if (!fs.existsSync(path.join(desktop, "package.json"))) fail("Desktop source is missing");
  const report = integrateGenerationPack(desktop, args.researchDir, args.packDir);
  process.stdout.write(JSON.stringify(report, null, 2) + "\n");
}
try { main(); } catch (error) { process.stderr.write("Wikidata generation candidate integration failed: " + (error.stack || error.message) + "\n"); process.exitCode = 1; }

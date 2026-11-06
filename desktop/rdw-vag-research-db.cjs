"use strict";

const fs = require("node:fs");
const path = require("node:path");
const crypto = require("node:crypto");
const { DatabaseSync } = require("node:sqlite");

const PACK_ID = "rdw-vag-nl-eu-type-approval-research";
const SOURCE_ID = "rdw-eu-vag-type-approval-open-data-nl";
const SOURCE_URL = "https://data.overheid.nl/dataset/basisregistratie-voertuigen---rdw";
const LICENSE_URL = "https://creativecommons.org/publicdomain/zero/1.0/";
const EXPECTED_TABLES = [
  "approval_auxiliary_rows", "approval_scope", "engine_designation_candidates",
  "gearbox_classifications", "registration_observations", "source_file_artifacts",
  "source_registry", "source_rows"
].sort();
const EXPECTED_INDEXES = [
  "idx_registration_make_trade", "idx_registration_make", "idx_registration_trade_name",
  "idx_registration_scope", "idx_approval_number", "idx_approval_variant", "idx_approval_version",
  "idx_approval_revision", "idx_approval_exact_scope_key", "idx_engine_designation",
  "idx_engine_scope", "idx_gearbox_classification", "idx_gearbox_scope"
];
const DATASET_URLS = Object.freeze({
  registration: SOURCE_URL,
  tgk_base: SOURCE_URL,
  tgk_drive: SOURCE_URL,
  tgk_gearbox: SOURCE_URL,
  tgk_make: SOURCE_URL,
  tgk_trade_name: SOURCE_URL
});
const summaryCache = new Map();

function rootDir(explicitRoot) {
  return path.resolve(explicitRoot || process.env.VAG_TECH_PRO_RESEARCH_DIR || path.join(process.cwd(), "data", "research"));
}
function safeFile(root, relative) {
  if (typeof relative !== "string" || !relative || path.isAbsolute(relative) || relative.includes("\\")) throw new Error("Unsafe RDW pack path");
  const base = fs.realpathSync(root);
  const candidate = path.resolve(base, relative);
  const rel = path.relative(base, candidate);
  if (!rel || rel === ".." || rel.startsWith(".." + path.sep) || path.isAbsolute(rel)) throw new Error("RDW path escaped its root");
  const real = fs.realpathSync(candidate);
  const realRel = path.relative(base, real);
  if (!realRel || realRel === ".." || realRel.startsWith(".." + path.sep) || path.isAbsolute(realRel)) throw new Error("RDW symlink escaped its root");
  if (!fs.statSync(real).isFile()) throw new Error("RDW pack entry is not a regular file");
  return real;
}
function readJson(file) { return JSON.parse(fs.readFileSync(file, "utf8")); }
function hashFile(file) {
  const digest = crypto.createHash("sha256");
  const fd = fs.openSync(file, "r");
  const buffer = Buffer.allocUnsafe(1024 * 1024);
  try {
    let bytes;
    do {
      bytes = fs.readSync(fd, buffer, 0, buffer.length, null);
      if (bytes > 0) digest.update(buffer.subarray(0, bytes));
    } while (bytes > 0);
  } finally { fs.closeSync(fd); }
  return digest.digest("hex");
}
function verifyFile(root, entry, fileField, hashField) {
  if (typeof entry[fileField] !== "string" || !/^[a-f0-9]{64}$/.test(entry[hashField] || "")) throw new Error("RDW manifest missing " + fileField + "/" + hashField);
  const file = safeFile(root, entry[fileField]);
  if (hashFile(file) !== entry[hashField]) throw new Error("RDW provenance SHA-256 mismatch: " + fileField);
  return file;
}
function assert(condition, message) { if (!condition) throw new Error(message); }
function openReadOnly(file) {
  const db = new DatabaseSync(file, { readOnly: true });
  db.exec("PRAGMA query_only=ON; PRAGMA trusted_schema=OFF;");
  return db;
}
function count(db, table) {
  if (!EXPECTED_TABLES.includes(table)) throw new Error("Unexpected RDW table");
  return db.prepare('SELECT count(*) AS n FROM "' + table + '"').get().n;
}
function stableSnapshotEntries(sourceFiles) {
  const fields = [
    "dataset_id", "dataset_name", "source_revision", "sha256", "byte_size", "row_count",
    "source_columns_sha256", "required_columns_sha256", "query_spec_sha256"
  ];
  return sourceFiles.map((item) => Object.fromEntries(fields.map((key) => [key, item[key]])))
    .sort((a, b) => a.dataset_id.localeCompare(b.dataset_id));
}

function getRdwSummary(explicitRoot) {
  const root = rootDir(explicitRoot);
  const rootManifestFile = safeFile(root, "manifest.json");
  const rootStat = fs.statSync(rootManifestFile);
  const cacheKey = root + "|" + rootStat.mtimeMs + "|" + rootStat.size;
  if (summaryCache.has(cacheKey)) return summaryCache.get(cacheKey);

  const manifest = readJson(rootManifestFile);
  assert(manifest.schema_version === 1 && Array.isArray(manifest.packs), "Invalid desktop research manifest");
  const entry = manifest.packs.find((item) => item.id === PACK_ID);
  assert(entry, "RDW NL/EU research pack is missing");
  assert(
    entry.source_id === SOURCE_ID && entry.license === "CC0 1.0" &&
    entry.license_status === "approved_by_published_CC0_license" && entry.rights_status === "approved_by_published_CC0_license" &&
    JSON.stringify(entry.market_scope) === JSON.stringify(["NL"]) &&
    entry.production_import === false && entry.ru_eaeu_applicability === false &&
    entry.fitment_claim === false && entry.exact_vehicle_fitment === false &&
    entry.exact_engine_gearbox_pair === false && entry.repair_applicability === false &&
    entry.diagnostic_execution_allowed === false && entry.attribution_required === false &&
    entry.commercial_use_allowed === true && entry.display_allowed === true &&
    entry.cache_allowed === true && entry.redistribution_allowed === true,
    "RDW rights, license or NL-only research boundary failed"
  );

  const database = verifyFile(root, entry, "database", "database_sha256");
  const packManifestFile = verifyFile(root, entry, "pack_manifest_file", "pack_manifest_sha256");
  const sourceManifestFile = verifyFile(root, entry, "source_manifest_file", "source_manifest_sha256");
  const attributionFile = verifyFile(root, entry, "attribution_file", "attribution_sha256");
  const licenseFile = verifyFile(root, entry, "license_file", "license_sha256");
  const buildReportFile = verifyFile(root, entry, "build_report_file", "build_report_sha256");
  const integrationReportFile = verifyFile(root, entry, "desktop_integration_report_file", "desktop_integration_report_sha256");

  const pack = readJson(packManifestFile);
  const source = readJson(sourceManifestFile);
  const buildReport = readJson(buildReportFile);
  const integrationReport = readJson(integrationReportFile);
  const rights = source.rights || {};
  const policy = source.import_policy || {};
  const applicability = source.applicability_policy || {};
  const snapshot = source.snapshot || {};
  const attributionText = fs.readFileSync(attributionFile, "utf8");
  const licenseText = fs.readFileSync(licenseFile, "utf8");

  assert(
    pack.pack_id === PACK_ID && pack.status === "verified_research_only" && pack.source_id === SOURCE_ID &&
    JSON.stringify(pack.market_scope) === JSON.stringify(["NL"]) &&
    pack.source_manifest_sha256 === entry.source_manifest_sha256 &&
    pack.database && pack.database.sha256 === entry.database_sha256 &&
    pack.source_snapshot_sha256 === entry.source_snapshot_sha256 &&
    pack.exact_engine_gearbox_pair === false && pack.pair_table_created === false &&
    source.source_id === SOURCE_ID && JSON.stringify(source.market_scope) === JSON.stringify(["NL"]) &&
    source.source_snapshot_sha256 === entry.source_snapshot_sha256 &&
    snapshot.status === "filtered_research_snapshot_acquired" &&
    snapshot.source_snapshot_sha256 === entry.source_snapshot_sha256 &&
    source.data_ingested === false &&
    source.research_pack && source.research_pack.status === "verified_research_only" &&
    source.research_pack.production_import === false &&
    source.research_pack.ru_eaeu_applicability === false &&
    source.research_pack.exact_engine_gearbox_pair === false &&
    rights.rights_status === "approved_by_published_CC0_license" &&
    String(rights.data_license_status || "").includes("CC0 1.0") &&
    ["commercial_use_allowed", "display_allowed", "offline_cache_allowed", "bulk_reuse_allowed", "redistribution_allowed"].every((key) => rights[key] === true) &&
    policy.namespace === "separate_read_only_research_pack" &&
    policy.production_import === false && policy.ru_eaeu_applicability === false &&
    policy.never_store_registration_plate === true &&
    policy.never_store_vin_or_holder_data === true &&
    policy.never_cross_join_engine_and_gearbox === true &&
    applicability.individual_vehicle_fitment === false &&
    applicability.vin_fitment === false &&
    applicability.production_fitment === false &&
    applicability.exact_vag_engine_code === false &&
    applicability.exact_vag_gearbox_code === false &&
    applicability.exact_engine_gearbox_pair === false &&
    applicability.ru_eaeu_applicability === false &&
    applicability.ecu_dtc_repair_applicability === false &&
    String(rights.attribution || "").includes("RDW Open Data (Netherlands)") &&
    attributionText.includes("RDW Open Data (Netherlands)") &&
    attributionText.includes("CC0 1.0") &&
    licenseText.includes("CC0 1.0") &&
    buildReport.database_sha256 === entry.database_sha256 &&
    buildReport.source_snapshot_sha256 === entry.source_snapshot_sha256 &&
    buildReport.exact_engine_gearbox_pair_claim === false &&
    integrationReport.status === "integrated_verified_research_only" &&
    JSON.stringify(integrationReport.market_scope) === JSON.stringify(["NL"]) &&
    integrationReport.database_sha256 === entry.database_sha256 &&
    integrationReport.source_manifest_sha256 === entry.source_manifest_sha256 &&
    integrationReport.source_snapshot_sha256 === entry.source_snapshot_sha256 &&
    integrationReport.source_run_id === entry.source_run_id &&
    integrationReport.artifact_sha256 === entry.source_artifact_sha256,
    "RDW source manifest, license, attribution, snapshot or applicability policy failed"
  );

  assert(JSON.stringify(snapshot.source_files) === JSON.stringify(stableSnapshotEntries(pack.source_files || [])), "RDW pinned source file list differs from pack manifest");
  assert(JSON.stringify(snapshot.source_revision) === JSON.stringify(pack.source_revisions), "RDW source revisions differ from pinned source manifest");
  assert(JSON.stringify(pack.search_indexes) === JSON.stringify(EXPECTED_INDEXES), "RDW search-index manifest differs from reviewed schema");

  for (const item of pack.source_files) {
    const file = safeFile(path.dirname(packManifestFile), item.path);
    assert(hashFile(file) === item.sha256, "RDW source snapshot SHA-256 mismatch: " + item.dataset_name);
    assert(fs.statSync(file).size === item.byte_size, "RDW source snapshot byte-size mismatch: " + item.dataset_name);
  }

  const db = openReadOnly(database);
  let counts;
  try {
    const integrity = db.prepare("PRAGMA integrity_check").all();
    assert(integrity.length === 1 && Object.values(integrity[0])[0] === "ok", "RDW SQLite integrity check failed");
    assert(db.prepare("PRAGMA foreign_key_check").all().length === 0, "RDW SQLite foreign-key check failed");
    const tables = db.prepare("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name").all().map((row) => row.name).sort();
    assert(JSON.stringify(tables) === JSON.stringify(EXPECTED_TABLES), "RDW SQLite table set differs from reviewed schema");
    const indexes = db.prepare("SELECT name FROM sqlite_master WHERE type='index'").all().map((row) => row.name);
    assert(EXPECTED_INDEXES.every((name) => indexes.includes(name)), "RDW SQLite search indexes are incomplete");
    for (const table of tables) {
      const columns = db.prepare('PRAGMA table_info("' + table + '")').all().map((row) => row.name.toLowerCase());
      assert(!columns.some((name) => /(vin|kenteken|plate|holder|owner|address|personal)/.test(name)), "Forbidden identity field in RDW table " + table);
    }

    const registry = db.prepare("SELECT source_id,license_id,rights_status,market_scope,production_import,ru_eaeu_applicability,source_manifest_sha256,verification_status FROM source_registry").all();
    assert(
      registry.length === 1 && registry[0].source_id === SOURCE_ID &&
      registry[0].license_id === "CC0-1.0" &&
      registry[0].rights_status === rights.rights_status &&
      registry[0].market_scope === "NL" &&
      registry[0].production_import === 0 && registry[0].ru_eaeu_applicability === 0 &&
      registry[0].source_manifest_sha256 === entry.source_manifest_sha256 &&
      registry[0].verification_status === "rights_cleared_research_only_not_oem_fitment",
      "RDW SQLite source registry mismatch"
    );

    const sourceFiles = db.prepare("SELECT dataset_id,dataset_name,source_revision,source_snapshot_sha256,byte_size,row_count,source_columns_sha256,required_columns_sha256,query_spec_sha256 FROM source_file_artifacts ORDER BY dataset_id").all();
    assert(sourceFiles.length === 6 && count(db, "source_rows") === pack.counts.source_rows, "RDW source artifact/source row count mismatch");
    const expectedById = new Map(pack.source_files.map((item) => [item.dataset_id, item]));
    for (const item of sourceFiles) {
      const expected = expectedById.get(item.dataset_id);
      assert(
        expected && item.dataset_name === expected.dataset_name &&
        item.source_revision === expected.source_revision &&
        item.source_snapshot_sha256 === expected.sha256 &&
        item.byte_size === expected.byte_size && item.row_count === expected.row_count &&
        item.source_columns_sha256 === expected.source_columns_sha256 &&
        item.required_columns_sha256 === expected.required_columns_sha256 &&
        item.query_spec_sha256 === expected.query_spec_sha256,
        "RDW SQLite source file provenance mismatch: " + item.dataset_id
      );
    }

    const invalidScope = db.prepare(
      "SELECT (SELECT count(*) FROM approval_scope WHERE market_scope!='NL' OR exact_vehicle_fitment!=0 OR ru_eaeu_applicability!=0 OR model_year IS NOT NULL OR generation IS NOT NULL) + " +
      "(SELECT count(*) FROM registration_observations WHERE market_scope!='NL' OR verification_status!='rdw_registration_observation_not_vehicle_fitment') + " +
      "(SELECT count(*) FROM engine_designation_candidates WHERE market_scope!='NL' OR verification_status!='rdw_engine_designation_candidate_not_oem_confirmed') + " +
      "(SELECT count(*) FROM gearbox_classifications WHERE market_scope!='NL' OR verification_status!='rdw_approval_gearbox_classification_not_vag_code') + " +
      "(SELECT count(*) FROM source_rows WHERE market_scope!='NL') + " +
      "(SELECT count(*) FROM approval_auxiliary_rows a JOIN source_rows s USING(source_row_sha256) WHERE s.market_scope!='NL') AS n"
    ).get().n;
    const pairTables = db.prepare("SELECT count(*) AS n FROM sqlite_master WHERE type='table' AND lower(name) LIKE '%pair%'").get().n;
    assert(invalidScope === 0 && pairTables === 0, "RDW market/applicability/pair boundary failed");

    counts = {
      approvalScopes: count(db, "approval_scope"),
      registrationObservations: count(db, "registration_observations"),
      engineDesignationCandidates: count(db, "engine_designation_candidates"),
      gearboxClassifications: count(db, "gearbox_classifications"),
      auxiliaryRows: count(db, "approval_auxiliary_rows"),
      sourceRows: count(db, "source_rows"),
      sourceFiles: sourceFiles.length
    };
    const expectedCounts = {
      approvalScopes: pack.counts.approval_scopes,
      registrationObservations: pack.counts.registration_observations,
      engineDesignationCandidates: pack.counts.engine_candidates,
      gearboxClassifications: pack.counts.gearbox_classifications,
      auxiliaryRows: pack.counts.auxiliary_rows,
      sourceRows: pack.counts.source_rows,
      sourceFiles: pack.counts.source_files
    };
    for (const key of Object.keys(expectedCounts)) assert(counts[key] === expectedCounts[key], "RDW count mismatch: " + key);
  } finally { db.close(); }

  const summary = {
    id: PACK_ID, sourceId: SOURCE_ID, source: "RDW (Dienst Wegverkeer), Netherlands",
    sourceUrl: SOURCE_URL, license: "CC0 1.0", licenseUrl: LICENSE_URL,
    rightsStatus: rights.rights_status, attributionText: attributionText.trim(),
    marketScope: "NL", applicabilityPrecision: "exact_RDW_approval_variant_version_revision_scope",
    reviewStatus: "verified_research_only", productionImport: false, ruEaeuApplicability: false,
    exactVehicleFitment: false, exactEngineGearboxPair: false, repairApplicability: false,
    diagnosticExecutionAllowed: false, sourceRevisions: pack.source_revisions,
    sourceSnapshotSha256: pack.source_snapshot_sha256, databaseSha256: entry.database_sha256,
    sourceManifestSha256: entry.source_manifest_sha256, packManifestSha256: entry.pack_manifest_sha256,
    licenseSha256: entry.license_sha256, attributionSha256: entry.attribution_sha256,
    buildReportSha256: entry.build_report_sha256, integrationReportSha256: entry.desktop_integration_report_sha256,
    counts,
    warning: "Только NL/EU approval research. Engine designation — кандидат RDW, не подтверждённый заводской код VAG; gearbox classification — не код КПП VAG. Двигатель и КПП показаны отдельно и не образуют подтверждённую пару. Нет RU/ЕАЭС, model year, generation, VIN/vehicle fitment, ECU, DTC или ремонтной применимости."
  };
  summaryCache.set(cacheKey, summary);
  return summary;
}

function validateQuery(value) {
  const query = String(value ?? "").trim();
  if (query.length < 2) throw new TypeError("Для поиска нужно минимум два символа.");
  if (query.length > 100) throw new TypeError("Слишком длинный поисковый запрос.");
  return query;
}
function likePattern(query) { return query.replace(/[\\%_]/g, "\\$&") + "%"; }

function searchRdwApprovals(query, limit = 25, explicitRoot) {
  const q = validateQuery(query);
  const boundedLimit = Math.max(1, Math.min(50, Number.isInteger(Number(limit)) ? Number(limit) : 25));
  const summary = getRdwSummary(explicitRoot);
  const root = rootDir(explicitRoot);
  const manifest = readJson(safeFile(root, "manifest.json"));
  const entry = manifest.packs.find((item) => item.id === PACK_ID);
  const db = openReadOnly(safeFile(root, entry.database));
  try {
    const pattern = likePattern(q);
    const scopeRows = db.prepare(
      "WITH candidate_scopes AS (" +
      "SELECT scope_id FROM approval_scope WHERE type_approval_number LIKE ? ESCAPE '\\' OR variant LIKE ? ESCAPE '\\' OR version LIKE ? ESCAPE '\\' OR revision LIKE ? ESCAPE '\\' " +
      "UNION SELECT scope_id FROM registration_observations WHERE make LIKE ? ESCAPE '\\' OR trade_name LIKE ? ESCAPE '\\' " +
      "UNION SELECT scope_id FROM engine_designation_candidates WHERE engine_designation LIKE ? ESCAPE '\\' " +
      "UNION SELECT scope_id FROM gearbox_classifications WHERE gearbox_type_classification LIKE ? ESCAPE '\\'" +
      ") SELECT s.scope_id,s.type_approval_number,s.variant,s.version,s.revision,s.applicability_precision,s.verification_status " +
      "FROM approval_scope s JOIN candidate_scopes c ON c.scope_id=s.scope_id WHERE s.market_scope='NL' " +
      "ORDER BY s.type_approval_number,s.variant,s.version,s.revision LIMIT ?"
    ).all(...Array(8).fill(pattern), boundedLimit);

    const registrationStmt = db.prepare(
      "SELECT make,trade_name,vehicle_category,registration_count,source_row_sha256,applicability_precision,verification_status " +
      "FROM registration_observations WHERE scope_id=? ORDER BY registration_count DESC,make,trade_name LIMIT 3"
    );
    const engineStmt = db.prepare(
      "SELECT engine_designation,engine_type_approval_number,displacement_cc,cylinders,source_row_sha256,applicability_precision,verification_status " +
      "FROM engine_designation_candidates WHERE scope_id=? ORDER BY engine_designation,source_row_sha256 LIMIT 5"
    );
    const gearboxStmt = db.prepare(
      "SELECT gearbox_type_classification,source_row_sha256,applicability_precision,verification_status " +
      "FROM gearbox_classifications WHERE scope_id=? ORDER BY gearbox_type_classification,source_row_sha256 LIMIT 5"
    );
    const sourceFileStmt = db.prepare("SELECT dataset_name,source_revision,source_snapshot_sha256 FROM source_file_artifacts WHERE dataset_id=?");
    const sourceRowsStmt = db.prepare("SELECT dataset_id FROM source_rows WHERE source_row_sha256=?");
    const output = [];

    for (const scope of scopeRows) {
      const registrationObservations = registrationStmt.all(scope.scope_id).map((row) => {
        const datasetId = sourceRowsStmt.get(row.source_row_sha256)?.dataset_id;
        const file = datasetId ? sourceFileStmt.get(datasetId) : null;
        return {
          make: row.make, tradeName: row.trade_name, vehicleCategory: row.vehicle_category,
          registrationCount: row.registration_count, sourceRowSha256: row.source_row_sha256,
          sourceRevision: file?.source_revision || null, sourceFileSha256: file?.source_snapshot_sha256 || null,
          sourceUrl: DATASET_URLS[file?.dataset_name] || SOURCE_URL,
          verificationStatus: row.verification_status
        };
      });
      const engineDesignationCandidates = engineStmt.all(scope.scope_id).map((row) => {
        const datasetId = sourceRowsStmt.get(row.source_row_sha256)?.dataset_id;
        const file = datasetId ? sourceFileStmt.get(datasetId) : null;
        return {
          engineDesignation: row.engine_designation, engineTypeApprovalNumber: row.engine_type_approval_number,
          displacementCc: row.displacement_cc, cylinders: row.cylinders, sourceRowSha256: row.source_row_sha256,
          sourceRevision: file?.source_revision || null, sourceFileSha256: file?.source_snapshot_sha256 || null,
          sourceUrl: DATASET_URLS[file?.dataset_name] || SOURCE_URL,
          verificationStatus: row.verification_status
        };
      });
      const gearboxClassifications = gearboxStmt.all(scope.scope_id).map((row) => {
        const datasetId = sourceRowsStmt.get(row.source_row_sha256)?.dataset_id;
        const file = datasetId ? sourceFileStmt.get(datasetId) : null;
        return {
          gearboxTypeClassification: row.gearbox_type_classification, sourceRowSha256: row.source_row_sha256,
          sourceRevision: file?.source_revision || null, sourceFileSha256: file?.source_snapshot_sha256 || null,
          sourceUrl: DATASET_URLS[file?.dataset_name] || SOURCE_URL,
          verificationStatus: row.verification_status
        };
      });
      output.push({
        id: scope.scope_id, typeApprovalNumber: scope.type_approval_number,
        variant: scope.variant, version: scope.version, revision: scope.revision,
        exactScopeKey: {
          typeApprovalNumber: scope.type_approval_number, variant: scope.variant,
          version: scope.version, revision: scope.revision
        },
        applicabilityPrecision: scope.applicability_precision, reviewStatus: scope.verification_status,
        marketScope: "NL", registrationObservations, engineDesignationCandidates, gearboxClassifications,
        modelYear: null, generation: null, engineCode: null, gearboxCode: null,
        exactVehicleFitment: false, productionFitment: false, ruEaeuApplicability: false,
        exactEngineGearboxPair: false, repairApplicability: false, diagnosticExecutionAllowed: false,
        sourceRevision: Object.values(summary.sourceRevisions).join(";"),
        sourceSnapshotSha256: summary.sourceSnapshotSha256, databaseSha256: summary.databaseSha256,
        sourceManifestSha256: summary.sourceManifestSha256, marketWarning: summary.warning,
        warning: "Approval-scope research only. Engine and gearbox rows are separate source observations; their co-occurrence does not establish a pair. RDW engine designation is not a confirmed VAG engine code; gearbox classification is not a VAG gearbox code. No model-year, generation, RU/EAEU or repair applicability.",
        sourceUrl: SOURCE_URL
      });
    }
    return output;
  } finally { db.close(); }
}

function clearCache() { summaryCache.clear(); }
module.exports = { getRdwSummary, searchRdwApprovals, clearCache };

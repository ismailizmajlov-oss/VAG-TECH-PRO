"use strict";
const fs = require("node:fs");
const path = require("node:path");
const crypto = require("node:crypto");
const { DatabaseSync } = require("node:sqlite");

const PACK_ID = "rdw-vag-nl-eu-type-approval-research";
const SOURCE_ID = "rdw-eu-vag-type-approval-open-data-nl";
const MAKES = ["AUDI", "BENTLEY", "BUGATTI", "CUPRA", "LAMBORGHINI", "PORSCHE", "SEAT", "SKODA", "VOLKSWAGEN"];
const FORBIDDEN_TOKENS = ["kenteken", "vin", "houder", "tenaamstelling", "owner", "address", "postcode"];
const ATTRIBUTION = "Source: RDW Open Data (Netherlands), CC0 1.0. Attribution is provided as a courtesy.";
const WARNING = "NL/EU type-approval research only. This is not Russian/EAEU applicability, individual-vehicle fitment, a factory VAG engine/gearbox code, a verified engine/gearbox pair, an ECU reference, a DTC or a repair procedure.";

let cachedSummary = null;
let cachedSummaryKey = null;

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
function hashFile(file) {
  return crypto.createHash("sha256").update(fs.readFileSync(file)).digest("hex");
}
function readJson(file) { return JSON.parse(fs.readFileSync(file, "utf8")); }
function verifyFile(root, entry, fileField, hashField) {
  if (typeof entry[fileField] !== "string" || !/^[a-f0-9]{64}$/.test(entry[hashField] || "")) throw new Error("RDW manifest is missing " + fileField + "/" + hashField);
  const file = safeFile(root, entry[fileField]);
  if (hashFile(file) !== entry[hashField]) throw new Error("RDW provenance SHA-256 mismatch: " + fileField);
  return file;
}
function openReadOnly(file) {
  const db = new DatabaseSync(file, { readOnly: true });
  db.exec("PRAGMA query_only=ON; PRAGMA trusted_schema=OFF;");
  return db;
}
function rejectForbidden(value, location = "row") {
  if (Array.isArray(value)) {
    value.forEach((item, index) => rejectForbidden(item, location + "[" + index + "]"));
    return;
  }
  if (!value || typeof value !== "object") return;
  for (const [key, child] of Object.entries(value)) {
    const lower = key.toLowerCase();
    if (FORBIDDEN_TOKENS.some((token) => lower.includes(token))) throw new Error("Forbidden RDW field " + key + " at " + location);
    rejectForbidden(child, location + "." + key);
  }
}
function validateRights(source, pack) {
  const rights = source.rights || {};
  const policy = source.import_policy || {};
  if (source.source_id !== SOURCE_ID || source.publisher !== "RDW (Dienst Wegverkeer), Netherlands" ||
      JSON.stringify(source.market_scope) !== JSON.stringify(["NL"]) ||
      rights.rights_status !== "approved_by_published_CC0_license" ||
      !["commercial_use_allowed", "display_allowed", "offline_cache_allowed", "bulk_reuse_allowed", "redistribution_allowed"].every((key) => rights[key] === true) ||
      rights.attribution_required !== false || policy.namespace !== "separate_read_only_research_pack" ||
      policy.production_import !== false || policy.ru_eaeu_applicability !== false ||
      policy.never_store_registration_plate !== true || policy.never_store_vin_or_holder_data !== true ||
      policy.never_cross_join_engine_and_gearbox !== true ||
      policy.never_promote_rdW_motorcode_to_vag_engine_code_without_independent_oem_evidence !== true ||
      policy.never_promote_rdW_gearbox_classification_to_vag_gearbox_code !== true ||
      JSON.stringify(source.vehicle_scope?.makes) !== JSON.stringify(MAKES)) {
    throw new Error("RDW source manifest rights, market or data-boundary gate failed");
  }
  if (pack.pack_id !== PACK_ID || pack.status !== "verified_research_only" || pack.source_id !== SOURCE_ID ||
      JSON.stringify(pack.market_scope) !== JSON.stringify(["NL"]) ||
      pack.production_import !== false || pack.product_import_allowed !== false || pack.ru_eaeu_applicability !== false ||
      pack.exact_vehicle_fitment !== false || pack.individual_vehicle_fitment !== false ||
      pack.exact_vag_engine_code !== false || pack.exact_vag_gearbox_code !== false ||
      pack.exact_engine_gearbox_pair !== false || pack.pair_table_created !== false ||
      pack.model_year_inferred !== false || pack.generation_inferred !== false ||
      pack.diagnostic_execution_allowed !== false || pack.ecu_dtc_repair_applicability !== false) {
    throw new Error("RDW pack production/fitment/pairing boundary failed");
  }
}
function summaryKey(root, entry, databaseFile) {
  const stat = fs.statSync(databaseFile);
  const manifestStat = fs.statSync(safeFile(root, "manifest.json"));
  return [root, stat.size, stat.mtimeMs, manifestStat.mtimeMs, entry.database_sha256, entry.pack_manifest_sha256].join("|");
}
function getRdwSummary(explicitRoot) {
  const root = rootDir(explicitRoot);
  const desktopManifestFile = safeFile(root, "manifest.json");
  const desktopManifest = readJson(desktopManifestFile);
  if (desktopManifest.schema_version !== 1 || !Array.isArray(desktopManifest.packs)) throw new Error("Invalid desktop research manifest");
  const entry = desktopManifest.packs.find((item) => item.id === PACK_ID);
  if (!entry) throw new Error("RDW NL/EU research pack is missing");
  if (entry.source_id !== SOURCE_ID || entry.license !== "CC0-1.0" ||
      entry.license_status !== "approved_by_published_CC0_license" ||
      entry.rights_status !== "approved_by_published_CC0_license" ||
      JSON.stringify(entry.market_scope) !== JSON.stringify(["NL"]) ||
      entry.production_import !== false || entry.ru_eaeu_applicability !== false ||
      entry.exact_vehicle_fitment !== false || entry.exact_engine_gearbox_pair !== false ||
      entry.repair_applicability !== false || entry.diagnostic_execution_allowed !== false ||
      entry.attribution_required !== false || entry.redistribution_allowed !== true) {
    throw new Error("RDW root-manifest rights or NL-only boundary failed");
  }
  const databaseFile = verifyFile(root, entry, "database", "database_sha256");
  const key = summaryKey(root, entry, databaseFile);
  if (cachedSummary && cachedSummaryKey === key) return cachedSummary;

  const packManifestFile = verifyFile(root, entry, "pack_manifest_file", "pack_manifest_sha256");
  const sourceManifestFile = verifyFile(root, entry, "source_manifest_file", "source_manifest_sha256");
  const attributionFile = verifyFile(root, entry, "attribution_file", "attribution_sha256");
  const rightsFile = verifyFile(root, entry, "rights_file", "rights_sha256");
  const pack = readJson(packManifestFile);
  const source = readJson(sourceManifestFile);
  validateRights(source, pack);
  const attribution = fs.readFileSync(attributionFile, "utf8");
  const rightsText = fs.readFileSync(rightsFile, "utf8");
  if (!attribution.includes(ATTRIBUTION) || !rightsText.includes("CC0 1.0") ||
      pack.source_manifest_sha256 !== entry.source_manifest_sha256 ||
      pack.database?.sha256 !== entry.database_sha256 ||
      pack.database?.byte_size !== fs.statSync(databaseFile).size) {
    throw new Error("RDW attribution, source manifest or database provenance mismatch");
  }

  const products = source.data_products || {};
  const sourceFiles = pack.source_files || [];
  if (!Array.isArray(sourceFiles) || sourceFiles.length !== 6) throw new Error("RDW pack must include six source snapshot manifests");
  const expectedIds = new Set(["m9d7-ebf2", "4by9-ammk", "7rjk-eycs", "byxc-wwua", "kyri-nuah", "x5v3-sewk"]);
  const sourceRevisions = {};
  let snapshotAggregate = "";
  for (const item of sourceFiles) {
    if (!expectedIds.has(item.dataset_id) || !/^[a-f0-9]{64}$/.test(item.sha256 || "")) throw new Error("RDW source snapshot manifest is invalid");
    const file = safeFile(path.dirname(packManifestFile), item.path);
    if (hashFile(file) !== item.sha256 || fs.statSync(file).size !== item.byte_size) throw new Error("RDW source snapshot SHA-256 mismatch: " + item.dataset_id);
    const product = Object.values(products).find((value) => value.dataset_id === item.dataset_id);
    if (!product || product.catalog_license !== "CC0 1.0") throw new Error("RDW dataset license evidence mismatch: " + item.dataset_id);
    sourceRevisions[item.dataset_id] = item.source_revision;
    snapshotAggregate += item.dataset_id + ":" + item.sha256 + "\n";
  }
  const sourceSnapshotSha256 = crypto.createHash("sha256").update(snapshotAggregate).digest("hex");

  const db = openReadOnly(databaseFile);
  let counts;
  try {
    const integrity = db.prepare("PRAGMA integrity_check").all();
    if (integrity.length !== 1 || Object.values(integrity[0])[0] !== "ok" || db.prepare("PRAGMA foreign_key_check").all().length) {
      throw new Error("RDW SQLite integrity or foreign-key check failed");
    }
    const tables = new Set(db.prepare("SELECT name FROM sqlite_master WHERE type='table'").all().map((row) => row.name));
    if (tables.has("engine_gearbox_pairs") || [...tables].some((name) => name.toLowerCase().includes("pair"))) {
      throw new Error("RDW pack must not contain an engine/gearbox pair table");
    }
    counts = {
      sourceFiles: db.prepare("SELECT count(*) AS n FROM source_file_artifacts").get().n,
      approvalScopes: db.prepare("SELECT count(*) AS n FROM approval_scope").get().n,
      registrationObservations: db.prepare("SELECT count(*) AS n FROM registration_observations").get().n,
      engineCandidates: db.prepare("SELECT count(*) AS n FROM engine_designation_candidates").get().n,
      gearboxClassifications: db.prepare("SELECT count(*) AS n FROM gearbox_classifications").get().n,
      auxiliaryRows: db.prepare("SELECT count(*) AS n FROM approval_auxiliary_rows").get().n,
      sourceRows: db.prepare("SELECT count(*) AS n FROM source_rows").get().n
    };
    const expected = {
      source_files: counts.sourceFiles,
      approval_scopes: counts.approvalScopes,
      registration_observations: counts.registrationObservations,
      engine_candidates: counts.engineCandidates,
      gearbox_classifications: counts.gearboxClassifications,
      auxiliary_rows: counts.auxiliaryRows,
      source_rows: counts.sourceRows
    };
    if (JSON.stringify(expected) !== JSON.stringify(pack.counts)) throw new Error("RDW SQLite counts do not match pack manifest");
    const registryCount = db.prepare("SELECT count(*) AS n FROM source_registry").get().n;
    const invalidRegistry = db.prepare(
      "SELECT count(*) AS n FROM source_registry WHERE source_id<>? OR rights_status<>? OR market_scope<>'NL' OR production_import<>0 OR ru_eaeu_applicability<>0"
    ).get(SOURCE_ID, "approved_by_published_CC0_license").n;
    for (const item of sourceFiles) {
      const stored = db.prepare(
        "SELECT source_revision, source_snapshot_sha256, byte_size, row_count, required_columns_sha256 FROM source_file_artifacts WHERE dataset_id=?"
      ).get(item.dataset_id);
      if (!stored || stored.source_revision !== item.source_revision || stored.source_snapshot_sha256 !== item.sha256 ||
          stored.byte_size !== item.byte_size || stored.row_count !== item.row_count ||
          stored.required_columns_sha256 !== item.required_columns_sha256) {
        throw new Error("RDW SQLite source-file provenance mismatch: " + item.dataset_id);
      }
    }
    const invalidEngine = db.prepare(
      "SELECT count(*) AS n FROM engine_designation_candidates WHERE market_scope<>'NL' OR verification_status<>'rdw_engine_designation_candidate_not_oem_confirmed'"
    ).get().n;
    const invalidGearbox = db.prepare(
      "SELECT count(*) AS n FROM gearbox_classifications WHERE market_scope<>'NL' OR verification_status<>'rdw_approval_gearbox_classification_not_vag_code'"
    ).get().n;
    const invalidScope = db.prepare(
      "SELECT count(*) AS n FROM approval_scope WHERE market_scope<>'NL' OR model_year IS NOT NULL OR generation IS NOT NULL OR exact_vehicle_fitment<>0 OR ru_eaeu_applicability<>0"
    ).get().n;
    if (registryCount !== 1 || invalidRegistry !== 0 || invalidEngine !== 0 || invalidGearbox !== 0 || invalidScope !== 0) {
      throw new Error("RDW SQLite rights, market or applicability promotion detected");
    }
    for (const row of db.prepare("SELECT raw_json FROM source_rows").all()) rejectForbidden(JSON.parse(row.raw_json), "sqlite.source_rows");
  } finally {
    db.close();
  }

  const summary = {
    id: PACK_ID, sourceId: SOURCE_ID, source: "RDW (Dienst Wegverkeer), Netherlands",
    sourceUrl: products.registered_vehicle_identity.catalog_url,
    license: "CC0-1.0", rightsStatus: "approved_by_published_CC0_license",
    attributionText: attribution.trim(), marketScope: "NL",
    applicabilityPrecision: "RDW approval/variant/version/revision scope only",
    reviewStatus: "verified_research_only", productionImport: false, productImportAllowed: false,
    ruEaeuApplicability: false, exactVehicleFitment: false, exactEngineGearboxPair: false,
    repairApplicability: false, diagnosticExecutionAllowed: false,
    sourceRevisions, sourceSnapshotSha256, databaseSha256: entry.database_sha256,
    sourceManifestSha256: entry.source_manifest_sha256, packManifestSha256: entry.pack_manifest_sha256,
    attributionSha256: entry.attribution_sha256, rightsSha256: entry.rights_sha256,
    counts, warning: WARNING
  };
  cachedSummary = summary;
  cachedSummaryKey = key;
  return summary;
}
function validateQuery(value) {
  const query = String(value ?? "").trim();
  if (query.length < 2) throw new TypeError("Для поиска нужно минимум два символа.");
  if (query.length > 100) throw new TypeError("Слишком длинный поисковый запрос.");
  return query;
}
function likePattern(query) { return "%" + query.replace(/[\\%_]/g, "\\$&") + "%"; }
function sourceEvidence(db, datasetId, summary, sourceManifest) {
  const row = db.prepare("SELECT source_revision, source_snapshot_sha256 FROM source_file_artifacts WHERE dataset_id=?").get(datasetId);
  if (!row) throw new Error("RDW source-file evidence is missing: " + datasetId);
  const product = Object.values(sourceManifest.data_products).find((item) => item.dataset_id === datasetId);
  return {
    sourceDatasetId: datasetId, sourceRevision: row.source_revision,
    sourceSnapshotSha256: row.source_snapshot_sha256, sourceFileSha256: row.source_snapshot_sha256,
    sourceUrl: product?.catalog_url || null
  };
}
function searchRdwApprovals(query, limit = 25, explicitRoot) {
  const q = validateQuery(query);
  const boundedLimit = Math.max(1, Math.min(50, Number.isInteger(Number(limit)) ? Number(limit) : 25));
  const summary = getRdwSummary(explicitRoot);
  const root = rootDir(explicitRoot);
  const desktopManifest = readJson(safeFile(root, "manifest.json"));
  const entry = desktopManifest.packs.find((item) => item.id === PACK_ID);
  const packManifestFile = safeFile(root, entry.pack_manifest_file);
  const packRoot = path.dirname(packManifestFile);
  const sourceManifest = readJson(safeFile(packRoot, "rdw-eu-vag-type-approval-open-data.json"));
  const db = openReadOnly(safeFile(root, entry.database));
  try {
    const pattern = likePattern(q);
    const scopeRows = db.prepare(
      "SELECT DISTINCT a.scope_id, a.type_approval_number, a.variant, a.version, a.revision, a.market_scope, " +
      "a.applicability_precision, a.verification_status, r.make, r.trade_name, r.vehicle_category, r.registration_count, " +
      "r.source_row_sha256 FROM approval_scope a LEFT JOIN registration_observations r ON r.scope_id=a.scope_id " +
      "WHERE a.type_approval_number LIKE ? ESCAPE '\\' OR a.variant LIKE ? ESCAPE '\\' OR a.version LIKE ? ESCAPE '\\' " +
      "OR a.revision LIKE ? ESCAPE '\\' OR r.make LIKE ? ESCAPE '\\' OR r.trade_name LIKE ? ESCAPE '\\' " +
      "ORDER BY r.make, r.trade_name, a.type_approval_number LIMIT ?"
    ).all(pattern, pattern, pattern, pattern, pattern, pattern, boundedLimit);
    const engineRows = db.prepare(
      "SELECT DISTINCT e.source_row_sha256, e.scope_id, e.engine_designation, e.engine_type_approval_number, e.displacement_cc, e.cylinders, " +
      "a.type_approval_number, a.variant, a.version, a.revision, r.make, r.trade_name, e.market_scope, " +
      "e.applicability_precision, e.verification_status FROM engine_designation_candidates e " +
      "JOIN approval_scope a ON a.scope_id=e.scope_id LEFT JOIN registration_observations r ON r.scope_id=a.scope_id " +
      "WHERE e.engine_designation LIKE ? ESCAPE '\\' OR e.engine_type_approval_number LIKE ? ESCAPE '\\' " +
      "OR a.type_approval_number LIKE ? ESCAPE '\\' OR r.make LIKE ? ESCAPE '\\' OR r.trade_name LIKE ? ESCAPE '\\' " +
      "ORDER BY r.make, r.trade_name, a.type_approval_number LIMIT ?"
    ).all(pattern, pattern, pattern, pattern, pattern, boundedLimit);
    const gearboxRows = db.prepare(
      "SELECT DISTINCT g.source_row_sha256, g.scope_id, g.gearbox_type_classification, a.type_approval_number, a.variant, a.version, a.revision, " +
      "r.make, r.trade_name, g.market_scope, g.applicability_precision, g.verification_status FROM gearbox_classifications g " +
      "JOIN approval_scope a ON a.scope_id=g.scope_id LEFT JOIN registration_observations r ON r.scope_id=a.scope_id " +
      "WHERE g.gearbox_type_classification LIKE ? ESCAPE '\\' OR a.type_approval_number LIKE ? ESCAPE '\\' " +
      "OR r.make LIKE ? ESCAPE '\\' OR r.trade_name LIKE ? ESCAPE '\\' " +
      "ORDER BY r.make, r.trade_name, a.type_approval_number LIMIT ?"
    ).all(pattern, pattern, pattern, pattern, boundedLimit);

    const rows = [];
    for (const row of scopeRows) {
      const evidence = sourceEvidence(db, "m9d7-ebf2", summary, sourceManifest);
      rows.push({
        id: row.scope_id, recordKind: "approval_scope", make: row.make, tradeName: row.trade_name,
        approvalNumber: row.type_approval_number, variant: row.variant, version: row.version, revision: row.revision,
        vehicleCategory: row.vehicle_category, registrationCount: row.registration_count,
        marketScope: "NL", applicabilityPrecision: row.applicability_precision,
        verificationStatus: row.verification_status, exactVehicleFitment: false, ruEaeuApplicability: false,
        modelYear: null, generation: null, engineCode: null, gearboxCode: null,
        exactEngineGearboxPair: false, repairApplicability: false, diagnosticExecutionAllowed: false,
        sourceRecordSha256: row.source_row_sha256, databaseSha256: summary.databaseSha256,
        sourceManifestSha256: summary.sourceManifestSha256, packManifestSha256: summary.packManifestSha256,
        ...evidence, warning: "Наблюдение RDW по области одобрения; не подтверждает комплектацию отдельного автомобиля."
      });
    }
    for (const row of engineRows) {
      const evidence = sourceEvidence(db, "4by9-ammk", summary, sourceManifest);
      rows.push({
        id: row.source_row_sha256, recordKind: "engine_candidate", make: row.make, tradeName: row.trade_name,
        approvalNumber: row.typegoedkeuringsnummer || row.type_approval_number, variant: row.variant, version: row.version, revision: row.revision,
        engineDesignation: row.engine_designation, engineTypeApprovalNumber: row.engine_type_approval_number,
        displacementCc: row.displacement_cc, cylinders: row.cylinders, marketScope: "NL",
        applicabilityPrecision: row.applicability_precision, verificationStatus: row.verification_status,
        exactVehicleFitment: false, ruEaeuApplicability: false, modelYear: null, generation: null,
        engineCode: null, gearboxCode: null, factoryVagEngineCodeClaim: false, factoryVagGearboxCodeClaim: false,
        exactEngineGearboxPair: false, repairApplicability: false, diagnosticExecutionAllowed: false,
        sourceRecordSha256: row.source_row_sha256, databaseSha256: summary.databaseSha256,
        sourceManifestSha256: summary.sourceManifestSha256, packManifestSha256: summary.packManifestSha256,
        ...evidence, warning: "motorcode RDW — только кандидат обозначения двигателя; не OEM-подтверждённый код VAG и не связан с классификацией КПП."
      });
    }
    for (const row of gearboxRows) {
      const evidence = sourceEvidence(db, "7rjk-eycs", summary, sourceManifest);
      rows.push({
        id: row.source_row_sha256, recordKind: "gearbox_classification", make: row.make, tradeName: row.trade_name,
        approvalNumber: row.type_approval_number, variant: row.variant, version: row.version, revision: row.revision,
        gearboxTypeClassification: row.gearbox_type_classification, marketScope: "NL",
        applicabilityPrecision: row.applicability_precision, verificationStatus: row.verification_status,
        exactVehicleFitment: false, ruEaeuApplicability: false, modelYear: null, generation: null,
        engineCode: null, gearboxCode: null, factoryVagEngineCodeClaim: false, factoryVagGearboxCodeClaim: false,
        exactEngineGearboxPair: false, repairApplicability: false, diagnosticExecutionAllowed: false,
        sourceRecordSha256: row.source_row_sha256, databaseSha256: summary.databaseSha256,
        sourceManifestSha256: summary.sourceManifestSha256, packManifestSha256: summary.packManifestSha256,
        ...evidence, warning: "codetypeversnellingsbak RDW — классификация в одобрении; не VAG-код КПП и не связан с обозначением двигателя."
      });
    }
    return rows;
  } finally {
    db.close();
  }
}
function clearRdwCache() { cachedSummary = null; cachedSummaryKey = null; }

module.exports = { getRdwSummary, searchRdwApprovals, clearRdwCache };

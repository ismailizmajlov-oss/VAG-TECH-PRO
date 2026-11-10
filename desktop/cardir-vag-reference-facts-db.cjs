"use strict";

const fs = require("node:fs");
const path = require("node:path");
const crypto = require("node:crypto");
const { DatabaseSync } = require("node:sqlite");

const PACK_ID = "cardir-vag-owner-manual-facts-research";
const SOURCE_ID = "cardir-vag-owner-manual-facts-cc-by-4.0";
const SOURCE_URL = "https://cardir.ru/dannye/";
const LICENSE_ID = "CC-BY-4.0";
const EXPECTED_TABLES = ["brands", "facts", "models", "pack_metadata", "source_files", "source_registry"].sort();
const EXPECTED_INDEXES = ["idx_cardir_facts_brand_model", "idx_cardir_facts_parameter", "idx_cardir_facts_qualifier", "idx_cardir_facts_search"].sort();

function assert(condition, message) {
  if (!condition) throw new Error(message);
}
function rootDir(explicitRoot) {
  return path.resolve(explicitRoot || process.env.VAG_TECH_PRO_RESEARCH_DIR || path.join(process.cwd(), "data", "research"));
}
function safeFile(root, relative) {
  if (typeof relative !== "string" || !relative || path.isAbsolute(relative) || relative.includes("\\")) throw new Error("Unsafe CarDir pack path");
  const base = fs.realpathSync(root);
  const candidate = path.resolve(base, relative);
  const rel = path.relative(base, candidate);
  if (!rel || rel === ".." || rel.startsWith(".." + path.sep) || path.isAbsolute(rel)) throw new Error("CarDir path escaped its root");
  const real = fs.realpathSync(candidate);
  const realRel = path.relative(base, real);
  if (!realRel || realRel === ".." || realRel.startsWith(".." + path.sep) || path.isAbsolute(realRel)) throw new Error("CarDir symlink escaped its root");
  if (!fs.statSync(real).isFile()) throw new Error("CarDir pack entry is not a regular file");
  return real;
}
function readJson(file) {
  return JSON.parse(fs.readFileSync(file, "utf8").replace(/^\uFEFF/, ""));
}
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
  } finally {
    fs.closeSync(fd);
  }
  return digest.digest("hex");
}
function verifyFile(root, entry, fileField, hashField) {
  assert(typeof entry[fileField] === "string" && /^[a-f0-9]{64}$/.test(entry[hashField] || ""), "CarDir manifest missing " + fileField + "/" + hashField);
  const file = safeFile(root, entry[fileField]);
  assert(hashFile(file) === entry[hashField], "CarDir provenance SHA-256 mismatch: " + fileField);
  return file;
}
function openReadOnly(file) {
  const db = new DatabaseSync(file, { readOnly: true });
  db.exec("PRAGMA query_only=ON; PRAGMA trusted_schema=OFF;");
  return db;
}
function count(db, sql) {
  return db.prepare(sql).get().n;
}
function getCardirSummary(explicitRoot) {
  const root = rootDir(explicitRoot);
  const rootManifestFile = safeFile(root, "manifest.json");
  const rootManifest = readJson(rootManifestFile);
  assert(rootManifest.schema_version === 1 && Array.isArray(rootManifest.packs), "Invalid desktop research manifest");
  const entry = rootManifest.packs.find((item) => item.id === PACK_ID);
  assert(entry, "CarDir VAG owner-manual facts pack is missing");

  assert(
    entry.source_id === SOURCE_ID &&
    entry.license === "CC BY 4.0" &&
    entry.license_status === "approved_by_published_CC_BY_4_0" &&
    entry.rights_status === "approved_by_published_CC_BY_4_0" &&
    JSON.stringify(entry.market_scope) === JSON.stringify(["UNKNOWN"]) &&
    entry.applicability_precision === "model_and_raw_qualifier_text" &&
    entry.review_status === "verified_research_only" &&
    entry.research_pack_ingested === true &&
    entry.product_database_ingested === false &&
    entry.data_ingested === false &&
    entry.production_import === false &&
    entry.product_import_allowed === false &&
    entry.ru_eaeu_applicability === false &&
    entry.exact_vehicle_fitment === false &&
    entry.exact_engine_gearbox_pair === false &&
    entry.repair_procedure === false &&
    entry.ecu_fitment === false &&
    entry.dtc_fitment === false &&
    entry.source_file_included_in_desktop === false &&
    entry.commercial_use_allowed === true &&
    entry.display_allowed === true &&
    entry.cache_allowed === true &&
    entry.bulk_reuse_allowed === true &&
    entry.redistribution_allowed === true &&
    entry.attribution_required === true,
    "CarDir rights, license or research-only applicability boundary failed"
  );

  const databaseFile = verifyFile(root, entry, "database", "database_sha256");
  const packManifestFile = verifyFile(root, entry, "pack_manifest_file", "pack_manifest_sha256");
  const sourceManifestFile = verifyFile(root, entry, "source_manifest_file", "source_manifest_sha256");
  const attributionFile = verifyFile(root, entry, "attribution_file", "attribution_sha256");
  const licenseFile = verifyFile(root, entry, "license_file", "license_sha256");
  const buildReportFile = verifyFile(root, entry, "build_report_file", "build_report_sha256");
  const snapshotManifestFile = verifyFile(root, entry, "source_snapshot_manifest_file", "source_snapshot_manifest_sha256");
  const integrationReportFile = verifyFile(root, entry, "desktop_integration_report_file", "desktop_integration_report_sha256");

  const pack = readJson(packManifestFile);
  const source = readJson(sourceManifestFile);
  const snapshot = readJson(snapshotManifestFile);
  const buildReport = readJson(buildReportFile);
  const integrationReport = readJson(integrationReportFile);
  const rights = source.rights || {};
  const policy = source.applicability_policy || {};
  const importPolicy = source.import_policy || {};
  const attributionText = fs.readFileSync(attributionFile, "utf8");
  const licenseText = fs.readFileSync(licenseFile, "utf8");

  assert(
    pack.pack_id === PACK_ID &&
    pack.source_id === SOURCE_ID &&
    pack.status === "verified_research_only" &&
    pack.license.id === LICENSE_ID &&
    pack.source_manifest_sha256 === entry.source_manifest_sha256 &&
    pack.source_snapshot_sha256 === entry.source_snapshot_sha256 &&
    pack.database.sha256 === entry.database_sha256 &&
    pack.database.integrity_check === "ok" &&
    pack.database.foreign_key_violations === 0 &&
    pack.market_scope.includes("UNKNOWN") &&
    pack.publisher_verification_status === "publisher_verified" &&
    pack.technical_review_status === "not_independently_reviewed" &&
    pack.exact_engine_code_mapping === false &&
    pack.exact_gearbox_code_mapping === false &&
    pack.exact_engine_gearbox_pair === false &&
    pack.exact_vehicle_fitment === false &&
    pack.model_generation_inferred === false &&
    pack.model_year_inferred === false &&
    pack.ru_eaeu_applicability === false &&
    pack.ecu_fitment === false &&
    pack.dtc_fitment === false &&
    pack.repair_procedure === false &&
    pack.wiring_or_pinout === false &&
    source.source_id === SOURCE_ID &&
    source.data_revision === entry.source_revision &&
    source.snapshot.source_snapshot_sha256 === entry.source_snapshot_sha256 &&
    source.snapshot.status === "source_snapshot_acquired_schema_verified" &&
    policy.market_scope === "UNKNOWN" &&
    policy.exact_engine_gearbox_pair === false &&
    policy.ru_eaeu_applicability === false &&
    importPolicy.production_import === false &&
    importPolicy.product_import_allowed === false &&
    rights.rights_status === "approved_by_published_CC_BY_4_0" &&
    rights.license_id === LICENSE_ID &&
    rights.commercial_use_allowed === true &&
    rights.display_allowed === true &&
    rights.offline_cache_allowed === true &&
    rights.bulk_reuse_allowed === true &&
    rights.redistribution_allowed === true &&
    rights.attribution_required === true &&
    attributionText.includes("CarDir") &&
    attributionText.includes("CC BY 4.0") &&
    licenseText.includes("CC BY 4.0") &&
    buildReport.status === "verified_research_only" &&
    buildReport.database_sha256 === entry.database_sha256 &&
    buildReport.source_snapshot_sha256 === entry.source_snapshot_sha256 &&
    buildReport.exact_engine_gearbox_pair === false &&
    integrationReport.status === "integrated_verified_research_only" &&
    integrationReport.source_run_id === entry.source_run_id &&
    integrationReport.artifact_sha256 === entry.source_artifact_sha256 &&
    integrationReport.database_sha256 === entry.database_sha256 &&
    integrationReport.production_import === false &&
    integrationReport.product_import_allowed === false &&
    integrationReport.ru_eaeu_applicability === false &&
    integrationReport.exact_engine_gearbox_pair === false,
    "CarDir source manifest, rights, attribution, snapshot or applicability policy failed"
  );

  assert(snapshot.source_snapshot_sha256 === entry.source_snapshot_sha256, "CarDir source snapshot hash reference mismatch");
  assert(snapshot.source_file_bytes === entry.source_file_bytes, "CarDir source snapshot byte-size mismatch");
  assert(snapshot.source_row_count === entry.source_row_count, "CarDir source snapshot row-count mismatch");
  assert(snapshot.vag_row_count === entry.filtered_vag_row_count, "CarDir filtered VAG row-count mismatch");

  const db = openReadOnly(databaseFile);
  let counts;
  try {
    const integrity = db.prepare("PRAGMA integrity_check").all();
    assert(integrity.length === 1 && Object.values(integrity[0])[0] === "ok", "CarDir SQLite integrity_check failed");
    assert(db.prepare("PRAGMA foreign_key_check").all().length === 0, "CarDir SQLite foreign_key_check failed");
    const tables = db.prepare("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name").all().map((row) => row.name).sort();
    assert(JSON.stringify(tables) === JSON.stringify(EXPECTED_TABLES), "CarDir SQLite table set mismatch");
    const indexes = db.prepare("SELECT name FROM sqlite_master WHERE type='index'").all().map((row) => row.name).sort();
    assert(EXPECTED_INDEXES.every((name) => indexes.includes(name)), "CarDir SQLite search indexes incomplete");
    const registry = db.prepare("SELECT source_id,license_id,rights_status,market_scope,applicability_precision,research_pack_only,production_import,exact_engine_code,exact_gearbox_code,exact_engine_gearbox_pair,model_generation,model_year,ru_eaeu_applicability,ecu_fitment,dtc_fitment,repair_procedure FROM source_registry").get();
    assert(
      registry &&
      registry.source_id === SOURCE_ID &&
      registry.license_id === LICENSE_ID &&
      registry.rights_status === rights.rights_status &&
      registry.market_scope === "UNKNOWN" &&
      registry.applicability_precision === "model_and_raw_qualifier_text" &&
      registry.research_pack_only === 1 &&
      registry.production_import === 0 &&
      registry.exact_engine_code === 0 &&
      registry.exact_gearbox_code === 0 &&
      registry.exact_engine_gearbox_pair === 0 &&
      registry.model_generation === 0 &&
      registry.model_year === 0 &&
      registry.ru_eaeu_applicability === 0 &&
      registry.ecu_fitment === 0 &&
      registry.dtc_fitment === 0 &&
      registry.repair_procedure === 0,
      "CarDir SQLite source registry boundary failed"
    );
    const sourceFile = db.prepare("SELECT sha256,byte_size,source_row_count,filtered_vag_row_count FROM source_files").get();
    assert(
      sourceFile &&
      sourceFile.sha256 === entry.source_snapshot_sha256 &&
      sourceFile.byte_size === entry.source_file_bytes &&
      sourceFile.source_row_count === entry.source_row_count &&
      sourceFile.filtered_vag_row_count === entry.filtered_vag_row_count,
      "CarDir SQLite source-file registry mismatch"
    );
    const invalid = count(db, "SELECT count(*) AS n FROM facts WHERE source_id!='" + SOURCE_ID + "' OR publisher_verification_status!='publisher_verified' OR technical_review_status!='not_independently_reviewed' OR market_scope!='UNKNOWN' OR applicability_precision NOT IN ('model_level_only','model_and_raw_qualifier_text') OR model_generation IS NOT NULL OR model_year_from IS NOT NULL OR model_year_to IS NOT NULL OR engine_code IS NOT NULL OR transmission_code IS NOT NULL OR exact_engine_gearbox_pair!=0 OR production_fitment!=0 OR ecu_fitment!=0 OR dtc_fitment!=0 OR repair_procedure!=0");
    const badHashes = count(db, "SELECT count(*) AS n FROM facts WHERE length(source_row_sha256)!=64 OR source_row_sha256 GLOB '*[^0-9a-f]*'");
    assert(invalid === 0 && badHashes === 0, "CarDir fact rows crossed the research-only or provenance boundary");
    counts = {
      sourceRows: pack.counts.source_rows,
      vagFacts: count(db, "SELECT count(*) AS n FROM facts"),
      vagBrands: count(db, "SELECT count(*) AS n FROM brands"),
      vagModels: count(db, "SELECT count(*) AS n FROM models"),
      parameterKeys: count(db, "SELECT count(DISTINCT parameter_key) AS n FROM facts")
    };
    assert(counts.vagFacts === pack.counts.vag_facts, "CarDir fact count mismatch");
    assert(counts.vagBrands === pack.counts.vag_brands, "CarDir brand count mismatch");
    assert(counts.vagModels === pack.counts.vag_models, "CarDir model count mismatch");
    assert(counts.parameterKeys === pack.counts.parameter_keys, "CarDir parameter-key count mismatch");
    assert(pack.counts.vag_facts === 948 && pack.counts.vag_models === 26 && pack.counts.vag_brands === 5 && pack.counts.parameter_keys === 19, "CarDir pinned research counts changed");
  } finally {
    db.close();
  }

  return {
    packId: PACK_ID,
    counts,
    marketScope: "UNKNOWN",
    rightsStatus: rights.rights_status,
    attributionText: rights.attribution_text,
    sourceUrl: SOURCE_URL,
    license: "CC BY 4.0",
    licenseUrl: "https://creativecommons.org/licenses/by/4.0/",
    sourceRevision: entry.source_revision,
    sourceSnapshotSha256: entry.source_snapshot_sha256,
    databaseSha256: entry.database_sha256,
    sourceManifestSha256: entry.source_manifest_sha256,
    warning: "CarDir is a publisher-curated owner-manual fact dataset, not OEM workshop documentation. Рынок UNKNOWN; исходные условия не интерпретируются into exact model-year, generation, engine or gearbox applicability.",
    productionImport: false,
    productImportAllowed: false,
    ruEaeuApplicability: false,
    exactVehicleFitment: false,
    exactEngineGearboxPair: false,
    repairProcedure: false,
    ecuFitment: false,
    dtcFitment: false,
    sourceFileIncludedInDesktop: false,
    pack, databaseFile,
    databaseHash: hashFile(databaseFile),
    sourceManifestHash: hashFile(sourceManifestFile),
    packManifestHash: hashFile(packManifestFile),
    attributionHash: hashFile(attributionFile),
    licenseHash: hashFile(licenseFile),
    buildReportHash: hashFile(buildReportFile),
    snapshotManifestHash: hashFile(snapshotManifestFile),
    sourceSnapshotHash: entry.source_snapshot_sha256
  };
}
function normalizeQuery(value) {
  return String(value || "").normalize("NFKC").toLowerCase().trim();
}
function escapeLike(value) {
  return value.replace(/[\\%_]/g, "\\$&");
}
function searchCardirFacts(query, limit, explicitRoot) {
  const normalized = normalizeQuery(query);
  const take = Number(limit);
  if (normalized.length < 2) throw new TypeError("Для поиска CarDir нужно минимум два символа.");
  if (normalized.length > 200) throw new TypeError("Поисковый запрос CarDir слишком длинный.");
  if (!Number.isInteger(take) || take < 1 || take > 50) throw new TypeError("Лимит CarDir должен быть от 1 до 50.");
  const summary = getCardirSummary(explicitRoot);
  const root = rootDir(explicitRoot);
  const entry = readJson(safeFile(root, "manifest.json")).packs.find((item) => item.id === PACK_ID);
  const databaseFile = safeFile(root, entry.database);
  const db = openReadOnly(databaseFile);
  try {
    const pattern = "%" + escapeLike(normalized) + "%";
    const rows = db.prepare(
      "SELECT f.source_row_number AS sourceRowNumber,b.source_value AS brand,m.source_value AS model," +
      "f.parameter_key AS parameterKey,f.parameter_label_ru AS parameterLabelRu,f.qualifier_raw AS qualifier," +
      "f.value_raw AS value,f.unit_raw AS unit,f.source_title AS sourceTitle,f.source_page AS sourcePage," +
      "f.source_url AS sourceUrl,f.page_url AS pageUrl,f.verified_at AS verifiedAt," +
      "f.source_row_sha256 AS sourceRowSha256,f.publisher_verification_status AS publisherVerificationStatus," +
      "f.technical_review_status AS technicalReviewStatus,f.market_scope AS marketScope," +
      "f.applicability_precision AS applicabilityPrecision,f.model_generation AS modelGeneration," +
      "f.model_year_from AS modelYearFrom,f.model_year_to AS modelYearTo,f.engine_code AS engineCode," +
      "f.transmission_code AS transmissionCode,f.exact_engine_gearbox_pair AS exactEngineGearboxPair," +
      "f.production_fitment AS productionFitment,f.ecu_fitment AS ecuFitment,f.dtc_fitment AS dtcFitment," +
      "f.repair_procedure AS repairProcedure,f.raw_fields_json AS rawFieldsJson " +
      "FROM facts f JOIN brands b ON b.brand_id=f.brand_id JOIN models m ON m.model_id=f.model_id " +
      "WHERE f.search_text_folded LIKE ? ESCAPE '\\' ORDER BY b.source_value,m.source_value,f.parameter_key,f.source_row_number LIMIT ?"
    ).all(pattern, take);
    return rows.map((row) => ({
      ...row,
      sourceRevision: summary.sourceRevision,
      sourceSnapshotSha256: summary.sourceSnapshotSha256,
      sourceFileSha256: summary.sourceSnapshotSha256,
      databaseSha256: summary.databaseSha256,
      sourceManifestSha256: summary.sourceManifestSha256,
      license: summary.license,
      licenseUrl: summary.licenseUrl,
      attributionText: summary.attributionText,
      warning: "CarDir — опубликованные факты из руководств владельца, а не заводская ремонтная документация. Рынок UNKNOWN; условие показано как исходный текст; применимость к точной модификации, году, двигателю и КПП не подтверждена. Перед работой сверяйте первичное руководство конкретного автомобиля.",
      exactVehicleFitment: false,
      exactEngineGearboxPair: false,
      productionFitment: false,
      ruEaeuApplicability: false,
      ecuFitment: false,
      dtcFitment: false,
      repairProcedure: false
    }));
  } finally {
    db.close();
  }
}

module.exports = { getCardirSummary, searchCardirFacts, rootDir };

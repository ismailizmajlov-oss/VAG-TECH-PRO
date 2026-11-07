"use strict";

const fs = require("node:fs");
const path = require("node:path");
const crypto = require("node:crypto");
const { DatabaseSync } = require("node:sqlite");

const PACK_ID = "kba-de-vag-stock-research";
const SOURCE_ID = "kba-de-fz-hersteller-handelsnamen-pkw";
const SOURCE_URL = "https://www.govdata.de/suche/daten/fz-hersteller-handelsnamen-pkw?ids=638594fd-195a-4e03-b91c-f5ea2eacfa39";
const LICENSE_ID = "DL-DE-BY-2.0";
const LICENSE_URL = "https://www.govdata.de/dl-de/by-2-0";
const EXPECTED_TABLES = ["federal_states","manufacturers","pack_metadata","reference_dates","source_files","source_registry","stock_observations","trade_names","type_keys"].sort();
const EXPECTED_INDEXES = ["idx_kba_stock_manufacturer","idx_kba_stock_trade_name","idx_kba_stock_type_key","idx_kba_stock_report_date","idx_kba_stock_make_trade_date","idx_kba_stock_federal_state"];
const summaryCache = new Map();

function assert(condition, message) { if (!condition) throw new Error(message); }
function rootDir(explicitRoot) {
  return path.resolve(explicitRoot || process.env.VAG_TECH_PRO_RESEARCH_DIR || path.join(process.cwd(), "data", "research"));
}
function safeFile(root, relative) {
  if (typeof relative !== "string" || !relative || path.isAbsolute(relative) || relative.includes("\\")) throw new Error("Unsafe KBA pack path");
  const base = fs.realpathSync(root);
  const candidate = path.resolve(base, relative);
  const rel = path.relative(base, candidate);
  if (!rel || rel === ".." || rel.startsWith(".." + path.sep) || path.isAbsolute(rel)) throw new Error("KBA path escaped its root");
  const real = fs.realpathSync(candidate);
  const realRel = path.relative(base, real);
  if (!realRel || realRel === ".." || realRel.startsWith(".." + path.sep) || path.isAbsolute(realRel)) throw new Error("KBA symlink escaped its root");
  if (!fs.statSync(real).isFile()) throw new Error("KBA pack entry is not a regular file");
  return real;
}
function readJson(file) { return JSON.parse(fs.readFileSync(file, "utf8").replace(/^\uFEFF/, "")); }
function hashFile(file) {
  const digest = crypto.createHash("sha256");
  const fd = fs.openSync(file, "r");
  const buffer = Buffer.allocUnsafe(1024 * 1024);
  try {
    let bytes;
    do { bytes = fs.readSync(fd, buffer, 0, buffer.length, null); if (bytes > 0) digest.update(buffer.subarray(0, bytes)); } while (bytes > 0);
  } finally { fs.closeSync(fd); }
  return digest.digest("hex");
}
function verifyFile(root, entry, fileField, hashField) {
  assert(typeof entry[fileField] === "string" && /^[a-f0-9]{64}$/.test(entry[hashField] || ""), "KBA manifest missing " + fileField + "/" + hashField);
  const file = safeFile(root, entry[fileField]);
  assert(hashFile(file) === entry[hashField], "KBA provenance SHA-256 mismatch: " + fileField);
  return file;
}
function openReadOnly(file) {
  const db = new DatabaseSync(file, { readOnly: true });
  db.exec("PRAGMA query_only=ON; PRAGMA trusted_schema=OFF;");
  return db;
}
function getKbaSummary(explicitRoot) {
  const root = rootDir(explicitRoot);
  const rootManifestFile = safeFile(root, "manifest.json");
  const stat = fs.statSync(rootManifestFile);
  const cacheKey = root + "|" + stat.mtimeMs + "|" + stat.size;
  if (summaryCache.has(cacheKey)) return summaryCache.get(cacheKey);

  const rootManifest = readJson(rootManifestFile);
  assert(rootManifest.schema_version === 1 && Array.isArray(rootManifest.packs), "Invalid desktop research manifest");
  const entry = rootManifest.packs.find((item) => item.id === PACK_ID);
  assert(entry, "KBA DE VAG stock research pack is missing");
  assert(
    entry.source_id === SOURCE_ID && entry.license === LICENSE_ID &&
    entry.license_status === "approved_by_published_DL_DE_BY_2_0" &&
    entry.rights_status === "approved_by_published_DL_DE_BY_2_0" &&
    JSON.stringify(entry.market_scope) === JSON.stringify(["DE"]) &&
    entry.applicability_precision === "aggregate_stock_observation" &&
    entry.review_status === "verified_research_only" &&
    entry.production_import === false && entry.product_import_allowed === false &&
    entry.ru_eaeu_applicability === false && entry.fitment_claim === false &&
    entry.exact_vehicle_fitment === false && entry.exact_engine_gearbox_pair === false &&
    entry.repair_applicability === false && entry.diagnostic_execution_allowed === false &&
    entry.model_year_inferred === false && entry.generation_inferred === false &&
    entry.engine_codes_included === false && entry.gearbox_codes_included === false &&
    entry.ecu_fitment === false && entry.dtc_fitment === false &&
    entry.commercial_use_allowed === true && entry.display_allowed === true &&
    entry.cache_allowed === true && entry.bulk_reuse_allowed === true &&
    entry.redistribution_allowed === true && entry.attribution_required === true,
    "KBA rights, licence or DE-only aggregate-stock boundary failed"
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
  const snapshot = source.snapshot || {};
  const attributionText = fs.readFileSync(attributionFile, "utf8");
  const licenseText = fs.readFileSync(licenseFile, "utf8");

  assert(
    pack.pack_id === PACK_ID && pack.source_id === SOURCE_ID && pack.status === "verified_research_only" &&
    JSON.stringify(pack.market_scope) === JSON.stringify(["DE"]) &&
    pack.license === LICENSE_ID && pack.license_url === LICENSE_URL &&
    pack.source_manifest_sha256 === entry.source_manifest_sha256 &&
    pack.source_snapshot_sha256 === entry.source_snapshot_sha256 &&
    pack.database?.sha256 === entry.database_sha256 &&
    pack.exact_engine_gearbox_pair === false && pack.exact_vehicle_fitment === false &&
    pack.production_import === false && pack.product_import_allowed === false &&
    pack.ru_eaeu_applicability === false &&
    source.source_id === SOURCE_ID && source.data_ingested === false &&
    source.product_import_allowed === false &&
    snapshot.status === "source_snapshot_acquired_schema_verified" &&
    snapshot.source_snapshot_sha256 === entry.source_snapshot_sha256 &&
    rights.rights_status === "approved_by_published_DL_DE_BY_2_0" &&
    rights.commercial_use_allowed === true && rights.display_allowed === true &&
    rights.offline_cache_allowed === true && rights.bulk_reuse_allowed === true &&
    rights.redistribution_allowed === true && rights.attribution_required === true &&
    entry.source_snapshot_sha256 === pack.source_file?.sha256 &&
    entry.source_revision === pack.source_revision &&
    buildReport.database_sha256 === entry.database_sha256 &&
    buildReport.source_snapshot_sha256 === entry.source_snapshot_sha256 &&
    buildReport.exact_engine_gearbox_pair_claim === false &&
    integrationReport.status === "integrated_verified_research_only" &&
    integrationReport.market_scope === "DE" &&
    integrationReport.database_sha256 === entry.database_sha256 &&
    integrationReport.source_manifest_sha256 === entry.source_manifest_sha256 &&
    integrationReport.source_snapshot_sha256 === entry.source_snapshot_sha256 &&
    integrationReport.source_run_id === entry.source_run_id &&
    integrationReport.artifact_sha256 === entry.source_artifact_sha256,
    "KBA source manifest, licence, attribution, snapshot or applicability policy failed"
  );
  assert(attributionText.includes("Kraftfahrt-Bundesamt (KBA)") && attributionText.includes("DL-DE BY 2.0") && attributionText.includes(SOURCE_URL) && attributionText.includes("Modified data"), "KBA attribution/modified-data notice missing");
  assert(licenseText.includes("DL-DE BY 2.0") && licenseText.includes(LICENSE_URL), "KBA licence reference missing");

  const db = openReadOnly(database);
  let counts;
  try {
    const integrity = db.prepare("PRAGMA integrity_check").all();
    assert(integrity.length === 1 && Object.values(integrity[0])[0] === "ok", "KBA SQLite integrity_check failed");
    assert(db.prepare("PRAGMA foreign_key_check").all().length === 0, "KBA SQLite foreign_key_check failed");
    const tables = db.prepare("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name").all().map((row) => row.name).sort();
    assert(JSON.stringify(tables) === JSON.stringify(EXPECTED_TABLES), "KBA SQLite table set mismatch");
    const indexes = db.prepare("SELECT name FROM sqlite_master WHERE type='index'").all().map((row) => row.name);
    assert(EXPECTED_INDEXES.every((name) => indexes.includes(name)), "KBA SQLite search indexes incomplete");
    const views = db.prepare("SELECT name FROM sqlite_master WHERE type='view'").all().map((row) => row.name);
    assert(views.includes("v_stock_observations"), "KBA provenance view missing");
    const registry = db.prepare("SELECT source_id,license_id,rights_status,market_scope,applicability_precision,review_status,source_revision,source_manifest_sha256,source_snapshot_sha256,product_import_allowed,exact_engine_gearbox_pair,ru_eaeu_applicability FROM source_registry").get();
    assert(
      registry && registry.source_id === SOURCE_ID && registry.license_id === LICENSE_ID &&
      registry.rights_status === rights.rights_status && registry.market_scope === "DE" &&
      registry.applicability_precision === "aggregate_stock_observation" && registry.review_status === "research_only" &&
      registry.source_revision === entry.source_revision && registry.source_manifest_sha256 === entry.source_manifest_sha256 &&
      registry.source_snapshot_sha256 === entry.source_snapshot_sha256 &&
      registry.product_import_allowed === 0 && registry.exact_engine_gearbox_pair === 0 &&
      registry.ru_eaeu_applicability === 0,
      "KBA SQLite source registry mismatch"
    );
    const fileRow = db.prepare("SELECT source_id,sha256,byte_size,source_row_count,filtered_row_count,columns_sha256 FROM source_files").get();
    assert(
      fileRow && fileRow.source_id === SOURCE_ID && fileRow.sha256 === entry.source_snapshot_sha256 &&
      fileRow.byte_size === pack.source_file.byte_size && fileRow.source_row_count === pack.counts.source_rows &&
      fileRow.filtered_row_count === pack.counts.vag_stock_observations,
      "KBA SQLite source-file registry mismatch"
    );
    const invalid = db.prepare(
      "SELECT count(*) AS n FROM v_stock_observations WHERE market_scope!='DE' OR applicability_precision!='aggregate_stock_observation' OR review_status!='research_only' OR individual_vehicle_fitment!=0 OR exact_vehicle_fitment!=0 OR model_year_inferred!=0 OR generation_inferred!=0 OR engine_codes_included!=0 OR gearbox_codes_included!=0 OR exact_engine_gearbox_pair!=0 OR ecu_fitment!=0 OR dtc_fitment!=0 OR repair_applicability!=0 OR ru_eaeu_applicability!=0"
    ).get().n;
    const pairTables = db.prepare("SELECT count(*) AS n FROM sqlite_master WHERE type='table' AND lower(name) LIKE '%pair%'").get().n;
    assert(invalid === 0 && pairTables === 0, "KBA market/applicability/pair boundary failed");
    counts = {
      sourceRows: fileRow.source_row_count,
      vagStockObservations: db.prepare("SELECT count(*) AS n FROM stock_observations").get().n,
      manufacturerLabels: db.prepare("SELECT count(*) AS n FROM manufacturers").get().n,
      uniqueMakeTradeNamePairs: db.prepare("SELECT count(*) AS n FROM (SELECT 1 FROM stock_observations GROUP BY manufacturer_id,trade_name_id)").get().n,
      uniqueMakeTypeKeyPairs: db.prepare("SELECT count(*) AS n FROM (SELECT 1 FROM stock_observations GROUP BY manufacturer_id,type_key_id)").get().n,
      uniqueMakeTradeTypeReferenceDateTuples: db.prepare("SELECT count(*) AS n FROM (SELECT 1 FROM stock_observations GROUP BY report_date_id,manufacturer_id,trade_name_id,type_key_id)").get().n,
      federalStates: db.prepare("SELECT count(*) AS n FROM federal_states").get().n,
      referenceDates: db.prepare("SELECT count(*) AS n FROM reference_dates").get().n
    };
    const expected = {
      sourceRows: pack.counts.source_rows, vagStockObservations: pack.counts.vag_stock_observations,
      manufacturerLabels: pack.counts.manufacturer_labels,
      uniqueMakeTradeNamePairs: pack.counts.unique_make_trade_name_pairs,
      uniqueMakeTypeKeyPairs: pack.counts.unique_make_type_key_pairs,
      uniqueMakeTradeTypeReferenceDateTuples: pack.counts.unique_make_trade_type_reference_date_tuples,
      federalStates: pack.counts.federal_states, referenceDates: pack.counts.reference_dates.length
    };
    for (const key of Object.keys(expected)) assert(counts[key] === expected[key], "KBA count mismatch: " + key);
  } finally { db.close(); }

  const summary = {
    id: PACK_ID, sourceId: SOURCE_ID, source: "Kraftfahrt-Bundesamt (KBA), published via GovData/Mobilithek",
    sourceUrl: SOURCE_URL, license: LICENSE_ID, licenseUrl: LICENSE_URL,
    rightsStatus: rights.rights_status, attributionText: attributionText.trim(),
    marketScope: "DE", applicabilityPrecision: "aggregate_stock_observation",
    reviewStatus: "verified_research_only", productionImport: false, productImportAllowed: false,
    ruEaeuApplicability: false, exactVehicleFitment: false, exactEngineGearboxPair: false,
    modelYearInferred: false, generationInferred: false, engineCodesIncluded: false,
    gearboxCodesIncluded: false, ecuFitment: false, dtcFitment: false, repairApplicability: false,
    sourceRevision: entry.source_revision, sourceSnapshotSha256: entry.source_snapshot_sha256,
    databaseSha256: entry.database_sha256, sourceManifestSha256: entry.source_manifest_sha256,
    packManifestSha256: entry.pack_manifest_sha256, licenseSha256: entry.license_sha256,
    attributionSha256: entry.attribution_sha256, buildReportSha256: entry.build_report_sha256,
    integrationReportSha256: entry.desktop_integration_report_sha256, sourceFileSha256: entry.source_file_sha256,
    sourceRunId: entry.source_run_id, sourceRunNumber: entry.source_run_number,
    sourceArtifactSha256: entry.source_artifact_sha256, counts,
    warning: "Только агрегированная статистика парка Германии. Typschlüssel сохранён как исходное поле KBA, но не подтверждён как TSN и не является кодом двигателя или КПП. Не предоставляются модельный год, поколение, VIN-комплектация, двигатель, коробка, ECU, DTC или ремонтная применимость. Не использовать для RU/ЕАЭС."
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
function searchKbaStock(query, limit = 25, explicitRoot) {
  const q = validateQuery(query);
  const boundedLimit = Math.max(1, Math.min(50, Number.isInteger(Number(limit)) ? Number(limit) : 25));
  const summary = getKbaSummary(explicitRoot);
  const root = rootDir(explicitRoot);
  const manifest = readJson(safeFile(root, "manifest.json"));
  const entry = manifest.packs.find((item) => item.id === PACK_ID);
  const db = openReadOnly(safeFile(root, entry.database));
  try {
    const rows = db.prepare(
      "SELECT source_row_number,source_object_id,report_date_raw,report_date_iso,manufacturer_raw,trade_name_raw,type_key_raw,federal_state_raw,vehicle_count,zs_count_raw,source_record_sha256,source_revision,source_snapshot_sha256,source_manifest_sha256,market_scope,applicability_precision,review_status,exact_vehicle_fitment,exact_engine_gearbox_pair,ru_eaeu_applicability FROM v_stock_observations WHERE instr(lower(manufacturer_raw),lower(?))>0 OR instr(lower(trade_name_raw),lower(?))>0 OR instr(lower(type_key_raw),lower(?))>0 OR instr(lower(federal_state_raw),lower(?))>0 OR instr(lower(report_date_iso),lower(?))>0 ORDER BY report_date_iso DESC,manufacturer_raw,trade_name_raw,type_key_raw,source_row_number LIMIT ?"
    ).all(q,q,q,q,q,boundedLimit);
    return rows.map((row) => ({
      id: String(row.source_row_number) + ":" + row.source_record_sha256,
      sourceRowNumber: row.source_row_number, sourceObjectId: row.source_object_id,
      reportDateRaw: row.report_date_raw, reportDate: row.report_date_iso,
      manufacturer: row.manufacturer_raw, tradeName: row.trade_name_raw, typeKey: row.type_key_raw,
      federalState: row.federal_state_raw, vehicleCount: row.vehicle_count, zsCountRaw: row.zs_count_raw,
      sourceRecordSha256: row.source_record_sha256, sourceRevision: row.source_revision,
      sourceSnapshotSha256: row.source_snapshot_sha256, sourceManifestSha256: row.source_manifest_sha256,
      marketScope: "DE", applicabilityPrecision: "aggregate_stock_observation", reviewStatus: "research_only",
      exactVehicleFitment: false, modelYear: null, generation: null, engineCode: null, gearboxCode: null,
      exactEngineGearboxPair: false, ruEaeuApplicability: false, ecuFitment: false, dtcFitment: false,
      repairApplicability: false, sourceUrl: SOURCE_URL, license: LICENSE_ID, licenseUrl: LICENSE_URL,
      warning: summary.warning
    }));
  } finally { db.close(); }
}
function clearCache() { summaryCache.clear(); }
module.exports = { getKbaSummary, searchKbaStock, clearCache };

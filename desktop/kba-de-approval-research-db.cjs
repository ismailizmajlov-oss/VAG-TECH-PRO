"use strict";

const fs = require("node:fs");
const path = require("node:path");
const crypto = require("node:crypto");
const { DatabaseSync } = require("node:sqlite");

const PACK_ID = "kba-de-vag-type-approval-research";
const SOURCE_ID = "kba-de-whole-vehicle-type-approvals";
const SOURCE_URL = "https://www.kba.de/DE/Themen/Typgenehmigung/Informationen_TGV/Liste_erteilter_Typgenehmigungen/liste_typgenehmigungen_Excel.xlsx?__blob=publicationFile&v=13";
const CATALOG_URL = "https://www.govdata.de/suche/daten/liste-der-erteilten-typgenehmigungen-gesamtfahrzeug?ids=1cb74abc-7356-49bf-bb07-ef5dd9d7abfb";
const LICENSE_ID = "DL-DE-BY-2.0";
const LICENSE_URL = "https://www.govdata.de/dl-de/by-2-0";
const EXPECTED_TABLES = ["approval_records", "source_files", "source_label_policy", "source_registry"];
const EXPECTED_INDEXES = ["idx_kba_appr_date", "idx_kba_appr_make", "idx_kba_appr_number", "idx_kba_appr_trade", "idx_kba_appr_type"];
const WARNING = "Только метаданные одобрений типа транспортного средства Германии. Дата одобрения не является модельным годом. Данные не содержат коды двигателя/КПП, их точные пары, ECU, DTC или ремонтные процедуры; не подтверждают применимость к конкретному автомобилю и не распространяются на RU/ЕАЭС.";

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

function rootDir(explicitRoot) {
  return path.resolve(explicitRoot || process.env.VAG_TECH_PRO_RESEARCH_DIR || path.join(process.cwd(), "data", "research"));
}

function safeFile(root, relative) {
  if (typeof relative !== "string" || !relative || path.isAbsolute(relative) || relative.includes("\\")) {
    throw new Error("Unsafe KBA approval-pack path");
  }
  const base = fs.realpathSync(root);
  const candidate = path.resolve(base, relative);
  const rel = path.relative(base, candidate);
  if (!rel || rel === ".." || rel.startsWith(".." + path.sep) || path.isAbsolute(rel)) {
    throw new Error("KBA approval path escaped its root");
  }
  const real = fs.realpathSync(candidate);
  const realRel = path.relative(base, real);
  if (!realRel || realRel === ".." || realRel.startsWith(".." + path.sep) || path.isAbsolute(realRel)) {
    throw new Error("KBA approval symlink escaped its root");
  }
  if (!fs.statSync(real).isFile()) throw new Error("KBA approval-pack entry is not a regular file");
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

function verifyFile(root, entry, pathField, hashField) {
  assert(typeof entry[pathField] === "string" && /^[a-f0-9]{64}$/.test(entry[hashField] || ""), "KBA approval manifest is missing " + pathField + "/" + hashField);
  const file = safeFile(root, entry[pathField]);
  assert(hashFile(file) === entry[hashField], "KBA approval provenance SHA-256 mismatch: " + pathField);
  return file;
}

function openReadOnly(file) {
  const db = new DatabaseSync(file, { readOnly: true });
  db.exec("PRAGMA query_only=ON; PRAGMA trusted_schema=OFF;");
  return db;
}

function getKbaApprovalSummary(explicitRoot) {
  const root = rootDir(explicitRoot);
  const rootManifest = readJson(safeFile(root, "manifest.json"));
  assert(rootManifest.schema_version === 1 && Array.isArray(rootManifest.packs), "Invalid desktop research manifest");
  const entry = rootManifest.packs.find((item) => item.id === PACK_ID);
  assert(entry, "KBA DE type-approval research pack is missing");

  assert(
    entry.source_id === SOURCE_ID &&
    entry.license === LICENSE_ID &&
    entry.license_status === "approved_by_published_DL_DE_BY_2_0" &&
    entry.rights_status === "approved_by_published_DL_DE_BY_2_0" &&
    JSON.stringify(entry.market_scope) === JSON.stringify(["DE"]) &&
    entry.applicability_precision === "type_approval_document_metadata_only" &&
    entry.review_status === "verified_research_only" &&
    entry.research_pack_ingested === true &&
    entry.product_database_ingested === false &&
    entry.data_ingested === false &&
    entry.production_import === false &&
    entry.product_import_allowed === false &&
    entry.ru_eaeu_applicability === false &&
    entry.exact_vehicle_fitment === false &&
    entry.exact_engine_gearbox_pair === false &&
    entry.repair_applicability === false &&
    entry.diagnostic_execution_allowed === false &&
    entry.model_year_inferred === false &&
    entry.generation_inferred === false &&
    entry.engine_codes_included === false &&
    entry.gearbox_codes_included === false &&
    entry.ecu_fitment === false &&
    entry.dtc_fitment === false &&
    entry.commercial_use_allowed === true &&
    entry.display_allowed === true &&
    entry.cache_allowed === true &&
    entry.bulk_reuse_allowed === true &&
    entry.redistribution_allowed === true &&
    entry.attribution_required === true &&
    entry.source_file_included_in_desktop === true,
    "KBA approval rights, licence or DE-only applicability boundary failed"
  );

  const database = verifyFile(root, entry, "database", "database_sha256");
  const packManifestFile = verifyFile(root, entry, "pack_manifest_file", "pack_manifest_sha256");
  const sourceManifestFile = verifyFile(root, entry, "source_manifest_file", "source_manifest_sha256");
  const attributionFile = verifyFile(root, entry, "attribution_file", "attribution_sha256");
  const licenseFile = verifyFile(root, entry, "license_file", "license_sha256");
  const rightsEvidenceFile = verifyFile(root, entry, "rights_evidence_file", "rights_evidence_sha256");
  const buildReportFile = verifyFile(root, entry, "build_report_file", "build_report_sha256");
  const integrationReportFile = verifyFile(root, entry, "desktop_integration_report_file", "desktop_integration_report_sha256");
  const sourceSnapshotFile = verifyFile(root, entry, "source_snapshot_file", "source_file_sha256");

  const pack = readJson(packManifestFile);
  const source = readJson(sourceManifestFile);
  const buildReport = readJson(buildReportFile);
  const integrationReport = readJson(integrationReportFile);
  const rightsEvidence = readJson(rightsEvidenceFile);
  const rights = source.rights || {};
  const snapshot = source.snapshot || {};
  const attributionText = fs.readFileSync(attributionFile, "utf8");
  const licenseText = fs.readFileSync(licenseFile, "utf8");

  assert(
    pack.pack_id === PACK_ID &&
    pack.source_id === SOURCE_ID &&
    pack.rights_status === "approved_by_published_DL_DE_BY_2_0" &&
    pack.license_id === LICENSE_ID &&
    pack.license_url === LICENSE_URL &&
    pack.market_scope === "DE" &&
    pack.applicability_precision === "type_approval_document_metadata_only" &&
    pack.review_status === "research_only" &&
    pack.research_pack_built === true &&
    pack.research_pack_ingested === false &&
    pack.product_database_ingested === false &&
    pack.product_import_allowed === false &&
    pack.production_import === false &&
    pack.applicability?.individual_vehicle_fitment === false &&
    pack.applicability?.exact_vehicle_fitment === false &&
    pack.applicability?.model_year === false &&
    pack.applicability?.generation === false &&
    pack.applicability?.engine_code === false &&
    pack.applicability?.gearbox_code === false &&
    pack.applicability?.exact_engine_gearbox_pair === false &&
    pack.applicability?.ecu_fitment === false &&
    pack.applicability?.dtc_fitment === false &&
    pack.applicability?.repair_applicability === false &&
    pack.applicability?.diagnostic_execution_allowed === false &&
    pack.applicability?.ru_eaeu_applicability === false &&
    pack.source_manifest_sha256 === entry.source_manifest_sha256 &&
    pack.source_snapshot_sha256 === entry.source_snapshot_sha256 &&
    pack.database_sha256 === entry.database_sha256 &&
    pack.source_file_sha256 === entry.source_file_sha256 &&
    pack.source_file_bytes === entry.source_file_bytes &&
    entry.source_revision === pack.source_revision &&
    source.source_id === SOURCE_ID &&
    source.data_ingested === false &&
    source.product_import_allowed === false &&
    snapshot.status === "resource_acquired_schema_available" &&
    snapshot.downloaded === true &&
    snapshot.source_snapshot_sha256 === entry.source_snapshot_sha256 &&
    rights.rights_status === "approved_by_published_DL_DE_BY_2_0" &&
    rights.commercial_use_allowed === true &&
    rights.display_allowed === true &&
    rights.offline_cache_allowed === true &&
    rights.bulk_reuse_allowed === true &&
    rights.redistribution_allowed === true &&
    rights.attribution_required === true &&
    buildReport.status === "verified_research_only" &&
    buildReport.database_sha256 === entry.database_sha256 &&
    buildReport.source_snapshot_sha256 === entry.source_snapshot_sha256 &&
    buildReport.exact_engine_gearbox_pair_claim === false &&
    integrationReport.status === "integrated_verified_research_only" &&
    integrationReport.research_pack_ingested === true &&
    integrationReport.product_database_ingested === false &&
    integrationReport.product_import_allowed === false &&
    integrationReport.production_import === false &&
    integrationReport.ru_eaeu_applicability === false &&
    integrationReport.exact_engine_gearbox_pair === false &&
    integrationReport.source_snapshot_in_desktop === true &&
    integrationReport.database_sha256 === entry.database_sha256 &&
    integrationReport.source_manifest_sha256 === entry.source_manifest_sha256 &&
    integrationReport.source_snapshot_sha256 === entry.source_snapshot_sha256 &&
    integrationReport.source_run_id === entry.source_run_id &&
    integrationReport.artifact_sha256 === entry.source_artifact_sha256 &&
    rightsEvidence.license_id === LICENSE_ID &&
    rightsEvidence.rights_status === "approved_by_published_DL_DE_BY_2_0" &&
    rightsEvidence.offline_cache_allowed === true &&
    rightsEvidence.redistribution_allowed === true,
    "KBA approval source manifest, rights, source snapshot or applicability policy failed"
  );

  assert(hashFile(sourceSnapshotFile) === entry.source_snapshot_sha256, "KBA source XLSX SHA-256 mismatch");
  assert(fs.statSync(sourceSnapshotFile).size === entry.source_file_bytes, "KBA source XLSX byte-size mismatch");
  assert(attributionText.includes("Kraftfahrt-Bundesamt (KBA)") && attributionText.includes("DL-DE BY 2.0") && attributionText.includes(SOURCE_URL) && attributionText.includes("Modified data"), "KBA approval attribution/modified-data notice missing");
  assert(licenseText.includes("DL-DE BY 2.0") && licenseText.includes(LICENSE_URL), "KBA approval licence reference missing");

  const db = openReadOnly(database);
  let counts;
  try {
    const integrity = db.prepare("PRAGMA integrity_check").all();
    assert(integrity.length === 1 && Object.values(integrity[0])[0] === "ok", "KBA approval SQLite integrity_check failed");
    assert(db.prepare("PRAGMA foreign_key_check").all().length === 0, "KBA approval SQLite foreign_key_check failed");
    const tables = db.prepare("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name").all().map((row) => row.name);
    assert(JSON.stringify(tables) === JSON.stringify(EXPECTED_TABLES), "KBA approval SQLite table set mismatch");
    const indexes = db.prepare("SELECT name FROM sqlite_master WHERE type='index'").all().map((row) => row.name);
    assert(EXPECTED_INDEXES.every((name) => indexes.includes(name)), "KBA approval SQLite search indexes incomplete");
    const views = db.prepare("SELECT name FROM sqlite_master WHERE type='view'").all().map((row) => row.name);
    assert(views.includes("v_approval_records"), "KBA approval provenance view missing");

    const registry = db.prepare("SELECT source_id,license_id,rights_status,market_scope,applicability_precision,review_status,source_revision,source_manifest_sha256,source_snapshot_sha256,product_import_allowed,exact_vehicle_fitment,exact_engine_gearbox_pair,ru_eaeu_applicability,ecu_fitment,dtc_fitment,repair_applicability FROM source_registry").get();
    assert(
      registry &&
      registry.source_id === SOURCE_ID &&
      registry.license_id === LICENSE_ID &&
      registry.rights_status === "approved_by_published_DL_DE_BY_2_0" &&
      registry.market_scope === "DE" &&
      registry.applicability_precision === "type_approval_document_metadata_only" &&
      registry.review_status === "research_only" &&
      registry.source_revision === entry.source_revision &&
      registry.source_manifest_sha256 === entry.source_manifest_sha256 &&
      registry.source_snapshot_sha256 === entry.source_snapshot_sha256 &&
      registry.product_import_allowed === 0 &&
      registry.exact_vehicle_fitment === 0 &&
      registry.exact_engine_gearbox_pair === 0 &&
      registry.ru_eaeu_applicability === 0 &&
      registry.ecu_fitment === 0 &&
      registry.dtc_fitment === 0 &&
      registry.repair_applicability === 0,
      "KBA approval SQLite source registry mismatch"
    );

    const fileRow = db.prepare("SELECT source_id,file_name,sha256,byte_size,source_row_count,filtered_row_count,sheet_name,header_row_number FROM source_files").get();
    assert(
      fileRow &&
      fileRow.source_id === SOURCE_ID &&
      fileRow.file_name === "kba-whole-vehicle-type-approvals.xlsx" &&
      fileRow.sha256 === entry.source_snapshot_sha256 &&
      fileRow.byte_size === entry.source_file_bytes &&
      fileRow.source_row_count === entry.counts.source_rows &&
      fileRow.filtered_row_count === entry.counts.approval_records &&
      fileRow.sheet_name === "Tabelle1" &&
      fileRow.header_row_number === 3,
      "KBA approval SQLite source-file registry mismatch"
    );

    const invalid = db.prepare(
      "SELECT count(*) AS n FROM v_approval_records WHERE market_scope!='DE' OR applicability_precision!='type_approval_document_metadata_only' OR review_status!='research_only' OR exact_vehicle_fitment!=0 OR model_year IS NOT NULL OR generation IS NOT NULL OR engine_code IS NOT NULL OR gearbox_code IS NOT NULL OR exact_engine_gearbox_pair!=0 OR ru_eaeu_applicability!=0 OR ecu_fitment!=0 OR dtc_fitment!=0 OR repair_applicability!=0 OR source_revision<>? OR source_snapshot_sha256<>?"
    ).get(entry.source_revision, entry.source_snapshot_sha256).n;
    const pairTables = db.prepare("SELECT count(*) AS n FROM sqlite_master WHERE type='table' AND lower(name) LIKE '%pair%'").get().n;
    assert(invalid === 0 && pairTables === 0, "KBA approval market/applicability/pair boundary failed");

    counts = {
      sourceRows: db.prepare("SELECT source_row_count AS n FROM source_files").get().n,
      approvalRecords: db.prepare("SELECT count(*) AS n FROM approval_records").get().n,
      manufacturerLabels: db.prepare("SELECT count(DISTINCT manufacturer_label) AS n FROM approval_records").get().n,
      distinctApprovalNumbers: db.prepare("SELECT count(DISTINCT type_approval_number_raw) AS n FROM approval_records").get().n,
      distinctRowHashes: db.prepare("SELECT count(DISTINCT source_record_sha256) AS n FROM approval_records").get().n,
      sourceLabelPolicyRows: db.prepare("SELECT count(*) AS n FROM source_label_policy").get().n
    };
    assert(counts.sourceRows === 3782, "KBA source row count changed");
    assert(counts.approvalRecords === 918, "KBA approval record count changed");
    assert(counts.manufacturerLabels === 8, "KBA exact manufacturer-label count changed");
    assert(counts.distinctApprovalNumbers === 918, "KBA approval-number count changed");
    assert(counts.distinctRowHashes === 918, "KBA row-hash uniqueness changed");
    assert(counts.sourceLabelPolicyRows === 9, "KBA label-policy row count changed");
  } finally {
    db.close();
  }

  return {
    id: PACK_ID,
    sourceId: SOURCE_ID,
    source: "Kraftfahrt-Bundesamt (KBA), Germany",
    sourceUrl: SOURCE_URL,
    catalogUrl: CATALOG_URL,
    license: LICENSE_ID,
    licenseUrl: LICENSE_URL,
    rightsStatus: "approved_by_published_DL_DE_BY_2_0",
    attributionText: attributionText.trim(),
    marketScope: "DE",
    applicabilityPrecision: "type_approval_document_metadata_only",
    reviewStatus: "verified_research_only",
    researchPackIngested: true,
    productDatabaseIngested: false,
    productionImport: false,
    productImportAllowed: false,
    dataIngested: false,
    ruEaeuApplicability: false,
    exactVehicleFitment: false,
    exactEngineGearboxPair: false,
    modelYearInferred: false,
    generationInferred: false,
    engineCodesIncluded: false,
    gearboxCodesIncluded: false,
    ecuFitment: false,
    dtcFitment: false,
    repairApplicability: false,
    diagnosticExecutionAllowed: false,
    sourceRevision: entry.source_revision,
    sourceSnapshotSha256: entry.source_snapshot_sha256,
    sourceFileSha256: entry.source_file_sha256,
    databaseSha256: entry.database_sha256,
    sourceManifestSha256: entry.source_manifest_sha256,
    packManifestSha256: entry.pack_manifest_sha256,
    licenseSha256: entry.license_sha256,
    attributionSha256: entry.attribution_sha256,
    rightsEvidenceSha256: entry.rights_evidence_sha256,
    buildReportSha256: entry.build_report_sha256,
    integrationReportSha256: entry.desktop_integration_report_sha256,
    sourceRunId: entry.source_run_id,
    sourceRunNumber: entry.source_run_number,
    sourceArtifactSha256: entry.source_artifact_sha256,
    counts,
    warning: WARNING
  };
}

function validateQuery(value) {
  const query = String(value ?? "").trim();
  if (query.length < 2) throw new TypeError("Для поиска нужно минимум два символа.");
  if (query.length > 100) throw new TypeError("Слишком длинный поисковый запрос.");
  return query;
}

function searchKbaApprovals(query, limit = 25, explicitRoot) {
  const q = validateQuery(query);
  const boundedLimit = Math.max(1, Math.min(50, Number.isInteger(Number(limit)) ? Number(limit) : 25));
  const summary = getKbaApprovalSummary(explicitRoot);
  const root = rootDir(explicitRoot);
  const manifest = readJson(safeFile(root, "manifest.json"));
  const entry = manifest.packs.find((item) => item.id === PACK_ID);
  const database = safeFile(root, entry.database);
  const db = openReadOnly(database);
  try {
    const rows = db.prepare(
      "SELECT source_row_number,manufacturer_label,manufacturer_label_mapping_status,trade_name_raw,type_designation_raw,approval_object_raw,type_approval_number_raw,technical_service_raw,procedure_type_raw,approval_date_raw,emissions_member_state_raw,source_record_sha256,source_revision,source_snapshot_sha256,market_scope,applicability_precision,review_status,exact_vehicle_fitment,model_year,generation,engine_code,gearbox_code,exact_engine_gearbox_pair,ru_eaeu_applicability,ecu_fitment,dtc_fitment,repair_applicability FROM v_approval_records WHERE instr(lower(coalesce(manufacturer_label,'')),lower(?))>0 OR instr(lower(coalesce(trade_name_raw,'')),lower(?))>0 OR instr(lower(coalesce(type_designation_raw,'')),lower(?))>0 OR instr(lower(coalesce(approval_object_raw,'')),lower(?))>0 OR instr(lower(coalesce(type_approval_number_raw,'')),lower(?))>0 OR instr(lower(coalesce(technical_service_raw,'')),lower(?))>0 OR instr(lower(coalesce(procedure_type_raw,'')),lower(?))>0 OR instr(lower(coalesce(emissions_member_state_raw,'')),lower(?))>0 ORDER BY approval_date_raw DESC,source_row_number ASC LIMIT ?"
    ).all(q,q,q,q,q,q,q,q,boundedLimit);

    return rows.map((row) => ({
      id: String(row.source_row_number) + ":" + row.source_record_sha256,
      sourceRowNumber: row.source_row_number,
      manufacturerLabel: row.manufacturer_label,
      manufacturerLabelMappingStatus: row.manufacturer_label_mapping_status,
      tradeName: row.trade_name_raw,
      typeDesignation: row.type_designation_raw,
      approvalObject: row.approval_object_raw,
      approvalNumber: row.type_approval_number_raw,
      technicalService: row.technical_service_raw,
      procedureType: row.procedure_type_raw,
      approvalDate: row.approval_date_raw,
      emissionsMemberState: row.emissions_member_state_raw,
      sourceRecordSha256: row.source_record_sha256,
      sourceRevision: row.source_revision,
      sourceSnapshotSha256: row.source_snapshot_sha256,
      sourceManifestSha256: summary.sourceManifestSha256,
      marketScope: "DE",
      applicabilityPrecision: "type_approval_document_metadata_only",
      reviewStatus: "research_only",
      exactVehicleFitment: false,
      modelYear: null,
      generation: null,
      engineCode: null,
      gearboxCode: null,
      exactEngineGearboxPair: false,
      ruEaeuApplicability: false,
      ecuFitment: false,
      dtcFitment: false,
      repairApplicability: false,
      sourceUrl: SOURCE_URL,
      catalogUrl: CATALOG_URL,
      license: LICENSE_ID,
      licenseUrl: LICENSE_URL,
      warning: WARNING
    }));
  } finally {
    db.close();
  }
}

module.exports = { getKbaApprovalSummary, searchKbaApprovals, validateQuery };

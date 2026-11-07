"use strict";
const fs = require("node:fs");
const path = require("node:path");
const crypto = require("node:crypto");
const { DatabaseSync } = require("node:sqlite");

const PACK_ID = "astra-fedro-targa-emissionen-vag-research";
const SOURCE_ID = "astra-fedro-targa-emissionen-approval-variants-ch";
const SOURCE_URL = "https://opendata.astra.admin.ch/ivzod/2000-Typengenehmigungen_TG_TARGA/2200-Basisdaten_TG_ab_1995/emissionen.txt";
const ATTRIBUTION = "Source: Federal Roads Office (FEDRO / ASTRA), TARGA emissions data (emissionen.txt)";
const WARNING = "Только швейцарская строка типового одобрения. Motortyp — исходное обозначение одобрения, не подтверждённый заводской код VAG; Getriebe — классификация ASTRA, не код КПП VAG. Не подтверждает российскую/ЕАЭС применимость, серийную комплектацию, VIN, модельный год, поколение, ECU, DTC или ремонт.";

function fail(message) { throw new Error(message); }
function rootDir(explicitRoot) {
  return path.resolve(explicitRoot || process.env.VAG_TECH_PRO_RESEARCH_DIR || path.join(process.cwd(), "data", "research"));
}
function sha256(bytes) { return crypto.createHash("sha256").update(bytes).digest("hex"); }
function sha256File(file) { return sha256(fs.readFileSync(file)); }
function readJson(file) { return JSON.parse(fs.readFileSync(file, "utf8")); }
function safeFile(root, relative) {
  if (typeof relative !== "string" || !relative || path.isAbsolute(relative) || relative.includes("\\")) fail("Unsafe ASTRA TARGA path");
  const base = fs.realpathSync(root);
  const candidate = path.resolve(base, relative);
  const rel = path.relative(base, candidate);
  if (!rel || rel === ".." || rel.startsWith(".." + path.sep) || path.isAbsolute(rel)) fail("ASTRA TARGA path escaped research root");
  const real = fs.realpathSync(candidate);
  const realRel = path.relative(base, real);
  if (!realRel || realRel === ".." || realRel.startsWith(".." + path.sep) || path.isAbsolute(realRel)) fail("ASTRA TARGA symlink escaped research root");
  const stat = fs.lstatSync(candidate);
  if (stat.isSymbolicLink() || !fs.statSync(real).isFile()) fail("ASTRA TARGA resource must be a regular file");
  return real;
}
function verifyFile(root, entry, fileField, hashField) {
  if (typeof entry[fileField] !== "string" || !/^[a-f0-9]{64}$/.test(entry[hashField] || "")) fail("ASTRA TARGA manifest is missing " + fileField + "/" + hashField);
  const file = safeFile(root, entry[fileField]);
  if (sha256File(file) !== entry[hashField]) fail("ASTRA TARGA SHA-256 mismatch: " + fileField);
  return file;
}
function openReadOnly(file) {
  const db = new DatabaseSync(file, { readOnly: true });
  db.exec("PRAGMA query_only=ON; PRAGMA trusted_schema=OFF;");
  return db;
}
function getAstraTargaSummary(explicitRoot) {
  const root = rootDir(explicitRoot);
  const manifest = readJson(safeFile(root, "manifest.json"));
  if (manifest.schema_version !== 1 || !Array.isArray(manifest.packs)) fail("Invalid desktop research manifest");
  const entry = manifest.packs.find((item) => item.id === SOURCE_ID);
  if (!entry || entry.source_id !== SOURCE_ID || entry.rights_status !== "approved_by_published_ogd_terms" ||
      entry.license !== "Swiss Open Government Data (OGD)" || JSON.stringify(entry.market_scope) !== JSON.stringify(["CH"]) ||
      entry.review_status !== "verified_research_only" || entry.production_import !== false || entry.product_import_allowed !== false ||
      entry.ru_eaeu_applicability !== false || entry.exact_vag_factory_code_pair !== false || entry.exact_vehicle_fitment !== false ||
      entry.repair_applicability !== false || entry.diagnostic_execution_allowed !== false || entry.attribution_required !== true) {
    fail("ASTRA TARGA rights, market or no-fitment boundary failed");
  }
  const database = verifyFile(root, entry, "database", "database_sha256");
  const packManifestFile = verifyFile(root, entry, "pack_manifest_file", "pack_manifest_sha256");
  const sourceManifestFile = verifyFile(root, entry, "source_manifest_file", "source_manifest_sha256");
  const registryManifestFile = verifyFile(root, entry, "source_registry_manifest_file", "source_registry_manifest_sha256");
  const attributionFile = verifyFile(root, entry, "attribution_file", "attribution_sha256");
  const fieldMapFile = verifyFile(root, entry, "field_map_file", "field_map_sha256");
  const buildReportFile = verifyFile(root, entry, "build_report_file", "build_report_sha256");
  const finalVerificationFile = verifyFile(root, entry, "final_verification_file", "final_verification_sha256");
  const pack = readJson(packManifestFile);
  const source = readJson(sourceManifestFile);
  const registry = readJson(registryManifestFile);
  const report = readJson(buildReportFile);
  const final = readJson(finalVerificationFile);
  const attribution = fs.readFileSync(attributionFile, "utf8");
  const rights = source.rights || {};
  const policy = source.applicability_policy || {};
  if (pack.pack_id !== PACK_ID || pack.status !== "verified_research_only" || pack.source_id !== SOURCE_ID ||
      JSON.stringify(pack.market_scope) !== JSON.stringify(["CH"]) || pack.rights_status !== "approved_by_published_ogd_terms" ||
      pack.database?.sha256 !== entry.database_sha256 || pack.source_manifest?.sha256 !== entry.source_manifest_sha256 ||
      source.source_id !== SOURCE_ID || source.rights?.rights_status !== "approved_by_published_ogd_terms" ||
      registry.source_id !== SOURCE_ID || registry.snapshot?.file_sha256 !== pack.source_file?.file_sha256 ||
      registry.market_scope?.[0] !== "CH" || registry.rights?.rights_status !== "approved_by_published_ogd_terms" ||
      ["commercial_use_allowed","display_allowed","offline_cache_allowed","bulk_reuse_allowed","redistribution_allowed","attribution_required"].some((key) => rights[key] !== true) ||
      ["commercial_use_allowed","display_allowed","offline_cache_allowed","bulk_reuse_allowed","redistribution_allowed","attribution_required"].some((key) => registry.rights[key] !== true) ||
      policy.market_scope !== "CH only" || policy.source_defined_variant_link !== true || policy.exact_vag_factory_code_pair !== false ||
      policy.production_fitment !== false || policy.ru_eaeu_applicability !== false || policy.model_year_inferred !== false ||
      policy.generation_inferred !== false || policy.repair_procedure_applicability !== false || policy.diagnostic_execution_allowed !== false ||
      !attribution.includes(ATTRIBUTION) || !attribution.includes("Swiss Open Government Data") ||
      final.database_sha256 !== entry.database_sha256 || final.source_file_sha256 !== pack.source_file?.file_sha256 ||
      final.exact_vag_factory_code_pair !== false || final.ru_eaeu_applicability !== false) {
    fail("ASTRA TARGA source manifest, rights, attribution or pack provenance failed");
  }
  const db = openReadOnly(database);
  try {
    const integrity = db.prepare("PRAGMA integrity_check").all();
    if (integrity.length !== 1 || Object.values(integrity[0])[0] !== "ok" || db.prepare("PRAGMA foreign_key_check").all().length) fail("ASTRA TARGA SQLite integrity check failed");
    const meta = Object.fromEntries(db.prepare("SELECT key,value FROM pack_metadata").all().map((row) => [row.key, row.value]));
    if (meta.pack_id !== PACK_ID || meta.source_id !== SOURCE_ID || meta.rights_status !== "approved_by_published_ogd_terms" ||
        meta.market_scope !== "CH" || meta.ru_eaeu_applicability !== "false" || meta.exact_vag_factory_code_pair !== "false" ||
        meta.exact_vehicle_fitment !== "false" || meta.model_year_inferred !== "false" || meta.generation_inferred !== "false" ||
        meta.source_defined_variant_link !== "true" || meta.attribution_required !== "true" ||
        meta.source_revision !== pack.source_revision || meta.source_file_sha256 !== pack.source_file?.file_sha256) {
      fail("ASTRA TARGA SQLite metadata mismatch");
    }
    const counts = {
      approvalPowertrainVariantRows: db.prepare("SELECT count(*) AS n FROM approval_powertrain_variant_rows").get().n,
      sourceDefinedVariantLinkRows: db.prepare("SELECT count(*) AS n FROM approval_powertrain_variant_rows WHERE source_defined_variant_link=1").get().n,
      exactVagFactoryCodePairRows: db.prepare("SELECT count(*) AS n FROM approval_powertrain_variant_rows WHERE exact_vag_factory_code_pair<>0").get().n,
      exactVehicleFitmentRows: db.prepare("SELECT count(*) AS n FROM approval_powertrain_variant_rows WHERE exact_vehicle_fitment<>0").get().n,
      ruEaeuApplicabilityRows: db.prepare("SELECT count(*) AS n FROM approval_powertrain_variant_rows WHERE ru_eaeu_applicability<>0").get().n
    };
    const expected = {
      approvalPowertrainVariantRows: Number(pack.counts?.approval_powertrain_variant_rows || 0),
      sourceDefinedVariantLinkRows: Number(pack.counts?.source_defined_variant_link_rows || 0),
      exactVagFactoryCodePairRows: Number(pack.counts?.exact_vag_factory_code_pair_rows || 0),
      exactVehicleFitmentRows: Number(pack.counts?.exact_vehicle_fitment_rows || 0),
      ruEaeuApplicabilityRows: Number(pack.counts?.ru_eaeu_applicability_rows || 0)
    };
    const invalidRows = db.prepare("SELECT count(*) AS n FROM approval_powertrain_variant_rows WHERE market_scope!='CH' OR applicability_precision!='CH_type_approval_gearbox_variant_row' OR exact_vag_factory_code_pair!=0 OR exact_vehicle_fitment!=0 OR ru_eaeu_applicability!=0 OR model_year_inferred!=0 OR generation_inferred!=0 OR engine_type_status!='raw_approval_engine_type_candidate' OR gearbox_status!='raw_approval_classification_not_vag_gearbox_code'").get().n;
    const dtcTables = db.prepare("SELECT count(*) AS n FROM sqlite_master WHERE type='table' AND lower(name) LIKE '%dtc%'").get().n;
    if (invalidRows || dtcTables || counts.approvalPowertrainVariantRows !== 53240 ||
        Object.keys(expected).some((key) => counts[key] !== expected[key]) ||
        counts.sourceDefinedVariantLinkRows !== counts.approvalPowertrainVariantRows) fail("ASTRA TARGA row counts or CH-only candidate boundary failed");
    return {
      id: SOURCE_ID, sourceId: SOURCE_ID, source: "Federal Roads Office (FEDRO / ASTRA), TARGA third-generation type approvals",
      sourceUrl: SOURCE_URL, rightsStatus: rights.rights_status, license: "Swiss Open Government Data (OGD)",
      attributionText: attribution.trim(), marketScope: "CH", applicabilityPrecision: "CH_type_approval_gearbox_variant_row",
      reviewStatus: "verified_research_only", productionImport: false, productImportAllowed: false,
      ruEaeuApplicability: false, exactVagFactoryCodePair: false, exactVehicleFitment: false,
      repairApplicability: false, diagnosticExecutionAllowed: false,
      sourceRevision: pack.source_revision, sourceFileSha256: pack.source_file.file_sha256,
      sourceSnapshotSha256: pack.source_file.file_sha256, databaseSha256: entry.database_sha256,
      sourceManifestSha256: entry.source_manifest_sha256, packManifestSha256: entry.pack_manifest_sha256,
      sourceRegistryManifestSha256: entry.source_registry_manifest_sha256, counts,
      note: WARNING
    };
  } finally { db.close(); }
}
function validateQuery(value) {
  const q = String(value ?? "").trim();
  if (q.length < 2) throw new TypeError("Для поиска нужно минимум два символа.");
  if (q.length > 100) throw new TypeError("Слишком длинный поисковый запрос.");
  return q;
}
function likePattern(query) { return "%" + query.replace(/[\\%_]/g, "\\$&") + "%"; }
function searchAstraTargaRows(query, limit = 25, explicitRoot) {
  const q = validateQuery(query);
  const boundedLimit = Math.max(1, Math.min(50, Number.isInteger(Number(limit)) ? Number(limit) : 25));
  const summary = getAstraTargaSummary(explicitRoot);
  const root = rootDir(explicitRoot);
  const manifest = readJson(safeFile(root, "manifest.json"));
  const entry = manifest.packs.find((item) => item.id === SOURCE_ID);
  const database = safeFile(root, entry.database);
  const db = openReadOnly(database);
  try {
    const pattern = likePattern(q);
    const rows = db.prepare(
      "SELECT id,source_row_number,source_row_sha256,source_record_locator,source_file_sha256,market_scope," +
      "approval_number_raw,make_raw,type_raw,gearbox_classification_raw,final_drive_ratio_raw,engine_make_raw," +
      "engine_type_raw,engine_construction_raw,fuel_raw,displacement_cc_raw,power_kw_raw,power_rpm_raw," +
      "torque_nm_raw,torque_rpm_raw,emission_control_raw,drive_raw,emissions_code_raw,homologation_date_raw," +
      "applicability_precision,source_defined_variant_link,exact_vag_factory_code_pair,exact_vehicle_fitment," +
      "ru_eaeu_applicability,model_year_inferred,generation_inferred,engine_type_status,gearbox_status " +
      "FROM approval_powertrain_variant_rows WHERE approval_number_raw LIKE ? ESCAPE '\\' OR make_normalized LIKE ? ESCAPE '\\' " +
      "OR type_raw LIKE ? ESCAPE '\\' OR engine_type_raw LIKE ? ESCAPE '\\' OR gearbox_classification_raw LIKE ? ESCAPE '\\' " +
      "ORDER BY make_normalized,approval_number_raw,source_row_number LIMIT ?"
    ).all(pattern, pattern, pattern, pattern, pattern, boundedLimit);
    return rows.map((row) => ({
      id: row.id, sourceRowNumber: row.source_row_number, sourceRecordSha256: row.source_row_sha256,
      sourceRecordLocator: row.source_record_locator, sourceFileSha256: row.source_file_sha256,
      approvalNumber: row.approval_number_raw, make: row.make_raw, type: row.type_raw,
      gearboxClassification: row.gearbox_classification_raw, finalDriveRatio: row.final_drive_ratio_raw,
      engineMake: row.engine_make_raw, engineType: row.engine_type_raw, engineConstruction: row.engine_construction_raw,
      fuel: row.fuel_raw, displacementCc: row.displacement_cc_raw == null ? null : Number(row.displacement_cc_raw), powerKw: row.power_kw_raw == null ? null : Number(row.power_kw_raw),
      powerRpm: row.power_rpm_raw, torqueNm: row.torque_nm_raw == null ? null : Number(row.torque_nm_raw), torqueRpm: row.torque_rpm_raw,
      emissionControl: row.emission_control_raw, drive: row.drive_raw, emissionsCode: row.emissions_code_raw,
      homologationDate: row.homologation_date_raw, marketScope: "CH", applicabilityPrecision: row.applicability_precision,
      sourceDefinedVariantLink: row.source_defined_variant_link === 1, exactVagFactoryCodePair: false,
      exactVehicleFitment: false, ruEaeuApplicability: false, modelYear: null, generation: null,
      engineTypeStatus: row.engine_type_status, gearboxStatus: row.gearbox_status,
      sourceRevision: summary.sourceRevision, sourceSnapshotSha256: summary.sourceSnapshotSha256,
      databaseSha256: summary.databaseSha256, sourceManifestSha256: summary.sourceManifestSha256,
      sourceUrl: SOURCE_URL, warning: WARNING
    }));
  } finally { db.close(); }
}
module.exports = { getAstraTargaSummary, searchAstraTargaRows };

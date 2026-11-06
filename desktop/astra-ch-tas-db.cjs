"use strict";
const fs = require("node:fs");
const path = require("node:path");
const crypto = require("node:crypto");
const { DatabaseSync } = require("node:sqlite");

const PACK_ID = "astra-fedro-tas-type-approvals-open-data-ch";
const SOURCE_ID = PACK_ID;
const ATTRIBUTION = "Source: Federal Roads Office (FEDRO/ASTRA), Type Approval System (TAS) open data.";
const SOURCE_URL = "https://www.astra.admin.ch/de/fahrzeugdaten";
const RIGHTS_URL = "https://opendata.astra.admin.ch/ivzod/5000-Newsletter/2026_1/Newsletter_Fahrzeugdaten_1_2026_EN.pdf";

function rootDir(explicitRoot) {
  return path.resolve(explicitRoot || process.env.VAG_TECH_PRO_RESEARCH_DIR || path.join(process.cwd(), "data", "research"));
}
function safeFile(root, relative) {
  if (typeof relative !== "string" || !relative || path.isAbsolute(relative) || relative.includes("\\")) throw new Error("Unsafe ASTRA pack path");
  const base = fs.realpathSync(root);
  const candidate = path.resolve(base, relative);
  const rel = path.relative(base, candidate);
  if (!rel || rel === ".." || rel.startsWith(".." + path.sep) || path.isAbsolute(rel)) throw new Error("ASTRA path escaped its root");
  const real = fs.realpathSync(candidate);
  const realRel = path.relative(base, real);
  if (!realRel || realRel === ".." || realRel.startsWith(".." + path.sep) || path.isAbsolute(realRel)) throw new Error("ASTRA symlink escaped its root");
  if (!fs.statSync(real).isFile()) throw new Error("ASTRA pack entry is not a regular file");
  return real;
}
function hashFile(file) {
  return crypto.createHash("sha256").update(fs.readFileSync(file)).digest("hex");
}
function readJson(file) { return JSON.parse(fs.readFileSync(file, "utf8")); }
function verifyFile(root, entry, fileField, hashField) {
  if (typeof entry[fileField] !== "string" || !/^[a-f0-9]{64}$/.test(entry[hashField] || "")) throw new Error("ASTRA manifest is missing " + fileField + "/" + hashField);
  const file = safeFile(root, entry[fileField]);
  if (hashFile(file) !== entry[hashField]) throw new Error("ASTRA provenance SHA-256 mismatch: " + fileField);
  return file;
}
function openReadOnly(file) {
  const db = new DatabaseSync(file, { readOnly: true });
  db.exec("PRAGMA query_only=ON; PRAGMA trusted_schema=OFF;");
  return db;
}
function getAstraSummary(explicitRoot) {
  const root = rootDir(explicitRoot);
  const manifest = readJson(safeFile(root, "manifest.json"));
  if (manifest.schema_version !== 1 || !Array.isArray(manifest.packs)) throw new Error("Invalid desktop research manifest");
  const entry = manifest.packs.find((item) => item.id === PACK_ID);
  if (!entry) throw new Error("ASTRA CH research pack is missing");
  if (entry.source_id !== SOURCE_ID || entry.rights_status !== "approved_by_published_ogd_terms" ||
      entry.license !== "Swiss Open Government Data (OGD)" || JSON.stringify(entry.market_scope) !== JSON.stringify(["CH"]) ||
      entry.production_import !== false || entry.ru_eaeu_applicability !== false || entry.fitment_claim !== false ||
      entry.repair_applicability !== false || entry.diagnostic_execution_allowed !== false || entry.attribution_required !== true) {
    throw new Error("ASTRA rights or CH-only boundary failed");
  }
  const database = verifyFile(root, entry, "database", "database_sha256");
  const packManifestFile = verifyFile(root, entry, "pack_manifest_file", "pack_manifest_sha256");
  const sourceManifestFile = verifyFile(root, entry, "source_manifest_file", "source_manifest_sha256");
  const attributionFile = verifyFile(root, entry, "attribution_file", "attribution_sha256");
  const rightsFile = verifyFile(root, entry, "rights_file", "rights_sha256");
  const pack = readJson(packManifestFile);
  const source = readJson(sourceManifestFile);
  const attribution = fs.readFileSync(attributionFile, "utf8");
  const rightsText = fs.readFileSync(rightsFile, "utf8");
  const rights = source.rights || {};
  const policy = source.import_policy || {};
  if (pack.pack_id !== "astra-ch-tas-vag-open-data" || pack.status !== "verified_research_only" ||
      pack.source_id !== SOURCE_ID || JSON.stringify(pack.market_scope) !== JSON.stringify(["CH"]) ||
      pack.source_manifest_sha256 !== entry.source_manifest_sha256 || pack.database?.sha256 !== entry.database_sha256 ||
      source.source_id !== SOURCE_ID || source.publisher !== "Federal Roads Office (FEDRO / ASTRA), Swiss Confederation" ||
      JSON.stringify(source.market_scope) !== JSON.stringify(["CH"]) || rights.rights_status !== "approved_by_published_ogd_terms" ||
      rights.attribution !== ATTRIBUTION || rights.evidence_url !== RIGHTS_URL || !String(rights.evidence || "").includes("2026-02-23") ||
      ["commercial_use_allowed", "display_allowed", "offline_cache_allowed", "bulk_reuse_allowed", "redistribution_allowed", "attribution_required"].some((key) => rights[key] !== true) ||
      policy.namespace !== "separate_read_only_research_pack" || policy.production_import !== false || policy.ru_eaeu_applicability !== false ||
      policy.exact_brand_match_only !== true || policy.never_cross_join_engine_and_gearbox_variants !== true ||
      !attribution.includes(ATTRIBUTION) || !rightsText.includes(ATTRIBUTION) || !rightsText.includes("CH")) {
    throw new Error("ASTRA source manifest, rights, attribution or pack identity failed");
  }
  const db = openReadOnly(database);
  try {
    const integrity = db.prepare("PRAGMA integrity_check").all();
    if (integrity.length !== 1 || Object.values(integrity[0])[0] !== "ok" || db.prepare("PRAGMA foreign_key_check").all().length) throw new Error("ASTRA SQLite integrity check failed");
    const meta = Object.fromEntries(db.prepare("SELECT key,value FROM pack_metadata").all().map((row) => [row.key, row.value]));
    if (meta.pack_status !== "verified_research_only" || meta.rights_status !== rights.rights_status || meta.market_scope !== "CH" ||
        meta.production_import !== "false" || meta.ru_eaeu_applicability !== "false" || meta.repair_applicability !== "false" ||
        meta.vin_fitment !== "false" || meta.source_revision !== pack.source_revision || meta.source_manifest_sha256 !== entry.source_manifest_sha256) {
      throw new Error("ASTRA SQLite metadata does not match pack manifest");
    }
    const counts = {
      approvals: db.prepare("SELECT count(*) AS n FROM type_approval_records").get().n,
      emissionsGearboxRows: db.prepare("SELECT count(*) AS n FROM emissions_gearbox_rows").get().n,
      linkedScopeRows: db.prepare("SELECT count(*) AS n FROM engine_gearbox_scope_links").get().n,
      exactScopeLinks: db.prepare("SELECT count(*) AS n FROM engine_gearbox_scope_links WHERE relation_precision='approval_version_exact'").get().n,
      wildcardScopeLinks: db.prepare("SELECT count(*) AS n FROM engine_gearbox_scope_links WHERE relation_precision='approval_variant_wildcard'").get().n,
      unlinkedScopeRows: db.prepare("SELECT count(*) AS n FROM emissions_gearbox_rows WHERE linked_approval_row_id IS NULL").get().n
    };
    const expected = {
      approvals: Number(pack.counts?.approval_rows?.passenger_cars?.total || 0) + Number(pack.counts?.approval_rows?.other_automobiles?.total || 0),
      emissionsGearboxRows: Number(pack.counts?.emissions_gearbox_rows?.total || 0),
      linkedScopeRows: Number(pack.counts?.linked_scope_rows || 0),
      exactScopeLinks: Number(pack.counts?.scope_link_counts?.exact || 0),
      wildcardScopeLinks: Number(pack.counts?.scope_link_counts?.wildcard || 0),
      unlinkedScopeRows: Number(pack.counts?.unlinked_scope_rows || 0)
    };
    const invalidMarket = db.prepare("SELECT (SELECT count(*) FROM type_approval_records WHERE market_scope!='CH') + (SELECT count(*) FROM emissions_gearbox_rows WHERE market_scope!='CH') + (SELECT count(*) FROM engine_gearbox_scope_links WHERE market_scope!='CH') AS n").get().n;
    const invalidClaims = db.prepare("SELECT count(*) AS n FROM engine_gearbox_scope_links WHERE factory_vag_engine_code_claim!=0 OR factory_vag_gearbox_code_claim!=0 OR production_fitment_claim!=0").get().n;
    const dtcTables = db.prepare("SELECT count(*) AS n FROM sqlite_master WHERE type='table' AND lower(name) LIKE '%dtc%'").get().n;
    if (invalidMarket || invalidClaims || dtcTables || Object.keys(expected).some((key) => expected[key] <= 0 || counts[key] !== expected[key]) ||
        counts.linkedScopeRows !== counts.exactScopeLinks + counts.wildcardScopeLinks ||
        counts.emissionsGearboxRows !== counts.linkedScopeRows + counts.unlinkedScopeRows) throw new Error("ASTRA data counts or CH-only no-fitment boundary failed");
    return {
      id: PACK_ID, sourceId: SOURCE_ID, source: "Federal Roads Office (FEDRO / ASTRA), Type Approval System (TAS)",
      sourceUrl: SOURCE_URL, rightsEvidenceUrl: RIGHTS_URL, rightsStatus: rights.rights_status,
      license: "Swiss Open Government Data (OGD)", attributionText: attribution.trim(), marketScope: "CH",
      applicabilityPrecision: "ch_type_approval_row", reviewStatus: "verified_research_only",
      productionImport: false, ruEaeuApplicability: false, exactVehicleFitment: false,
      repairApplicability: false, diagnosticExecutionAllowed: false,
      sourceRevision: pack.source_revision, sourceSnapshotDate: pack.source_snapshot_date,
      sourceSnapshotSha256: pack.source_snapshot_sha256, databaseSha256: entry.database_sha256,
      sourceManifestSha256: entry.source_manifest_sha256, packManifestSha256: entry.pack_manifest_sha256,
      attributionSha256: entry.attribution_sha256, rightsSha256: entry.rights_sha256, counts,
      note: "Swiss type-approval evidence only. engineType is an approval designation, not automatically a VAG engine code; chGearboxType is a Swiss classification, not a VAG gearbox code. No RU/EAEU, VIN, model-year, ECU, DTC or repair applicability."
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
function safeHttpsUrl(value) {
  try {
    const url = new URL(String(value || ""));
    const host = url.hostname.toLowerCase();
    return url.protocol === "https:" && (host === "astra.admin.ch" || host.endsWith(".astra.admin.ch")) ? url.toString() : null;
  } catch { return null; }
}
function searchAstraApprovals(query, limit = 25, explicitRoot) {
  const q = validateQuery(query);
  const boundedLimit = Math.max(1, Math.min(50, Number.isInteger(Number(limit)) ? Number(limit) : 25));
  const summary = getAstraSummary(explicitRoot);
  const root = rootDir(explicitRoot);
  const manifest = readJson(safeFile(root, "manifest.json"));
  const entry = manifest.packs.find((item) => item.id === PACK_ID);
  const db = openReadOnly(safeFile(root, entry.database));
  try {
    const pattern = likePattern(q);
    const sql = "SELECT a.approval_row_id, a.source_row_sha256 AS approval_record_sha256, a.source_record_locator AS approval_record_locator, " +
      "a.approval_number, a.make_name, a.commercial_name, a.type_designation, a.variant, a.version, a.engine_type_designation, " +
      "a.stamped_engine_marking, a.fuel_type, a.engine_capacity_cc, a.maximum_net_power, a.drive_type, " +
      "g.source_row_sha256 AS gearbox_record_sha256, g.source_record_locator AS gearbox_record_locator, g.gearbox_number, " +
      "g.ch_gearbox_type, g.ch_mapping, g.version_defined, g.scope_link_status, g.applicability_precision AS gearbox_applicability_precision, " +
      "l.relation_precision, l.factory_vag_engine_code_claim, l.factory_vag_gearbox_code_claim, l.production_fitment_claim " +
      "FROM type_approval_records a LEFT JOIN emissions_gearbox_rows g ON g.linked_approval_row_id=a.approval_row_id " +
      "LEFT JOIN engine_gearbox_scope_links l ON l.approval_row_id=a.approval_row_id AND l.gearbox_row_id=g.gearbox_row_id " +
      "WHERE a.market_scope='CH' AND (a.approval_number LIKE ? ESCAPE '\\' OR a.make_name LIKE ? ESCAPE '\\' OR " +
      "a.commercial_name LIKE ? ESCAPE '\\' OR a.type_designation LIKE ? ESCAPE '\\' OR a.variant LIKE ? ESCAPE '\\' OR " +
      "a.version LIKE ? ESCAPE '\\' OR a.engine_type_designation LIKE ? ESCAPE '\\' OR a.stamped_engine_marking LIKE ? ESCAPE '\\' OR " +
      "g.ch_gearbox_type LIKE ? ESCAPE '\\' OR g.ch_mapping LIKE ? ESCAPE '\\' OR g.gearbox_number LIKE ? ESCAPE '\\') " +
      "ORDER BY a.make_name, a.commercial_name, a.approval_number, g.gearbox_number LIMIT ?";
    const rows = db.prepare(sql).all(...Array(11).fill(pattern), boundedLimit);
    return rows.map((row) => ({
      id: row.approval_row_id, approvalNumber: row.approval_number, make: row.make_name,
      commercialName: row.commercial_name, typeDesignation: row.type_designation, variant: row.variant, version: row.version,
      engineTypeDesignation: row.engine_type_designation, stampedEngineMarking: row.stamped_engine_marking,
      fuelType: row.fuel_type, engineCapacityCc: row.engine_capacity_cc, maximumNetPower: row.maximum_net_power, driveType: row.drive_type,
      gearboxNumber: row.gearbox_number, gearboxClass: row.ch_gearbox_type, gearboxMapping: row.ch_mapping,
      gearboxVersionScope: row.version_defined, gearboxScopeStatus: row.scope_link_status,
      relationPrecision: row.relation_precision || row.gearbox_applicability_precision || "unlinked_scope",
      gearboxClassificationKind: "swiss_type_approval_gearbox_classification", marketScope: "CH",
      applicabilityPrecision: row.relation_precision || row.gearbox_applicability_precision || "ch_type_approval_row",
      modelYear: null, engineCode: null, gearboxCode: null, factoryVagEngineCodeClaim: false,
      factoryVagGearboxCodeClaim: false, productionFitmentClaim: false, repairApplicability: false,
      diagnosticExecutionAllowed: false, sourceRevision: summary.sourceRevision,
      sourceSnapshotSha256: summary.sourceSnapshotSha256, databaseSha256: summary.databaseSha256,
      sourceManifestSha256: summary.sourceManifestSha256, sourceRecordSha256: row.approval_record_sha256,
      gearboxRecordSha256: row.gearbox_record_sha256,
      sourceUrl: safeHttpsUrl(row.approval_record_locator) || safeHttpsUrl(row.gearbox_record_locator) || SOURCE_URL,
      warning: "Только швейцарское типовое одобрение. engineType не подтверждает заводской код двигателя VAG; chGearboxType — швейцарская классификация, не код КПП VAG. Не использовать для подтверждения комплектации, ремонта или диагностики."
    }));
  } finally { db.close(); }
}
module.exports = { getAstraSummary, searchAstraApprovals };

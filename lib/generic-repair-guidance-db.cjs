"use strict";

const fs = require("node:fs");
const path = require("node:path");
const crypto = require("node:crypto");
const { DatabaseSync } = require("node:sqlite");

const PACK_ID = "mechanicdb-generic-repair-guidance-odbl";
const PACK_DIR = "mechanicdb-generic-repair-guidance-odbl";
const SOURCE_ID = "mechanicdb-public-generic-repair-guidance";
const SOURCE_REVISION = "c788dfe9ed1517d4cd0be27f5aacb4776abf4864";
const EXPECTED_SOURCE_FILES = Object.freeze({
  "dtc_codes.csv": "2dfae2637abbe5e24ceb98506b8df26703e454989fcee631b1e64ae77c820994",
  "diagnostic_fixes.csv": "e8484473d5924bad06fd75709480edde2fd3b1e498e02d196c53c60d02031c2b"
});
const WARNING = "Общий образовательный материал MechanicDB, не VAG-specific и не OEM-процедура. Рынок UNKNOWN; применимость к модели, поколению, году, двигателю, КПП, ECU, PR-коду и VIN отсутствует. Техническая проверка не завершена, безопасность не оценена. Не выполнять как тест-план или ремонтную инструкцию; для работ использовать точную заводскую процедуру и требования безопасности.";
const VERIFIED_FILES = new Set();

function fail(message) { throw new Error(message); }
function sha256(bytes) { return crypto.createHash("sha256").update(bytes).digest("hex"); }
function sha256File(file) { return sha256(fs.readFileSync(file)); }
function readJson(file) {
  try { return JSON.parse(fs.readFileSync(file, "utf8")); }
  catch (error) { fail("Cannot read JSON " + file + ": " + error.message); }
}
function getResearchRoot(explicitRoot) {
  return path.resolve(explicitRoot || process.env.VAG_TECH_PRO_RESEARCH_DIR || path.join(process.cwd(), "data", "research"));
}
function safeFile(root, relative) {
  if (typeof relative !== "string" || !relative || path.isAbsolute(relative) || relative.includes("\\")) fail("Unsafe research path: " + String(relative));
  const base = fs.realpathSync(root);
  const candidate = path.resolve(base, relative);
  const rel = path.relative(base, candidate);
  if (!rel || rel === ".." || rel.startsWith(".." + path.sep) || path.isAbsolute(rel)) fail("Research path escaped its root: " + relative);
  const stat = fs.lstatSync(candidate);
  if (!stat.isFile() || stat.isSymbolicLink()) fail("Research artifact must be a regular non-symlink file: " + relative);
  const real = fs.realpathSync(candidate);
  const realRel = path.relative(base, real);
  if (!realRel || realRel === ".." || realRel.startsWith(".." + path.sep) || path.isAbsolute(realRel)) fail("Research artifact symlink escaped its root: " + relative);
  return real;
}
function verifyHash(root, relative, expected, label) {
  if (!/^[a-f0-9]{64}$/.test(String(expected || ""))) fail("Invalid SHA-256 for " + label);
  const file = safeFile(root, relative);
  const stat = fs.statSync(file);
  const key = file + "|" + stat.size + "|" + stat.mtimeMs + "|" + expected;
  if (VERIFIED_FILES.has(key)) return expected;
  const actual = sha256File(file);
  if (actual !== expected) fail("SHA-256 mismatch for " + label + ": expected " + expected + ", got " + actual);
  VERIFIED_FILES.add(key);
  return actual;
}
function validateQuery(value) {
  const query = String(value == null ? "" : value).trim();
  if (query.length < 2) throw new TypeError("Search query must contain at least 2 characters");
  if (query.length > 100) throw new TypeError("Search query is too long");
  return query;
}
function clampLimit(value, fallback) {
  const n = Number(value);
  if (!Number.isInteger(n)) return fallback == null ? 25 : fallback;
  return Math.max(1, Math.min(50, n));
}
function likePattern(query) { return "%" + query.replace(/[!%_]/g, function (character) { return "!" + character; }) + "%"; }
function safeHttpsUrl(value) {
  try {
    const url = new URL(String(value || ""));
    return url.protocol === "https:" ? url.toString() : null;
  } catch { return null; }
}
function openReadOnly(root, relative) {
  const file = safeFile(root, relative);
  const db = new DatabaseSync(file, { readOnly: true });
  db.exec("PRAGMA query_only=ON; PRAGMA trusted_schema=OFF;");
  return db;
}

function verifyPack(rootArg) {
  const root = getResearchRoot(rootArg);
  const rootManifestPath = safeFile(root, "manifest.json");
  const rootManifest = readJson(rootManifestPath);
  if (rootManifest.schema_version !== 1 || !Array.isArray(rootManifest.packs)) fail("Desktop research root manifest is invalid");
  const entry = rootManifest.packs.find(function (item) { return item.id === PACK_ID; });
  if (!entry) fail("Desktop research root manifest is missing " + PACK_ID);

  const manifestPath = safeFile(root, entry.source_manifest_file);
  const manifestSha = sha256File(manifestPath);
  if (manifestSha !== entry.source_manifest_sha256) fail("Generic guidance source-manifest SHA-256 mismatch");
  const manifest = readJson(manifestPath);
  if (manifest.schema_version !== 1 || manifest.pack_id !== PACK_ID || manifest.source_revision !== SOURCE_REVISION ||
      manifest.publisher !== "MechanicDB / DataEngineered" || manifest.source_repository !== "https://github.com/MechanicDB/MechanicDB-public" ||
      manifest.data_license !== "ODbL-1.0" || manifest.rights_status !== "approved_by_published_license" ||
      manifest.commercial_use_allowed !== true || manifest.display_allowed !== true || manifest.offline_cache_allowed !== true ||
      manifest.redistribution_allowed !== true || manifest.share_alike_required !== true || manifest.attribution_required !== true) {
    fail("Generic guidance pack identity, revision or published-license rights gate failed");
  }
  const scope = manifest.scope || {};
  if (scope.namespace !== "generic_sae_iso" || scope.manufacturer !== "UNKNOWN" || scope.market_scope !== "UNKNOWN" ||
      scope.applicability_level !== "generic_only" || scope.vag_specific !== false || scope.exact_vehicle_fitment !== false ||
      scope.model_generation_year_fitment !== false || scope.engine_gearbox_fitment !== false || scope.ecu_fitment !== false ||
      scope.pr_code_fitment !== false || scope.vin_fitment !== false || scope.diagnostic_execution_allowed !== false ||
      scope.oem_repair_procedure !== false || scope.technical_review_status !== "not_independently_reviewed" ||
      scope.safety_review_status !== "not_assessed") fail("Generic guidance pack scope/applicability boundary failed");
  if (manifest.counts == null || manifest.counts.generic_sae_dtc_references !== 75 || manifest.counts.generic_authored_guidance !== 275 ||
      manifest.counts.manufacturer_labelled_dtc_rows_excluded !== 15 || manifest.counts.manufacturer_labelled_guidance_rows_excluded !== 51 ||
      manifest.counts.orphan_guidance_rows !== 0 || manifest.counts.generic_dtc_descriptions_copied !== 0 ||
      manifest.counts.detailed_code_explanations_copied !== 0 || manifest.counts.replacement_parts_rows_copied !== 0 ||
      manifest.counts.cost_or_labor_estimates_copied !== 0) fail("Generic guidance pack counts/exclusion policy changed");

  const packFiles = manifest.pack_files || {};
  const databaseRelative = PACK_DIR + "/generic-repair-guidance.sqlite";
  const licenseRelative = PACK_DIR + "/LICENSE-ODbL.txt";
  const upstreamLicenseRelative = PACK_DIR + "/LICENSE-MIT.txt";
  const attributionRelative = PACK_DIR + "/ATTRIBUTION.md";
  const databaseSha = verifyHash(root, databaseRelative, manifest.database_sha256, "generic guidance SQLite");
  const licenseSha = verifyHash(root, licenseRelative, packFiles["LICENSE-ODbL.txt"] && packFiles["LICENSE-ODbL.txt"].sha256, "ODbL license");
  const upstreamLicenseSha = verifyHash(root, upstreamLicenseRelative, packFiles["LICENSE-MIT.txt"] && packFiles["LICENSE-MIT.txt"].sha256, "upstream MIT notice");
  const attributionSha = verifyHash(root, attributionRelative, packFiles["ATTRIBUTION.md"] && packFiles["ATTRIBUTION.md"].sha256, "attribution notice");
  if (manifest.database_file !== "generic-repair-guidance.sqlite" || manifest.database_sha256 !== (packFiles["generic-repair-guidance.sqlite"] && packFiles["generic-repair-guidance.sqlite"].sha256) ||
      manifest.database_sha256 !== entry.database_sha256 || entry.database !== databaseRelative ||
      entry.license !== "ODbL-1.0" || entry.license_file !== licenseRelative || entry.license_file_sha256 !== licenseSha ||
      entry.upstream_license_file !== upstreamLicenseRelative || entry.upstream_license_file_sha256 !== upstreamLicenseSha ||
      entry.attribution_file !== attributionRelative || entry.attribution_sha256 !== attributionSha ||
      entry.source_manifest_file !== PACK_DIR + "/manifest.json" || entry.source_manifest_sha256 !== manifestSha) {
    fail("Generic guidance root-manifest provenance or license pointers mismatch");
  }
  Object.entries(EXPECTED_SOURCE_FILES).forEach(function (item) {
    if (!manifest.source_files || !manifest.source_files[item[0]] || manifest.source_files[item[0]].sha256 !== item[1]) fail("Pinned MechanicDB source file hash changed: " + item[0]);
  });
  if (!/MechanicDB/i.test(fs.readFileSync(safeFile(root, attributionRelative), "utf8")) ||
      !/Open Database License\s*\(ODbL\)\s*v1\.0/i.test(fs.readFileSync(safeFile(root, licenseRelative), "utf8")) ||
      !/MIT License/i.test(fs.readFileSync(safeFile(root, upstreamLicenseRelative), "utf8"))) {
    fail("Generic guidance attribution or license notice is incomplete");
  }
  return { root: root, entry: entry, manifest: manifest, manifestSha: manifestSha, databaseSha: databaseSha, licenseSha: licenseSha, upstreamLicenseSha: upstreamLicenseSha, attributionSha: attributionSha, databaseRelative: databaseRelative };
}

function inspectDatabase(pack) {
  const db = openReadOnly(pack.root, pack.databaseRelative);
  try {
    const integrity = db.prepare("PRAGMA integrity_check").get().integrity_check;
    const foreignKeys = db.prepare("PRAGMA foreign_key_check").all();
    if (integrity !== "ok" || foreignKeys.length) fail("Generic guidance SQLite integrity/foreign-key check failed");
    const source = db.prepare("SELECT * FROM source_registry WHERE source_id=?").get(SOURCE_ID);
    if (!source || source.data_license !== "ODbL-1.0" || source.rights_status !== "approved_by_published_license" ||
        source.commercial_use_allowed !== 1 || source.display_allowed !== 1 || source.offline_cache_allowed !== 1 ||
        source.redistribution_allowed !== 1 || source.share_alike_required !== 1 || source.attribution_required !== 1 ||
        source.market_scope !== "UNKNOWN" || source.applicability_precision !== "generic_code_only" ||
        source.technical_review_status !== "not_independently_reviewed" || source.safety_review_status !== "not_assessed" ||
        source.source_revision !== pack.manifest.source_revision) fail("Generic guidance SQLite source-registry rights/provenance gate failed");

    const counts = {
      genericDtcReferences: db.prepare("SELECT count(*) AS n FROM generic_dtc_references").get().n,
      genericRepairGuidance: db.prepare("SELECT count(*) AS n FROM generic_repair_guidance").get().n,
      invalidDtcRows: db.prepare("SELECT count(*) AS n FROM generic_dtc_references WHERE namespace!='generic_sae_iso' OR manufacturer!='UNKNOWN' OR market_scope!='UNKNOWN' OR applicability_level!='generic_only' OR vag_specific!=0 OR diagnostic_execution_allowed!=0 OR technical_review_status!='not_independently_reviewed'").get().n,
      invalidGuidanceRows: db.prepare("SELECT count(*) AS n FROM generic_repair_guidance WHERE namespace!='generic_sae_iso' OR manufacturer!='UNKNOWN' OR market_scope!='UNKNOWN' OR applicability_level!='generic_only' OR vag_specific!=0 OR diagnostic_execution_allowed!=0 OR technical_review_status!='not_independently_reviewed' OR safety_review_status!='not_assessed' OR source_license!='ODbL-1.0'").get().n
    };
    if (counts.genericDtcReferences !== 75 || counts.genericRepairGuidance !== 275 || counts.invalidDtcRows || counts.invalidGuidanceRows) {
      fail("Generic guidance SQLite namespace/count gate failed: " + JSON.stringify(counts));
    }
    const sourceFiles = pack.manifest.source_files || {};
    ["generic_dtc_references", "generic_repair_guidance"].forEach(function (table) {
      const rows = db.prepare("SELECT source_file_id, source_revision, source_file_sha256, source_line_no, source_line_sha256 FROM " + table).all();
      rows.forEach(function (row) {
        const sourceFile = sourceFiles[row.source_file_id];
        if (!sourceFile || row.source_revision !== pack.manifest.source_revision || row.source_file_sha256 !== sourceFile.sha256 ||
            !Number.isInteger(row.source_line_no) || row.source_line_no < 2 || row.source_line_no > Number(sourceFile.record_count || 0) + 1 ||
            !/^[a-f0-9]{64}$/.test(row.source_line_sha256 || "")) fail("Generic guidance row provenance is incomplete in " + table);
      });
    });
    return { integrity: integrity, foreignKeyViolations: foreignKeys.length, genericDtcReferences: counts.genericDtcReferences, genericRepairGuidance: counts.genericRepairGuidance, invalidDtcRows: counts.invalidDtcRows, invalidGuidanceRows: counts.invalidGuidanceRows };
  } finally { db.close(); }
}

function getSummary(root) {
  const pack = verifyPack(root);
  const counts = inspectDatabase(pack);
  return {
    id: PACK_ID,
    kind: "generic_repair_guidance",
    license: "ODbL-1.0",
    source: pack.manifest.publisher,
    sourceUrl: pack.manifest.source_repository,
    sourceRevision: pack.manifest.source_revision,
    snapshotGeneratedAt: pack.manifest.built_at_utc,
    sourceSnapshotSha256: pack.manifest.source_snapshot_sha256,
    logicalContentSha256: pack.manifest.logical_content_sha256,
    sourceManifestSha256: pack.manifestSha,
    databaseSha256: pack.manifest.database_sha256,
    licenseSha256: pack.licenseSha,
    upstreamLicenseSha256: pack.upstreamLicenseSha,
    attributionSha256: pack.attributionSha,
    attributionText: pack.manifest.attribution_text,
    attributionRequired: true,
    shareAlikeRequired: true,
    marketScope: "UNKNOWN",
    applicabilityPrecision: "generic_code_only",
    vagSpecific: false,
    exactVehicleFitment: false,
    modelGenerationYearFitment: false,
    engineGearboxFitment: false,
    ecuFitment: false,
    diagnosticExecutionAllowed: false,
    oemRepairProcedure: false,
    technicalReviewStatus: "not_independently_reviewed",
    safetyReviewStatus: "not_assessed",
    counts: {
      genericDtcReferences: counts.genericDtcReferences,
      genericRepairGuidance: counts.genericRepairGuidance,
      manufacturerLabelledDtcRowsExcluded: pack.manifest.counts.manufacturer_labelled_dtc_rows_excluded,
      manufacturerLabelledGuidanceRowsExcluded: pack.manifest.counts.manufacturer_labelled_guidance_rows_excluded
    },
    warning: WARNING,
    limitations: pack.manifest.limitations
  };
}

function search(query, limit, root) {
  const q = validateQuery(query);
  const pack = verifyPack(root);
  inspectDatabase(pack);
  const db = openReadOnly(pack.root, pack.databaseRelative);
  try {
    const pattern = likePattern(q);
    const rows = db.prepare(
      "SELECT g.guidance_id, g.dtc_code, g.consideration_order, g.skill_level, g.title, g.instructions, g.action_type, g.rationale, " +
      "g.source_file_id, g.source_revision, g.source_file_sha256, g.source_line_no, g.source_line_sha256, " +
      "d.system_category, d.source_file_id AS dtc_source_file_id, d.source_file_sha256 AS dtc_source_file_sha256, " +
      "d.source_line_no AS dtc_source_line_no, d.source_line_sha256 AS dtc_source_line_sha256 " +
      "FROM generic_repair_guidance g JOIN generic_dtc_references d ON d.dtc_code=g.dtc_code " +
      "WHERE g.dtc_code LIKE ? ESCAPE '!' OR g.title LIKE ? ESCAPE '!' OR g.instructions LIKE ? ESCAPE '!' OR COALESCE(g.rationale,'') LIKE ? ESCAPE '!' " +
      "ORDER BY g.dtc_code, g.consideration_order LIMIT ?"
    ).all(pattern, pattern, pattern, pattern, clampLimit(limit, 25));
    const sourceFiles = pack.manifest.source_files;
    return rows.map(function (row) {
      const sourceFile = sourceFiles[row.source_file_id];
      return {
        guidanceId: row.guidance_id,
        dtcCode: row.dtc_code,
        systemCategory: row.system_category,
        considerationOrder: row.consideration_order,
        skillLevel: row.skill_level,
        title: row.title,
        instructions: row.instructions,
        actionType: row.action_type,
        rationale: row.rationale,
        sourceRevision: row.source_revision,
        sourceFile: row.source_file_id,
        sourceFileUrl: safeHttpsUrl(sourceFile && sourceFile.source_url),
        sourceFileSha256: row.source_file_sha256,
        sourceLineNo: row.source_line_no,
        sourceLineSha256: row.source_line_sha256,
        dtcSourceFile: row.dtc_source_file_id,
        dtcSourceFileSha256: row.dtc_source_file_sha256,
        dtcSourceLineNo: row.dtc_source_line_no,
        dtcSourceLineSha256: row.dtc_source_line_sha256,
        sourceSnapshotSha256: pack.manifest.source_snapshot_sha256,
        logicalContentSha256: pack.manifest.logical_content_sha256,
        sourceManifestSha256: pack.manifestSha,
        databaseSha256: pack.manifest.database_sha256,
        sourceUrl: pack.manifest.source_repository,
        sourceLicense: "ODbL-1.0",
        attributionText: pack.manifest.attribution_text,
        attributionRequired: true,
        shareAlikeRequired: true,
        namespace: "generic_sae_iso",
        manufacturer: "UNKNOWN",
        marketScope: "UNKNOWN",
        applicabilityLevel: "generic_only",
        applicabilityPrecision: "generic_code_only",
        vagSpecific: false,
        exactVehicleFitment: false,
        modelGenerationYearFitment: false,
        engineGearboxFitment: false,
        ecuFitment: false,
        diagnosticExecutionAllowed: false,
        oemRepairProcedure: false,
        technicalReviewStatus: "not_independently_reviewed",
        safetyReviewStatus: "not_assessed",
        considerationOrderIsProbability: false,
        warning: WARNING
      };
    });
  } finally { db.close(); }
}

module.exports = { getSummary: getSummary, search: search, verifyPack: verifyPack, inspectDatabase: inspectDatabase, validateQuery: validateQuery, clampLimit: clampLimit };

"use strict";

const fs = require("node:fs");
const path = require("node:path");
const crypto = require("node:crypto");
const { DatabaseSync } = require("node:sqlite");

const PACK_DIR = "wikipedia-vag-engine-code-candidates-cc-by-sa-4-0";
const HASH_RE = /^[a-f0-9]{64}$/;

function fail(message) { throw new Error(message); }
function sha256(bytes) { return crypto.createHash("sha256").update(bytes).digest("hex"); }
function sha256File(file) { return sha256(fs.readFileSync(file)); }
function readJson(file) {
  try { return JSON.parse(fs.readFileSync(file, "utf8")); }
  catch (error) { fail("Cannot read Wikipedia candidate provenance " + path.basename(file) + ": " + error.message); }
}
function getResearchRoot(explicitRoot) {
  return path.resolve(explicitRoot || process.env.VAG_TECH_PRO_RESEARCH_DIR || path.join(process.cwd(), "data", "research"));
}
function resolveRegularFile(root, relativeFile) {
  const base = fs.realpathSync(root);
  const candidate = path.resolve(base, relativeFile);
  const relative = path.relative(base, candidate);
  if (!relative || relative.startsWith(".." + path.sep) || relative === ".." || path.isAbsolute(relative)) {
    fail("Wikipedia candidate path escaped the configured research directory");
  }
  const real = fs.realpathSync(candidate);
  const realRelative = path.relative(base, real);
  if (realRelative.startsWith(".." + path.sep) || realRelative === ".." || path.isAbsolute(realRelative)) {
    fail("Wikipedia candidate symlink escaped the configured research directory");
  }
  const stat = fs.lstatSync(candidate);
  if (!stat.isFile() || stat.isSymbolicLink()) fail("Wikipedia candidate provenance entry is not a regular file");
  return real;
}
function verifyFile(root, relativeFile, expectedHash) {
  if (!HASH_RE.test(String(expectedHash || ""))) fail("Wikipedia candidate file has no valid SHA-256: " + relativeFile);
  const file = resolveRegularFile(root, relativeFile);
  if (sha256File(file) !== expectedHash) fail("Wikipedia candidate SHA-256 mismatch: " + relativeFile);
  return file;
}
function validateManifest(manifest, sourceManifest) {
  if (manifest.schema_version !== 2 || manifest.pack_id !== "wikipedia-vag-engine-code-candidates-cc-by-sa-4-0") {
    fail("Wikipedia candidate pack identity/schema mismatch");
  }
  if (manifest.source_id !== "wikipedia-vag-engine-code-lists-cc-by-sa-4-0" ||
      manifest.data_license !== "CC-BY-SA-4.0" ||
      manifest.rights_status !== "approved_by_published_license") {
    fail("Wikipedia candidate license/source rights mismatch");
  }
  for (const field of ["commercial_use_allowed", "display_allowed", "offline_cache_allowed", "bulk_reuse_allowed", "redistribution_allowed", "attribution_required", "share_alike_required", "separate_pack_required"]) {
    if (manifest[field] !== true) fail("Wikipedia candidate license obligation/permission missing: " + field);
  }
  if (manifest.market_scope !== "UNKNOWN" ||
      manifest.applicability_precision !== "community_engine_code_candidate_only" ||
      manifest.verification_status !== "community_reference_unverified" ||
      manifest.quality_review_status !== "not_approved_for_technical_use" ||
      manifest.candidate_only !== true) {
    fail("Wikipedia candidate-only market/quality boundary mismatch");
  }
  for (const field of ["product_import_allowed", "exact_vehicle_fitment", "generation_year_fitment", "engine_gearbox_fitment", "ecu_fitment", "dtc_fitment", "repair_use_allowed", "diagnostic_execution_allowed"]) {
    if (manifest[field] !== false) fail("Wikipedia candidate technical-use prohibition missing: " + field);
  }
  if (sourceManifest.schema_version !== 2 ||
      sourceManifest.source_id !== manifest.source_id ||
      sourceManifest.data_license !== "CC-BY-SA-4.0" ||
      sourceManifest.rights_status !== "approved_by_published_license" ||
      sourceManifest.market_scope !== "UNKNOWN" ||
      sourceManifest.applicability_precision !== "community_engine_code_candidate_only" ||
      sourceManifest.quality_review_status !== "not_approved_for_technical_use" ||
      sourceManifest.candidate_only?.product_import_allowed !== false ||
      sourceManifest.candidate_only?.repair_use_allowed !== false ||
      sourceManifest.candidate_only?.diagnostic_execution_allowed !== false) {
    fail("Wikipedia source-manifest candidate-only boundary mismatch");
  }
  if (!Array.isArray(sourceManifest.pages) || sourceManifest.pages.length !== 4 ||
      !Array.isArray(manifest.pages) || manifest.pages.length !== 4 ||
      !Array.isArray(manifest.quality_warnings) || manifest.quality_warnings.length < 4) {
    fail("Wikipedia candidate source revision/quality evidence is incomplete");
  }
}
function openVerifiedDatabase(root, manifest) {
  const relativeFile = PACK_DIR + "/" + manifest.database_file;
  const file = verifyFile(root, relativeFile, manifest.database_sha256);
  const db = new DatabaseSync(file, { readOnly: true });
  db.exec("PRAGMA query_only=ON; PRAGMA trusted_schema=OFF;");
  if (db.prepare("PRAGMA integrity_check").get().integrity_check !== "ok") {
    db.close();
    fail("Wikipedia candidate SQLite integrity_check failed");
  }
  if (db.prepare("PRAGMA foreign_key_check").all().length) {
    db.close();
    fail("Wikipedia candidate SQLite foreign_key_check failed");
  }
  return db;
}
function verifyPack(explicitRoot) {
  const researchRoot = getResearchRoot(explicitRoot);
  const manifestFile = resolveRegularFile(researchRoot, PACK_DIR + "/manifest.json");
  const sourceManifestFile = resolveRegularFile(researchRoot, PACK_DIR + "/source-manifest.json");
  const manifest = readJson(manifestFile);
  const sourceManifest = readJson(sourceManifestFile);
  validateManifest(manifest, sourceManifest);

  const manifestSha = sha256File(manifestFile);
  const sourceManifestSha = sha256File(sourceManifestFile);
  if (sourceManifestSha !== manifest.source_manifest_sha256) fail("Wikipedia source-manifest SHA-256 mismatch");
  if (sourceManifest.source_snapshot_sha256 !== manifest.source_snapshot_sha256) fail("Wikipedia source-snapshot SHA-256 mismatch");

  const attributionFile = verifyFile(researchRoot, PACK_DIR + "/ATTRIBUTION.md", manifest.attribution_sha256);
  const licenseNoticeFile = verifyFile(researchRoot, PACK_DIR + "/LICENSE-NOTICE.txt", manifest.license_notice_sha256);
  const evidenceFile = resolveRegularFile(researchRoot, PACK_DIR + "/build-evidence.json");
  const artifactFile = resolveRegularFile(researchRoot, PACK_DIR + "/source-artifact.zip");
  const evidence = readJson(evidenceFile);
  if (evidence.artifact_file !== "wikipedia-vag-engine-candidates.zip" ||
      sha256File(artifactFile) !== evidence.artifact_sha256 ||
      evidence.manifest?.database_sha256 !== manifest.database_sha256 ||
      evidence.manifest?.source_manifest_sha256 !== manifest.source_manifest_sha256) {
    fail("Wikipedia candidate build-artifact provenance mismatch");
  }

  const revisions = {};
  for (const page of sourceManifest.pages) {
    const revision = String(page.revision_id);
    if (!/^\d+$/.test(revision)) fail("Wikipedia source revision ID is invalid");
    revisions[page.title] = revision;
    for (const item of [
      ["wikitext", "wikitext_bytes", "wikitext_sha256"],
      ["html", "rendered_html_bytes", "rendered_html_sha256"],
    ]) {
      const relativeFile = PACK_DIR + "/source-snapshots/" + revision + "." + item[0];
      const file = verifyFile(researchRoot, relativeFile, page[item[2]]);
      if (fs.statSync(file).size !== page[item[1]]) fail("Wikipedia source snapshot byte count mismatch: " + revision + "." + item[0]);
    }
  }

  const db = openVerifiedDatabase(researchRoot, manifest);
  try {
    const tables = db.prepare("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").all().map((row) => row.name);
    if (!tables.includes("engine_code_candidates") ||
        ["dtc_codes", "repair_procedures", "wiring_diagrams", "pinouts", "ecu_fitment"].some((name) => tables.includes(name))) {
      fail("Wikipedia candidate SQLite schema boundary mismatch");
    }
    const counts = {
      sourceDocuments: db.prepare("SELECT count(DISTINCT source_revision_id) AS n FROM engine_code_candidates").get().n,
      candidateRows: db.prepare("SELECT count(*) AS n FROM engine_code_candidates").get().n,
      uniqueCandidateCodes: db.prepare("SELECT count(DISTINCT candidate_code) AS n FROM engine_code_candidates").get().n,
      sourceRowsWithCodes: db.prepare("SELECT count(*) AS n FROM (SELECT DISTINCT source_revision_id, source_row_number FROM engine_code_candidates)").get().n,
    };
    const expected = manifest.counts;
    if (counts.sourceDocuments !== expected.source_documents ||
        counts.candidateRows !== expected.candidate_rows ||
        counts.uniqueCandidateCodes !== expected.unique_candidate_codes ||
        counts.sourceRowsWithCodes !== expected.source_rows_with_codes ||
        counts.sourceDocuments !== 4 || counts.candidateRows !== 241 ||
        counts.uniqueCandidateCodes !== 241 || counts.sourceRowsWithCodes !== 64) {
      fail("Wikipedia candidate SQLite row counts mismatch");
    }
    const unsafe = db.prepare("SELECT count(*) AS n FROM engine_code_candidates WHERE market_scope<>'UNKNOWN' OR applicability_precision<>'community_engine_code_candidate_only' OR review_status<>'candidate' OR product_import_allowed<>0 OR exact_vehicle_fitment<>0 OR generation_year_fitment<>0 OR engine_gearbox_fitment<>0 OR ecu_fitment<>0 OR dtc_fitment<>0 OR repair_use_allowed<>0 OR diagnostic_execution_allowed<>0").get().n;
    if (unsafe !== 0) fail("Wikipedia candidate SQLite contains a promoted or actionable row");
    const invalidCodes = db.prepare("SELECT count(*) AS n FROM engine_code_candidates WHERE candidate_code GLOB '*[^A-Z0-9]*' OR length(candidate_code)<2 OR length(candidate_code)>5").get().n;
    if (invalidCodes !== 0) fail("Wikipedia candidate SQLite contains a malformed code token");
    const invalidRows = db.prepare("SELECT count(*) AS n FROM engine_code_candidates WHERE source_revision_id NOT IN (1383476161,1383504097,1381198237,1375791889) OR source_title='' OR source_url NOT LIKE 'https://en.wikipedia.org/w/index.php?oldid=%' OR source_row_text='' OR candidate_value_text='' OR length(source_row_sha256)<>64 OR source_snapshot_sha256<>? OR source_manifest_sha256<>?").get(manifest.source_snapshot_sha256, manifest.source_manifest_sha256).n;
    if (invalidRows !== 0) fail("Wikipedia candidate row provenance or revision boundary mismatch");
    const revisionIds = new Set(sourceManifest.pages.map((page) => Number(page.revision_id)));
    if (revisionIds.size !== 4) fail("Wikipedia candidate revision set is incomplete");
    const perRowRevisions = db.prepare("SELECT DISTINCT source_revision_id FROM engine_code_candidates").all().map((row) => row.source_revision_id);
    if (perRowRevisions.some((id) => !revisionIds.has(Number(id)))) fail("Wikipedia candidate row references an unpinned revision");
    return {
      researchRoot,
      manifest,
      sourceManifest,
      evidence,
      counts,
      revisions,
      manifestSha256: manifestSha,
      sourceManifestSha256: sourceManifestSha,
      sourceSnapshotSha256: manifest.source_snapshot_sha256,
      databaseSha256: manifest.database_sha256,
      attributionSha256: manifest.attribution_sha256,
      licenseNoticeSha256: manifest.license_notice_sha256,
      sourceArtifactSha256: evidence.artifact_sha256,
      attributionText: fs.readFileSync(attributionFile, "utf8"),
      licenseNoticeText: fs.readFileSync(licenseNoticeFile, "utf8"),
    };
  } finally {
    db.close();
  }
}
function getSummary(explicitRoot) {
  const verified = verifyPack(explicitRoot);
  return {
    packId: verified.manifest.pack_id,
    license: verified.manifest.data_license,
    licenseUrl: verified.manifest.license_url,
    rightsStatus: verified.manifest.rights_status,
    marketScope: verified.manifest.market_scope,
    applicabilityPrecision: verified.manifest.applicability_precision,
    verificationStatus: verified.manifest.verification_status,
    qualityReviewStatus: verified.manifest.quality_review_status,
    productImportAllowed: false,
    exactVehicleFitment: false,
    generationYearFitment: false,
    engineGearboxFitment: false,
    ecuFitment: false,
    dtcFitment: false,
    repairUseAllowed: false,
    diagnosticExecutionAllowed: false,
    counts: verified.counts,
    sourceRevisions: verified.revisions,
    qualityWarnings: verified.manifest.quality_warnings,
    databaseSha256: verified.databaseSha256,
    sourceManifestSha256: verified.sourceManifestSha256,
    sourceSnapshotSha256: verified.sourceSnapshotSha256,
    attributionSha256: verified.attributionSha256,
    licenseNoticeSha256: verified.licenseNoticeSha256,
    sourceArtifactSha256: verified.sourceArtifactSha256,
    attributionText: verified.attributionText,
    licenseNoticeText: verified.licenseNoticeText,
  };
}
function validateQuery(value) {
  const query = String(value ?? "").trim();
  if (query.length < 2) throw new TypeError("Введите не менее двух символов для поиска кода-кандидата.");
  if (query.length > 100) throw new TypeError("Поисковый запрос слишком длинный.");
  return query;
}
function escapeLike(value) { return "%" + value.replace(/[\\%_]/g, "\\$&") + "%"; }
function safeSourceUrl(value, revision) {
  const url = new URL(String(value || ""));
  if (url.protocol !== "https:" || url.hostname !== "en.wikipedia.org" ||
      url.pathname !== "/w/index.php" || url.searchParams.get("oldid") !== String(revision)) {
    fail("Wikipedia candidate source URL is not pinned to its revision");
  }
  return url.toString();
}
function searchCandidates(queryValue, limitValue = 25, explicitRoot) {
  const query = validateQuery(queryValue);
  const limit = Number(limitValue);
  if (!Number.isInteger(limit) || limit < 1 || limit > 50) throw new TypeError("Лимит поиска должен быть от 1 до 50.");
  const verified = verifyPack(explicitRoot);
  const db = openVerifiedDatabase(verified.researchRoot, verified.manifest);
  try {
    const pattern = escapeLike(query);
    const sql = "SELECT candidate_id, candidate_code, source_revision_id, source_title, source_url, " +
      "section_heading, source_row_kind, source_row_number, source_row_text, candidate_value_text, " +
      "source_row_sha256, source_snapshot_sha256, source_manifest_sha256, market_scope, " +
      "applicability_precision, review_status FROM engine_code_candidates " +
      "WHERE candidate_code LIKE ? ESCAPE '\\' OR source_title LIKE ? ESCAPE '\\' " +
      "OR section_heading LIKE ? ESCAPE '\\' OR source_row_text LIKE ? ESCAPE '\\' " +
      "ORDER BY candidate_code, source_revision_id, source_row_number LIMIT ?";
    const rows = db.prepare(sql).all(pattern, pattern, pattern, pattern, limit);
    return rows.map((row) => ({
      candidateId: row.candidate_id,
      candidateCode: row.candidate_code,
      sourceRevisionId: row.source_revision_id,
      sourceTitle: row.source_title,
      sourceUrl: safeSourceUrl(row.source_url, row.source_revision_id),
      sectionHeading: row.section_heading,
      sourceRowKind: row.source_row_kind,
      sourceRowNumber: row.source_row_number,
      sourceRowText: row.source_row_text,
      candidateValueText: row.candidate_value_text,
      sourceRowSha256: row.source_row_sha256,
      sourceSnapshotSha256: row.source_snapshot_sha256,
      sourceManifestSha256: row.source_manifest_sha256,
      marketScope: row.market_scope,
      applicabilityPrecision: row.applicability_precision,
      reviewStatus: row.review_status,
      productImportAllowed: false,
      exactVehicleFitment: false,
      generationYearFitment: false,
      engineGearboxFitment: false,
      ecuFitment: false,
      dtcFitment: false,
      repairUseAllowed: false,
      diagnosticExecutionAllowed: false,
    }));
  } finally {
    db.close();
  }
}

module.exports = { getSummary, searchCandidates, verifyPack };

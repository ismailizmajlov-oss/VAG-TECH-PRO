"use strict";

const fs = require("node:fs");
const path = require("node:path");
const crypto = require("node:crypto");
const { DatabaseSync } = require("node:sqlite");

const PACK_ID = "wikipedia-vag-engine-code-candidates-cc-by-sa-4-0";
const SOURCE_ID = "wikipedia-vag-engine-code-lists-cc-by-sa-4-0";
const REL = Object.freeze({
  database: "wikipedia-vag-engine-candidates/wikipedia-vag-engine-candidates.sqlite",
  packManifest: "wikipedia-vag-engine-candidates/manifest.json",
  sourceManifest: "wikipedia-vag-engine-candidates/source-manifest.json",
  attribution: "wikipedia-vag-engine-candidates/ATTRIBUTION.md",
  licenseNotice: "wikipedia-vag-engine-candidates/LICENSE-NOTICE.txt",
  provenance: "wikipedia-vag-engine-candidates/build-provenance.json",
});

function rootOf(root) {
  return path.resolve(root || process.env.VAG_TECH_PRO_RESEARCH_DIR || path.join(process.cwd(), "data", "research"));
}
function readJson(file) {
  return JSON.parse(fs.readFileSync(file, "utf8").replace(/^\uFEFF/, ""));
}
function hash(file) {
  return crypto.createHash("sha256").update(fs.readFileSync(file)).digest("hex");
}
function fileInside(root, relative) {
  const base = fs.realpathSync(root);
  const candidate = path.resolve(base, relative);
  const real = fs.realpathSync(candidate);
  const rel = path.relative(base, real);
  if (!rel || rel === ".." || rel.startsWith(".." + path.sep) || path.isAbsolute(rel)) {
    throw new Error("Wikipedia research path escaped root");
  }
  if (!fs.statSync(real).isFile()) throw new Error("Wikipedia research artifact is not a regular file");
  return real;
}
function validateQuery(value) {
  const q = String(value ?? "").trim();
  if (q.length < 2) throw new TypeError("Search query must contain at least 2 characters");
  if (q.length > 100) throw new TypeError("Search query is too long");
  return q;
}
function like(q) {
  return "%" + q.replace(/[\\%_]/g, "\\$&") + "%";
}
function limitValue(value) {
  const n = Number(value);
  return Number.isInteger(n) ? Math.max(1, Math.min(50, n)) : 25;
}

function verify(root) {
  const base = rootOf(root);
  const index = readJson(path.join(base, "manifest.json"));
  if (index.schema_version !== 1 || !Array.isArray(index.packs)) throw new Error("Invalid local research pack manifest");
  const entry = index.packs.find((p) => p.id === PACK_ID);
  if (!entry || entry.license !== "CC-BY-SA-4.0" || entry.product_import_allowed !== false ||
      entry.market_scope !== "UNKNOWN" || entry.applicability_precision !== "community_engine_code_candidate_only" ||
      entry.review_status !== "community_reference_unverified" || entry.exact_vehicle_fitment !== false ||
      entry.engine_gearbox_fitment !== false || entry.repair_use_allowed !== false ||
      entry.diagnostic_execution_allowed !== false || entry.attribution_required !== true ||
      entry.share_alike_required !== true || entry.separate_pack_required !== true) {
    throw new Error("Wikipedia candidate pack manifest boundary failed");
  }
  const fields = [
    ["database", "database_sha256"],
    ["pack_manifest_file", "pack_manifest_sha256"],
    ["source_manifest_file", "source_manifest_sha256"],
    ["attribution_file", "attribution_sha256"],
    ["license_notice_file", "license_notice_sha256"],
    ["build_provenance_file", "build_provenance_sha256"],
  ];
  const files = {};
  for (const pair of fields) {
    const fileField = pair[0], hashField = pair[1];
    const relative = entry[fileField], expected = entry[hashField];
    if (typeof relative !== "string" || !/^[a-f0-9]{64}$/.test(expected || "")) {
      throw new Error("Wikipedia candidate pack hash metadata is missing");
    }
    files[fileField] = fileInside(base, relative);
    if (hash(files[fileField]) !== expected) throw new Error("Wikipedia candidate pack SHA-256 mismatch: " + fileField);
  }

  const manifest = readJson(files.pack_manifest_file);
  const sourceManifest = readJson(files.source_manifest_file);
  if (manifest.pack_id !== PACK_ID || manifest.source_id !== SOURCE_ID ||
      manifest.data_license !== "CC-BY-SA-4.0" || manifest.rights_status !== "approved_by_published_license" ||
      manifest.commercial_use_allowed !== true || manifest.display_allowed !== true ||
      manifest.offline_cache_allowed !== true || manifest.bulk_reuse_allowed !== true ||
      manifest.redistribution_allowed !== true || manifest.attribution_required !== true ||
      manifest.share_alike_required !== true || manifest.separate_pack_required !== true ||
      manifest.market_scope !== "UNKNOWN" || manifest.applicability_precision !== "community_engine_code_candidate_only" ||
      manifest.verification_status !== "community_reference_unverified" ||
      manifest.quality_review_status !== "not_approved_for_technical_use" || manifest.candidate_only !== true ||
      manifest.product_import_allowed !== false || manifest.exact_vehicle_fitment !== false ||
      manifest.generation_year_fitment !== false || manifest.engine_gearbox_fitment !== false ||
      manifest.ecu_fitment !== false || manifest.dtc_fitment !== false || manifest.repair_use_allowed !== false ||
      manifest.diagnostic_execution_allowed !== false || manifest.source_snapshot_sha256 !== entry.source_snapshot_sha256 ||
      manifest.database_sha256 !== entry.database_sha256 || manifest.source_manifest_sha256 !== entry.source_manifest_sha256) {
    throw new Error("Wikipedia candidate pack pinned manifest mismatch");
  }
  if (!Array.isArray(manifest.pages) || manifest.pages.length !== 4 ||
      !Array.isArray(sourceManifest.pages) || sourceManifest.pages.length !== 4) {
    throw new Error("Wikipedia candidate pack source revision list is incomplete");
  }

  const db = new DatabaseSync(files.database, { readOnly: true });
  try {
    db.exec("PRAGMA query_only=ON; PRAGMA trusted_schema=OFF;");
    if (db.prepare("PRAGMA integrity_check").all()[0]?.integrity_check !== "ok" ||
        db.prepare("PRAGMA foreign_key_check").all().length) throw new Error("Wikipedia candidate SQLite integrity failure");
    const source = db.prepare("SELECT * FROM source_registry WHERE source_id=?").get(SOURCE_ID);
    const counts = {
      sourceDocuments: db.prepare("SELECT count(*) AS n FROM source_documents").get().n,
      candidateRows: db.prepare("SELECT count(*) AS n FROM engine_code_candidates").get().n,
      uniqueCandidateCodes: db.prepare("SELECT count(DISTINCT candidate_code) AS n FROM engine_code_candidates").get().n,
    };
    const invalid = db.prepare(
      "SELECT count(*) AS n FROM engine_code_candidates WHERE market_scope!='UNKNOWN' OR applicability_precision!='community_engine_code_candidate_only' OR review_status!='candidate' OR product_import_allowed!=0 OR exact_vehicle_fitment!=0 OR generation_year_fitment!=0 OR engine_gearbox_fitment!=0 OR ecu_fitment!=0 OR dtc_fitment!=0 OR repair_use_allowed!=0 OR diagnostic_execution_allowed!=0 OR length(source_row_sha256)!=64 OR source_snapshot_sha256!=? OR source_manifest_sha256!=?"
    ).get(manifest.source_snapshot_sha256, manifest.source_manifest_sha256).n;
    if (!source || source.data_license !== "CC-BY-SA-4.0" || source.rights_status !== "approved_by_published_license" ||
        source.commercial_use_allowed !== 1 || source.display_allowed !== 1 || source.offline_cache_allowed !== 1 ||
        source.bulk_reuse_allowed !== 1 || source.redistribution_allowed !== 1 || source.attribution_required !== 1 ||
        source.share_alike_required !== 1 || source.separate_pack_required !== 1 ||
        source.market_scope !== "UNKNOWN" || source.applicability_precision !== "community_engine_code_candidate_only" ||
        source.review_status !== "candidate" || source.source_snapshot_sha256 !== manifest.source_snapshot_sha256 ||
        source.source_manifest_sha256 !== manifest.source_manifest_sha256 || counts.sourceDocuments !== 4 ||
        counts.candidateRows !== 241 || counts.uniqueCandidateCodes !== 241 || invalid !== 0) {
      throw new Error("Wikipedia candidate SQLite rights/count/applicability gate failed");
    }
    const pageRows = db.prepare("SELECT revision_id,source_url,wikitext_sha256,rendered_html_sha256,source_snapshot_sha256 FROM source_documents ORDER BY revision_id").all();
    const expectedPages = [...manifest.pages].sort((a, b) => a.revision_id - b.revision_id);
    if (pageRows.length !== expectedPages.length) throw new Error("Wikipedia SQLite source document count mismatch");
    for (let i = 0; i < pageRows.length; i++) {
      const row = pageRows[i], page = expectedPages[i];
      if (row.revision_id !== page.revision_id || row.source_url !== page.source_url ||
          row.wikitext_sha256 !== page.wikitext_sha256 || row.rendered_html_sha256 !== page.rendered_html_sha256 ||
          row.source_snapshot_sha256 !== manifest.source_snapshot_sha256) {
        throw new Error("Wikipedia SQLite source revision mismatch: " + page.revision_id);
      }
    }
    return { base, entry, manifest, sourceManifest, files, counts };
  } finally {
    db.close();
  }
}

function getSummary(root) {
  const pack = verify(root);
  const attributionText = fs.readFileSync(pack.files.attribution, "utf8");
  return {
    id: PACK_ID,
    kind: "community_engine_code_candidates",
    license: "CC-BY-SA-4.0",
    licenseUrl: "https://creativecommons.org/licenses/by-sa/4.0/",
    source: "Wikipedia contributors",
    sourceUrl: "https://en.wikipedia.org/",
    status: "community_reference_unverified",
    displayStatus: "candidate_only_not_oem_verified",
    marketScope: "UNKNOWN",
    applicabilityPrecision: "community_engine_code_candidate_only",
    reviewStatus: "community_reference_unverified",
    productImportAllowed: false,
    exactVehicleFitment: false,
    engineGearboxFitment: false,
    repairUseAllowed: false,
    diagnosticExecutionAllowed: false,
    attributionRequired: true,
    shareAlikeRequired: true,
    separatePackRequired: true,
    counts: {
      candidateRows: pack.counts.candidateRows,
      uniqueCandidateCodes: pack.counts.uniqueCandidateCodes,
      sourceDocuments: pack.counts.sourceDocuments,
      sourceRowsWithCodes: pack.manifest.counts.source_rows_with_codes,
    },
    sourceRevision: pack.manifest.source_revision,
    builtAtUtc: pack.manifest.built_at_utc,
    sourceSnapshotSha256: pack.manifest.source_snapshot_sha256,
    sourceManifestSha256: pack.manifest.source_manifest_sha256,
    packManifestSha256: pack.entry.pack_manifest_sha256,
    databaseSha256: pack.manifest.database_sha256,
    sourceArtifactSha256: pack.entry.source_artifact_sha256,
    sourceArchiveSha256: pack.entry.source_archive_sha256,
    attributionSha256: pack.manifest.attribution_sha256,
    licenseNoticeSha256: pack.manifest.license_notice_sha256,
    attributionText,
    qualityWarnings: pack.manifest.quality_warnings || [],
    note: "241 community engine-code candidates from four pinned Wikipedia revisions. Market UNKNOWN; no OEM verification, exact vehicle/generation/year fitment, engine/gearbox pairing, ECU/DTC fitment, repair use or diagnostic execution.",
  };
}

function search(query, limit = 25, root) {
  const q = validateQuery(query);
  const summary = getSummary(root);
  const pack = verify(root);
  const db = new DatabaseSync(pack.files.database, { readOnly: true });
  try {
    db.exec("PRAGMA query_only=ON; PRAGMA trusted_schema=OFF;");
    const pattern = like(q);
    const rows = db.prepare(
      "SELECT c.candidate_code,c.source_revision_id,c.source_title,c.source_url,c.section_heading,c.source_row_kind,c.source_row_number,c.source_row_text,c.candidate_value_text,c.source_row_sha256,c.source_snapshot_sha256,c.source_manifest_sha256,d.revision_timestamp,d.quality_warnings_json FROM engine_code_candidates c JOIN source_documents d ON d.revision_id=c.source_revision_id WHERE c.candidate_code LIKE ? ESCAPE '\\' OR c.source_title LIKE ? ESCAPE '\\' OR COALESCE(c.section_heading,'') LIKE ? ESCAPE '\\' OR c.source_row_text LIKE ? ESCAPE '\\' OR c.candidate_value_text LIKE ? ESCAPE '\\' ORDER BY c.candidate_code,c.source_title,c.source_row_number LIMIT ?"
    ).all(pattern, pattern, pattern, pattern, pattern, limitValue(limit));
    return rows.map((row) => ({
      code: row.candidate_code,
      sourceRevisionId: row.source_revision_id,
      sourceRevision: String(row.source_revision_id),
      revisionTimestamp: row.revision_timestamp,
      sourceTitle: row.source_title,
      sourceUrl: /^https:\/\//.test(row.source_url) ? row.source_url : null,
      sectionHeading: row.section_heading,
      sourceRowKind: row.source_row_kind,
      sourceRowNumber: row.source_row_number,
      sourceRowText: row.source_row_text,
      candidateValueText: row.candidate_value_text,
      sourceRowSha256: row.source_row_sha256,
      sourceSnapshotSha256: row.source_snapshot_sha256,
      sourceManifestSha256: row.source_manifest_sha256,
      databaseSha256: summary.databaseSha256,
      packManifestSha256: summary.packManifestSha256,
      license: "CC-BY-SA-4.0",
      marketScope: "UNKNOWN",
      applicabilityPrecision: "community_engine_code_candidate_only",
      reviewStatus: "community_reference_unverified",
      productImportAllowed: false,
      exactVehicleFitment: false,
      engineGearboxFitment: false,
      ecuFitment: false,
      dtcFitment: false,
      repairUseAllowed: false,
      diagnosticExecutionAllowed: false,
      attributionRequired: true,
      shareAlikeRequired: true,
      qualityWarnings: JSON.parse(row.quality_warnings_json),
      warning: "Community candidate only. Wikipedia list pages contain source-quality warnings; this is not an OEM-confirmed VAG engine code, exact vehicle fitment, engine/gearbox pairing, repair instruction or diagnostic test plan.",
    }));
  } finally {
    db.close();
  }
}

module.exports = { getSummary, search, verify };

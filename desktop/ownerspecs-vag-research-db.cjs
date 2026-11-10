"use strict";

const fs = require("node:fs");
const path = require("node:path");
const crypto = require("node:crypto");
const { DatabaseSync } = require("node:sqlite");

const PACK_ID = "ownerspecs-vag-vehicle-specs-research";
const SOURCE_ID = "ownerspecs-verified-vehicle-specs-cc-by-sa-4.0";
const SOURCE_URL = "https://ownerspecs.com/data";
const LICENSE_ID = "CC-BY-SA-4.0";
const EXPECTED_COUNTS = { vagGenerations: 20, vagFacts: 233, sourceGenerations: 111, sourceFacts: 2369 };
const EXPECTED_TABLES = ["facts", "generations", "pack_metadata", "source_files", "source_registry"].sort();

function assert(condition, message) { if (!condition) throw new Error(message); }
function rootDir(explicitRoot) {
  return path.resolve(explicitRoot || process.env.VAG_TECH_PRO_RESEARCH_DIR || path.join(process.cwd(), "data", "research"));
}
function safeFile(root, relative) {
  if (typeof relative !== "string" || !relative || path.isAbsolute(relative) || relative.includes("\\")) throw new Error("Unsafe OwnerSpecs pack path");
  const base = fs.realpathSync(root);
  const candidate = path.resolve(base, relative);
  const rel = path.relative(base, candidate);
  if (!rel || rel === ".." || rel.startsWith(".." + path.sep) || path.isAbsolute(rel)) throw new Error("OwnerSpecs path escaped research root");
  const real = fs.realpathSync(candidate);
  const realRel = path.relative(base, real);
  if (!realRel || realRel === ".." || realRel.startsWith(".." + path.sep) || path.isAbsolute(realRel)) throw new Error("OwnerSpecs symlink escaped research root");
  if (!fs.statSync(real).isFile()) throw new Error("OwnerSpecs entry is not a regular file");
  return real;
}
function readJson(file) { return JSON.parse(fs.readFileSync(file, "utf8").replace(/^\uFEFF/, "")); }
function hashFile(file) {
  const hash = crypto.createHash("sha256");
  const fd = fs.openSync(file, "r");
  const buffer = Buffer.allocUnsafe(1024 * 1024);
  try {
    let bytes;
    do { bytes = fs.readSync(fd, buffer, 0, buffer.length, null); if (bytes > 0) hash.update(buffer.subarray(0, bytes)); } while (bytes > 0);
  } finally { fs.closeSync(fd); }
  return hash.digest("hex");
}
function verifyFile(root, entry, fileField, hashField) {
  assert(typeof entry[fileField] === "string" && /^[a-f0-9]{64}$/.test(entry[hashField] || ""), "OwnerSpecs manifest is missing " + fileField + "/" + hashField);
  const file = safeFile(root, entry[fileField]);
  assert(hashFile(file) === entry[hashField], "OwnerSpecs provenance SHA-256 mismatch: " + fileField);
  return file;
}
function openReadOnly(file) {
  const db = new DatabaseSync(file, { readOnly: true });
  db.exec("PRAGMA query_only=ON; PRAGMA trusted_schema=OFF;");
  return db;
}
function count(db, sql) { return db.prepare(sql).get().n; }

function getOwnerSpecsSummary(explicitRoot) {
  const root = rootDir(explicitRoot);
  const rootManifest = readJson(safeFile(root, "manifest.json"));
  assert(rootManifest.schema_version === 1 && Array.isArray(rootManifest.packs), "Invalid desktop research manifest");
  const entry = rootManifest.packs.find((item) => item.id === PACK_ID);
  assert(entry, "OwnerSpecs VAG research pack is missing");

  assert(
    entry.source_id === SOURCE_ID &&
    entry.publisher === "ownerspecs.com" &&
    entry.license === "CC BY-SA 4.0" &&
    entry.license_status === "approved_by_published_CC_BY_SA_4_0_for_separate_research_pack" &&
    entry.rights_status === "approved_by_published_CC_BY_SA_4_0_for_separate_research_pack" &&
    JSON.stringify(entry.market_scope) === JSON.stringify(["UNKNOWN"]) &&
    entry.applicability_precision === "publisher_generation_candidate_only" &&
    entry.review_status === "verified_research_only" &&
    entry.research_pack_ingested === true &&
    entry.product_database_ingested === false &&
    entry.data_ingested === false &&
    entry.production_import === false &&
    entry.product_import_allowed === false &&
    entry.ru_eaeu_applicability === false &&
    entry.exact_vehicle_fitment === false &&
    entry.exact_engine_code_mapping === false &&
    entry.exact_gearbox_code_mapping === false &&
    entry.exact_engine_gearbox_pair === false &&
    entry.ecu_fitment === false &&
    entry.dtc_fitment === false &&
    entry.repair_procedure_applicability === false &&
    entry.critical_technical_values_publishable === false &&
    entry.commercial_use_allowed === true &&
    entry.display_allowed === true &&
    entry.cache_allowed === true &&
    entry.bulk_reuse_allowed === true &&
    entry.redistribution_allowed === true &&
    entry.attribution_required === true &&
    entry.share_alike_required === true &&
    entry.separate_pack_required === true,
    "OwnerSpecs rights, Share-Alike or research-only applicability boundary failed"
  );

  const databaseFile = verifyFile(root, entry, "database", "database_sha256");
  const packManifestFile = verifyFile(root, entry, "pack_manifest_file", "pack_manifest_sha256");
  const sourceManifestFile = verifyFile(root, entry, "source_manifest_file", "source_manifest_sha256");
  const sourceSnapshotFile = verifyFile(root, entry, "source_snapshot_file", "source_snapshot_sha256");
  const sourceJsonFile = verifyFile(root, entry, "source_file", "source_file_sha256");
  assert(fs.statSync(sourceJsonFile).size === entry.source_file_bytes, "OwnerSpecs raw source snapshot byte size mismatch");
  const acquisitionSnapshotFile = verifyFile(root, entry, "acquisition_snapshot_file", "acquisition_snapshot_sha256");
  const attributionFile = verifyFile(root, entry, "attribution_file", "attribution_sha256");
  const licenseFile = verifyFile(root, entry, "license_file", "license_sha256");

  const pack = readJson(packManifestFile);
  const source = readJson(sourceManifestFile);
  const snapshot = readJson(sourceSnapshotFile);
  const acquisition = readJson(acquisitionSnapshotFile);
  const attribution = fs.readFileSync(attributionFile, "utf8");
  const license = fs.readFileSync(licenseFile, "utf8");

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
    pack.critical_technical_values_publishable === false &&
    pack.exact_engine_gearbox_pair === false &&
    pack.exact_vehicle_fitment === false &&
    pack.ru_eaeu_applicability === false &&
    pack.repair_procedure_applicability === false &&
    source.source_id === SOURCE_ID &&
    source.snapshot.source_snapshot_sha256 === entry.source_snapshot_sha256 &&
    source.snapshot.source_file_bytes === entry.source_file_bytes &&
    source.rights.rights_status === "approved_by_published_CC_BY_SA_4_0_for_separate_research_pack" &&
    source.rights.share_alike_required === true &&
    source.rights.separate_pack_required === true &&
    source.import_policy.production_import === false &&
    source.import_policy.product_import_allowed === false &&
    source.applicability_policy.market_scope === "UNKNOWN" &&
    source.applicability_policy.exact_engine_gearbox_pair === false &&
    source.applicability_policy.ru_eaeu_applicability === false &&
    snapshot.source_snapshot_sha256 === entry.source_snapshot_sha256 &&
    snapshot.source_file_bytes === entry.source_file_bytes &&
    acquisition.source_snapshot_sha256 === entry.source_snapshot_sha256 &&
    acquisition.retrieved_at_utc === entry.acquisition_retrieved_at_utc &&
    attribution.includes("ownerspecs.com") &&
    attribution.includes("CC BY-SA 4.0") &&
    license.includes("CC BY-SA 4.0") &&
    license.includes("must remain under CC BY-SA 4.0"),
    "OwnerSpecs pack manifest, rights, attribution or snapshot provenance failed"
  );

  const db = openReadOnly(databaseFile);
  let counts;
  try {
    const integrity = db.prepare("PRAGMA integrity_check").all();
    assert(integrity.length === 1 && Object.values(integrity[0])[0] === "ok", "OwnerSpecs SQLite integrity_check failed");
    assert(db.prepare("PRAGMA foreign_key_check").all().length === 0, "OwnerSpecs SQLite foreign_key_check failed");
    const tables = db.prepare("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name").all().map((row) => row.name).sort();
    assert(JSON.stringify(tables) === JSON.stringify(EXPECTED_TABLES), "OwnerSpecs SQLite table set mismatch");
    const registry = db.prepare("SELECT source_id,license_id,rights_status,commercial_use_allowed,display_allowed,offline_cache_allowed,bulk_reuse_allowed,redistribution_allowed,attribution_required,share_alike_required,separate_pack_required,market_scope,research_pack_only,production_import,product_import_allowed,exact_vehicle_fitment,exact_engine_code_mapping,exact_gearbox_code_mapping,exact_engine_gearbox_pair,ru_eaeu_applicability,ecu_fitment,dtc_fitment,repair_procedure_applicability,critical_technical_values_publishable FROM source_registry").get();
    assert(registry && registry.source_id === SOURCE_ID && registry.license_id === LICENSE_ID && registry.rights_status === source.rights.rights_status &&
      registry.commercial_use_allowed === 1 && registry.display_allowed === 1 && registry.offline_cache_allowed === 1 &&
      registry.bulk_reuse_allowed === 1 && registry.redistribution_allowed === 1 && registry.attribution_required === 1 &&
      registry.share_alike_required === 1 && registry.separate_pack_required === 1 && registry.market_scope === "UNKNOWN" &&
      registry.research_pack_only === 1 && registry.production_import === 0 && registry.product_import_allowed === 0 &&
      registry.exact_vehicle_fitment === 0 && registry.exact_engine_code_mapping === 0 && registry.exact_gearbox_code_mapping === 0 &&
      registry.exact_engine_gearbox_pair === 0 && registry.ru_eaeu_applicability === 0 && registry.ecu_fitment === 0 &&
      registry.dtc_fitment === 0 && registry.repair_procedure_applicability === 0 && registry.critical_technical_values_publishable === 0,
      "OwnerSpecs SQLite source registry boundary failed");
    const sourceFile = db.prepare("SELECT sha256,byte_size,generation_count,fact_count,retrieved_at_utc FROM source_files").get();
    assert(sourceFile && sourceFile.sha256 === entry.source_snapshot_sha256 && sourceFile.byte_size === entry.source_file_bytes &&
      sourceFile.generation_count === EXPECTED_COUNTS.sourceGenerations && sourceFile.fact_count === EXPECTED_COUNTS.sourceFacts &&
      sourceFile.retrieved_at_utc === entry.source_retrieved_at_utc, "OwnerSpecs SQLite source-file registry mismatch");
    const invalidGenerations = count(db, "SELECT count(*) AS n FROM generations WHERE source_id!='" + SOURCE_ID +
      "' OR publisher_verification_status!='publisher_verified' OR technical_review_status!='not_independently_reviewed' OR market_scope!='UNKNOWN' OR applicability_precision!='publisher_generation_candidate_only' OR model_generation_candidate!=1 OR model_year_candidate!=1 OR exact_vehicle_fitment!=0 OR exact_engine_code_mapping!=0 OR exact_gearbox_code_mapping!=0 OR exact_engine_gearbox_pair!=0 OR ru_eaeu_applicability!=0 OR ecu_fitment!=0 OR dtc_fitment!=0 OR repair_procedure_applicability!=0");
    const invalidFacts = count(db, "SELECT count(*) AS n FROM facts WHERE publisher_verification_status!='publisher_verified' OR technical_review_status!='not_independently_reviewed' OR market_scope!='UNKNOWN' OR applicability_precision!='publisher_generation_candidate_only' OR critical_value_publishable!=0 OR exact_engine_code_mapping!=0 OR exact_gearbox_code_mapping!=0 OR exact_engine_gearbox_pair!=0 OR ru_eaeu_applicability!=0 OR repair_procedure_applicability!=0 OR primary_document_url IS NOT NULL OR primary_document_revision IS NOT NULL");
    const badHashes = count(db, "SELECT count(*) AS n FROM facts WHERE length(source_row_sha256)!=64 OR source_row_sha256 GLOB '*[^0-9a-f]*'");
    const badGenerationHashes = count(db, "SELECT count(*) AS n FROM generations WHERE length(generation_sha256)!=64 OR generation_sha256 GLOB '*[^0-9a-f]*'");
    counts = {
      sourceGenerations: count(db, "SELECT count(*) AS n FROM generations"),
      sourceFacts: count(db, "SELECT count(*) AS n FROM facts"),
      vagGenerations: count(db, "SELECT count(*) AS n FROM generations WHERE brand IN ('Audi','Porsche','SEAT','Skoda','Volkswagen')"),
      vagFacts: count(db, "SELECT count(*) AS n FROM facts")
    };
    assert(invalidGenerations === 0 && invalidFacts === 0 && badHashes === 0 && badGenerationHashes === 0, "OwnerSpecs rows crossed the candidate-only or provenance boundary");
    assert(counts.sourceGenerations === EXPECTED_COUNTS.sourceGenerations && counts.sourceFacts === EXPECTED_COUNTS.sourceFacts &&
      counts.vagGenerations === EXPECTED_COUNTS.vagGenerations && counts.vagFacts === EXPECTED_COUNTS.vagFacts,
      "OwnerSpecs pinned research counts mismatch");
  } finally { db.close(); }

  return {
    packId: PACK_ID, counts, marketScope: "UNKNOWN",
    rightsStatus: source.rights.rights_status, license: "CC BY-SA 4.0",
    sourceUrl: SOURCE_URL, licenseUrl: source.rights.license_url,
    attributionText: source.rights.attribution_text,
    sourceRevision: entry.source_revision, sourceFileSha256: entry.source_file_sha256, sourceFileBytes: entry.source_file_bytes,
    sourceSnapshotSha256: entry.source_snapshot_sha256,
    sourceManifestSha256: entry.source_manifest_sha256, databaseSha256: entry.database_sha256,
    packManifestSha256: entry.pack_manifest_sha256, artifactSha256: entry.source_artifact_sha256,
    sourceRetrievedAtUtc: entry.source_retrieved_at_utc, acquisitionRetrievedAtUtc: entry.acquisition_retrieved_at_utc,
    counts, warning: "OwnerSpecs generation and technical facts are publisher-verified research candidates, not independently reviewed OEM repair data. Market UNKNOWN. No exact vehicle fitment, factory engine/gearbox mapping, ECU/DTC applicability or Russian/EAEU applicability is established. Critical technical values are not publishable for repair decisions.",
    productionImport: false, productImportAllowed: false, criticalTechnicalValuesPublishable: false,
    exactVehicleFitment: false, exactEngineGearboxPair: false, ruEaeuApplicability: false,
    repairProcedureApplicability: false, ecuFitment: false, dtcFitment: false
  };
}

function normalize(value) { return String(value || "").normalize("NFKC").toLowerCase().trim(); }
function searchOwnerSpecsFacts(query, limit, explicitRoot) {
  const q = normalize(query);
  const take = Number(limit);
  if (q.length < 2) throw new TypeError("Для поиска OwnerSpecs нужно минимум два символа.");
  if (q.length > 200) throw new TypeError("Поисковый запрос OwnerSpecs слишком длинный.");
  if (!Number.isInteger(take) || take < 1 || take > 50) throw new TypeError("Лимит OwnerSpecs должен быть от 1 до 50.");
  const summary = getOwnerSpecsSummary(explicitRoot);
  const root = rootDir(explicitRoot);
  const entry = readJson(safeFile(root, "manifest.json")).packs.find((item) => item.id === PACK_ID);
  const db = openReadOnly(safeFile(root, entry.database));
  try {
    const pattern = "%" + q.replace(/[\\%_]/g, "\\$&") + "%";
    const rows = db.prepare(
      "SELECT g.generation_id AS generationId,g.brand,g.model,g.generation_label AS generationLabel,g.generation_slug AS generationSlug," +
      "g.generation_url AS generationUrl,g.year_start AS yearStartCandidate,g.year_end AS yearEndCandidate,g.body_type AS bodyTypeCandidate," +
      "g.generation_sha256 AS generationSha256,f.fact_id AS factId,f.category,f.field_key AS fieldKey,f.label,f.value_json AS valueJson," +
      "f.value_max_json AS valueMaxJson,f.unit,f.is_range AS isRange,f.source_count AS sourceCount,f.provenance_json AS provenanceJson," +
      "f.source_row_sha256 AS sourceRowSha256,f.publisher_verification_status AS publisherVerificationStatus," +
      "f.technical_review_status AS technicalReviewStatus,f.market_scope AS marketScope,f.applicability_precision AS applicabilityPrecision," +
      "f.critical_value_publishable AS criticalValuePublishable,f.primary_document_url AS primaryDocumentUrl," +
      "f.primary_document_revision AS primaryDocumentRevision " +
      "FROM facts f JOIN generations g ON g.generation_id=f.generation_id " +
      "WHERE instr(lower(g.brand),?)>0 OR instr(lower(g.model),?)>0 OR instr(lower(g.generation_label),?)>0 OR " +
      "instr(lower(f.field_key),?)>0 OR instr(lower(f.label),?)>0 OR instr(lower(COALESCE(f.value_json,'')),?)>0 OR " +
      "instr(lower(COALESCE(f.value_max_json,'')),?)>0 OR instr(lower(f.provenance_json),?)>0 " +
      "ORDER BY g.brand,g.model,g.year_start,f.category,f.field_key,f.source_ordinal LIMIT ?"
    ).all(q,q,q,q,q,q,q,q,take);
    return rows.map((row) => ({
      ...row,
      value: row.valueJson === null ? null : JSON.parse(row.valueJson),
      valueMax: row.valueMaxJson === null ? null : JSON.parse(row.valueMaxJson),
      provenance: JSON.parse(row.provenanceJson || "[]"),
      sourceRevision: summary.sourceRevision,
      sourceSnapshotSha256: summary.sourceSnapshotSha256,
      sourceManifestSha256: summary.sourceManifestSha256,
      databaseSha256: summary.databaseSha256,
      packManifestSha256: summary.packManifestSha256,
      sourceArtifactSha256: summary.artifactSha256,
      license: summary.license,
      licenseUrl: summary.licenseUrl,
      attributionText: summary.attributionText,
      warning: summary.warning,
      marketScope: "UNKNOWN",
      exactVehicleFitment: false,
      exactEngineCodeMapping: false,
      exactGearboxCodeMapping: false,
      exactEngineGearboxPair: false,
      ruEaeuApplicability: false,
      criticalValuePublishable: 0,
      repairProcedureApplicability: false,
      ecuFitment: false,
      dtcFitment: false
    }));
  } finally { db.close(); }
}

module.exports = { getOwnerSpecsSummary, searchOwnerSpecsFacts };

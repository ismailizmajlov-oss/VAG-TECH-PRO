#!/usr/bin/env node
"use strict";

const fs = require("node:fs");
const path = require("node:path");
const crypto = require("node:crypto");
const { DatabaseSync } = require("node:sqlite");

const PACK_ID = "mechanicdb-vag-dtc-sample-repair-leads-odbl";
const UPSTREAM_PACK_ID = "mechanicdb-vag-dtc-candidates-odbl";
const SOURCE_ID = "mechanicdb-vag-dtc-sample-odbl";
const SOURCE_REVISION = "c788dfe9ed1517d4cd0be27f5aacb4776abf4864";
const EXPECTED_DATABASE_SHA256 = "b0708f055c485018b69263904f60f66124f90f758da9bc597f2145d46ffe5c7d";
const EXPECTED_SNAPSHOT_SHA256 = "3e1357acba252f4aa1f49b94438540b1448fb23663f5a6be5cdfd4e74f2f0eb2";
const EXPECTED_ARTIFACT_SHA256 = "aaabbb30cc3c616e8136ad31d6371073e42d8ae1c5461b67e80f921a8724d490";
const ROOT = path.resolve(__dirname, "..");
const DEFAULT_RESEARCH = path.join(ROOT, "data", "research");
const fail = (message) => { throw new Error(message); };
const sha256 = (bytes) => crypto.createHash("sha256").update(bytes).digest("hex");
const sha256File = (file) => sha256(fs.readFileSync(file));
const gitBlobSha1 = (bytes) => crypto.createHash("sha1").update(Buffer.concat([
  Buffer.from("blob " + bytes.length + "\0", "utf8"), bytes,
])).digest("hex");

function readJson(file) {
  try { return JSON.parse(fs.readFileSync(file, "utf8")); }
  catch (error) { fail("Invalid JSON " + path.basename(file) + ": " + error.message); }
}
function safeRelative(root, relative) {
  if (typeof relative !== "string" || !relative || path.isAbsolute(relative) || relative.includes("\\")) fail("Invalid relative path: " + String(relative));
  const base = path.resolve(root);
  const target = path.resolve(base, relative);
  const rel = path.relative(base, target);
  if (!rel || rel === ".." || rel.startsWith(".." + path.sep) || path.isAbsolute(rel)) fail("Path escapes root: " + relative);
  return target;
}
function normalizedGitBlobSha1(bytes) {
  const text = bytes.toString("utf8");
  if (text.includes("\r") && /\r(?!\n)/.test(text)) fail("Source text contains bare carriage returns");
  return gitBlobSha1(Buffer.from(text.replace(/\r\n/g, "\n"), "utf8"));
}
function physicalLines(bytes) {
  const lines = [];
  let start = 0;
  for (let i = 0; i < bytes.length; i += 1) {
    if (bytes[i] === 0x0a) { lines.push(bytes.subarray(start, i + 1)); start = i + 1; }
  }
  if (start < bytes.length) lines.push(bytes.subarray(start));
  return lines;
}
function parseSums(file) {
  const entries = new Map();
  for (const line of fs.readFileSync(file, "utf8").split(/\r?\n/).filter(Boolean)) {
    const match = /^([a-f0-9]{64})\s+\*?(.+)$/.exec(line);
    if (!match || entries.has(match[2].trim())) fail("Malformed or duplicate SHA256SUMS entry: " + line);
    entries.set(match[2].trim(), match[1]);
  }
  if (!entries.size) fail("SHA256SUMS.txt is empty");
  return entries;
}
function openReadOnly(file) {
  const real = fs.realpathSync(file);
  const stat = fs.statSync(real);
  if (!stat.isFile()) fail("SQLite path is not a regular file");
  const db = new DatabaseSync(real, { readOnly: true });
  db.exec("PRAGMA query_only=ON; PRAGMA trusted_schema=OFF;");
  const integrity = db.prepare("PRAGMA integrity_check").get().integrity_check;
  if (integrity !== "ok") { db.close(); fail("SQLite integrity_check failed: " + integrity); }
  const foreignKeys = db.prepare("PRAGMA foreign_key_check").all();
  if (foreignKeys.length) { db.close(); fail("SQLite has " + foreignKeys.length + " foreign-key violations"); }
  return db;
}
function verifyArtifact(input, sourceManifestPath) {
  const root = path.resolve(input);
  const manifestPath = safeRelative(root, "manifest.json");
  const sumsPath = safeRelative(root, "SHA256SUMS.txt");
  const manifestBytes = fs.readFileSync(manifestPath);
  const pack = readJson(manifestPath);
  if (pack.schema_version !== 2 || pack.pack_id !== UPSTREAM_PACK_ID || pack.source_revision !== SOURCE_REVISION) fail("Unexpected MechanicDB v2 pack identity or source revision");
  if (pack.data_license !== "ODbL-1.0" || pack.rights_status !== "approved_by_published_license" ||
      pack.commercial_use_allowed !== true || pack.display_allowed !== true || pack.cache_allowed !== true ||
      pack.redistribution_allowed !== true || pack.share_alike_required !== true || pack.attribution_required !== true) {
    fail("MechanicDB ODbL rights gate failed");
  }
  if (pack.market_scope !== "UNKNOWN" || pack.applicability_precision !== "manufacturer_make_candidate" ||
      pack.verification_status !== "community_reference_unverified" ||
      pack.product_eligibility !== "candidate_reference_only_visible_separate_namespace" ||
      pack.display_status !== "candidate_reference_visible_separate_namespace" ||
      pack.exact_vehicle_fitment !== false || pack.ecu_fitment !== false || pack.pr_code_fitment !== false ||
      pack.diagnostic_execution_allowed !== false || pack.repair_procedures_included !== false ||
      pack.community_repair_leads_included !== true || pack.community_repair_leads_verified !== false ||
      pack.oem_part_numbers_included !== false || pack.cost_or_labor_estimates_included !== false ||
      pack.external_part_search_urls_included !== false) fail("MechanicDB v2 candidate-only/display boundary changed");
  const expectedCounts = {
    manufacturer_controlled_candidates: 2, audi_candidates: 1, volkswagen_candidates: 1,
    generic_dtc_rows: 0, repair_procedure_rows: 0, part_rows: 0,
    community_repair_lead_rows: 6, community_part_candidate_rows: 6,
  };
  if (JSON.stringify(pack.counts) !== JSON.stringify(expectedCounts)) fail("MechanicDB v2 pack counts changed");
  if (pack.database_sha256 !== EXPECTED_DATABASE_SHA256 || pack.source_snapshot_sha256 !== EXPECTED_SNAPSHOT_SHA256) fail("MechanicDB v2 database/snapshot hash is not the pinned artifact");

  const sums = parseSums(sumsPath);
  const packFiles = pack.pack_files || {};
  const packFileNames = Object.keys(packFiles).sort();
  const sumsNames = [...sums.keys()].filter((name) => name !== "SHA256SUMS.txt").sort();
  if (JSON.stringify(packFileNames) !== JSON.stringify(sumsNames)) fail("SHA256SUMS and pack_files describe different file sets");
  for (const [relative, metadata] of Object.entries(packFiles)) {
    const file = safeRelative(root, relative);
    const stat = fs.lstatSync(file);
    if (!stat.isFile() || stat.isSymbolicLink()) fail("Pack entry is not a regular file: " + relative);
    const bytes = fs.readFileSync(file);
    if (bytes.length !== metadata.byte_size || sha256(bytes) !== metadata.sha256) fail("Pack file size/SHA-256 mismatch: " + relative);
    if (relative !== "SHA256SUMS.txt" && sums.get(relative) !== metadata.sha256) fail("SHA256SUMS mismatch: " + relative);
  }
  const databasePath = safeRelative(root, pack.database_path);
  if (sha256File(databasePath) !== pack.database_sha256) fail("MechanicDB v2 SQLite SHA-256 mismatch");

  const sourceFiles = pack.source_files || {};
  if (Object.keys(sourceFiles).length !== 7) fail("MechanicDB v2 source file registry must contain seven pinned files");
  for (const [relative, metadata] of Object.entries(sourceFiles)) {
    const file = safeRelative(root, relative);
    const bytes = fs.readFileSync(file);
    if (bytes.length !== metadata.byte_size || sha256(bytes) !== metadata.sha256 ||
        normalizedGitBlobSha1(bytes) !== metadata.git_blob_sha1) fail("Pinned upstream source SHA/Git blob mismatch: " + relative);
  }
  const sourceManifest = readJson(sourceManifestPath);
  if (sourceManifest.source_id !== SOURCE_ID || sourceManifest.source_revision !== SOURCE_REVISION ||
      sourceManifest.data_license !== "ODbL-1.0" || sourceManifest.rights_status !== "approved_by_published_license" ||
      sourceManifest.share_alike_required !== true || sourceManifest.attribution_required !== true ||
      sourceManifest.display_allowed !== true || sourceManifest.cache_allowed !== true ||
      sourceManifest.redistribution_allowed !== true) fail("Project source manifest rights/revision mismatch");
  for (const [name, metadata] of Object.entries(sourceManifest.source_files || {})) {
    const relative = "upstream/" + name;
    const built = sourceFiles[relative];
    if (!built || built.git_blob_sha1 !== metadata.git_blob_sha1 || built.source_url !== metadata.url) fail("Project/upstream source manifest mismatch: " + name);
  }

  for (const [sourcePath, evidenceList] of [
    ["upstream/dtc_codes.csv", pack.source_line_evidence || []],
    ["upstream/diagnostic_fixes.csv", pack.community_fix_line_evidence || []],
    ["upstream/replacement_parts.csv", pack.community_part_line_evidence || []],
  ]) {
    const bytes = fs.readFileSync(safeRelative(root, sourcePath));
    const lines = physicalLines(bytes);
    const sourceHash = sourceFiles[sourcePath].sha256;
    for (const evidence of evidenceList) {
      const line = lines[evidence.source_line_no - 1];
      if (!line || sha256(line) !== evidence.source_line_sha256 || evidence.source_file !== sourcePath) {
        fail("Source line provenance mismatch: " + sourcePath + ":" + evidence.source_line_no);
      }
      if (!sourceHash) fail("Missing source file hash: " + sourcePath);
    }
  }
  if ((pack.source_line_evidence || []).length !== 2 ||
      (pack.community_fix_line_evidence || []).length !== 6 ||
      (pack.community_part_line_evidence || []).length !== 6) fail("MechanicDB v2 line-evidence counts changed");

  const attribution = fs.readFileSync(safeRelative(root, "ATTRIBUTION.txt"), "utf8");
  const odbl = fs.readFileSync(safeRelative(root, "upstream/LICENSE-ODbL.txt"), "utf8");
  const mit = fs.readFileSync(safeRelative(root, "upstream/LICENSE-MIT.txt"), "utf8");
  if (!/MechanicDB/i.test(attribution) || !/ODbL/i.test(attribution) || !/Wal33D/i.test(attribution) ||
      !/Open Database License\s*\(ODbL\)\s*v1\.0/i.test(odbl) || !/Share-Alike/i.test(odbl) ||
      !/MIT License/i.test(mit) || !/Wal33D\s*\(Waleed Judah\)/i.test(mit)) fail("MechanicDB attribution/license notices are incomplete");

  const db = openReadOnly(databasePath);
  try {
    const tables = db.prepare("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").all().map((row) => row.name);
    const expectedTables = ["community_fix_candidates","community_part_candidates","dtc_candidates","pack_metadata","source_files","source_registry"];
    if (JSON.stringify(tables) !== JSON.stringify(expectedTables)) fail("MechanicDB v2 SQLite schema changed");
    const source = db.prepare("SELECT * FROM source_registry WHERE source_id=?").get(SOURCE_ID);
    if (!source || source.data_license !== "ODbL-1.0" || source.rights_status !== "approved_by_published_license" ||
        source.commercial_use_allowed !== 1 || source.display_allowed !== 1 || source.offline_cache_allowed !== 1 ||
        source.redistribution_allowed !== 1 || source.share_alike_required !== 1 || source.attribution_required !== 1 ||
        source.market_scope !== "UNKNOWN" || source.applicability_precision !== "manufacturer_make_candidate" ||
        source.technical_review_status !== "community_reference_unverified" || source.source_revision !== SOURCE_REVISION ||
        source.source_snapshot_sha256 !== pack.source_snapshot_sha256) fail("MechanicDB v2 embedded source registry failed");
    const dtcs = db.prepare("SELECT oem_make,dtc_code,namespace,verification_status,market_scope,applicability_precision,vehicle_fitment_claim,ecu_fitment_claim,pr_code_claim,diagnostic_execution_allowed,repair_procedure_included,oem_part_number_included FROM dtc_candidates ORDER BY oem_make").all();
    if (dtcs.length !== 2 || dtcs[0].oem_make !== "Audi" || dtcs[0].dtc_code !== "P3000" ||
        dtcs[1].oem_make !== "Volkswagen" || dtcs[1].dtc_code !== "P1128" ||
        dtcs.some((row) => row.namespace !== "manufacturer_controlled_candidate" || row.verification_status !== "community_reference_unverified" ||
          row.market_scope !== "UNKNOWN" || row.applicability_precision !== "manufacturer_make_candidate" ||
          row.vehicle_fitment_claim !== 0 || row.ecu_fitment_claim !== 0 || row.pr_code_claim !== 0 ||
          row.diagnostic_execution_allowed !== 0 || row.repair_procedure_included !== 0 || row.oem_part_number_included !== 0)) {
      fail("MechanicDB v2 DTC candidate boundary failed");
    }
    const fixes = db.prepare("SELECT fix_id,dtc_code,oem_make,fix_title,consideration_order,namespace,verification_status,market_scope,applicability_precision,diagnostic_execution_allowed,manufacturer_procedure,oem_part_number,cost_estimates_included,source_file,source_line_no,source_line_sha256,source_file_sha256,source_revision FROM community_fix_candidates ORDER BY fix_id").all();
    if (fixes.length !== 6 || fixes.some((row) => row.namespace !== "community_repair_lead" ||
        row.verification_status !== "community_reference_unverified" || row.market_scope !== "UNKNOWN" ||
        row.applicability_precision !== "manufacturer_make_candidate" || row.diagnostic_execution_allowed !== 0 ||
        row.manufacturer_procedure !== 0 || row.oem_part_number !== 0 || row.cost_estimates_included !== 0 ||
        row.source_file !== "upstream/diagnostic_fixes.csv" || row.source_revision !== SOURCE_REVISION ||
        !/^[a-f0-9]{64}$/.test(row.source_line_sha256) || !/^[a-f0-9]{64}$/.test(row.source_file_sha256))) {
      fail("MechanicDB v2 community repair-lead boundary failed");
    }
    const parts = db.prepare("SELECT part_id,namespace,verification_status,market_scope,applicability_precision,oem_part_number,source_file,source_revision FROM community_part_candidates").all();
    if (parts.length !== 6 || parts.some((row) => row.namespace !== "community_part_name_candidate" ||
        row.verification_status !== "community_reference_unverified" || row.market_scope !== "UNKNOWN" ||
        row.applicability_precision !== "manufacturer_make_candidate" || row.oem_part_number !== 0 ||
        row.source_file !== "upstream/replacement_parts.csv" || row.source_revision !== SOURCE_REVISION)) {
      fail("MechanicDB v2 generic part-name candidate boundary failed");
    }
    const metadata = Object.fromEntries(db.prepare("SELECT key,value FROM pack_metadata").all().map((row) => [row.key,row.value]));
    if (metadata.verified_repair_procedure_rows !== "0" || metadata.oem_part_number_rows !== "0" ||
        metadata.generic_dtc_rows !== "0" || metadata.diagnostic_execution_allowed !== "false" ||
        metadata.community_repair_lead_rows !== "6" || metadata.community_part_candidate_rows !== "6") {
      fail("MechanicDB v2 embedded pack metadata failed");
    }
    const sourceRows = db.prepare("SELECT relative_path,source_revision,git_blob_sha1,sha256,byte_size FROM source_files").all();
    if (sourceRows.length !== 7) fail("MechanicDB v2 SQLite source_files count mismatch");
    for (const row of sourceRows) {
      const expected = sourceFiles[row.relative_path];
      if (!expected || row.source_revision !== SOURCE_REVISION || row.git_blob_sha1 !== expected.git_blob_sha1 ||
          row.sha256 !== expected.sha256 || row.byte_size !== expected.byte_size) fail("MechanicDB v2 SQLite source_files provenance mismatch");
    }
  } finally { db.close(); }
  return { pack, sourceManifest, attribution, manifestSha256: sha256(manifestBytes), databaseSha256: pack.database_sha256 };
}

function atomicWriteJson(file, value) {
  const dir = path.dirname(file);
  const temp = path.join(dir, ".manifest.staging-" + process.pid + "-" + crypto.randomBytes(6).toString("hex"));
  const backup = path.join(dir, ".manifest.backup-" + process.pid + "-" + crypto.randomBytes(6).toString("hex"));
  fs.writeFileSync(temp, JSON.stringify(value, null, 2) + "\n", { flag: "wx" });
  let movedOld = false;
  try {
    if (fs.existsSync(file)) { fs.renameSync(file, backup); movedOld = true; }
    fs.renameSync(temp, file);
    if (movedOld) fs.rmSync(backup, { force: true });
  } catch (error) {
    if (movedOld && !fs.existsSync(file) && fs.existsSync(backup)) fs.renameSync(backup, file);
    fs.rmSync(temp, { force: true });
    throw error;
  }
}
function copyTree(source, target) {
  const stat = fs.lstatSync(source);
  if (stat.isSymbolicLink()) fail("Symlink is not allowed in MechanicDB artifact");
  if (stat.isFile()) {
    fs.mkdirSync(path.dirname(target), { recursive: true });
    fs.copyFileSync(source, target, fs.constants.COPYFILE_EXCL);
    if (sha256File(source) !== sha256File(target)) fail("Copy SHA-256 mismatch: " + source);
    return;
  }
  if (!stat.isDirectory()) fail("Unsupported MechanicDB artifact entry: " + source);
  fs.mkdirSync(target, { recursive: true });
  for (const name of fs.readdirSync(source).sort()) copyTree(path.join(source, name), path.join(target, name));
}
function parseArgs(argv) {
  const result = { input: null, sourceManifest: null, artifactSha256: null, runId: null, artifactId: null, researchRoot: DEFAULT_RESEARCH };
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === "--input") result.input = argv[++i];
    else if (arg === "--source-manifest") result.sourceManifest = argv[++i];
    else if (arg === "--artifact-sha256") result.artifactSha256 = argv[++i];
    else if (arg === "--run-id") result.runId = Number(argv[++i]);
    else if (arg === "--artifact-id") result.artifactId = Number(argv[++i]);
    else if (arg === "--research-root") result.researchRoot = argv[++i];
    else fail("Unknown argument: " + arg);
  }
  return result;
}
function integrate(args) {
  if (!args.input || !args.sourceManifest || args.artifactSha256 !== EXPECTED_ARTIFACT_SHA256 ||
      args.runId !== 41956857684 || args.artifactId !== 13383726909) fail("Usage or pinned GitHub artifact provenance mismatch");
  const input = path.resolve(args.input);
  const research = path.resolve(args.researchRoot);
  const verified = verifyArtifact(input, path.resolve(args.sourceManifest));
  const rootManifestPath = path.join(research, "manifest.json");
  const rootManifest = readJson(rootManifestPath);
  if (rootManifest.schema_version !== 1 || !Array.isArray(rootManifest.packs)) fail("Desktop research root manifest is invalid");
  const existing = rootManifest.packs.find((pack) => pack.id === PACK_ID);
  const finalDirectory = path.join(research, PACK_ID);
  if (existing) {
    if (existing.database_sha256 !== verified.databaseSha256 || existing.source_manifest_sha256 !== verified.manifestSha256 ||
        existing.source_artifact_zip_sha256 !== EXPECTED_ARTIFACT_SHA256) fail("A different repair-lead pack is already registered; refusing to overwrite it");
    return { status: "already_integrated", packId: PACK_ID, databaseSha256: verified.databaseSha256 };
  }
  if (fs.existsSync(finalDirectory)) fail("Unregistered repair-lead directory already exists; refusing to overwrite it");
  const stage = path.join(research, "." + PACK_ID + ".staging-" + process.pid + "-" + crypto.randomBytes(6).toString("hex"));
  let finalCreated = false;
  try {
    fs.mkdirSync(stage, { recursive: false });
    for (const name of fs.readdirSync(input).sort()) copyTree(path.join(input, name), path.join(stage, name));
    const projectManifestBytes = fs.readFileSync(args.sourceManifest);
    fs.writeFileSync(path.join(stage, "PROJECT-SOURCE-MANIFEST.json"), projectManifestBytes, { flag: "wx" });
    if (sha256File(path.join(stage, "manifest.json")) !== verified.manifestSha256 ||
        sha256File(path.join(stage, verified.pack.database_path)) !== verified.databaseSha256) fail("Staged repair-lead pack differs from verified artifact");
    const pack = verified.pack;
    const prefix = PACK_ID + "/";
    const entry = {
      id: PACK_ID,
      kind: "community_repair_leads_separate_namespace",
      database: prefix + pack.database_path,
      database_sha256: pack.database_sha256,
      license: "ODbL-1.0",
      license_status: "approved_by_published_license; share_alike_required",
      license_file: prefix + "upstream/LICENSE-ODbL.txt",
      license_file_sha256: pack.pack_files["upstream/LICENSE-ODbL.txt"].sha256,
      upstream_license: "MIT",
      upstream_license_file: prefix + "upstream/LICENSE-MIT.txt",
      upstream_license_file_sha256: pack.pack_files["upstream/LICENSE-MIT.txt"].sha256,
      documentation_license: "CC-BY-4.0",
      source_manifest_file: prefix + "manifest.json",
      source_manifest_sha256: verified.manifestSha256,
      project_source_manifest_file: prefix + "PROJECT-SOURCE-MANIFEST.json",
      project_source_manifest_sha256: sha256(projectManifestBytes),
      attribution_file: prefix + "ATTRIBUTION.txt",
      attribution_sha256: pack.pack_files["ATTRIBUTION.txt"].sha256,
      source_file: prefix + "upstream/diagnostic_fixes.csv",
      source_file_sha256: pack.source_files["upstream/diagnostic_fixes.csv"].sha256,
      sources_file: prefix + "upstream/SOURCES.md",
      sources_file_sha256: pack.pack_files["upstream/SOURCES.md"].sha256,
      data_dictionary_file: prefix + "upstream/DATA_DICTIONARY.md",
      data_dictionary_sha256: pack.pack_files["upstream/DATA_DICTIONARY.md"].sha256,
      sha256sums_file: prefix + "SHA256SUMS.txt",
      sha256sums_sha256: pack.pack_files["SHA256SUMS.txt"].sha256,
      source_artifact_zip_sha256: EXPECTED_ARTIFACT_SHA256,
      publisher: pack.publisher,
      dataset: "MechanicDB community repair-lead titles for Audi/Volkswagen make-labelled DTC candidates",
      source_url: pack.source_repository,
      upstream_revision: pack.source_revision,
      snapshot_date: pack.snapshot_date,
      source_snapshot_sha256: pack.source_snapshot_sha256,
      counts: pack.counts,
      market_scope: "UNKNOWN",
      applicability_precision: "manufacturer_make_candidate",
      review_status: "community_reference_unverified",
      display_status: "candidate_reference_visible_separate_namespace",
      fitment_claim: false,
      ecu_fitment_claim: false,
      pr_code_fitment_claim: false,
      execution_allowed: false,
      diagnostic_execution_allowed: false,
      repair_procedures_included: false,
      step_by_step_instructions_exposed: false,
      oem_part_numbers_included: false,
      part_names_exposed: false,
      cost_or_labor_estimates_included: false,
      share_alike_required: true,
      attribution_required: true,
      commercial_use_allowed: true,
      display_allowed: true,
      cache_allowed: true,
      redistribution_allowed: true,
      source_line_evidence: pack.source_line_evidence,
      community_fix_line_evidence: pack.community_fix_line_evidence,
      source_workflow: {
        repository: "ismailizmajlov-oss/VAG-TECH-PRO",
        branch: "automation/mechanicdb-repair-leads-run72",
        commit: "5f4f42c6660bee92f13f7950d9677aadc76f03cc",
        run_id: args.runId,
        artifact_id: args.artifactId,
        artifact_sha256: EXPECTED_ARTIFACT_SHA256,
      },
      limitations: [
        "Six community-authored repair-lead titles only; detailed steps and part names are intentionally not exposed by the desktop UI/API.",
        "Not an OEM/factory repair procedure, not a verified test plan and not safety-reviewed.",
        "No exact model, generation, year, engine, gearbox, ECU, PR-code, VIN or market applicability.",
        "The two associated DTC rows remain make-labelled community candidates, not OEM-confirmed VAG-specific codes.",
        "ODbL attribution and share-alike apply to this separate SQLite database; the upstream MIT notice is preserved.",
      ],
    };
    rootManifest.packs.push(entry);
    rootManifest.integrated_artifacts = [
      ...(Array.isArray(rootManifest.integrated_artifacts) ? rootManifest.integrated_artifacts : []),
      { pack_id: PACK_ID, artifact_zip_sha256: EXPECTED_ARTIFACT_SHA256, source_revision: SOURCE_REVISION, workflow_run_id: args.runId, artifact_id: args.artifactId },
    ];
    rootManifest.generated_at_utc = new Date().toISOString();
    fs.renameSync(stage, finalDirectory);
    finalCreated = true;
    atomicWriteJson(rootManifestPath, rootManifest);
    return {
      status: "integrated",
      packId: PACK_ID,
      databaseSha256: verified.databaseSha256,
      sourceSnapshotSha256: EXPECTED_SNAPSHOT_SHA256,
      sourceManifestSha256: verified.manifestSha256,
      projectSourceManifestSha256: sha256(fs.readFileSync(args.sourceManifest)),
      artifactSha256: EXPECTED_ARTIFACT_SHA256,
      counts: verified.pack.counts,
      diagnosticExecutionAllowed: false,
      repairProceduresIncluded: false,
    };
  } catch (error) {
    if (finalCreated) { try { fs.rmSync(finalDirectory, { recursive: true, force: true }); } catch {} }
    throw error;
  } finally {
    try { fs.rmSync(stage, { recursive: true, force: true }); } catch {}
  }
}
if (require.main === module) {
  try { console.log(JSON.stringify(integrate(parseArgs(process.argv.slice(2))), null, 2)); }
  catch (error) { console.error("MechanicDB repair-lead integration failed: " + error.message); process.exitCode = 1; }
}
module.exports = { integrate, verifyArtifact, parseArgs, PACK_ID };

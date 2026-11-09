"use strict";

const fs = require("node:fs");
const path = require("node:path");
const crypto = require("node:crypto");

function fail(message) { throw new Error(message); }
function sha256(bytes) { return crypto.createHash("sha256").update(bytes).digest("hex"); }
function sha256File(file) { return sha256(fs.readFileSync(file)); }
function readJson(file) {
  try { return JSON.parse(fs.readFileSync(file, "utf8")); }
  catch (error) { fail(`Cannot read JSON ${file}: ${error.message}`); }
}
function safeRoot(root) { return path.resolve(root); }
function safeJoin(root, relative) {
  if (typeof relative !== "string" || !relative || path.isAbsolute(relative) || relative.includes("\\")) {
    fail(`Unsafe relative path: ${String(relative)}`);
  }
  const resolved = path.resolve(root, relative);
  const prefix = root.endsWith(path.sep) ? root : `${root}${path.sep}`;
  if (resolved !== root && !resolved.startsWith(prefix)) fail(`Path escapes its root: ${relative}`);
  return resolved;
}
function hashRelative(root, relative) {
  const file = safeJoin(root, relative);
  const stat = fs.lstatSync(file);
  if (!stat.isFile() || stat.isSymbolicLink()) fail(`Expected regular file: ${relative}`);
  return sha256File(file);
}
function copyVerified(sourceRoot, sourceRelative, targetRoot, targetRelative, expectedSha) {
  const source = safeJoin(sourceRoot, sourceRelative);
  const sourceStat = fs.lstatSync(source);
  if (!sourceStat.isFile() || sourceStat.isSymbolicLink()) fail(`Pack source is not a regular file: ${sourceRelative}`);
  const actual = sha256File(source);
  if (expectedSha && actual !== expectedSha) fail(`Pack source SHA-256 mismatch: ${sourceRelative}`);
  const target = safeJoin(targetRoot, targetRelative);
  fs.mkdirSync(path.dirname(target), { recursive: true });
  fs.copyFileSync(source, target);
  if (sha256File(target) !== actual) fail(`Copied file SHA-256 mismatch: ${targetRelative}`);
  return actual;
}
function copyTreeVerified(sourceRoot, sourceRelative, targetRoot, targetRelative) {
  const source = safeJoin(sourceRoot, sourceRelative);
  const target = safeJoin(targetRoot, targetRelative);
  const stat = fs.lstatSync(source);
  if (stat.isSymbolicLink()) fail(`Symlinks are not allowed in source packs: ${sourceRelative}`);
  if (stat.isFile()) {
    fs.mkdirSync(path.dirname(target), { recursive: true });
    fs.copyFileSync(source, target);
    if (sha256File(source) !== sha256File(target)) fail(`Copy verification failed: ${sourceRelative}`);
    return;
  }
  if (!stat.isDirectory()) fail(`Unsupported source-pack entry: ${sourceRelative}`);
  fs.mkdirSync(target, { recursive: true });
  for (const name of fs.readdirSync(source).sort()) {
    copyTreeVerified(sourceRoot, path.posix.join(sourceRelative, name), targetRoot, path.posix.join(targetRelative, name));
  }
}
function fileEntry(root, relative) { return { path: relative, sha256: hashRelative(root, relative) }; }
function updateEntry(manifest, id, update) {
  const entry = manifest.packs.find((item) => item.id === id);
  if (!entry) fail(`Root research manifest is missing pack ${id}`);
  Object.assign(entry, update);
}
function atomicWriteJson(file, value) {
  const dir = path.dirname(file);
  const temp = path.join(dir, `.manifest.json.staging-${process.pid}-${crypto.randomBytes(6).toString("hex")}`);
  const backup = path.join(dir, `.manifest.json.backup-${process.pid}-${crypto.randomBytes(6).toString("hex")}`);
  const bytes = `${JSON.stringify(value, null, 2)}\n`;
  fs.writeFileSync(temp, bytes, { flag: "wx" });
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
function verifyObdex(packRoot, descriptor) {
  const sourceManifest = readJson(safeJoin(packRoot, descriptor.manifest_path));
  const report = readJson(safeJoin(packRoot, descriptor.report_path));
  if (sourceManifest.source_id !== "obdex-generic-cc0" || sourceManifest.data_license !== "CC0-1.0") fail("OBDex source manifest identity/license mismatch");
  if (sourceManifest.commit_sha !== descriptor.source_revision || sourceManifest.license_sha256 !== hashRelative(packRoot, "obdex-generic-cc0/source/LICENSE-DATA")) fail("OBDex source revision/license hash mismatch");
  const upstreamExpected = sourceManifest.expected_counts || {};
  if (upstreamExpected.generic_dtcs !== 9533 || upstreamExpected.pids_total !== 132 || upstreamExpected.searchable_generic_dtcs !== 9204 || upstreamExpected.quarantined_unresolved_namespace_rows !== 329) fail("OBDex source manifest expected counts mismatch");
  const policy = sourceManifest.source_reference_policy || {};
  if (policy.validation !== "syntax_only" || policy.external_fetch !== false || policy.rights_review !== "not_inherited_from_cc0_dataset" || policy.display_policy !== "external_reference_link_only") fail("OBDex external source-reference policy is incomplete");
  const scope = sourceManifest.scope || {};
  if (scope.dtc_namespace !== "generic_sae_iso_obd2" || scope.manufacturer_specific_codes_included !== false || scope.exact_vag_fitment !== false || scope.repair_procedures_or_pinouts_included !== false) fail("OBDex generic-only scope failed");
  const normalization = descriptor.normalization_policy || {};
  const displayPolicy = normalization.display_policy || {};
  const namespacePolicy = descriptor.namespace_policy || {};
  const allowedRanges = ["P0xxx", "P2xxx", "B0xxx", "C0xxx", "U0xxx"];
  const quarantinedRanges = ["P34xx-P39xx", "U3xxx", "B3xxx", "C3xxx"];
  if (normalization.research_pack_only !== true || normalization.normalized_product_dtc_import_allowed !== false || JSON.stringify(normalization.unverified_ranges_for_normalized_import) !== JSON.stringify(quarantinedRanges)) fail("OBDex unresolved/reserved ranges must remain excluded from normalized product DTC import");
  if (displayPolicy.policy_id !== "vag-tech-pro-dtc-namespace-ranges" || displayPolicy.policy_revision !== "run87-2026-11-08" || JSON.stringify(displayPolicy.allowed_generic_ranges) !== JSON.stringify(allowedRanges) || JSON.stringify(displayPolicy.quarantined_unresolved_ranges) !== JSON.stringify(quarantinedRanges) || displayPolicy.upstream_generic_label_is_not_authoritative !== true || displayPolicy.searchable_generic_only !== true) fail("OBDex display policy does not match the canonical DTC namespace policy");
  if (namespacePolicy.policy_id !== displayPolicy.policy_id || namespacePolicy.policy_revision !== displayPolicy.policy_revision || JSON.stringify(namespacePolicy.allowed_generic_ranges) !== JSON.stringify(allowedRanges) || JSON.stringify(namespacePolicy.quarantined_unresolved_ranges) !== JSON.stringify(quarantinedRanges) || namespacePolicy.searchable_generic_dtcs !== 9204 || namespacePolicy.quarantined_unresolved_namespace_rows !== 329 || namespacePolicy.unclassified_rows !== 0) fail("OBDex bundle namespace policy/counts are incomplete");
  if (descriptor.counts?.generic_dtcs !== 9533 || descriptor.counts?.searchable_generic_dtcs !== 9204 || descriptor.counts?.quarantined_unresolved_namespace_rows !== 329 || descriptor.counts?.pids !== 132) fail("OBDex source/searchable/quarantined counts mismatch");
  if (JSON.stringify(scope.generic_code_ranges) !== JSON.stringify(["P0xxx", "P2xxx", "P34xx", "B0xxx", "C0xxx", "U0xxx", "U3xxx"])) fail("OBDex generic code ranges are not constrained");
  if (JSON.stringify(scope.excluded_manufacturer_controlled_ranges) !== JSON.stringify(["P1xxx", "P30xx-P33xx", "P35xx-P39xx", "B1xxx-B2xxx", "C1xxx-C2xxx", "U1xxx-U2xxx"])) fail("OBDex manufacturer-controlled ranges are not excluded");
  if (report.database_sha256 !== descriptor.database_sha256 || report.integrity_check !== "ok" || report.vag_specific_dtc_rows !== 0 || report.fitment_claims !== 0 || report.production_rows !== 0 || report.generic_dtcs !== 9533 || report.pids !== 132) fail("OBDex SQLite report failed its generic-only boundary");
  if (sha256File(safeJoin(packRoot, descriptor.database_path)) !== descriptor.database_sha256) fail("OBDex database hash mismatch");
  if (sha256File(safeJoin(packRoot, descriptor.manifest_path)) !== descriptor.manifest_sha256) fail("OBDex source manifest hash mismatch");
  const sourceFiles = Object.fromEntries((sourceManifest.source_files || []).map((item) => [item.path, item.sha256]));
  if (Object.keys(sourceFiles).length !== 10) fail("OBDex source file manifest is incomplete");
  for (const item of sourceManifest.source_files) {
    const file = safeJoin(packRoot, path.posix.join("obdex-generic-cc0/source", item.path));
    if (!fs.statSync(file).isFile() || fs.statSync(file).size !== item.bytes || sha256File(file) !== item.sha256) fail(`OBDex source snapshot mismatch: ${item.path}`);
  }
  return { sourceManifest, report };
}
function verifyObdb(packRoot, descriptor) {
  const sourceManifest = readJson(safeJoin(packRoot, descriptor.manifest_path));
  if (sourceManifest.dataset_id !== "obdb-vag-signalsets-cc-by-sa" || sourceManifest.license_id !== "CC-BY-SA-4.0" || sourceManifest.share_alike_required !== true) fail("OBDb source manifest identity/license mismatch");
  if (sourceManifest.commercial_use_allowed !== true || sourceManifest.display_allowed !== true || sourceManifest.cache_allowed !== true || sourceManifest.redistribution_allowed !== true) fail("OBDb reuse rights are incomplete");
  if (sha256File(safeJoin(packRoot, descriptor.database_path)) !== descriptor.database_sha256 || sourceManifest.database_sha256 !== descriptor.database_sha256) fail("OBDb database hash mismatch");
  if (sha256File(safeJoin(packRoot, descriptor.manifest_path)) !== descriptor.manifest_sha256) fail("OBDb source manifest hash mismatch");
  if ((sourceManifest.sources || []).length !== 16) fail("OBDb pinned source registry is incomplete");
  return sourceManifest;
}
function verifyVehiclesDb(packRoot, descriptor) {
  const sourceManifest = readJson(safeJoin(packRoot, descriptor.manifest_path));
  const upstreamPath = descriptor.attribution_files[1];
  const upstream = readJson(safeJoin(packRoot, upstreamPath));
  if (sourceManifest.pack_id !== "vehiclesdb-vag-identity" || sourceManifest.dataset_license !== "CC-BY-4.0" || sourceManifest.database_sha256 !== descriptor.database_sha256) fail("VehiclesDB identity/license mismatch");
  if (sourceManifest.ru_evidence_present !== false || sourceManifest.fitment_claim !== false || sourceManifest.engine_codes_included !== false || sourceManifest.gearbox_codes_included !== false) fail("VehiclesDB market/applicability boundary failed");
  if (upstream.version !== sourceManifest.dataset_version || upstream.license !== "CC-BY-4.0") fail("VehiclesDB upstream manifest mismatch");
  if (sha256File(safeJoin(packRoot, descriptor.database_path)) !== descriptor.database_sha256 || sourceManifest.database_sha256 !== descriptor.database_sha256) fail("VehiclesDB database hash mismatch");
  if (sha256File(safeJoin(packRoot, descriptor.manifest_path)) !== descriptor.manifest_sha256) fail("VehiclesDB source manifest hash mismatch");
  return { sourceManifest, upstreamPath };
}
function sync(packRootArg, researchRootArg) {
  const packRoot = safeRoot(packRootArg);
  const researchRoot = safeRoot(researchRootArg);
  if (!fs.statSync(packRoot).isDirectory() || !fs.statSync(researchRoot).isDirectory()) fail("Pack and research roots must be existing directories");
  const index = readJson(safeJoin(packRoot, "offline-data-pack-index.json"));
  if (index.schema_version !== 1 || index.bundle_status !== "verified_offline_data_packs_not_installer" || index.target_platform !== "windows-x64" || index.database_count !== 3) fail("Offline data-pack index is not a verified Windows x64 three-database bundle");
  const byId = Object.fromEntries((index.packs || []).map((item) => [item.pack_id, item]));
  const required = ["obdex-generic-cc0", "obdb-vag-signals-cc-by-sa", "vehiclesdb-vag-identity"];
  for (const id of required) if (!byId[id]) fail(`Offline data-pack bundle is missing ${id}`);
  for (const sourceId of ["wal33d-vag-oem-dtc-mit", "gor3a-vehicle-makes-models-odbl", "vag-wiki-community-technical-hub"]) {
    if (!(index.excluded_sources || []).some((item) => item.source_id === sourceId && item.included === false)) fail(`Restricted source is not explicitly excluded: ${sourceId}`);
  }
  for (const item of index.bundle_files || []) {
    const file = safeJoin(packRoot, item.path);
    const stat = fs.lstatSync(file);
    if (!stat.isFile() || stat.isSymbolicLink() || stat.size !== item.byte_size || sha256File(file) !== item.sha256) fail(`Offline bundle file hash/size mismatch: ${item.path}`);
  }

  const ob = byId["obdex-generic-cc0"];
  const obdb = byId["obdb-vag-signals-cc-by-sa"];
  const vehicles = byId["vehiclesdb-vag-identity"];
  const obVerified = verifyObdex(packRoot, ob);
  const obdbManifest = verifyObdb(packRoot, obdb);
  const vehiclesVerified = verifyVehiclesDb(packRoot, vehicles);

  for (const descriptor of [ob, obdb, vehicles]) {
    const sourceDir = safeJoin(packRoot, descriptor.relative_dir);
    const targetDir = safeJoin(researchRoot, descriptor.pack_id);
    copyTreeVerified(packRoot, descriptor.relative_dir, researchRoot, descriptor.pack_id);
  }

  const obBase = "obdex-generic-cc0";
  const obLicenseSource = ob.license_files[0];
  const obManifestTarget = `${obBase}/source-snapshot-manifest.json`;
  const obReportTarget = `${obBase}/acquisition-report.json`;
  const obLicenseTarget = `${obBase}/LICENSE-DATA`;
  const obDatabaseTarget = `${obBase}/generic-obdex-research.sqlite`;
  const obManifestSha = copyVerified(packRoot, ob.manifest_path, researchRoot, obManifestTarget, ob.manifest_sha256);
  const obReportSha = copyVerified(packRoot, ob.report_path, researchRoot, obReportTarget);
  const obLicenseSha = copyVerified(packRoot, obLicenseSource, researchRoot, obLicenseTarget);
  if (obLicenseSha !== obVerified.sourceManifest.license_sha256) fail("OBDex copied data-license hash mismatch");
  const obDatabaseSha = copyVerified(packRoot, ob.database_path, researchRoot, obDatabaseTarget, ob.database_sha256);

  const rootManifestPath = safeJoin(researchRoot, "manifest.json");
  const rootManifest = readJson(rootManifestPath);
  if (rootManifest.schema_version !== 1 || !Array.isArray(rootManifest.packs)) fail("Root desktop research manifest schema mismatch");

  const obSource = obVerified.sourceManifest;
  updateEntry(rootManifest, "obdex-generic-cc0", {
    database: obDatabaseTarget,
    database_sha256: obDatabaseSha,
    license_file: obLicenseTarget,
    license_file_sha256: obLicenseSha,
    license: "CC0-1.0",
    license_status: "upstream_data_license_verified",
    source_manifest_file: obManifestTarget,
    source_manifest_sha256: obManifestSha,
    acquisition_report_file: obReportTarget,
    acquisition_report_sha256: obReportSha,
    publisher: obSource.publisher,
    dataset: "OBDex",
    source_url: obSource.repository,
    upstream_revision: obSource.commit_sha,
    snapshot_generated_at_utc: obSource.generated_at_utc,
    source_file_sha256: Object.fromEntries(obSource.source_files.map((item) => [item.path, item.sha256])),
    counts: {
      generic_dtcs: obVerified.report.generic_dtcs,
      searchable_generic_dtcs: obdex.counts.searchable_generic_dtcs,
      quarantined_unresolved_namespace_rows: obdex.counts.quarantined_unresolved_namespace_rows,
      pids: obVerified.report.pids
    },
    namespace_policy: obdex.namespace_policy,
    market_scope: obSource.scope.market_scope,
    applicability_precision: "generic_code_only_no_vehicle_fitment",
    review_status: "research_only",
    fitment_claim: false,
    execution_allowed: false,
    commercial_use_allowed: true,
    display_allowed: true,
    cache_allowed: true,
    redistribution_allowed: true,
    source_reference_policy: obSource.source_reference_policy,
    limitations: [
      "Generic SAE/ISO OBD-II only; never VAG-specific.",
      "No exact vehicle/ECU fitment or vehicle-specific test plan.",
      "No repair procedure, pinout, torque value or adaptation is provided.",
      "External references are syntax-validated only; they are not fetched, displayed or re-licensed by the CC0 data grant.",
      "Upstream-labelled P34xx-P39xx, U3xxx, B3xxx and C3xxx rows remain in the source snapshot but are quarantined from the searchable generic DTC catalog."
    ]
  });

  const obdbLicensePath = obdb.license_files[0];
  const obdbAttributionPath = obdb.attribution_files[0];
  const obdbDatabaseSha = hashRelative(researchRoot, obdb.database_path);
  updateEntry(rootManifest, "obdb-vag-signals-cc-by-sa", {
    database: obdb.database_path,
    database_sha256: obdbDatabaseSha,
    license_file: obdbLicensePath,
    license_file_sha256: hashRelative(researchRoot, obdbLicensePath),
    license: "CC-BY-SA-4.0",
    license_status: obdbManifest.license_status,
    source_manifest_file: obdb.manifest_path,
    source_manifest_sha256: hashRelative(researchRoot, obdb.manifest_path),
    attribution_file: obdbAttributionPath,
    attribution_sha256: hashRelative(researchRoot, obdbAttributionPath),
    publisher: "OBDb community contributors",
    dataset: "OBDb VAG signalsets",
    source_url: "https://github.com/OBDb",
    upstream_revision: "multiple pinned repository commits; see source manifest",
    snapshot_generated_at_utc: obdbManifest.generated_at_utc,
    counts: obdbManifest.counts,
    market_scope: "UNKNOWN",
    applicability_precision: "vehicle_model_candidate",
    review_status: "research_only",
    fitment_claim: false,
    execution_allowed: false,
    share_alike_required: true,
    attribution_required: true,
    commercial_use_allowed: true,
    display_allowed: true,
    cache_allowed: true,
    redistribution_allowed: true,
    source_revisions: Object.fromEntries(obdbManifest.sources.map((item) => [item.source_id, item.commit_sha])),
    limitations: obdbManifest.limitations
  });

  const vehiclesSource = vehiclesVerified.sourceManifest;
  const vehiclesLicensePath = vehicles.license_files[0];
  const vehiclesAttributionPath = vehicles.attribution_files[0];
  const vehiclesUpstreamPath = vehiclesVerified.upstreamPath;
  updateEntry(rootManifest, "vehiclesdb-vag-identity", {
    database: vehicles.database_path,
    database_sha256: vehicles.database_sha256,
    license_file: vehiclesLicensePath,
    license_file_sha256: hashRelative(researchRoot, vehiclesLicensePath),
    license: "CC-BY-4.0",
    license_status: vehiclesSource.rights_status,
    source_manifest_file: vehicles.manifest_path,
    source_manifest_sha256: hashRelative(researchRoot, vehicles.manifest_path),
    upstream_manifest_file: vehiclesUpstreamPath,
    upstream_manifest_sha256: hashRelative(researchRoot, vehiclesUpstreamPath),
    attribution_file: vehiclesAttributionPath,
    attribution_sha256: hashRelative(researchRoot, vehiclesAttributionPath),
    publisher: vehiclesSource.publisher,
    dataset: "VehiclesDB VAG identity projection",
    source_url: vehiclesSource.source_repository,
    upstream_revision: vehiclesSource.upstream_tag,
    snapshot_generated_at_utc: index.built_at_utc,
    source_file_sha256: vehiclesSource.source_snapshot_sha256,
    counts: vehiclesSource.counts,
    make_counts: vehiclesSource.make_counts,
    market_scope: vehiclesSource.market_scope_countries,
    applicability_precision: vehiclesSource.applicability_precision,
    review_status: "identity_candidate",
    fitment_claim: false,
    execution_allowed: false,
    attribution_required: true,
    commercial_use_allowed: true,
    display_allowed: true,
    cache_allowed: true,
    redistribution_allowed: true,
    ru_evidence_present: false,
    limitations: vehicles.warnings
  });

  rootManifest.generated_at_utc = index.built_at_utc;
  rootManifest.target_platform = "windows-x64";
  rootManifest.source_commit_sha = index.source_commit_sha;
  rootManifest.workflow_run_id = index.workflow_run_id;
  rootManifest.offline_data_pack_bundle_id = index.bundle_id;
  rootManifest.offline_data_pack_source_commit_sha = index.source_commit_sha;
  rootManifest.offline_data_pack_workflow_run_id = index.workflow_run_id;
  rootManifest.license_separation_policy = index.license_separation_policy;
  const excludedById = new Map((rootManifest.excluded_sources || []).map((item) => [item.source_id, item]));
  for (const item of index.excluded_sources || []) excludedById.set(item.source_id, item);
  rootManifest.excluded_sources = [...excludedById.values()];
  rootManifest.product_import_policy = [...new Set([...(rootManifest.product_import_policy || []), ...(index.product_import_policy || [])])];
  atomicWriteJson(rootManifestPath, rootManifest);

  for (const entry of rootManifest.packs.filter((item) => required.includes(item.id))) {
    if (entry.database && entry.database_sha256 && hashRelative(researchRoot, entry.database) !== entry.database_sha256) fail(`Final research database hash mismatch: ${entry.id}`);
    for (const [fileKey, hashKey] of [["license_file", "license_file_sha256"], ["source_manifest_file", "source_manifest_sha256"], ["acquisition_report_file", "acquisition_report_sha256"], ["attribution_file", "attribution_sha256"], ["upstream_manifest_file", "upstream_manifest_sha256"]]) {
      if (entry[fileKey] && entry[hashKey] && hashRelative(researchRoot, entry[fileKey]) !== entry[hashKey]) fail(`Final research provenance hash mismatch: ${entry.id}/${fileKey}`);
    }
  }

  return {
    status: "synchronized_verified",
    bundle_run_id: String(index.workflow_run_id),
    source_commit_sha: index.source_commit_sha,
    database_count: index.database_count,
    packs: required.map((id) => ({ id, database_sha256: rootManifest.packs.find((item) => item.id === id).database_sha256 }))
  };
}

function parseArgs(argv) {
  const result = {};
  for (let i = 0; i < argv.length; i += 1) {
    const key = argv[i];
    if (!["--pack-dir", "--research-dir"].includes(key)) fail(`Unknown argument: ${key}`);
    if (!argv[i + 1] || argv[i + 1].startsWith("--")) fail(`${key} requires a value`);
    result[key] = argv[++i];
  }
  if (!result["--pack-dir"] || !result["--research-dir"]) fail("Both --pack-dir and --research-dir are required");
  return result;
}

if (require.main === module) {
  try {
    const args = parseArgs(process.argv.slice(2));
    const result = sync(args["--pack-dir"], args["--research-dir"]);
    process.stdout.write(`${JSON.stringify(result, null, 2)}\n`);
  } catch (error) {
    process.stderr.write(`${error.stack || error.message}\n`);
    process.exitCode = 1;
  }
}

module.exports = { sync };
"use strict";

const fs = require("node:fs");
const path = require("node:path");
const crypto = require("node:crypto");

const ROOT = path.resolve(__dirname);
const DESKTOP = path.resolve(ROOT, process.argv[2] || "desktop-source");
const RESEARCH = path.join(DESKTOP, "data", "research");
const PACK_ID = "mechanicdb-vag-dtc-sample-repair-leads-odbl";
const DATABASE_SHA256 = "b0708f055c485018b69263904f60f66124f90f758da9bc597f2145d46ffe5c7d";
const SNAPSHOT_SHA256 = "3e1357acba252f4aa1f49b94438540b1448fb23663f5a6be5cdfd4e74f2f0eb2";
const MANIFEST_SHA256 = "aaabbb30cc3c616e8136ad31d6371073e42d8ae1c5461b67e80f921a8724d490";
const SOURCE_REVISION = "c788dfe9ed1517d4cd0be27f5aacb4776abf4864";
const fail = (message) => { throw new Error("[run75] " + message); };
const sha256 = (bytes) => crypto.createHash("sha256").update(bytes).digest("hex");
const sha256File = (file) => sha256(fs.readFileSync(file));
function readText(file) {
  if (!fs.existsSync(file)) fail("Required file missing: " + path.relative(DESKTOP, file));
  return fs.readFileSync(file, "utf8").replace(/\r\n/g, "\n");
}
function readJson(file) {
  try { return JSON.parse(readText(file)); }
  catch (error) { fail("Invalid JSON " + path.relative(DESKTOP, file) + ": " + error.message); }
}
function writeText(file, value) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, value.replace(/\r\n/g, "\n"), "utf8");
}
function exact(source, before, after, label) {
  if (source.includes(after)) return source;
  const count = source.split(before).length - 1;
  if (count !== 1) fail(label + ": expected one anchor, found " + count);
  return source.replace(before, after);
}
function addFile(file, value) {
  if (fs.existsSync(file)) {
    if (readText(file) !== value.replace(/\r\n/g, "\n")) fail("Refusing to overwrite a different file: " + path.relative(DESKTOP, file));
    return;
  }
  writeText(file, value);
}
function verifyIntegratedPack() {
  const rootManifest = readJson(path.join(RESEARCH, "manifest.json"));
  const entry = rootManifest.packs.find((item) => item.id === PACK_ID);
  if (!entry || entry.database_sha256 !== DATABASE_SHA256 ||
      entry.source_snapshot_sha256 !== SNAPSHOT_SHA256 ||
      entry.source_artifact_zip_sha256 !== MANIFEST_SHA256 ||
      entry.review_status !== "community_reference_unverified" ||
      entry.market_scope !== "UNKNOWN" ||
      entry.applicability_precision !== "manufacturer_make_candidate" ||
      entry.diagnostic_execution_allowed !== false ||
      entry.repair_procedures_included !== false ||
      entry.oem_part_numbers_included !== false ||
      entry.step_by_step_instructions_exposed !== false) fail("Pinned MechanicDB repair-lead pack is not transactionally integrated with the expected safety boundary");
  const packDir = path.join(RESEARCH, PACK_ID);
  const pack = readJson(path.join(packDir, "manifest.json"));
  if (pack.database_sha256 !== DATABASE_SHA256 || pack.source_snapshot_sha256 !== SNAPSHOT_SHA256 ||
      pack.source_revision !== SOURCE_REVISION || pack.community_repair_leads_verified !== false ||
      pack.diagnostic_execution_allowed !== false || pack.repair_procedures_included !== false ||
      pack.counts?.community_repair_lead_rows !== 6 || pack.counts?.community_part_candidate_rows !== 6) {
    fail("MechanicDB v2 pack manifest does not match the pinned candidate-only release");
  }
  if (!fs.existsSync(path.join(packDir, "PROJECT-SOURCE-MANIFEST.json"))) fail("Project source manifest was not retained with the offline pack");
  return { rootManifest, entry, pack };
}

function patchDatabase() {
  const dbPath = path.join(DESKTOP, "lib", "local-research-db.cjs");
  let db = readText(dbPath);
  const descriptor = [
    '  mechanicdbRepairLeads: Object.freeze({',
    '    id: "mechanicdb-vag-dtc-sample-repair-leads-odbl",',
    '    file: "mechanicdb-vag-dtc-sample-repair-leads-odbl/mechanicdb-vag-dtc-candidates.sqlite",',
    '    manifest: "mechanicdb-vag-dtc-sample-repair-leads-odbl/manifest.json",',
    '    projectSourceManifest: "mechanicdb-vag-dtc-sample-repair-leads-odbl/PROJECT-SOURCE-MANIFEST.json",',
    '    attribution: "mechanicdb-vag-dtc-sample-repair-leads-odbl/ATTRIBUTION.txt",',
    '    licenseFile: "mechanicdb-vag-dtc-sample-repair-leads-odbl/upstream/LICENSE-ODbL.txt",',
    '    upstreamLicenseFile: "mechanicdb-vag-dtc-sample-repair-leads-odbl/upstream/LICENSE-MIT.txt",',
    '    sourceFile: "mechanicdb-vag-dtc-sample-repair-leads-odbl/upstream/diagnostic_fixes.csv",',
    '    sourcesFile: "mechanicdb-vag-dtc-sample-repair-leads-odbl/upstream/SOURCES.md",',
    '    dataDictionaryFile: "mechanicdb-vag-dtc-sample-repair-leads-odbl/upstream/DATA_DICTIONARY.md",',
    '    sha256sumsFile: "mechanicdb-vag-dtc-sample-repair-leads-odbl/SHA256SUMS.txt",',
    '    license: "ODbL-1.0", source: "MechanicDB / MechanicDB-public", sourceUrl: "https://github.com/MechanicDB/MechanicDB-public",',
    '    scope: "Six community repair-lead titles only; not OEM procedures, not safety-reviewed, market UNKNOWN; no exact vehicle/ECU fitment",',
    '  }),'
  ].join("\n");
  if (!db.includes('id: "mechanicdb-vag-dtc-sample-repair-leads-odbl"')) {
    db = exact(db, "\n});\n\nfunction getResearchRoot", "\n" + descriptor + "\n});\n\nfunction getResearchRoot", "MechanicDB repair-lead PACKS descriptor");
  }

  const functions = [
    "function getMechanicDbRepairLeadsSummary(root) {",
    "  const rootPack = verifyPackDatabaseHash(root, PACKS.mechanicdbRepairLeads.id, PACKS.mechanicdbRepairLeads.file);",
    "  for (const [fileField, hashField] of [[\"license_file\", \"license_file_sha256\"], [\"upstream_license_file\", \"upstream_license_file_sha256\"], [\"source_manifest_file\", \"source_manifest_sha256\"], [\"project_source_manifest_file\", \"project_source_manifest_sha256\"], [\"attribution_file\", \"attribution_sha256\"], [\"source_file\", \"source_file_sha256\"], [\"sources_file\", \"sources_file_sha256\"], [\"data_dictionary_file\", \"data_dictionary_sha256\"], [\"sha256sums_file\", \"sha256sums_sha256\"]]) verifyPackFileHash(root, PACKS.mechanicdbRepairLeads.id, fileField, hashField);",
    "  const base = getResearchRoot(root);",
    "  const pack = JSON.parse(fs.readFileSync(path.join(base, PACKS.mechanicdbRepairLeads.manifest), \"utf8\"));",
    "  const projectSourceManifest = JSON.parse(fs.readFileSync(path.join(base, PACKS.mechanicdbRepairLeads.projectSourceManifest), \"utf8\"));",
    "  const db = openReadOnly(root, PACKS.mechanicdbRepairLeads.file);",
    "  try {",
    "    const source = db.prepare(\"SELECT * FROM source_registry WHERE source_id=?\").get(\"mechanicdb-vag-dtc-sample-odbl\");",
    "    const counts = {",
    "      manufacturerCandidates: db.prepare(\"SELECT count(*) AS n FROM dtc_candidates WHERE namespace='manufacturer_controlled_candidate' AND verification_status='community_reference_unverified' AND market_scope='UNKNOWN' AND applicability_precision='manufacturer_make_candidate'\").get().n,",
    "      audiCandidates: db.prepare(\"SELECT count(*) AS n FROM dtc_candidates WHERE oem_make='Audi'\").get().n,",
    "      volkswagenCandidates: db.prepare(\"SELECT count(*) AS n FROM dtc_candidates WHERE oem_make='Volkswagen'\").get().n,",
    "      genericDtcRows: db.prepare(\"SELECT count(*) AS n FROM dtc_candidates WHERE namespace!='manufacturer_controlled_candidate'\").get().n,",
    "      repairLeads: db.prepare(\"SELECT count(*) AS n FROM community_fix_candidates WHERE namespace='community_repair_lead' AND verification_status='community_reference_unverified' AND market_scope='UNKNOWN' AND applicability_precision='manufacturer_make_candidate'\").get().n,",
    "      partNameCandidates: db.prepare(\"SELECT count(*) AS n FROM community_part_candidates WHERE namespace='community_part_name_candidate' AND verification_status='community_reference_unverified' AND market_scope='UNKNOWN' AND applicability_precision='manufacturer_make_candidate'\").get().n,",
    "      verifiedRepairProcedures: db.prepare(\"SELECT count(*) AS n FROM community_fix_candidates WHERE manufacturer_procedure!=0 OR verification_status!='community_reference_unverified'\").get().n,",
    "      oemPartNumbers: db.prepare(\"SELECT count(*) AS n FROM community_part_candidates WHERE oem_part_number!=0\").get().n,",
    "      unsafeRepairLeads: db.prepare(\"SELECT count(*) AS n FROM community_fix_candidates WHERE diagnostic_execution_allowed!=0 OR manufacturer_procedure!=0 OR oem_part_number!=0 OR cost_estimates_included!=0 OR market_scope!='UNKNOWN' OR applicability_precision!='manufacturer_make_candidate' OR verification_status!='community_reference_unverified'\").get().n,",
    "      unsafePartCandidates: db.prepare(\"SELECT count(*) AS n FROM community_part_candidates WHERE oem_part_number!=0 OR market_scope!='UNKNOWN' OR applicability_precision!='manufacturer_make_candidate' OR verification_status!='community_reference_unverified'\").get().n",
    "    };",
    "    const metadata = Object.fromEntries(db.prepare(\"SELECT key,value FROM pack_metadata\").all().map((row) => [row.key, row.value]));",
    "    const attributionText = fs.readFileSync(path.join(base, PACKS.mechanicdbRepairLeads.attribution), \"utf8\").trim();",
    "    const licenseText = fs.readFileSync(path.join(base, PACKS.mechanicdbRepairLeads.licenseFile), \"utf8\");",
    "    const upstreamLicenseText = fs.readFileSync(path.join(base, PACKS.mechanicdbRepairLeads.upstreamLicenseFile), \"utf8\");",
    "    const policy = projectSourceManifest.product_policy || {};",
    "    if (!source || source.data_license!==\"ODbL-1.0\" || source.rights_status!==\"approved_by_published_license\" || source.commercial_use_allowed!==1 || source.display_allowed!==1 || source.offline_cache_allowed!==1 || source.redistribution_allowed!==1 || source.share_alike_required!==1 || source.attribution_required!==1 || source.market_scope!==\"UNKNOWN\" || source.applicability_precision!==\"manufacturer_make_candidate\" || source.technical_review_status!==\"community_reference_unverified\" || source.source_revision!==pack.source_revision || source.source_snapshot_sha256!==pack.source_snapshot_sha256) throw new Error(\"MechanicDB repair-lead source registry rights/provenance gate failed\");",
    "    if (pack.schema_version!==2 || pack.pack_id!==\"mechanicdb-vag-dtc-candidates-odbl\" || pack.source_id!==\"mechanicdb-vag-dtc-sample-odbl\" || pack.source_revision!==\"c788dfe9ed1517d4cd0be27f5aacb4776abf4864\" || pack.database_sha256!==rootPack.database_sha256 || pack.source_snapshot_sha256!==rootPack.source_snapshot_sha256 || pack.data_license!==\"ODbL-1.0\" || pack.rights_status!==\"approved_by_published_license\" || pack.commercial_use_allowed!==true || pack.display_allowed!==true || pack.cache_allowed!==true || pack.redistribution_allowed!==true || pack.share_alike_required!==true || pack.attribution_required!==true || pack.display_status!==\"candidate_reference_visible_separate_namespace\" || pack.product_eligibility!==\"candidate_reference_only_visible_separate_namespace\" || pack.verification_status!==\"community_reference_unverified\" || pack.market_scope!==\"UNKNOWN\" || pack.applicability_precision!==\"manufacturer_make_candidate\" || pack.diagnostic_execution_allowed!==false || pack.repair_procedures_included!==false || pack.community_repair_leads_included!==true || pack.community_repair_leads_verified!==false || pack.oem_part_numbers_included!==false || pack.cost_or_labor_estimates_included!==false || pack.external_part_search_urls_included!==false || pack.display_policy?.repair_leads_visible!==true || pack.display_policy?.repair_leads_verified!==false || pack.display_policy?.manufacturer_repair_procedure!==false || pack.display_policy?.exact_vehicle_fitment!==false || pack.display_policy?.diagnostic_execution_allowed!==false) throw new Error(\"MechanicDB repair-lead pack manifest rights/applicability gate failed\");",
    "    if (projectSourceManifest.source_id!==\"mechanicdb-vag-dtc-sample-odbl\" || projectSourceManifest.source_revision!==pack.source_revision || projectSourceManifest.data_license!==\"ODbL-1.0\" || projectSourceManifest.rights_status!==\"approved_by_published_license\" || projectSourceManifest.commercial_use_status!==\"allowed_under_odbl_free_sample_terms; no paid/full database content\" || projectSourceManifest.display_allowed!==true || projectSourceManifest.cache_allowed!==true || projectSourceManifest.redistribution_allowed!==true || projectSourceManifest.share_alike_required!==true || projectSourceManifest.attribution_required!==true || policy.display_status!==\"candidate_reference_visible_separate_namespace\" || policy.repair_procedure_status!==\"community_authored_not_factory_not_verified\" || policy.vehicle_fitment_claim!==false || policy.ecu_fitment_claim!==false || policy.pr_code_claim!==false || policy.production_import!==false || policy.generic_dtc_rows!==0 || policy.community_repair_leads_visible!==true || policy.community_repair_leads_verified!==false || policy.community_repair_lead_count!==6 || policy.community_part_name_candidate_count!==6 || policy.market_scope!==\"UNKNOWN\" || policy.applicability_precision!==\"manufacturer_make_only_candidate\" || policy.diagnostic_execution_allowed!==false || policy.oem_part_numbers_included!==false || policy.cost_or_labor_estimates_included!==false || policy.external_part_search_urls_included!==false) throw new Error(\"MechanicDB project source manifest policy gate failed\");",
    "    if (counts.manufacturerCandidates!==2 || counts.audiCandidates!==1 || counts.volkswagenCandidates!==1 || counts.genericDtcRows!==0 || counts.repairLeads!==6 || counts.partNameCandidates!==6 || counts.verifiedRepairProcedures!==0 || counts.oemPartNumbers!==0 || counts.unsafeRepairLeads!==0 || counts.unsafePartCandidates!==0 || pack.counts?.manufacturer_controlled_candidates!==2 || pack.counts?.community_repair_lead_rows!==6 || pack.counts?.community_part_candidate_rows!==6 || pack.counts?.generic_dtc_rows!==0 || pack.counts?.repair_procedure_rows!==0 || pack.counts?.part_rows!==0) throw new Error(\"MechanicDB repair-lead counts or candidate-only boundary failed\");",
    "    if (metadata.verified_repair_procedure_rows!==\"0\" || metadata.oem_part_number_rows!==\"0\" || metadata.generic_dtc_rows!==\"0\" || metadata.diagnostic_execution_allowed!==\"false\" || metadata.community_repair_lead_rows!==\"6\" || metadata.community_part_candidate_rows!==\"6\") throw new Error(\"MechanicDB repair-lead embedded metadata gate failed\");",
    "    if (pack.community_fix_line_evidence?.length!==6 || pack.community_part_line_evidence?.length!==6 || pack.source_line_evidence?.length!==2 || Object.keys(pack.source_files || {}).length!==7) throw new Error(\"MechanicDB repair-lead source evidence is incomplete\");",
    "    if (rootPack.source_artifact_zip_sha256!==\"aaabbb30cc3c616e8136ad31d6371073e42d8ae1c5461b67e80f921a8724d490\" || rootPack.source_workflow?.run_id!==41956857684 || rootPack.source_workflow?.artifact_id!==13383726909) throw new Error(\"MechanicDB repair-lead artifact provenance is not pinned\");",
    "    if (!/Open Database License\\s*\\(ODbL\\)\\s*v1\\.0/i.test(licenseText) || !/Share-Alike/i.test(licenseText) || !/MIT License/i.test(upstreamLicenseText) || !/MechanicDB/i.test(attributionText) || !/ODbL/i.test(attributionText)) throw new Error(\"MechanicDB repair-lead attribution/license notices are incomplete\");",
    "    return { id:PACKS.mechanicdbRepairLeads.id, kind:\"community_repair_lead_titles_separate_namespace\", license:\"ODbL-1.0\", source:PACKS.mechanicdbRepairLeads.source, sourceUrl:PACKS.mechanicdbRepairLeads.sourceUrl, status:\"community_reference_unverified\", displayStatus:pack.display_status, reviewStatus:pack.verification_status, marketScope:pack.market_scope, applicabilityPrecision:pack.applicability_precision, diagnosticExecutionAllowed:false, exactVehicleFitment:false, repairProceduresIncluded:false, oemPartNumbersIncluded:false, shareAlikeRequired:true, attributionRequired:true, counts, upstreamRevision:pack.source_revision, sourceSnapshotSha256:pack.source_snapshot_sha256, sourceManifestSha256:rootPack.source_manifest_sha256, projectSourceManifestSha256:rootPack.project_source_manifest_sha256, databaseSha256:pack.database_sha256, artifactSha256:rootPack.source_artifact_zip_sha256, attributionText, note:\"Six community-authored repair-lead titles only. Detailed steps and part names are intentionally not exposed. Not an OEM procedure, not a test plan, not safety-reviewed and not exact vehicle/ECU fitment.\" };",
    "  } finally { db.close(); }",
    "}",
    "",
    "function searchMechanicDbRepairLeads(query, limit=25, root) {",
    "  const q = validateQuery(query);",
    "  const summary = getMechanicDbRepairLeadsSummary(root);",
    "  const base = getResearchRoot(root);",
    "  const pack = JSON.parse(fs.readFileSync(path.join(base, PACKS.mechanicdbRepairLeads.manifest), \"utf8\"));",
    "  const rootPack = verifyPackDatabaseHash(root, PACKS.mechanicdbRepairLeads.id, PACKS.mechanicdbRepairLeads.file);",
    "  const sourceRelative = \"upstream/diagnostic_fixes.csv\";",
    "  const sourceBytes = fs.readFileSync(path.join(base, PACKS.mechanicdbRepairLeads.sourceFile));",
    "  const sourceHash = crypto.createHash(\"sha256\").update(sourceBytes).digest(\"hex\");",
    "  if (sourceHash!==rootPack.source_file_sha256 || sourceHash!==pack.source_files?.[sourceRelative]?.sha256) throw new Error(\"MechanicDB repair-lead source CSV SHA-256 mismatch\");",
    "  const physicalLines = []; let start = 0;",
    "  for (let index=0; index<sourceBytes.length; index+=1) if (sourceBytes[index]===0x0a) { physicalLines.push(sourceBytes.subarray(start,index+1)); start=index+1; }",
    "  if (start<sourceBytes.length) physicalLines.push(sourceBytes.subarray(start));",
    "  const evidence = new Map((pack.community_fix_line_evidence || []).map((item) => [String(item.fix_id), item]));",
    "  const pattern = \"%\" + q.replace(/[\\\\%_]/g, \"\\\\$&\") + \"%\";",
    "  const db = openReadOnly(root, PACKS.mechanicdbRepairLeads.file);",
    "  try {",
    "    const gate = db.prepare(\"SELECT count(*) AS total, sum(CASE WHEN namespace!='community_repair_lead' OR verification_status!='community_reference_unverified' OR market_scope!='UNKNOWN' OR applicability_precision!='manufacturer_make_candidate' OR diagnostic_execution_allowed!=0 OR manufacturer_procedure!=0 OR oem_part_number!=0 OR cost_estimates_included!=0 THEN 1 ELSE 0 END) AS unsafe FROM community_fix_candidates\").get();",
    "    if (gate.total!==6 || Number(gate.unsafe||0)!==0) throw new Error(\"MechanicDB community repair-lead table crossed its candidate-only boundary\");",
    "    const partGate = db.prepare(\"SELECT count(*) AS total, sum(CASE WHEN namespace!='community_part_name_candidate' OR verification_status!='community_reference_unverified' OR market_scope!='UNKNOWN' OR applicability_precision!='manufacturer_make_candidate' OR oem_part_number!=0 THEN 1 ELSE 0 END) AS unsafe FROM community_part_candidates\").get();",
    "    if (partGate.total!==6 || Number(partGate.unsafe||0)!==0) throw new Error(\"MechanicDB community part-name candidate table crossed its boundary\");",
    "    const rows = db.prepare(\"SELECT fix_id,dtc_code,oem_make,fix_title,namespace,verification_status,market_scope,applicability_precision,diagnostic_execution_allowed,manufacturer_procedure,oem_part_number,cost_estimates_included,source_file,source_line_no,source_line_sha256,source_file_sha256,source_revision FROM community_fix_candidates WHERE namespace='community_repair_lead' AND verification_status='community_reference_unverified' AND market_scope='UNKNOWN' AND applicability_precision='manufacturer_make_candidate' AND diagnostic_execution_allowed=0 AND manufacturer_procedure=0 AND oem_part_number=0 AND cost_estimates_included=0 AND (dtc_code LIKE ? ESCAPE '\\\\' OR oem_make LIKE ? ESCAPE '\\\\' OR fix_title LIKE ? ESCAPE '\\\\') ORDER BY oem_make,dtc_code,fix_id LIMIT ?\").all(pattern,pattern,pattern,clampLimit(limit));",
    "    return rows.map((row) => {",
    "      const line = physicalLines[row.source_line_no-1];",
    "      const lineHash = line ? crypto.createHash(\"sha256\").update(line).digest(\"hex\") : null;",
    "      const item = evidence.get(String(row.fix_id));",
    "      if (!item || item.source_file!==sourceRelative || item.source_line_no!==row.source_line_no || item.source_line_sha256!==row.source_line_sha256 || lineHash!==row.source_line_sha256 || row.source_file!==sourceRelative || row.source_file_sha256!==sourceHash || row.source_revision!==pack.source_revision) throw new Error(\"MechanicDB repair-lead source-line provenance mismatch: \" + row.fix_id);",
    "      return { fixId:row.fix_id, code:row.dtc_code, make:row.oem_make, title:row.fix_title, namespace:row.namespace, reviewStatus:row.verification_status, marketScope:row.market_scope, applicabilityPrecision:row.applicability_precision, exactVehicleFitment:false, ecuFitment:false, prCodeFitment:false, diagnosticExecutionAllowed:false, manufacturerProcedure:false, oemPartNumber:false, sourceLineNo:row.source_line_no, sourceLineSha256:row.source_line_sha256, sourceFileSha256:sourceHash, sourceRevision:row.source_revision, sourceSnapshotSha256:summary.sourceSnapshotSha256, sourceManifestSha256:summary.sourceManifestSha256, projectSourceManifestSha256:summary.projectSourceManifestSha256, databaseSha256:summary.databaseSha256, artifactSha256:summary.artifactSha256, license:\"ODbL-1.0\", sourceUrl:summary.sourceUrl, sourceFileUrl:safeHttpsUrl(pack.source_files?.[sourceRelative]?.source_url), attribution:summary.attributionText, warning:\"Community-authored title only. Detailed steps and part names are intentionally hidden. This is not an OEM repair procedure, not a test plan, not safety-reviewed and not exact vehicle/ECU fitment. Do not perform repairs based on this record.\" };",
    "    });",
    "  } finally { db.close(); }",
    "}"
  ].join("\n");
  if (!db.includes("function getMechanicDbRepairLeadsSummary(")) {
    const exportIndex = db.lastIndexOf("\nmodule.exports");
    if (exportIndex < 0) fail("local-research-db exports block missing");
    db = db.slice(0, exportIndex) + "\n" + functions + "\n" + db.slice(exportIndex);
  }
  if (!db.includes("  getMechanicDbRepairLeadsSummary,")) {
    const anchor = "  searchWikidataGenerationCandidates,\n  validateQuery,";
    db = exact(db, anchor, "  searchWikidataGenerationCandidates,\n  getMechanicDbRepairLeadsSummary,\n  searchMechanicDbRepairLeads,\n  validateQuery,", "MechanicDB repair-lead exports");
  }
  writeText(dbPath, db);

  const typesPath = path.join(DESKTOP, "lib", "local-research-db.d.cts");
  let types = readText(typesPath);
  if (!types.includes("getMechanicDbRepairLeadsSummary")) {
    types += "\nexport function getMechanicDbRepairLeadsSummary(root?: string): Record<string, unknown>;\n";
    types += "export function searchMechanicDbRepairLeads(query: string, limit?: number, root?: string): Array<Record<string, unknown>>;\n";
    writeText(typesPath, types);
  }
}

function patchRoute() {
  const routePath = path.join(DESKTOP, "app", "api", "local-research", "route.ts");
  let route = readText(routePath);
  if (!route.includes('dataset === "mechanicdb-fixes-summary"')) {
    const anchor = '    else if (dataset === "wikidata-generations") rows = localResearch.searchWikidataGenerationCandidates(query, limit);';
    const addition = [anchor, '    else if (dataset === "mechanicdb-fixes-summary") {', '      const summary = localResearch.getMechanicDbRepairLeadsSummary();', '      return Response.json({ ok: true, summary }, { headers });', '    }', '    else if (dataset === "mechanicdb-fixes") rows = localResearch.searchMechanicDbRepairLeads(query, limit);'].join("\n");
    route = exact(route, anchor, addition, "MechanicDB repair-lead API route");
    writeText(routePath, route);
  }
}

function patchUi() {
  const uiPath = path.join(DESKTOP, "components", "local-research-catalog.tsx");
  let ui = readText(uiPath);
  if (!ui.includes("type MechanicDbRepairLeadsSummary =")) {
    const anchor = "type Dataset =";
    const index = ui.indexOf(anchor);
    if (index < 0) fail("Research UI Dataset type missing");
    const typeCode = [
      "type MechanicDbRepairLeadsSummary = {",
      "  id: string; license: string; source: string; sourceUrl: string; status: string;",
      "  marketScope: string; applicabilityPrecision: string; reviewStatus: string;",
      "  counts: { manufacturerCandidates: number; repairLeads: number; partNameCandidates: number; genericDtcRows: number; verifiedRepairProcedures: number; oemPartNumbers: number };",
      "  databaseSha256: string; sourceSnapshotSha256: string; sourceManifestSha256: string; artifactSha256: string;",
      "  attributionText: string; note: string; diagnosticExecutionAllowed: false; repairProceduresIncluded: false; oemPartNumbersIncluded: false;",
      "};"
    ].join("\n") + "\n";
    ui = ui.slice(0, index) + typeCode + ui.slice(index);
  }
  const datasetMatch = ui.match(/type Dataset = ([^;]+);/);
  if (!datasetMatch) fail("Research UI Dataset type is malformed");
  if (!datasetMatch[1].includes('"mechanicdb-fixes"')) {
    ui = ui.replace(datasetMatch[0], "type Dataset = " + datasetMatch[1] + ' | "mechanicdb-fixes";');
  }

  const stateAnchor = '  const [wikidataGenerationSummary, setWikidataGenerationSummary] = useState<WikidataGenerationSummary | null>(null);';
  if (!ui.includes("mechanicDbRepairLeadsSummary")) {
    if (!ui.includes(stateAnchor)) fail("Wikidata generation summary state missing before MechanicDB repair-lead UI patch");
    const stateLine = '  const [mechanicDbRepairLeadsSummary, setMechanicDbRepairLeadsSummary] = useState<MechanicDbRepairLeadsSummary | null>(null);';
    ui = exact(ui, stateAnchor, stateAnchor + '\n' + stateLine, "MechanicDB repair-lead summary state");
    const effect = [
      "",
      "  useEffect(() => {",
      '    if (dataset !== "mechanicdb-fixes") return;',
      "    let active = true;",
      '    fetch("/api/local-research?dataset=mechanicdb-fixes-summary")',
      "      .then((response) => response.json())",
      "      .then((payload) => { if (active && payload?.ok) setMechanicDbRepairLeadsSummary(payload.summary); })",
      "      .catch(() => { if (active) setMechanicDbRepairLeadsSummary(null); });",
      "    return () => { active = false; };",
      "  }, [dataset]);"
    ].join("\n");
    const insertAt = ui.indexOf(stateLine) + stateLine.length;
    ui = ui.slice(0, insertAt) + effect + ui.slice(insertAt);
  }

  if (!ui.includes('id: "mechanicdb-fixes"')) {
    const anchor = '  { id: "mechanicdb", label: "DTC · кандидаты марок", hint: "ODbL · community · не OEM" },\n';
    ui = exact(ui, anchor, anchor + '  { id: "mechanicdb-fixes", label: "Ремонтные ориентиры сообщества", hint: "ODbL · только названия · не OEM" },\n', "MechanicDB community repair-lead tab");
  }
  if (!ui.includes('dataset === "mechanicdb-fixes" ?')) {
    const anchor = 'dataset === "mechanicdb" ? "P1128, P3000, Audi, Volkswagen…" :';
    ui = exact(ui, anchor, 'dataset === "mechanicdb-fixes" ? "P3000, P1128, Audi, Volkswagen…" : ' + anchor, "MechanicDB repair-lead search placeholder");
  }
  if (!ui.includes("Подробные шаги и наименования деталей намеренно скрыты")) {
    const mechanicBlock = ui.indexOf("{mechanicDb && <p>");
    if (mechanicBlock < 0) fail("MechanicDB candidate boundary note missing");
    const end = ui.indexOf("</p>}", mechanicBlock);
    if (end < 0) fail("MechanicDB candidate boundary note end missing");
    const addition = '\n      {mechanicDbRepairLeadsSummary && <p>{formatNumber(mechanicDbRepairLeadsSummary.counts.repairLeads)} community repair-lead titles are available in a separate ODbL research tab. Detailed steps and part names are intentionally hidden; these are not OEM procedures, not test plans, not safety-reviewed and not exact vehicle/ECU fitment. Market UNKNOWN; no repair action or diagnostic execution is enabled.</p>}';
    ui = ui.slice(0, end + 5) + addition + ui.slice(end + 5);
  }
  if (!ui.includes('dataset === "mechanicdb-fixes" && rows.map')) {
    const anchor = '      {dataset === "dtc" && rows.map((row) => <article className="research-result"';
    const index = ui.indexOf(anchor);
    if (index < 0) fail("Generic DTC result renderer anchor missing");
    const card = [
      '      {dataset === "mechanicdb-fixes" && rows.map((row) => <article className="research-result" key={row.fixId}>',
      '        <div className="research-result-top"><div><small>MECHANICDB · COMMUNITY REPAIR LEAD · {row.make} · {row.code}</small><h3>{row.title}</h3></div><span className="research-candidate">НЕ OEM-ПРОЦЕДУРА</span></div>',
      '        <div className="research-warning-line">Показано только название. Подробные шаги и наименования деталей намеренно скрыты. Это не заводская процедура, не тест-план, не проверенная применимость и не указание к действию.</div>',
      '        <div className="research-source"><span>ODbL-1.0 · ревизия {row.sourceRevision} · строка источника {row.sourceLineNo} · SHA строки {String(row.sourceLineSha256).slice(0,12)}… · SHA БД {String(row.databaseSha256).slice(0,12)}… · SHA манифеста {String(row.sourceManifestSha256).slice(0,12)}…</span><a href={row.sourceUrl} target="_blank" rel="noopener noreferrer">Открыть источник</a></div>',
      '      </article>)}',
      '      {dataset === "mechanicdb-fixes" && mechanicDbRepairLeadsSummary && <details className="research-details"><summary>Лицензия, атрибуция и ограничения</summary><p>{mechanicDbRepairLeadsSummary.note}</p><pre>{mechanicDbRepairLeadsSummary.attributionText}</pre></details>}',
      ''
    ].join("\n");
    ui = ui.slice(0, index) + card + ui.slice(index);
  }
  writeText(uiPath, ui);
}

function patchVerifierAndPackage() {
  const verifierPath = path.join(DESKTOP, "scripts", "verify-local-research-packs.cjs");
  let verifier = readText(verifierPath);
  verifier = verifier.replace(/manifest\.packs\.length\s*===\s*9/, "manifest.packs.length === 10");
  verifier = verifier.replace(/Expected nine separately licensed research packs/g, "Expected ten separately licensed research packs");
  if (!verifier.includes("manifest.packs.length === 10")) fail("Local research pack-count verifier was not updated to ten");
  writeText(verifierPath, verifier);

  const packagePath = path.join(DESKTOP, "package.json");
  const pkg = readJson(packagePath);
  if (!pkg.scripts || typeof pkg.scripts["test:research"] !== "string" || typeof pkg.scripts["verify:local-research"] !== "string") fail("Desktop package research scripts missing");
  if (!pkg.scripts["test:research"].includes("tests/mechanicdb-repair-leads.test.cjs")) {
    pkg.scripts["test:research"] += " tests/mechanicdb-repair-leads.test.cjs";
  }
  if (!pkg.scripts["verify:local-research"].includes("verify-mechanicdb-repair-leads-pack.cjs")) {
    pkg.scripts["verify:local-research"] += " && node scripts/verify-mechanicdb-repair-leads-pack.cjs";
  }
  writeText(packagePath, JSON.stringify(pkg, null, 2) + "\n");
}

function addTestsAndVerifier() {
  const testCode = [
    '"use strict";',
    'const test = require("node:test");',
    'const assert = require("node:assert/strict");',
    'const fs = require("node:fs");',
    'const path = require("node:path");',
    'const local = require("../lib/local-research-db.cjs");',
    'const root = path.join(__dirname, "..", "data", "research");',
    '',
    'test("MechanicDB community repair leads remain title-only and separately namespaced", () => {',
    '  const summary = local.getMechanicDbRepairLeadsSummary(root);',
    '  assert.equal(summary.counts.manufacturerCandidates, 2);',
    '  assert.equal(summary.counts.repairLeads, 6);',
    '  assert.equal(summary.counts.partNameCandidates, 6);',
    '  assert.equal(summary.counts.genericDtcRows, 0);',
    '  assert.equal(summary.counts.verifiedRepairProcedures, 0);',
    '  assert.equal(summary.counts.oemPartNumbers, 0);',
    '  assert.equal(summary.diagnosticExecutionAllowed, false);',
    '  assert.equal(summary.repairProceduresIncluded, false);',
    '  assert.equal(summary.oemPartNumbersIncluded, false);',
    '  const audi = local.searchMechanicDbRepairLeads("P3000", 10, root);',
    '  const volkswagen = local.searchMechanicDbRepairLeads("P1128", 10, root);',
    '  assert.equal(audi.length, 3);',
    '  assert.equal(volkswagen.length, 3);',
    '  for (const row of [...audi, ...volkswagen]) {',
    '    assert.equal(row.namespace, "community_repair_lead");',
    '    assert.equal(row.reviewStatus, "community_reference_unverified");',
    '    assert.equal(row.marketScope, "UNKNOWN");',
    '    assert.equal(row.applicabilityPrecision, "manufacturer_make_candidate");',
    '    assert.equal(row.exactVehicleFitment, false);',
    '    assert.equal(row.ecuFitment, false);',
    '    assert.equal(row.prCodeFitment, false);',
    '    assert.equal(row.diagnosticExecutionAllowed, false);',
    '    assert.equal(row.manufacturerProcedure, false);',
    '    assert.equal(row.oemPartNumber, false);',
    '    assert.match(row.sourceLineSha256, /^[a-f0-9]{64}$/);',
    '    assert.match(row.sourceFileSha256, /^[a-f0-9]{64}$/);',
    '    assert.equal(row.sourceRevision, "c788dfe9ed1517d4cd0be27f5aacb4776abf4864");',
    '    assert.equal(Object.hasOwn(row, "stepByStepInstructions"), false);',
    '    assert.equal(Object.hasOwn(row, "procedureRationale"), false);',
    '    assert.equal(Object.hasOwn(row, "partName"), false);',
    '    assert.equal(Object.hasOwn(row, "oemPartNumberValue"), false);',
    '  }',
    '  assert.equal(local.searchGenericDtcs("P3000", 10, root).length, 0);',
    '  assert.equal(local.searchGenericDtcs("P1128", 10, root).length, 0);',
    '  assert.equal(local.searchMechanicDbCandidates("P3000", 10, root).length, 1);',
    '  assert.equal(local.searchMechanicDbCandidates("P1128", 10, root).length, 1);',
    '});',
    '',
    'test("MechanicDB repair-lead UI and API never expose unreviewed steps or parts", () => {',
    '  const ui = fs.readFileSync(path.join(__dirname, "..", "components", "local-research-catalog.tsx"), "utf8");',
    '  const route = fs.readFileSync(path.join(__dirname, "..", "app", "api", "local-research", "route.ts"), "utf8");',
    '  assert.match(ui, /id: "mechanicdb-fixes"/);',
    '  assert.match(ui, /mechanicdb-fixes-summary/);',
    '  assert.match(ui, /Подробные шаги и наименования деталей намеренно скрыты/);',
    '  assert.match(route, /dataset === "mechanicdb-fixes"/);',
    '  assert.doesNotMatch(ui, /step_by_step_instructions|stepByStepInstructions|procedureRationale|replacement_parts/);',
    '});',
    ''
  ].join("\n");
  addFile(path.join(DESKTOP, "tests", "mechanicdb-repair-leads.test.cjs"), testCode);

  const verifierCode = [
    '"use strict";',
    'const path = require("node:path");',
    'const local = require("../lib/local-research-db.cjs");',
    'const root = path.join(__dirname, "..", "data", "research");',
    'function fail(message) { throw new Error("[MechanicDB repair-leads verifier] " + message); }',
    'const summary = local.getMechanicDbRepairLeadsSummary(root);',
    'const audi = local.searchMechanicDbRepairLeads("P3000", 10, root);',
    'const volkswagen = local.searchMechanicDbRepairLeads("P1128", 10, root);',
    'if (summary.counts.repairLeads !== 6 || summary.counts.partNameCandidates !== 6 || summary.counts.genericDtcRows !== 0 || summary.counts.verifiedRepairProcedures !== 0 || summary.counts.oemPartNumbers !== 0) fail("Candidate-only pack counts or safety flags mismatch");',
    'if (audi.length !== 3 || volkswagen.length !== 3) fail("Expected three source-backed title-only leads for each make-labelled DTC candidate");',
    'if ([...audi, ...volkswagen].some((row) => row.marketScope !== "UNKNOWN" || row.reviewStatus !== "community_reference_unverified" || row.diagnosticExecutionAllowed !== false || row.manufacturerProcedure !== false || row.oemPartNumber !== false || Object.hasOwn(row, "stepByStepInstructions") || Object.hasOwn(row, "partName"))) fail("A repair-lead row crossed the read-only title-only boundary");',
    'if (local.searchGenericDtcs("P3000", 10, root).length || local.searchGenericDtcs("P1128", 10, root).length) fail("Manufacturer-labelled candidates leaked into generic DTC search");',
    'const report = { status: "verified_community_reference_titles_only", pack_id: summary.id, license: summary.license, review_status: summary.reviewStatus, market_scope: summary.marketScope, applicability_precision: summary.applicabilityPrecision, counts: summary.counts, source_revision: summary.upstreamRevision, source_snapshot_sha256: summary.sourceSnapshotSha256, source_manifest_sha256: summary.sourceManifestSha256, database_sha256: summary.databaseSha256, artifact_sha256: summary.artifactSha256, search_rows: { audi_p3000: audi.length, volkswagen_p1128: volkswagen.length }, generic_namespace_leakage: 0, diagnostic_execution_allowed: false, repair_procedures_included: false, oem_part_numbers_included: false, steps_exposed: false, part_names_exposed: false };',
    'process.stdout.write(JSON.stringify(report, null, 2) + "\\n");',
    ''
  ].join("\n");
  addFile(path.join(DESKTOP, "scripts", "verify-mechanicdb-repair-leads-pack.cjs"), verifierCode);
}

function patchLifecycleAndDocs() {
  const lifecyclePath = path.join(DESKTOP, "scripts", "windows-installer-lifecycle.ps1");
  let lifecycle = readText(lifecyclePath);
  if (!lifecycle.includes("mechanicdb-fixes-summary")) {
    const anchor = "  # generic_repair_guidance is a separate local SQLite pack and must remain readable with external network blocked.";
    const index = lifecycle.indexOf(anchor);
    if (index < 0) fail("Windows lifecycle generic offline research check anchor missing");
    const checks = [
      '  $repairLeadSummary = Invoke-RestMethod -Uri "$baseUrl/api/local-research?dataset=mechanicdb-fixes-summary" -TimeoutSec 20',
      '  if ($repairLeadSummary.summary.counts.repairLeads -ne 6 -or $repairLeadSummary.summary.counts.partNameCandidates -ne 6 -or $repairLeadSummary.summary.marketScope -ne "UNKNOWN" -or $repairLeadSummary.summary.reviewStatus -ne "community_reference_unverified" -or $repairLeadSummary.summary.diagnosticExecutionAllowed -ne $false) { throw "MechanicDB repair-lead candidate-only summary failed offline lifecycle verification." }',
      '  $repairLeadRows = Invoke-RestMethod -Uri "$baseUrl/api/local-research?dataset=mechanicdb-fixes&q=P3000&limit=10" -TimeoutSec 20',
      '  if (@($repairLeadRows.rows).Count -ne 3 -or @($repairLeadRows.rows | Where-Object { $_.marketScope -ne "UNKNOWN" -or $_.reviewStatus -ne "community_reference_unverified" -or $_.diagnosticExecutionAllowed -ne $false -or $_.manufacturerProcedure -ne $false -or $_.oemPartNumber -ne $false }).Count -gt 0) { throw "MechanicDB repair-lead search crossed its title-only offline lifecycle boundary." }',
      '  if (@($repairLeadRows.rows | Where-Object { $_.title -eq $null -or $_.sourceLineSha256 -notmatch "^[a-f0-9]{64}$" }).Count -gt 0) { throw "MechanicDB repair-lead provenance is missing in offline lifecycle." }',
      ''
    ].join("\n");
    lifecycle = lifecycle.slice(0, index) + checks + lifecycle.slice(index);
    writeText(lifecyclePath, lifecycle);
  }

  const readmePath = path.join(RESEARCH, "README.md");
  let readme = readText(readmePath);
  const row = '| MechanicDB community repair-lead sample | ODbL-1.0; upstream DTC code spine MIT | 6 community repair-lead titles; 6 generic part-name candidates withheld from UI | Separate research SQLite and tab; titles only; no steps, no OEM procedures, no exact vehicle/ECU fitment, no test plan; market UNKNOWN; attribution/share-alike required |';
  if (!readme.includes("MechanicDB community repair-lead sample")) {
    const anchor = '| MechanicDB Audi/VW DTC sample |';
    const index = readme.indexOf(anchor);
    if (index < 0) fail("Research README MechanicDB DTC table row missing");
    const end = readme.indexOf("\n", index);
    readme = readme.slice(0, end + 1) + row + "\n" + readme.slice(end + 1);
    writeText(readmePath, readme);
  }
  const docsPath = path.join(DESKTOP, "docs", "RESEARCH_DATA_PACKS.md");
  if (fs.existsSync(docsPath)) {
    let docs = readText(docsPath);
    if (!docs.includes("MechanicDB community repair-lead sample")) {
      docs += [
        "",
        "## MechanicDB community repair-lead sample — ODbL-1.0",
        "",
        "- Six community-authored repair-lead titles are available in a separate read-only research tab.",
        "- The source's detailed steps and six generic part-name candidates are not exposed by the desktop UI/API.",
        "- These are not OEM repair procedures, not verified test plans, not safety-reviewed and have no exact model/year/engine/gearbox/ECU/PR-code/market applicability.",
        "- The two associated Audi/Volkswagen DTC rows remain make-labelled community candidates and are not promoted into generic DTC or verified VAG-specific namespaces.",
        "- ODbL attribution and share-alike apply; the upstream MIT notice is retained. Source revision " + SOURCE_REVISION + "; database SHA-256 " + DATABASE_SHA256 + ".",
        ""
      ].join("\n");
      writeText(docsPath, docs);
    }
  }
}

function main() {
  verifyIntegratedPack();
  patchDatabase();
  patchRoute();
  patchUi();
  addTestsAndVerifier();
  patchVerifierAndPackage();
  patchLifecycleAndDocs();

  const local = require(path.join(DESKTOP, "lib", "local-research-db.cjs"));
  const summary = local.getMechanicDbRepairLeadsSummary(RESEARCH);
  const audi = local.searchMechanicDbRepairLeads("P3000", 10, RESEARCH);
  const volkswagen = local.searchMechanicDbRepairLeads("P1128", 10, RESEARCH);
  if (summary.counts.repairLeads !== 6 || audi.length !== 3 || volkswagen.length !== 3 ||
      local.searchGenericDtcs("P3000", 10, RESEARCH).length !== 0 ||
      local.searchGenericDtcs("P1128", 10, RESEARCH).length !== 0) fail("Final desktop API smoke test failed");
  const report = {
    status: "integrated_verified_community_reference_titles_only",
    pack_id: PACK_ID,
    source_revision: SOURCE_REVISION,
    source_snapshot_sha256: SNAPSHOT_SHA256,
    database_sha256: DATABASE_SHA256,
    artifact_sha256: MANIFEST_SHA256,
    counts: summary.counts,
    searches: { audi_p3000: audi.length, volkswagen_p1128: volkswagen.length },
    generic_namespace_leakage: 0,
    market_scope: "UNKNOWN",
    applicability_precision: "manufacturer_make_candidate",
    review_status: "community_reference_unverified",
    detailed_steps_exposed: false,
    part_names_exposed: false,
    oem_procedures_included: false,
    diagnostic_execution_allowed: false,
    exact_vehicle_fitment: false
  };
  writeText(path.join(RESEARCH, "mechanicdb-repair-leads-browser-verification.json"), JSON.stringify(report, null, 2) + "\n");
  process.stdout.write(JSON.stringify(report, null, 2) + "\n");
}
try { main(); }
catch (error) { process.stderr.write("MechanicDB repair-lead browser integration failed: " + (error.stack || error.message) + "\n"); process.exitCode = 1; }

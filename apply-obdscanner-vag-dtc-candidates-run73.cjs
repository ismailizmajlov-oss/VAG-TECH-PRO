"use strict";

const fs = require("node:fs");
const path = require("node:path");
const crypto = require("node:crypto");

const ROOT = path.resolve(process.cwd(), "desktop-source");
const RESEARCH = path.join(ROOT, "data", "research");
const PACK_ID = "obdscanner-vag-dtc-candidates-mit";
const DATABASE_NAME = "obdscanner-vag-dtc-candidates.sqlite";
const REVISION = "af1ca44704281e1ff3e2ed84cb55bd92dd9bb996";
const DISPLAY_STATUS = "candidate_reference_visible_separate_namespace";
const PRODUCT_ELIGIBILITY = "candidate_reference_only_visible_separate_namespace";
const WARNING = "Набор помечен источником как VAG-family, но это не подтверждение производителя. Все 528 P1xxx записей — community_reference_unverified; рынок UNKNOWN, точная модель/поколение/год/двигатель/КПП/ECU/PR/VIN применимость отсутствует. Не использовать как тест-план, команду диагностики, ремонтную процедуру или OEM-применяемость.";

function fail(message) { throw new Error("[run73] " + message); }
function readText(file) {
  if (!fs.existsSync(file)) fail("Required file missing: " + path.relative(ROOT, file));
  return fs.readFileSync(file, "utf8").replace(/\r\n/g, "\n");
}
function writeText(file, value) { fs.writeFileSync(file, value.replace(/\r\n/g, "\n"), "utf8"); }
function readJson(file) { return JSON.parse(readText(file)); }
function writeJson(file, value) { writeText(file, JSON.stringify(value, null, 2) + "\n"); }
function sha256(bytes) { return crypto.createHash("sha256").update(bytes).digest("hex"); }
function replaceExactly(file, before, after, label) {
  const current = readText(file);
  if (current.includes(after)) return false;
  const count = current.split(before).length - 1;
  if (count !== 1) fail(label + ": expected exactly one anchor, found " + count);
  writeText(file, current.replace(before, after));
  return true;
}
function insertBeforeUnique(file, anchor, insertion, label) {
  const current = readText(file);
  if (current.includes(insertion.trim())) return false;
  const count = current.split(anchor).length - 1;
  if (count !== 1) fail(label + ": expected exactly one insertion anchor, found " + count);
  writeText(file, current.replace(anchor, insertion + anchor));
  return true;
}
function insertAfterUnique(file, anchor, insertion, label) {
  const current = readText(file);
  if (current.includes(insertion.trim())) return false;
  const count = current.split(anchor).length - 1;
  if (count !== 1) fail(label + ": expected exactly one insertion anchor, found " + count);
  writeText(file, current.replace(anchor, anchor + insertion));
  return true;
}

const packDir = path.join(RESEARCH, PACK_ID);
const packManifestPath = path.join(packDir, "manifest.json");
const databasePath = path.join(packDir, DATABASE_NAME);
const sourcePath = path.join(packDir, "upstream", "vag.json");
const licensePath = path.join(packDir, "LICENSE-OBDSCANNER-MIT.txt");
const upstreamLicensePath = path.join(packDir, "LICENSE-WAL33D-MIT.txt");
const attributionPath = path.join(packDir, "ATTRIBUTION.txt");
for (const file of [packManifestPath, databasePath, sourcePath, licensePath, upstreamLicensePath, attributionPath]) {
  if (!fs.existsSync(file)) fail("Built pack file is missing: " + path.relative(ROOT, file));
}

const packManifestBytes = fs.readFileSync(packManifestPath);
const packManifest = JSON.parse(packManifestBytes.toString("utf8"));
const databaseBytes = fs.readFileSync(databasePath);
const sourceBytes = fs.readFileSync(sourcePath);
const licenseBytes = fs.readFileSync(licensePath);
const upstreamLicenseBytes = fs.readFileSync(upstreamLicensePath);
const attributionBytes = fs.readFileSync(attributionPath);
const packManifestHash = sha256(packManifestBytes);
const databaseHash = sha256(databaseBytes);
const sourceHash = sha256(sourceBytes);
const licenseHash = sha256(licenseBytes);
const upstreamLicenseHash = sha256(upstreamLicenseBytes);
const attributionHash = sha256(attributionBytes);

if (packManifest.pack_id !== PACK_ID || packManifest.source_revision !== REVISION ||
    packManifest.database_file !== DATABASE_NAME || packManifest.database_sha256 !== databaseHash ||
    packManifest.source_file !== "upstream/vag.json" || packManifest.source_file_sha256 !== sourceHash ||
    packManifest.license_file_sha256 !== licenseHash ||
    packManifest.upstream_license_file_sha256 !== upstreamLicenseHash ||
    packManifest.attribution_sha256 !== attributionHash ||
    packManifest.data_license !== "MIT" || packManifest.upstream_data_license !== "MIT" ||
    packManifest.rights_status !== "approved_by_published_license" ||
    packManifest.market_scope !== "UNKNOWN" ||
    packManifest.applicability_precision !== "manufacturer_family_candidate" ||
    packManifest.verification_status !== "community_reference_unverified" ||
    packManifest.display_status !== DISPLAY_STATUS ||
    packManifest.product_eligibility !== PRODUCT_ELIGIBILITY ||
    packManifest.vag_oem_confirmation !== false || packManifest.exact_vehicle_fitment !== false ||
    packManifest.ecu_fitment !== false || packManifest.diagnostic_execution_allowed !== false ||
    packManifest.repair_procedures_included !== false || packManifest.oem_part_numbers_included !== false ||
    packManifest.counts?.manufacturer_family_candidates !== 528 ||
    packManifest.counts?.p1xxx_candidates !== 528 ||
    packManifest.counts?.generic_dtc_rows !== 0 || packManifest.counts?.unsafe_rows !== 0) {
  fail("Pack manifest, revision, rights or candidate-only boundary failed");
}
if (!/MIT License/i.test(licenseBytes.toString("utf8")) ||
    !/MIT License/i.test(upstreamLicenseBytes.toString("utf8")) ||
    !/Wal33D \(Waleed Judah\)/i.test(upstreamLicenseBytes.toString("utf8")) ||
    !/OBDScanner/i.test(attributionBytes.toString("utf8")) ||
    !/Wal33D/i.test(attributionBytes.toString("utf8"))) {
  fail("MIT notices or attribution are incomplete");
}

const rootManifest = readJson(path.join(RESEARCH, "manifest.json"));
const rootPack = rootManifest.packs.find((item) => item.id === PACK_ID);
if (!rootPack || rootPack.database_sha256 !== databaseHash || rootPack.source_manifest_sha256 !== packManifestHash ||
    rootPack.source_file_sha256 !== sourceHash || rootPack.license_file_sha256 !== licenseHash ||
    rootPack.upstream_license_file_sha256 !== upstreamLicenseHash || rootPack.attribution_sha256 !== attributionHash ||
    rootPack.market_scope !== "UNKNOWN" || rootPack.applicability_precision !== "manufacturer_family_candidate" ||
    rootPack.review_status !== "community_reference_unverified" || rootPack.display_status !== DISPLAY_STATUS ||
    rootPack.fitment_claim !== false || rootPack.execution_allowed !== false || rootPack.vag_oem_confirmation !== false) {
  fail("Root research manifest entry is missing or inconsistent");
}

const coreDbFile = path.join(ROOT, "lib", "local-research-db.cjs");
const mechanicScopeBlock = [
  '    scope: "Two Audi/Volkswagen make-labelled community DTC candidates; visible only in a separate research tab; market UNKNOWN; not OEM-confirmed",',
  "  }),",
  "});",
].join("\n");
const newPackDescriptor = [
  '    scope: "Two Audi/Volkswagen make-labelled community DTC candidates; visible only in a separate research tab; market UNKNOWN; not OEM-confirmed",',
  "  }),",
  "  obdscannerVagDtc: Object.freeze({",
  '    id: "' + PACK_ID + '",',
  '    file: "' + PACK_ID + "/" + DATABASE_NAME + '",',
  '    manifest: "' + PACK_ID + '/manifest.json",',
  '    attribution: "' + PACK_ID + '/ATTRIBUTION.txt",',
  '    licenseFile: "' + PACK_ID + '/LICENSE-OBDSCANNER-MIT.txt",',
  '    upstreamLicenseFile: "' + PACK_ID + '/LICENSE-WAL33D-MIT.txt",',
  '    sourceFile: "' + PACK_ID + '/upstream/vag.json",',
  '    license: "MIT",',
  '    source: "OBDScanner / Wal33D DTC Database",',
  '    sourceUrl: "https://github.com/parhipov/OBDScanner",',
  '    scope: "P1xxx VAG-family candidates only; market UNKNOWN; not OEM-confirmed",',
  "  }),",
  "});",
].join("\n");
replaceExactly(coreDbFile, mechanicScopeBlock, newPackDescriptor, "PACKS registry");

replaceExactly(coreDbFile,
  '  const mechanicDbManifest = manifest.packs.find((pack) => pack.id === PACKS.mechanicdb.id);',
  '  const mechanicDbManifest = manifest.packs.find((pack) => pack.id === PACKS.mechanicdb.id);\n  const obdscannerVagDtcManifest = manifest.packs.find((pack) => pack.id === PACKS.obdscannerVagDtc.id);',
  "research summary manifest lookup");
replaceExactly(coreDbFile,
  '  if (!obManifest || !vagManifest || !udsManifest || !vehiclesDbManifest || !mechanicDbManifest) throw new Error("A required local research pack is missing from the manifest");',
  '  if (!obManifest || !vagManifest || !udsManifest || !vehiclesDbManifest || !mechanicDbManifest || !obdscannerVagDtcManifest) throw new Error("A required local research pack is missing from the manifest");',
  "research summary required pack gate");
replaceExactly(coreDbFile,
  '  verifyPackDatabaseHash(root, PACKS.mechanicdb.id, PACKS.mechanicdb.file);',
  '  verifyPackDatabaseHash(root, PACKS.mechanicdb.id, PACKS.mechanicdb.file);\n  verifyPackDatabaseHash(root, PACKS.obdscannerVagDtc.id, PACKS.obdscannerVagDtc.file);',
  "research summary database hash verification");
replaceExactly(coreDbFile,
  '    [PACKS.mechanicdb.id, [["license_file", "license_file_sha256"], ["upstream_license_file", "upstream_license_file_sha256"], ["source_manifest_file", "source_manifest_sha256"], ["attribution_file", "attribution_sha256"], ["source_file", "source_file_sha256"], ["sources_file", "sources_file_sha256"], ["data_dictionary_file", "data_dictionary_sha256"], ["sha256sums_file", "sha256sums_sha256"]]],',
  '    [PACKS.mechanicdb.id, [["license_file", "license_file_sha256"], ["upstream_license_file", "upstream_license_file_sha256"], ["source_manifest_file", "source_manifest_sha256"], ["attribution_file", "attribution_sha256"], ["source_file", "source_file_sha256"], ["sources_file", "sources_file_sha256"], ["data_dictionary_file", "data_dictionary_sha256"], ["sha256sums_file", "sha256sums_sha256"]]],\n    [PACKS.obdscannerVagDtc.id, [["license_file", "license_file_sha256"], ["upstream_license_file", "upstream_license_file_sha256"], ["source_manifest_file", "source_manifest_sha256"], ["attribution_file", "attribution_sha256"], ["source_file", "source_file_sha256"]]],',
  "research summary provenance hash list");
replaceExactly(coreDbFile,
  '  const mechanicDb = openReadOnly(root, PACKS.mechanicdb.file);',
  '  const mechanicDb = openReadOnly(root, PACKS.mechanicdb.file);\n  const obdscannerVagDtcDb = openReadOnly(root, PACKS.obdscannerVagDtc.file);',
  "research summary database open");

const summaryGateAnchor = '      throw new Error("MechanicDB DTC candidate pack failed its license, provenance, hidden-status or candidate-only gate");\n    }\n\n    return {';
const summaryGateInsert = [
  '      throw new Error("MechanicDB DTC candidate pack failed its license, provenance, hidden-status or candidate-only gate");',
  "    }",
  "",
  '    const obdscannerPackManifest = JSON.parse(fs.readFileSync(path.join(getResearchRoot(root), PACKS.obdscannerVagDtc.manifest), "utf8"));',
  '    const obdscannerAttribution = fs.readFileSync(path.join(getResearchRoot(root), PACKS.obdscannerVagDtc.attribution), "utf8");',
  '    const obdscannerLicense = fs.readFileSync(path.join(getResearchRoot(root), PACKS.obdscannerVagDtc.licenseFile), "utf8");',
  '    const obdscannerUpstreamLicense = fs.readFileSync(path.join(getResearchRoot(root), PACKS.obdscannerVagDtc.upstreamLicenseFile), "utf8");',
  '    const obdscannerSource = obdscannerVagDtcDb.prepare("SELECT * FROM source_registry WHERE source_id=?").get("obdscanner-vag-dtc-candidates");',
  "    const obdscannerCounts = {",
  '      sources: obdscannerVagDtcDb.prepare("SELECT count(*) AS n FROM source_registry").get().n,',
  '      manufacturerFamilyCandidates: obdscannerVagDtcDb.prepare("SELECT count(*) AS n FROM dtc_candidates WHERE namespace=? AND verification_status=? AND market_scope=? AND applicability_precision=?").get("vag_family_candidate", "community_reference_unverified", "UNKNOWN", "manufacturer_family_candidate").n,',
  '      p1xxxCandidates: obdscannerVagDtcDb.prepare("SELECT count(*) AS n FROM dtc_candidates WHERE dtc_code GLOB ?").get("P1[0-9][0-9][0-9]").n,',
  '      genericDtcRows: obdscannerVagDtcDb.prepare("SELECT count(*) AS n FROM dtc_candidates WHERE namespace!=?").get("vag_family_candidate").n,',
  '      unsafeRows: obdscannerVagDtcDb.prepare("SELECT count(*) AS n FROM dtc_candidates WHERE vehicle_fitment_claim!=0 OR ecu_fitment_claim!=0 OR diagnostic_execution_allowed!=0 OR repair_procedure_included!=0 OR oem_part_number_included!=0").get().n,',
  "    };",
  '    const obdscannerSourceBytes = fs.readFileSync(path.join(getResearchRoot(root), PACKS.obdscannerVagDtc.sourceFile));',
  '    if (PACKS.obdscannerVagDtc.license !== "MIT" || !/MIT License/i.test(obdscannerLicense) || !/MIT License/i.test(obdscannerUpstreamLicense) || !/Wal33D \\(Waleed Judah\\)/i.test(obdscannerUpstreamLicense) ||',
  '        !/OBDScanner/i.test(obdscannerAttribution) || !/Wal33D/i.test(obdscannerAttribution) ||',
  '        obdscannerPackManifest.source_revision !== REVISION || obdscannerPackManifest.database_sha256 !== obdscannerVagDtcManifest.database_sha256 ||',
  '        obdscannerPackManifest.source_file_sha256 !== obdscannerVagDtcManifest.source_file_sha256 || obdscannerPackManifest.source_snapshot_sha256 !== obdscannerVagDtcManifest.source_snapshot_sha256 ||',
  '        obdscannerPackManifest.data_license !== "MIT" || obdscannerPackManifest.upstream_data_license !== "MIT" || obdscannerPackManifest.rights_status !== "approved_by_published_license" ||',
  '        obdscannerPackManifest.display_status !== "' + DISPLAY_STATUS + '" || obdscannerPackManifest.product_eligibility !== "' + PRODUCT_ELIGIBILITY + '" ||',
  '        obdscannerPackManifest.market_scope !== "UNKNOWN" || obdscannerPackManifest.applicability_precision !== "manufacturer_family_candidate" ||',
  '        obdscannerPackManifest.verification_status !== "community_reference_unverified" || obdscannerPackManifest.vag_oem_confirmation !== false ||',
  '        obdscannerPackManifest.exact_vehicle_fitment !== false || obdscannerPackManifest.ecu_fitment !== false || obdscannerPackManifest.diagnostic_execution_allowed !== false ||',
  '        obdscannerPackManifest.repair_procedures_included !== false || obdscannerPackManifest.oem_part_numbers_included !== false ||',
  '        crypto.createHash("sha256").update(obdscannerSourceBytes).digest("hex") !== obdscannerPackManifest.source_file_sha256 ||',
  '        !obdscannerSource || obdscannerSource.data_license !== "MIT" || obdscannerSource.upstream_license !== "MIT" ||',
  '        obdscannerSource.rights_status !== "approved_by_published_license" || obdscannerSource.commercial_use_allowed !== 1 || obdscannerSource.display_allowed !== 1 ||',
  '        obdscannerSource.offline_cache_allowed !== 1 || obdscannerSource.redistribution_allowed !== 1 || obdscannerSource.attribution_required !== 1 ||',
  '        obdscannerSource.share_alike_required !== 0 || obdscannerSource.market_scope !== "UNKNOWN" ||',
  '        obdscannerSource.applicability_precision !== "manufacturer_family_candidate" || obdscannerSource.verification_status !== "community_reference_unverified" ||',
  '        obdscannerSource.vag_oem_confirmation !== 0 || obdscannerSource.exact_vehicle_fitment !== 0 || obdscannerSource.ecu_fitment !== 0 ||',
  '        obdscannerSource.diagnostic_execution_allowed !== 0 || obdscannerSource.repair_procedures_included !== 0 || obdscannerSource.oem_part_numbers_included !== 0 ||',
  '        obdscannerCounts.sources !== 1 || obdscannerCounts.manufacturerFamilyCandidates !== 528 || obdscannerCounts.p1xxxCandidates !== 528 ||',
  '        obdscannerCounts.genericDtcRows !== 0 || obdscannerCounts.unsafeRows !== 0) {',
  '      throw new Error("OBDScanner VAG-family DTC candidate pack failed its MIT, provenance, P1xxx namespace or candidate-only gate");',
  "    }",
  "",
  "    return {",
].join("\n");
replaceExactly(coreDbFile, summaryGateAnchor, summaryGateInsert, "research summary candidate-only verification block");

const summaryArrayAnchor = '      ],\n    };\n  } finally {\n    obdex.close();';
const newSummaryObject = [
  "        {",
  "          id: PACKS.obdscannerVagDtc.id,",
  '          kind: "vag_family_dtc_candidates",',
  "          license: PACKS.obdscannerVagDtc.license,",
  "          source: PACKS.obdscannerVagDtc.source,",
  "          sourceUrl: PACKS.obdscannerVagDtc.sourceUrl,",
  "          scope: PACKS.obdscannerVagDtc.scope,",
  '          status: "research_only",',
  '          displayStatus: "' + DISPLAY_STATUS + '",',
  '          reviewStatus: "community_reference_unverified",',
  '          marketScope: "UNKNOWN",',
  '          applicabilityPrecision: "manufacturer_family_candidate",',
  "          fitmentClaim: false,",
  "          executionAllowed: false,",
  "          attributionRequired: true,",
  "          shareAlikeRequired: false,",
  "          counts: {",
  "            manufacturerFamilyCandidates: obdscannerCounts.manufacturerFamilyCandidates,",
  "            p1xxxCandidates: obdscannerCounts.p1xxxCandidates,",
  "            genericDtcRows: obdscannerCounts.genericDtcRows,",
  "          },",
  "          upstreamRevision: obdscannerPackManifest.source_revision,",
  "          sourceManifestSha256: obdscannerVagDtcManifest.source_manifest_sha256,",
  "          sourceSnapshotSha256: obdscannerPackManifest.source_snapshot_sha256,",
  "          databaseSha256: obdscannerVagDtcManifest.database_sha256,",
  "          attributionText: obdscannerAttribution,",
  '          note: "528 P1xxx VAG-family source labels only. Not OEM-confirmed, not mapped to exact vehicle/ECU/market, not a test plan or repair procedure; separate from generic SAE/ISO DTC.",',
  "        },",
].join("\n");
const coreSummary = readText(coreDbFile);
const mechanicSummaryIndex = coreSummary.indexOf("id: PACKS.mechanicdb.id");
const summaryArrayEnd = mechanicSummaryIndex < 0 ? -1 : coreSummary.indexOf(summaryArrayAnchor, mechanicSummaryIndex);
if (summaryArrayEnd < 0) fail("Research summary pack array insertion anchor is missing");
if (!coreSummary.includes("id: PACKS.obdscannerVagDtc.id")) {
  writeText(coreDbFile, coreSummary.slice(0, summaryArrayEnd) + newSummaryObject + "\n" + coreSummary.slice(summaryArrayEnd));
}
replaceExactly(coreDbFile,
  "    mechanicDb.close();",
  "    mechanicDb.close();\n    obdscannerVagDtcDb.close();",
  "research summary database close");

const searchFunction = [
  "function searchObdscannerVagDtcCandidates(query, limit = 25, root) {",
  "  const q = validateQuery(query);",
  "  const pack = verifyPackDatabaseHash(root, PACKS.obdscannerVagDtc.id, PACKS.obdscannerVagDtc.file);",
  "  for (const [fileField, hashField] of [",
  '    ["license_file", "license_file_sha256"],',
  '    ["upstream_license_file", "upstream_license_file_sha256"],',
  '    ["source_manifest_file", "source_manifest_sha256"],',
  '    ["attribution_file", "attribution_sha256"],',
  '    ["source_file", "source_file_sha256"],',
  "  ]) verifyPackFileHash(root, PACKS.obdscannerVagDtc.id, fileField, hashField);",
  "  const researchRoot = getResearchRoot(root);",
  '  const packManifest = JSON.parse(fs.readFileSync(path.join(researchRoot, PACKS.obdscannerVagDtc.manifest), "utf8"));',
  '  const sourceRelative = "upstream/vag.json";',
  "  const sourceBytes = fs.readFileSync(path.join(researchRoot, PACKS.obdscannerVagDtc.id, sourceRelative));",
  '  const sourceFileSha256 = crypto.createHash("sha256").update(sourceBytes).digest("hex");',
  "  if (sourceFileSha256 !== pack.source_file_sha256 || sourceFileSha256 !== packManifest.source_file_sha256 ||",
  '      pack.display_status !== "' + DISPLAY_STATUS + '" || pack.review_status !== "community_reference_unverified" ||',
  "      pack.source_snapshot_sha256 !== packManifest.source_snapshot_sha256 || packManifest.source_revision !== \"" + REVISION + "\" ||",
  '      packManifest.data_license !== "MIT" || packManifest.upstream_data_license !== "MIT" ||',
  '      packManifest.rights_status !== "approved_by_published_license" || packManifest.market_scope !== "UNKNOWN" ||',
  '      packManifest.applicability_precision !== "manufacturer_family_candidate" || packManifest.verification_status !== "community_reference_unverified" ||',
  "      packManifest.vag_oem_confirmation !== false || packManifest.exact_vehicle_fitment !== false || packManifest.ecu_fitment !== false ||",
  "      packManifest.diagnostic_execution_allowed !== false || packManifest.repair_procedures_included !== false || packManifest.oem_part_numbers_included !== false) {",
  '    throw new Error("OBDScanner VAG-family DTC candidate browser failed its source, rights or non-fitment gate");',
  "  }",
  '  const sourcePayload = JSON.parse(sourceBytes.toString("utf8"));',
  '  if (sourcePayload.set !== "vag" || !String(sourcePayload.source || "").includes("Wal33D") || !sourcePayload.codes) throw new Error("OBDScanner source family identity changed");',
  "  const canonical = (value) => {",
  "    if (Array.isArray(value)) return value.map(canonical);",
  '    if (value && typeof value === "object") { const result = {}; for (const key of Object.keys(value).sort()) result[key] = canonical(value[key]); return result; }',
  "    return value;",
  "  };",
  "  const db = openReadOnly(root, PACKS.obdscannerVagDtc.file);",
  "  try {",
  '    const gateSql = "SELECT count(*) AS total, " +',
  '      "sum(CASE WHEN namespace!=? OR verification_status!=? OR market_scope!=? OR applicability_precision!=? THEN 1 ELSE 0 END) AS invalid_namespace, " +',
  '      "sum(CASE WHEN vehicle_fitment_claim!=0 OR ecu_fitment_claim!=0 OR diagnostic_execution_allowed!=0 OR repair_procedure_included!=0 OR oem_part_number_included!=0 THEN 1 ELSE 0 END) AS unsafe_rows, " +',
  '      "sum(CASE WHEN dtc_code NOT GLOB ? THEN 1 ELSE 0 END) AS non_p1_rows FROM dtc_candidates";',
  '    const gate = db.prepare(gateSql).get("vag_family_candidate", "community_reference_unverified", "UNKNOWN", "manufacturer_family_candidate", "P1[0-9][0-9][0-9]");',
  '    if (gate.total !== 528 || gate.invalid_namespace !== 0 || gate.unsafe_rows !== 0 || gate.non_p1_rows !== 0) throw new Error("OBDScanner DTC candidate-only row gate failed");',
  "    const qUpper = q.toUpperCase();",
  '    const rowsSql = "SELECT dtc_code, title_en, title_ru, namespace, verification_status, market_scope, applicability_precision, " +',
  '      "vehicle_fitment_claim, ecu_fitment_claim, diagnostic_execution_allowed, repair_procedure_included, oem_part_number_included, " +',
  '      "source_revision, source_file, source_file_sha256, source_record_sha256, data_license, source_url, upstream_source_url " +',
  '      "FROM dtc_candidates WHERE namespace=? AND verification_status=? AND market_scope=? AND applicability_precision=? " +',
  '      "AND vehicle_fitment_claim=0 AND ecu_fitment_claim=0 AND diagnostic_execution_allowed=0 AND repair_procedure_included=0 AND oem_part_number_included=0 " +',
  '      "AND (instr(upper(dtc_code),?)>0 OR instr(upper(title_en),?)>0 OR instr(upper(title_ru),?)>0) " +',
  '      "ORDER BY CASE WHEN dtc_code=? THEN 0 WHEN substr(dtc_code,1,length(?))=? THEN 1 ELSE 2 END, dtc_code LIMIT ?";',
  '    const rows = db.prepare(rowsSql).all("vag_family_candidate", "community_reference_unverified", "UNKNOWN", "manufacturer_family_candidate", qUpper, qUpper, qUpper, qUpper, qUpper, qUpper, clampLimit(limit));',
  '    const attribution = fs.readFileSync(path.join(researchRoot, PACKS.obdscannerVagDtc.attribution), "utf8").trim();',
  "    return rows.map((row) => {",
  "      const sourceRecord = sourcePayload.codes[row.dtc_code];",
  '      const recordHash = sourceRecord ? crypto.createHash("sha256").update(JSON.stringify(canonical(sourceRecord))).digest("hex") : null;',
  "      if (!sourceRecord || sourceRecord.en !== row.title_en || sourceRecord.ru !== row.title_ru ||",
  '          row.source_revision !== packManifest.source_revision || row.source_file !== sourceRelative ||',
  '          row.source_file_sha256 !== sourceFileSha256 || row.data_license !== "MIT" || recordHash !== row.source_record_sha256) {',
  '        throw new Error("OBDScanner source record provenance mismatch for " + row.dtc_code);',
  "      }",
  "      return {",
  "        code: row.dtc_code,",
  "        title: row.title_ru,",
  "        titleRu: row.title_ru,",
  "        titleEn: row.title_en,",
  "        namespace: row.namespace,",
  "        reviewStatus: row.verification_status,",
  "        displayStatus: packManifest.display_status,",
  "        marketScope: row.market_scope,",
  "        applicabilityPrecision: row.applicability_precision,",
  "        exactFitment: false,",
  "        vagOemConfirmation: false,",
  "        ecuFitment: false,",
  "        diagnosticExecutionAllowed: false,",
  "        repairProcedureIncluded: false,",
  "        oemPartNumberIncluded: false,",
  "        sourceRevision: row.source_revision,",
  "        sourceFile: row.source_file,",
  "        sourceRecordSha256: row.source_record_sha256,",
  "        sourceFileSha256: sourceFileSha256,",
  "        sourceSnapshotSha256: packManifest.source_snapshot_sha256,",
  "        sourceManifestSha256: pack.source_manifest_sha256,",
  "        databaseSha256: pack.database_sha256,",
  "        license: packManifest.data_license,",
  "        upstreamLicense: packManifest.upstream_data_license,",
  "        attributionRequired: true,",
  "        shareAlikeRequired: false,",
  "        sourceUrl: safeHttpsUrl(packManifest.source_repository),",
  "        sourceFileUrl: safeHttpsUrl(packManifest.source_file_url),",
  "        upstreamSourceUrl: safeHttpsUrl(packManifest.upstream_source_repository),",
  "        attribution: attribution,",
  "        warning: " + JSON.stringify(WARNING) + ",",
  "      };",
  "    });",
  "  } finally { db.close(); }",
  "}",
  "",
].join("\n");
insertBeforeUnique(coreDbFile, "function searchGenericDtcs(query, limit = 25, root) {", searchFunction, "VAG-family DTC candidate search function");
replaceExactly(coreDbFile,
  "  searchMechanicDbCandidates,\n  validateQuery,",
  "  searchMechanicDbCandidates,\n  searchObdscannerVagDtcCandidates,\n  validateQuery,",
  "VAG-family DTC candidate export");

const typesFile = path.join(ROOT, "lib", "local-research-db.d.cts");
replaceExactly(typesFile,
  "export function searchMechanicDbCandidates(query: string, limit?: number, root?: string): Array<Record<string, unknown>>;\n",
  "export function searchMechanicDbCandidates(query: string, limit?: number, root?: string): Array<Record<string, unknown>>;\nexport function searchObdscannerVagDtcCandidates(query: string, limit?: number, root?: string): Array<Record<string, unknown>>;\n",
  "VAG-family DTC TypeScript declaration");

const routeFile = path.join(ROOT, "app", "api", "local-research", "route.ts");
replaceExactly(routeFile,
  '    else if (dataset === "mechanicdb") rows = localResearch.searchMechanicDbCandidates(query, limit);\n',
  '    else if (dataset === "mechanicdb") rows = localResearch.searchMechanicDbCandidates(query, limit);\n    else if (dataset === "obdscanner-vag-dtc") rows = localResearch.searchObdscannerVagDtcCandidates(query, limit);\n',
  "VAG-family DTC API route");

const uiFile = path.join(ROOT, "components", "local-research-catalog.tsx");
let ui = readText(uiFile);
const datasetMatch = ui.match(/type Dataset = ([^;]+);/);
if (!datasetMatch) fail("Research UI dataset type declaration is missing");
if (!datasetMatch[1].split("|").some((part) => part.trim() === '"obdscanner-vag-dtc"')) {
  ui = ui.replace(datasetMatch[0], "type Dataset = " + datasetMatch[1] + ' | "obdscanner-vag-dtc";');
}
if (!ui.includes('id: "obdscanner-vag-dtc"')) {
  const tabAnchor = '  { id: "mechanicdb", label: "DTC · кандидаты марок", hint: "ODbL · community · не OEM" },\n';
  if (ui.split(tabAnchor).length - 1 !== 1) fail("VAG-family DTC UI tab anchor is missing or ambiguous");
  ui = ui.replace(tabAnchor, tabAnchor + '  { id: "obdscanner-vag-dtc", label: "VAG DTC · кандидаты", hint: "MIT · 528 P1xxx · не OEM" },\n');
}
if (!ui.includes('const obdscannerVagDtc = summary.find((pack) => pack.id === "' + PACK_ID + '");')) {
  const summaryAnchor = '  const mechanicDb = summary.find((pack) => pack.id === "mechanicdb-vag-dtc-candidates-odbl");\n';
  if (ui.split(summaryAnchor).length - 1 !== 1) fail("VAG-family DTC summary UI anchor is missing or ambiguous");
  ui = ui.replace(summaryAnchor, summaryAnchor + '  const obdscannerVagDtc = summary.find((pack) => pack.id === "' + PACK_ID + '");\n');
}
const rowTypeStart = ui.indexOf("type ResearchRow = {");
const rowTypeEnd = rowTypeStart < 0 ? -1 : ui.indexOf("\n};", rowTypeStart);
if (rowTypeStart < 0 || rowTypeEnd < 0) fail("Research row type declaration is missing");
const rowTypeText = ui.slice(rowTypeStart, rowTypeEnd);
const rowFields = [
  "titleEn?: string;",
  "reviewStatus?: string;",
  "displayStatus?: string;",
  "marketScope?: string;",
  "applicabilityPrecision?: string;",
  "vagOemConfirmation?: boolean;",
  "sourceRevision?: string;",
  "sourceRecordSha256?: string;",
  "sourceManifestSha256?: string;",
  "databaseSha256?: string;",
  "license?: string;",
  "sourceUrl?: string;",
  "warning?: string;",
];
const missingRowFields = rowFields.filter((field) => !rowTypeText.includes(field));
if (missingRowFields.length) {
  ui = ui.slice(0, rowTypeEnd) + "\n" + missingRowFields.map((field) => "  " + field).join("\n") + ui.slice(rowTypeEnd);
}
if (!ui.includes("obdscannerVagDtc?.counts?.manufacturerFamilyCandidates")) {
  const statsAnchor = '      <article className="research-stat"><small>Модели VehiclesDB</small><strong>{formatNumber(vehiclesDb?.counts?.models)}</strong><span>{formatNumber(vehiclesDb?.counts?.marketEvidence)} зарубежных свидетельств · RU отсутствует</span></article>\n';
  if (ui.split(statsAnchor).length - 1 !== 1) fail("VAG-family DTC research-stat insertion anchor is missing or ambiguous");
  ui = ui.replace(statsAnchor, statsAnchor + '      <article className="research-stat"><small>VAG-family P1xxx</small><strong>{formatNumber(obdscannerVagDtc?.counts?.manufacturerFamilyCandidates)}</strong><span>MIT · отдельные кандидаты · не OEM</span></article>\n');
}
const mechanicBoundary = '      {mechanicDb && <p>{formatNumber(mechanicDb.counts.manufacturerCandidates)} make-labelled DTC-кандидата MechanicDB доступны только в отдельной исследовательской вкладке. Это community reference, а не OEM-подтверждение: рынок UNKNOWN, точная применимость к модели, поколению, двигателю, КПП и ECU отсутствует. Они не входят в поиск общих DTC и не являются подтверждёнными VAG-specific кодами.</p>}\n';
if (!ui.includes("528 P1xxx определений")) {
  if (ui.split(mechanicBoundary).length - 1 !== 1) fail("VAG-family DTC boundary note anchor is missing or ambiguous");
  ui = ui.replace(mechanicBoundary, mechanicBoundary + '      {obdscannerVagDtc && <p>Отдельная MIT-база содержит {formatNumber(obdscannerVagDtc.counts.manufacturerFamilyCandidates)} VAG-family P1xxx определений из OBDScanner / Wal33D. Это только source-family кандидаты: не OEM-подтверждены, не привязаны к модели, поколению, году, рынку или ECU и не входят в поиск общих SAE/ISO DTC.</p>}\n');
}
const searchInputStart = ui.indexOf('<input aria-label="Поиск по локальному справочнику"');
const placeholderStart = searchInputStart < 0 ? -1 : ui.indexOf("placeholder={", searchInputStart);
const placeholderEnd = placeholderStart < 0 ? -1 : ui.indexOf("}", placeholderStart);
if (placeholderStart < 0 || placeholderEnd < 0) fail("Local research search placeholder expression is missing");
let placeholderExpression = ui.slice(placeholderStart, placeholderEnd + 1);
if (!placeholderExpression.includes('dataset === "obdscanner-vag-dtc"')) {
  const mechanicBranch = ': dataset === "mechanicdb" ? "P1128, P3000, Audi, Volkswagen…" :';
  if (!placeholderExpression.includes(mechanicBranch)) fail("VAG-family DTC search placeholder anchor is missing");
  placeholderExpression = placeholderExpression.replace(mechanicBranch, ': dataset === "obdscanner-vag-dtc" ? "P1101, P1128, описание неисправности…" : dataset === "mechanicdb" ? "P1128, P3000, Audi, Volkswagen…" :');
  ui = ui.slice(0, placeholderStart) + placeholderExpression + ui.slice(placeholderEnd + 1);
}
const dtcRenderAnchor = '      {dataset === "dtc" && rows.map((row) => <article className="research-result" key={row.code}>';
const dtcCandidateCard = [
  '      {dataset === "obdscanner-vag-dtc" && rows.map((row) => <article className="research-result" key={row.code}>',
  '        <div className="research-result-top"><div><small>OBDSCANNER / WAL33D · VAG-FAMILY P1xxx CANDIDATE</small><h3 className="research-code">{row.code}</h3></div><span className="research-candidate">НЕ OEM-ПОДТВЕРЖДЁН</span></div>',
  '        <p className="research-description"><b>{row.title}</b></p>',
  '        <p className="research-description">{row.titleEn}</p>',
  '        <div className="research-data-grid"><div><small>Namespace</small><b>{row.namespace}</b></div><div><small>Статус</small><b>{row.reviewStatus}</b></div><div><small>Рынок</small><b>{row.marketScope}</b></div><div><small>Точность применимости</small><b>{row.applicabilityPrecision}</b></div><div><small>Модель / ECU</small><b>Не подтверждены</b></div><div><small>OEM подтверждение</small><b>Нет</b></div></div>',
  '        <div className="research-warning-line">{row.warning}</div>',
  '        <details className="research-details"><summary>Provenance и контрольные суммы</summary><p>Ревизия {row.sourceRevision} · SHA записи {row.sourceRecordSha256} · SHA файла {row.sourceFileSha256} · SHA SQLite {row.databaseSha256} · SHA манифеста {row.sourceManifestSha256}</p></details>',
  '        <div className="research-source"><span>OBDScanner / Wal33D · MIT · attribution required · community candidate only</span>{row.sourceUrl && <a href={row.sourceUrl} target="_blank" rel="noopener noreferrer">Открыть OBDScanner</a>}</div>',
  '      </article>)}',
  "",
].join("\n");
if (!ui.includes('dataset === "obdscanner-vag-dtc" && rows.map')) {
  if (ui.split(dtcRenderAnchor).length - 1 !== 1) fail("VAG-family DTC result-card insertion anchor is missing or ambiguous");
  ui = ui.replace(dtcRenderAnchor, dtcCandidateCard + dtcRenderAnchor);
}
const creditAnchor = '      {vehiclesDb?.attributionText && <details className="research-details"><summary>Полные уведомления VehiclesDB и исходных реестров</summary><pre className="research-attribution">{vehiclesDb.attributionText}</pre></details>}\n';
if (!ui.includes("obdscannerVagDtc.attributionText")) {
  if (ui.split(creditAnchor).length - 1 !== 1) fail("VAG-family DTC attribution UI anchor is missing or ambiguous");
  ui = ui.replace(creditAnchor, '      {obdscannerVagDtc?.attributionText && <><p><a href="https://github.com/parhipov/OBDScanner" target="_blank" rel="noopener noreferrer">OBDScanner</a> — MIT; upstream <a href="https://github.com/Wal33D/dtc-database" target="_blank" rel="noopener noreferrer">Wal33D / dtc-database</a> — MIT. 528 P1xxx definitions remain community_reference_unverified and are not OEM-confirmed.</p><details className="research-details"><summary>OBDScanner / Wal33D attribution and provenance</summary><pre className="research-attribution">{obdscannerVagDtc.attributionText}</pre><p>Ревизия {obdscannerVagDtc.upstreamRevision} · SHA-256 БД {obdscannerVagDtc.databaseSha256} · SHA-256 манифеста {obdscannerVagDtc.sourceManifestSha256} · статус {obdscannerVagDtc.displayStatus}</p></details></>}\n' + creditAnchor);
}
writeText(uiFile, ui);

const dbTestFile = path.join(ROOT, "tests", "local-research-db.test.cjs");
const dbTestAnchor = '  assert.equal(audi[0].sourceLineNo, 77);\n});';
const dbTestInsert = [
  '  assert.equal(audi[0].sourceLineNo, 77);',
  '});',
  '',
  'test("VAG-family P1xxx candidates stay separate from generic DTC and never claim OEM or vehicle fitment", () => {',
  '  const rows = local.searchObdscannerVagDtcCandidates("P1101", 5, root);',
  '  assert.equal(rows.length, 1);',
  '  assert.equal(rows[0].code, "P1101");',
  '  assert.equal(rows[0].namespace, "vag_family_candidate");',
  '  assert.equal(rows[0].reviewStatus, "community_reference_unverified");',
  '  assert.equal(rows[0].displayStatus, "' + DISPLAY_STATUS + '");',
  '  assert.equal(rows[0].marketScope, "UNKNOWN");',
  '  assert.equal(rows[0].applicabilityPrecision, "manufacturer_family_candidate");',
  '  assert.equal(rows[0].exactFitment, false);',
  '  assert.equal(rows[0].vagOemConfirmation, false);',
  '  assert.equal(rows[0].ecuFitment, false);',
  '  assert.equal(rows[0].diagnosticExecutionAllowed, false);',
  '  assert.equal(rows[0].repairProcedureIncluded, false);',
  '  assert.equal(rows[0].oemPartNumberIncluded, false);',
  '  assert.equal(rows[0].license, "MIT");',
  '  assert.equal(rows[0].sourceRevision, "' + REVISION + '");',
  '  assert.match(rows[0].sourceRecordSha256, /^[a-f0-9]{64}$/);',
  '  assert.match(rows[0].sourceFileSha256, /^[a-f0-9]{64}$/);',
  '  assert.match(rows[0].sourceManifestSha256, /^[a-f0-9]{64}$/);',
  '  assert.match(rows[0].databaseSha256, /^[a-f0-9]{64}$/);',
  '  assert.equal(local.searchGenericDtcs("P1101", 5, root).length, 0);',
  '  assert.equal(local.searchObdscannerVagDtcCandidates("P0300", 5, root).length, 0);',
  '  const summary = local.getResearchSummary(root).packs.find((item) => item.id === "' + PACK_ID + '");',
  '  assert.deepEqual(summary.counts, { manufacturerFamilyCandidates: 528, p1xxxCandidates: 528, genericDtcRows: 0 });',
  '  assert.equal(summary.marketScope, "UNKNOWN");',
  '  assert.equal(summary.fitmentClaim, false);',
  '  assert.equal(summary.executionAllowed, false);',
  '});',
].join("\n");
replaceExactly(dbTestFile, dbTestAnchor, dbTestInsert, "VAG-family DTC database regression test");

const uiTestFile = path.join(ROOT, "tests", "local-research-ui-contract.test.cjs");
insertAfterUnique(uiTestFile,
  '  assert.match(component, /не являются подтверждёнными VAG-specific кодами/);',
  '\n  assert.match(component, /id: "obdscanner-vag-dtc", label: "VAG DTC · кандидаты"/);\n  assert.match(component, /НЕ OEM-ПОДТВЕРЖДЁН/);\n  assert.match(component, /528 P1xxx определений/);\n  assert.doesNotMatch(component, /detailedTechnicalExplanation/);\n  const candidateRoute = fs.readFileSync(path.join(__dirname, "../app/api/local-research/route.ts"), "utf8");\n  assert.match(candidateRoute, /dataset === "obdscanner-vag-dtc"/);\n  assert.match(candidateRoute, /searchObdscannerVagDtcCandidates/);',
  "VAG-family DTC UI contract");

const packTestFile = path.join(ROOT, "tests", "local-research-packs.test.cjs");
insertAfterUnique(packTestFile,
  '  assert.equal(result.mechanicdb_vag_dtc_candidates.unsafeRows, 0);',
  '\n  assert.equal(result.obdscanner_vag_dtc_candidates.sources, 1);\n  assert.equal(result.obdscanner_vag_dtc_candidates.manufacturerFamilyCandidates, 528);\n  assert.equal(result.obdscanner_vag_dtc_candidates.p1xxxCandidates, 528);\n  assert.equal(result.obdscanner_vag_dtc_candidates.genericDtcRows, 0);\n  assert.equal(result.obdscanner_vag_dtc_candidates.unsafeRows, 0);',
  "VAG-family DTC pack verifier test");

const verifierFile = path.join(ROOT, "scripts", "verify-local-research-packs.cjs");
replaceExactly(verifierFile,
  'manifest.packs.length === 5, "Expected five separately licensed research packs"',
  'manifest.packs.length === 6, "Expected six separately licensed research packs"',
  "research verifier expected pack count");
replaceExactly(verifierFile,
  '  const mechanicdb = byId["mechanicdb-vag-dtc-candidates-odbl"];\n  assert(ob && vag && obdb && vehiclesdb && mechanicdb, "All five research packs must be registered");',
  '  const mechanicdb = byId["mechanicdb-vag-dtc-candidates-odbl"];\n  const obdscanner = byId["' + PACK_ID + '"];\n  assert(ob && vag && obdb && vehiclesdb && mechanicdb && obdscanner, "All six research packs must be registered");',
  "research verifier pack lookup");
insertAfterUnique(verifierFile,
  '  safeFile(mechanicdb.sha256sums_file, mechanicdb.sha256sums_sha256);',
  '\n  safeFile(obdscanner.database, obdscanner.database_sha256);\n  safeFile(obdscanner.license_file, obdscanner.license_file_sha256);\n  safeFile(obdscanner.upstream_license_file, obdscanner.upstream_license_file_sha256);\n  safeFile(obdscanner.source_manifest_file, obdscanner.source_manifest_sha256);\n  safeFile(obdscanner.attribution_file, obdscanner.attribution_sha256);\n  safeFile(obdscanner.source_file, obdscanner.source_file_sha256);',
  "research verifier OBDScanner source hashes");
replaceExactly(verifierFile,
  '  const mechanicDb = openReadOnly(path.join(RESEARCH, mechanicdb.database));',
  '  const mechanicDb = openReadOnly(path.join(RESEARCH, mechanicdb.database));\n  const obdscannerDb = openReadOnly(path.join(RESEARCH, obdscanner.database));',
  "research verifier OBDScanner database open");
const verifierMechanicBlock = '    const mechanicRows = mechanicDb.prepare("SELECT oem_make, dtc_code, source_line_no, source_line_sha256, source_file_sha256, source_revision FROM dtc_candidates ORDER BY oem_make").all();';
const verifierNewBlock = [
  '    const obdscannerLicense = fs.readFileSync(path.join(RESEARCH, obdscanner.license_file), "utf8");',
  '    const obdscannerUpstreamLicense = fs.readFileSync(path.join(RESEARCH, obdscanner.upstream_license_file), "utf8");',
  '    const obdscannerAttribution = fs.readFileSync(path.join(RESEARCH, obdscanner.attribution_file), "utf8");',
  '    const obdscannerSnapshot = readJson(path.join(RESEARCH, obdscanner.source_manifest_file));',
  '    assert(obdscanner.license === "MIT" && /MIT License/i.test(obdscannerLicense) && /MIT License/i.test(obdscannerUpstreamLicense) && /Wal33D \\(Waleed Judah\\)/i.test(obdscannerUpstreamLicense), "OBDScanner/Wal33D MIT license notices are missing");',
  '    assert(obdscannerSnapshot.pack_id === "' + PACK_ID + '" && obdscannerSnapshot.source_revision === obdscanner.upstream_revision && obdscannerSnapshot.data_license === "MIT" && obdscannerSnapshot.upstream_data_license === "MIT", "OBDScanner source identity/revision/license mismatch");',
  '    assert(obdscannerSnapshot.database_sha256 === obdscanner.database_sha256 && obdscannerSnapshot.source_file_sha256 === obdscanner.source_file_sha256 && obdscannerSnapshot.source_snapshot_sha256 === obdscanner.source_snapshot_sha256, "OBDScanner source/database hash mismatch");',
  '    assert(obdscannerSnapshot.market_scope === "UNKNOWN" && obdscannerSnapshot.applicability_precision === "manufacturer_family_candidate" && obdscannerSnapshot.verification_status === "community_reference_unverified" && obdscannerSnapshot.vag_oem_confirmation === false && obdscannerSnapshot.exact_vehicle_fitment === false && obdscannerSnapshot.ecu_fitment === false && obdscannerSnapshot.diagnostic_execution_allowed === false && obdscannerSnapshot.repair_procedures_included === false && obdscannerSnapshot.oem_part_numbers_included === false, "OBDScanner candidate-only applicability/execution boundary changed");',
  '    assert(obdscanner.commercial_use_allowed === true && obdscanner.display_allowed === true && obdscanner.cache_allowed === true && obdscanner.redistribution_allowed === true && obdscanner.attribution_required === true && obdscanner.share_alike_required === false && obdscanner.fitment_claim === false && obdscanner.execution_allowed === false, "OBDScanner published MIT rights gate failed");',
  '    const obdscannerSourceBytes = fs.readFileSync(path.join(RESEARCH, obdscanner.source_file));',
  '    assert(sha256(obdscannerSourceBytes) === obdscanner.source_file_sha256 && obdscanner.source_manifest_sha256 === sha256(fs.readFileSync(path.join(RESEARCH, obdscanner.source_manifest_file))), "OBDScanner source or manifest SHA-256 mismatch");',
  '    const obdscannerCounts = {',
  '      sources: count(obdscannerDb, "SELECT count(*) AS n FROM source_registry"),',
  '      manufacturerFamilyCandidates: count(obdscannerDb, "SELECT count(*) AS n FROM dtc_candidates WHERE namespace=\\'vag_family_candidate\\' AND verification_status=\\'community_reference_unverified\\' AND market_scope=\\'UNKNOWN\\' AND applicability_precision=\\'manufacturer_family_candidate\\'"),',
  '      p1xxxCandidates: count(obdscannerDb, "SELECT count(*) AS n FROM dtc_candidates WHERE dtc_code GLOB \\'P1[0-9][0-9][0-9]\\'"),',
  '      genericDtcRows: count(obdscannerDb, "SELECT count(*) AS n FROM dtc_candidates WHERE namespace!=\\'vag_family_candidate\\'"),',
  '      unsafeRows: count(obdscannerDb, "SELECT count(*) AS n FROM dtc_candidates WHERE vehicle_fitment_claim!=0 OR ecu_fitment_claim!=0 OR diagnostic_execution_allowed!=0 OR repair_procedure_included!=0 OR oem_part_number_included!=0"),',
  '    };',
  '    const obdscannerSourceRow = obdscannerDb.prepare("SELECT * FROM source_registry WHERE source_id=\\'obdscanner-vag-dtc-candidates\\'").get();',
  '    assert(obdscannerSourceRow && obdscannerSourceRow.data_license === "MIT" && obdscannerSourceRow.upstream_license === "MIT" && obdscannerSourceRow.rights_status === "approved_by_published_license" && obdscannerSourceRow.commercial_use_allowed === 1 && obdscannerSourceRow.display_allowed === 1 && obdscannerSourceRow.offline_cache_allowed === 1 && obdscannerSourceRow.redistribution_allowed === 1 && obdscannerSourceRow.attribution_required === 1 && obdscannerSourceRow.share_alike_required === 0 && obdscannerSourceRow.market_scope === "UNKNOWN" && obdscannerSourceRow.applicability_precision === "manufacturer_family_candidate" && obdscannerSourceRow.verification_status === "community_reference_unverified" && obdscannerSourceRow.vag_oem_confirmation === 0 && obdscannerSourceRow.exact_vehicle_fitment === 0 && obdscannerSourceRow.ecu_fitment === 0 && obdscannerSourceRow.diagnostic_execution_allowed === 0 && obdscannerSourceRow.repair_procedures_included === 0 && obdscannerSourceRow.oem_part_numbers_included === 0, "OBDScanner SQLite source registry rights/provenance gate failed");',
  '    assert(obdscannerCounts.sources === 1 && obdscannerCounts.manufacturerFamilyCandidates === 528 && obdscannerCounts.p1xxxCandidates === 528 && obdscannerCounts.genericDtcRows === 0 && obdscannerCounts.unsafeRows === 0, "OBDScanner VAG-family candidate-only gate failed: " + JSON.stringify(obdscannerCounts));',
  '',
].join("\n");
insertBeforeUnique(verifierFile, verifierMechanicBlock, verifierNewBlock + verifierMechanicBlock, "research verifier OBDScanner checks");
replaceExactly(verifierFile,
  '      mechanicdb_vag_dtc_candidates: mechanicCounts,\n      production_fitment_rows_added: 0,',
  '      mechanicdb_vag_dtc_candidates: mechanicCounts,\n      obdscanner_vag_dtc_candidates: obdscannerCounts,\n      production_fitment_rows_added: 0,',
  "research verifier OBDScanner result");
replaceExactly(verifierFile,
  "    mechanicDb.close();",
  "    mechanicDb.close();\n    obdscannerDb.close();",
  "research verifier OBDScanner database close");

const readmeFile = path.join(RESEARCH, "README.md");
const readmeText = readText(readmeFile);
if (!readmeText.includes("OBDScanner VAG-family P1xxx")) {
  writeText(readmeFile, readmeText + "\n\n## OBDScanner / Wal33D VAG-family DTC candidates\n\nA separate MIT SQLite pack contains 528 P1xxx source-family definitions. The direct OBDScanner source snapshot is pinned to commit " + REVISION + " and SHA-256 is recorded per source file and record. The upstream DTC database is attributed to Wal33D / Waleed Judah under MIT. These records remain community_reference_unverified, market UNKNOWN, and manufacturer_family_candidate; they are not OEM-confirmed, are not mapped to exact vehicle/ECU applicability, and are not available in the generic SAE/ISO DTC lookup. No diagnostic execution, test plan, repair procedure, adaptation, pinout, torque value or OEM part mapping is provided.\n");
}
const docsFile = path.join(ROOT, "docs", "RESEARCH_DATA_PACKS.md");
if (fs.existsSync(docsFile)) {
  const doc = readText(docsFile);
  if (!doc.includes("OBDScanner / Wal33D VAG-family DTC candidates")) {
    writeText(docsFile, doc + "\n\n## OBDScanner / Wal33D VAG-family DTC candidates\n\nMIT-licensed, pinned source-family P1xxx definitions (528 records) in a separate SQLite namespace. community_reference_unverified; market UNKNOWN; no OEM confirmation, exact vehicle/ECU fitment, test plans, repair procedures or part mappings. Generic SAE/ISO DTC search does not query this pack.\n");
  }
}

const lifecycleFile = path.join(ROOT, "scripts", "windows-installer-lifecycle.ps1");
insertAfterUnique(lifecycleFile,
  '  if ($summary.mode -ne "offline_local_sqlite_admin") { throw "The local SQLite API did not initialize in offline mode." }',
  '\n  $researchSummary = Invoke-RestMethod -Uri "$baseUrl/api/local-research?dataset=summary" -TimeoutSec 20\n  $candidatePack = @($researchSummary.packs | Where-Object { $_.id -eq "' + PACK_ID + '" })\n  if ($candidatePack.Count -ne 1 -or $candidatePack[0].counts.manufacturerFamilyCandidates -ne 528 -or $candidatePack[0].marketScope -ne "UNKNOWN" -or $candidatePack[0].fitmentClaim -ne $false -or $candidatePack[0].executionAllowed -ne $false) { throw "Installed offline research summary does not contain the isolated MIT VAG-family candidate pack." }\n  $candidateRows = Invoke-RestMethod -Uri "$baseUrl/api/local-research?dataset=obdscanner-vag-dtc&q=P1101&limit=5" -TimeoutSec 20\n  if ($candidateRows.count -ne 1 -or $candidateRows.rows[0].code -ne "P1101" -or $candidateRows.rows[0].exactFitment -ne $false -or $candidateRows.rows[0].diagnosticExecutionAllowed -ne $false) { throw "Installed offline VAG-family candidate lookup failed its non-fitment gate." }\n  $genericRows = Invoke-RestMethod -Uri "$baseUrl/api/local-research?dataset=dtc&q=P1101&limit=5" -TimeoutSec 20\n  if ($genericRows.count -ne 0) { throw "VAG-family P1xxx candidates leaked into generic SAE/ISO DTC search." }',
  "Windows lifecycle offline VAG-family DTC checks");

const verification = {
  status: "verified_candidate_reference_only",
  pack_id: PACK_ID,
  source_revision: packManifest.source_revision,
  source_file_sha256: sourceHash,
  source_manifest_sha256: packManifestHash,
  database_sha256: databaseHash,
  license: "MIT",
  market_scope: "UNKNOWN",
  applicability_precision: "manufacturer_family_candidate",
  verification_status: "community_reference_unverified",
  display_status: DISPLAY_STATUS,
  counts: packManifest.counts,
  exact_vehicle_fitment: false,
  vag_oem_confirmation: false,
  diagnostic_execution_allowed: false,
  generic_namespace_rows: 0,
  warning: WARNING,
};
writeJson(path.join(packDir, "desktop-integration-verification.json"), verification);

const local = require(path.join(ROOT, "lib", "local-research-db.cjs"));
const candidateRows = local.searchObdscannerVagDtcCandidates("P1101", 5, RESEARCH);
if (candidateRows.length !== 1 || candidateRows[0].code !== "P1101" || candidateRows[0].exactFitment !== false ||
    candidateRows[0].diagnosticExecutionAllowed !== false || local.searchGenericDtcs("P1101", 5, RESEARCH).length !== 0) {
  fail("Runtime candidate lookup or generic-DTC namespace isolation failed");
}
const summary = local.getResearchSummary(RESEARCH).packs.find((item) => item.id === PACK_ID);
if (!summary || summary.counts.manufacturerFamilyCandidates !== 528 || summary.marketScope !== "UNKNOWN" ||
    summary.fitmentClaim !== false || summary.executionAllowed !== false) fail("Runtime research summary failed the candidate-only gate");

console.log(JSON.stringify(verification, null, 2));

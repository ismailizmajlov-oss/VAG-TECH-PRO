#!/usr/bin/env node
"use strict";

const fs = require("node:fs");
const path = require("node:path");
const crypto = require("node:crypto");
const { DatabaseSync } = require("node:sqlite");

const SOURCE_ID = "kba-de-whole-vehicle-type-approvals";
const PACK_ID = "kba-de-vag-type-approval-research";
const SOURCE_MANIFEST = "data/source-manifests/kba-de-whole-vehicle-type-approvals.json";
const BUILDER = "scripts/build_kba_de_vag_approval_research_pack.py";
const SOURCE_URL = "https://www.kba.de/DE/Themen/Typgenehmigung/Informationen_TGV/Liste_erteilter_Typgenehmigungen/liste_typgenehmigungen_Excel.xlsx?__blob=publicationFile&v=13";
const CATALOG_URL = "https://www.govdata.de/suche/daten/liste-der-erteilten-typgenehmigungen-gesamtfahrzeug?ids=1cb74abc-7356-49bf-bb07-ef5dd9d7abfb";
const LICENSE_ID = "DL-DE-BY-2.0";
const LICENSE_URL = "https://www.govdata.de/dl-de/by-2-0";
const TABLES = ["approval_records","source_files","source_label_policy","source_registry"].sort();
const INDEXES = ["idx_kba_appr_date","idx_kba_appr_make","idx_kba_appr_number","idx_kba_appr_trade","idx_kba_appr_type"];

function fail(message) { throw new Error(message); }
function assert(condition, message) { if (!condition) fail(message); }
function isOutsideRoot(baseReal, candidateReal) {
  const relative = path.relative(baseReal, candidateReal);
  return relative === ".." || relative.startsWith(".." + path.sep) || path.isAbsolute(relative);
}
function lstatIfExists(file) {
  try { return fs.lstatSync(file); }
  catch (error) {
    if (error && (error.code === "ENOENT" || error.code === "ENOTDIR")) return null;
    throw error;
  }
}
function safeJoin(root, relative) {
  const base = path.resolve(root), target = path.resolve(base, relative), rel = path.relative(base, target);
  if (!rel || isOutsideRoot(base, target)) fail("Path escaped root: " + relative);
  const baseReal = fs.realpathSync(base);
  let ancestor = target;
  while (!lstatIfExists(ancestor)) {
    const parent = path.dirname(ancestor);
    if (parent === ancestor) fail("No existing ancestor for path: " + relative);
    ancestor = parent;
  }
  let ancestorReal;
  try { ancestorReal = fs.realpathSync(ancestor); }
  catch { fail("Unresolvable symlink ancestor: " + relative); }
  if (isOutsideRoot(baseReal, ancestorReal)) fail("Symlink ancestor escaped root: " + relative);
  if (lstatIfExists(target)) {
    let targetReal;
    try { targetReal = fs.realpathSync(target); }
    catch { fail("Unresolvable symlink target: " + relative); }
    if (isOutsideRoot(baseReal, targetReal)) fail("Symlink escaped root: " + relative);
  }
  return target;
}
function readJson(file) { return JSON.parse(fs.readFileSync(file, "utf8").replace(/^\uFEFF/, "")); }
function atomicJson(file, value) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  const temp = file + ".tmp-" + process.pid;
  fs.writeFileSync(temp, JSON.stringify(value, null, 2) + "\n", "utf8");
  fs.renameSync(temp, file);
}
function shaFile(file) {
  const hash = crypto.createHash("sha256"), fd = fs.openSync(file, "r"), buffer = Buffer.allocUnsafe(1024 * 1024);
  try { let bytes; do { bytes = fs.readSync(fd, buffer, 0, buffer.length, null); if (bytes > 0) hash.update(buffer.subarray(0, bytes)); } while (bytes > 0); }
  finally { fs.closeSync(fd); }
  return hash.digest("hex");
}
function replaceOnce(source, before, after, label) {
  const count = source.split(before).length - 1;
  if (count === 0 && source.includes(after)) return source;
  if (count !== 1) fail(label + ": expected exactly one original block, found " + count);
  return source.replace(before, after);
}
function locatePackRoot(downloadRoot) {
  const candidates = [
    path.resolve(downloadRoot),
    path.resolve(downloadRoot, "kba-de-vag-approval-research-pack"),
    path.resolve(downloadRoot, "artifacts", "kba-de-vag-approval-research-pack")
  ];
  const found = candidates.find((candidate) => fs.existsSync(path.join(candidate, "manifest.json")));
  if (!found) fail("Downloaded KBA approval artifact does not contain manifest.json");
  return found;
}
function openReadOnly(file) {
  const db = new DatabaseSync(file, { readOnly: true });
  db.exec("PRAGMA query_only=ON; PRAGMA trusted_schema=OFF;");
  return db;
}
function validatePack(repoRoot, packRoot) {
  const pack = readJson(path.join(packRoot, "manifest.json"));
  const sourceFile = path.join(packRoot, "source-manifest.json");
  const buildReportFile = path.join(packRoot, "build-report.json");
  const rightsFile = path.join(packRoot, "RIGHTS-EVIDENCE.json");
  const licenseFile = path.join(packRoot, "LICENSE.txt");
  const attributionFile = path.join(packRoot, "ATTRIBUTION.md");
  const sourceSnapshotFile = path.join(packRoot, "source-snapshot.xlsx");
  const databaseFile = safeJoin(packRoot, "kba-de-vag-approvals.sqlite");
  const sourceHash = shaFile(sourceFile);
  const rootSourceHash = shaFile(safeJoin(repoRoot, SOURCE_MANIFEST));
  const builderHash = shaFile(safeJoin(repoRoot, BUILDER));
  const databaseHash = shaFile(databaseFile);
  const sourceSnapshotHash = shaFile(sourceSnapshotFile);
  const rightsHash = shaFile(rightsFile);
  const licenseHash = shaFile(licenseFile);
  const attributionHash = shaFile(attributionFile);
  const source = readJson(sourceFile);
  const buildReport = readJson(buildReportFile);
  const rightsEvidence = readJson(rightsFile);
  const rights = source.rights || {};
  const snapshot = source.snapshot || {};
  const licenseText = fs.readFileSync(licenseFile, "utf8");
  const attributionText = fs.readFileSync(attributionFile, "utf8");

  assert(pack.pack_id === PACK_ID && pack.source_id === SOURCE_ID, "KBA approval pack identity mismatch");
  assert(pack.rights_status === "approved_by_published_DL_DE_BY_2_0" && pack.license_id === LICENSE_ID && pack.license_url === LICENSE_URL, "KBA approval published licence mismatch");
  assert(pack.market_scope === "DE" && pack.applicability_precision === "type_approval_document_metadata_only" && pack.review_status === "research_only", "KBA approval market/precision/review boundary mismatch");
  assert(pack.research_pack_built === true && pack.research_pack_ingested === false && pack.product_database_ingested === false && pack.product_import_allowed === false && pack.production_import === false, "KBA approval build/import lifecycle flags mismatch");
  assert(pack.source_manifest_sha256 === sourceHash && sourceHash === rootSourceHash, "KBA approval source manifest differs from pinned repository manifest");
  assert(pack.build_script_sha256 === builderHash, "KBA approval pack was built by a stale or different builder revision");
  assert(pack.database_sha256 === databaseHash && pack.source_file_sha256 === sourceSnapshotHash, "KBA approval database/source snapshot hash mismatch");
  assert(pack.source_file_bytes === fs.statSync(sourceSnapshotFile).size, "KBA approval source snapshot byte-size mismatch");
  assert(pack.source_snapshot_sha256 === sourceSnapshotHash, "KBA approval source snapshot revision hash mismatch");
  assert(pack.license_sha256 === licenseHash && pack.rights_evidence_sha256 === rightsHash && pack.attribution_sha256 === attributionHash, "KBA approval rights/attribution file hashes mismatch");
  assert(source.source_id === SOURCE_ID && source.data_ingested === false && source.product_import_allowed === false, "KBA approval source manifest product-import boundary failed");
  assert(snapshot.status === "resource_acquired_schema_available" && snapshot.downloaded === true && snapshot.source_snapshot_sha256 === sourceSnapshotHash, "KBA approval source snapshot is not acquired and schema-verified");
  assert(rights.rights_status === "approved_by_published_DL_DE_BY_2_0", "KBA approval published licence status missing");
  for (const key of ["commercial_use_allowed","display_allowed","offline_cache_allowed","bulk_reuse_allowed","redistribution_allowed","attribution_required"]) assert(rights[key] === true, "KBA approval licence permission/condition missing: " + key);
  assert(rightsEvidence.license_id === LICENSE_ID && rightsEvidence.rights_status === rights.rights_status && rightsEvidence.commercial_use_allowed === true && rightsEvidence.display_allowed === true && rightsEvidence.offline_cache_allowed === true && rightsEvidence.bulk_reuse_allowed === true && rightsEvidence.redistribution_allowed === true && rightsEvidence.attribution_required === true, "KBA approval independent rights evidence mismatch");
  for (const key of ["individual_vehicle_fitment","exact_vehicle_fitment","model_year","generation","engine_code","gearbox_code","exact_engine_gearbox_pair","ecu_fitment","dtc_fitment","repair_applicability","diagnostic_execution_allowed","ru_eaeu_applicability"]) assert(pack.applicability?.[key] === false, "KBA approval applicability boundary failed: " + key);
  assert(pack.counts?.source_rows === 3782 && pack.counts?.approval_records === 918 && pack.counts?.manufacturer_labels === 8 && pack.counts?.distinct_approval_numbers === 918, "KBA approval pack counts changed");
  assert(buildReport.status === "verified_research_only" && buildReport.database_sha256 === databaseHash && buildReport.source_snapshot_sha256 === sourceSnapshotHash && buildReport.exact_engine_gearbox_pair_claim === false, "KBA approval build report provenance/boundary mismatch");
  assert(licenseText.includes("DL-DE BY 2.0") && licenseText.includes(LICENSE_URL), "KBA approval licence text missing");
  assert(attributionText.includes("Kraftfahrt-Bundesamt (KBA)") && attributionText.includes("DL-DE BY 2.0") && attributionText.includes(SOURCE_URL) && attributionText.includes("Modified data"), "KBA approval attribution/modified-data notice missing");

  for (const [name, descriptor] of Object.entries(pack.files || {})) {
    const file = safeJoin(packRoot, name);
    assert(fs.statSync(file).size === descriptor.byte_size && shaFile(file) === descriptor.sha256, "KBA approval artifact file hash/size mismatch: " + name);
  }

  const db = openReadOnly(databaseFile);
  let counts;
  try {
    const integrity = db.prepare("PRAGMA integrity_check").all();
    assert(integrity.length === 1 && Object.values(integrity[0])[0] === "ok", "KBA approval SQLite integrity_check failed");
    assert(db.prepare("PRAGMA foreign_key_check").all().length === 0, "KBA approval SQLite foreign_key_check failed");
    const tables = db.prepare("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name").all().map((row) => row.name).sort();
    assert(JSON.stringify(tables) === JSON.stringify(TABLES), "KBA approval SQLite table set mismatch");
    const indexes = db.prepare("SELECT name FROM sqlite_master WHERE type='index'").all().map((row) => row.name);
    assert(INDEXES.every((name) => indexes.includes(name)), "KBA approval SQLite search indexes incomplete");
    const views = db.prepare("SELECT name FROM sqlite_master WHERE type='view'").all().map((row) => row.name);
    assert(views.includes("v_approval_records"), "KBA approval provenance view missing");
    const registry = db.prepare("SELECT source_id,license_id,rights_status,market_scope,applicability_precision,review_status,source_revision,source_manifest_sha256,source_snapshot_sha256,product_import_allowed,exact_vehicle_fitment,exact_engine_gearbox_pair,ru_eaeu_applicability,ecu_fitment,dtc_fitment,repair_applicability FROM source_registry").get();
    assert(registry && registry.source_id === SOURCE_ID && registry.license_id === LICENSE_ID && registry.rights_status === rights.rights_status && registry.market_scope === "DE" && registry.applicability_precision === "type_approval_document_metadata_only" && registry.review_status === "research_only" && registry.source_revision === pack.source_revision && registry.source_manifest_sha256 === sourceHash && registry.source_snapshot_sha256 === sourceSnapshotHash && registry.product_import_allowed === 0 && registry.exact_vehicle_fitment === 0 && registry.exact_engine_gearbox_pair === 0 && registry.ru_eaeu_applicability === 0 && registry.ecu_fitment === 0 && registry.dtc_fitment === 0 && registry.repair_applicability === 0, "KBA approval SQLite source registry mismatch");
    const fileRow = db.prepare("SELECT source_id,file_name,sha256,byte_size,source_row_count,filtered_row_count,sheet_name,header_row_number FROM source_files").get();
    assert(fileRow && fileRow.source_id === SOURCE_ID && fileRow.file_name === "kba-whole-vehicle-type-approvals.xlsx" && fileRow.sha256 === sourceSnapshotHash && fileRow.byte_size === pack.source_file_bytes && fileRow.source_row_count === 3782 && fileRow.filtered_row_count === 918 && fileRow.sheet_name === "Tabelle1" && fileRow.header_row_number === 3, "KBA approval SQLite source-file registry mismatch");
    const invalid = db.prepare("SELECT count(*) AS n FROM v_approval_records WHERE market_scope!='DE' OR applicability_precision!='type_approval_document_metadata_only' OR review_status!='research_only' OR exact_vehicle_fitment!=0 OR model_year IS NOT NULL OR generation IS NOT NULL OR engine_code IS NOT NULL OR gearbox_code IS NOT NULL OR exact_engine_gearbox_pair!=0 OR ru_eaeu_applicability!=0 OR ecu_fitment!=0 OR dtc_fitment!=0 OR repair_applicability!=0").get().n;
    const pairTables = db.prepare("SELECT count(*) AS n FROM sqlite_master WHERE type='table' AND lower(name) LIKE '%pair%'").get().n;
    const technicalTables = db.prepare("SELECT count(*) AS n FROM sqlite_master WHERE type='table' AND (lower(name) LIKE '%dtc%' OR lower(name) LIKE '%repair%' OR lower(name) LIKE '%wiring%' OR lower(name) LIKE '%pinout%')").get().n;
    assert(invalid === 0 && pairTables === 0 && technicalTables === 0, "KBA approval market/applicability/technical-data boundary failed");
    counts = {
      source_rows: db.prepare("SELECT source_row_count AS n FROM source_files").get().n,
      approval_records: db.prepare("SELECT count(*) AS n FROM approval_records").get().n,
      manufacturer_labels: db.prepare("SELECT count(DISTINCT manufacturer_label) AS n FROM approval_records").get().n,
      distinct_approval_numbers: db.prepare("SELECT count(DISTINCT type_approval_number_raw) AS n FROM approval_records").get().n,
      source_label_policy_rows: db.prepare("SELECT count(*) AS n FROM source_label_policy").get().n
    };
    const expected = { source_rows: 3782, approval_records: 918, manufacturer_labels: 8, distinct_approval_numbers: 918, source_label_policy_rows: 9 };
    for (const key of Object.keys(expected)) assert(counts[key] === expected[key], "KBA approval count mismatch: " + key);
    const excludedBugatti = db.prepare("SELECT included,mapping_status FROM source_label_policy WHERE manufacturer_label='Bugatti Automobiles S.A.S.'").get();
    assert(excludedBugatti && excludedBugatti.included === 0 && excludedBugatti.mapping_status === "excluded_unresolved_group_relation", "KBA approval unresolved Bugatti group label must remain excluded");
    const malformedHashes = db.prepare("SELECT count(*) AS n FROM approval_records WHERE length(source_record_sha256)<>64 OR source_record_sha256 GLOB '*[^0-9a-f]*'").get().n;
    assert(malformedHashes === 0, "KBA approval row-level SHA-256 provenance is malformed");
  } finally { db.close(); }

  return {
    pack, counts, databaseFile, databaseHash, sourceHash, sourceSnapshotHash,
    packManifestHash: shaFile(path.join(packRoot, "manifest.json")),
    attributionHash, licenseHash, rightsHash,
    buildReportHash: shaFile(buildReportFile),
    snapshotHash: sourceSnapshotHash,
    sourceRevision: pack.source_revision
  };
}

function patchApi(desktopRoot) {
  const file = safeJoin(desktopRoot, "app/api/local-research/route.ts");
  let text = fs.readFileSync(file, "utf8");
  const stockImport = 'import * as kbaDeResearch from "../../../lib/kba-de-stock-research-db.cjs";';
  if (!text.includes('from "../../../lib/kba-de-approval-research-db.cjs"')) {
    text = replaceOnce(text, stockImport, stockImport + '\nimport * as kbaApprovalResearch from "../../../lib/kba-de-approval-research-db.cjs";', "KBA approval API import");
  }
  const stockSummary = '    if (dataset === "kba-de-summary") {\n      return Response.json({ ok: true, summary: kbaDeResearch.getKbaSummary() }, { headers });\n    }';
  text = replaceOnce(text, stockSummary, stockSummary + '\n    if (dataset === "kba-de-approvals-summary") {\n      return Response.json({ ok: true, summary: kbaApprovalResearch.getKbaApprovalSummary() }, { headers });\n    }', "KBA approval summary route");
  const stockSearch = '    else if (dataset === "kba-de") rows = kbaDeResearch.searchKbaStock(query, limit);';
  text = replaceOnce(text, stockSearch, stockSearch + '\n    else if (dataset === "kba-de-approvals") rows = kbaApprovalResearch.searchKbaApprovals(query, limit);', "KBA approval search route");
  fs.writeFileSync(file, text, "utf8");
}

function patchUi(desktopRoot) {
  const file = safeJoin(desktopRoot, "components/local-research-catalog.tsx");
  let text = fs.readFileSync(file, "utf8");
  const datasetAnchors = [
    'type Dataset = "vehicles" | "vehiclesdb" | "dtc" | "pids" | "uds" | "autodiag2" | "mechanicdb" | "wikidata" | "generic-guidance" | "wikidata-generations" | "astra" | "astra-targa" | "rdw" | "kba-de";',
    'type Dataset = "vehicles" | "vehiclesdb" | "dtc" | "pids" | "uds" | "autodiag2" | "mechanicdb" | "wikidata" | "generic-guidance" | "wikidata-generations" | "astra" | "rdw" | "kba-de";'
  ];
  const datasetAnchor = datasetAnchors.find((candidate) => text.includes(candidate));
  if (!datasetAnchor) fail("KBA approval dataset type anchor missing from the pinned desktop source.");
  const newDataset = datasetAnchor.replace(' | "kba-de";', ' | "kba-de" | "kba-de-approvals";');
  const types = [
    'type KbaApprovalSummary = { id: string; counts: { sourceRows: number; approvalRecords: number; manufacturerLabels: number; distinctApprovalNumbers: number; sourceLabelPolicyRows: number }; marketScope: string; rightsStatus: string; attributionText: string; sourceUrl: string; catalogUrl: string; license: string; licenseUrl: string; sourceRevision: string; sourceSnapshotSha256: string; sourceFileSha256: string; databaseSha256: string; sourceManifestSha256: string; warning: string; productionImport: false; productImportAllowed: false; ruEaeuApplicability: false; exactVehicleFitment: false; exactEngineGearboxPair: false; };',
    'type KbaApprovalRow = { id: string; sourceRowNumber: number; manufacturerLabel: string; manufacturerLabelMappingStatus: string; tradeName: string | null; typeDesignation: string | null; approvalObject: string | null; approvalNumber: string | null; technicalService: string | null; procedureType: string | null; approvalDate: string | null; emissionsMemberState: string | null; sourceRecordSha256: string; sourceRevision: string; sourceSnapshotSha256: string; sourceManifestSha256: string; marketScope: string; applicabilityPrecision: string; reviewStatus: string; exactVehicleFitment: false; modelYear: null; generation: null; engineCode: null; gearboxCode: null; exactEngineGearboxPair: false; ruEaeuApplicability: false; ecuFitment: false; dtcFitment: false; repairApplicability: false; sourceUrl: string; catalogUrl: string; license: string; licenseUrl: string; warning: string };'
  ].join("\n");
  if (!text.includes('type KbaApprovalSummary =')) {
    const kbaRow = 'type KbaDeRow = { id: string; sourceRowNumber: number; sourceObjectId: string; reportDateRaw: string; reportDate: string; manufacturer: string; tradeName: string; typeKey: string; federalState: string; vehicleCount: number; zsCountRaw: string; sourceRecordSha256: string; sourceRevision: string; sourceSnapshotSha256: string; sourceManifestSha256: string; marketScope: string; applicabilityPrecision: string; reviewStatus: string; exactVehicleFitment: false; modelYear: null; generation: null; engineCode: null; gearboxCode: null; exactEngineGearboxPair: false; ruEaeuApplicability: false; ecuFitment: false; dtcFitment: false; repairApplicability: false; sourceUrl: string; license: string; licenseUrl: string; warning: string };';
    text = replaceOnce(text, kbaRow, kbaRow + "\n" + types, "KBA approval UI types");
  }
  text = replaceOnce(text, datasetAnchor, newDataset, "KBA approval dataset type");
  const stockTab = '  { id: "kba-de", label: "KBA · DE", hint: "KBA · DL-DE BY 2.0 · статистика парка, не применяемость" },';
  text = replaceOnce(text, stockTab, stockTab + '\n  { id: "kba-de-approvals", label: "KBA · DE approvals", hint: "KBA · DL-DE BY 2.0 · немецкие одобрения типа, не применяемость" },', "KBA approval tab");
  const stockState = '  const [kbaDeSummary, setKbaDeSummary] = useState<KbaDeSummary | null>(null);';
  text = replaceOnce(text, stockState, stockState + '\n  const [kbaApprovalSummary, setKbaApprovalSummary] = useState<KbaApprovalSummary | null>(null);', "KBA approval state");
  const stockEffect = '  useEffect(() => {\n    let active = true;\n    fetch("/api/local-research?dataset=kba-de-summary", { cache: "no-store" })\n      .then(async (response) => { const payload = await response.json(); if (!response.ok) throw new Error(payload.error || "KBA DE справочник недоступен."); return payload; })\n      .then((payload) => { if (active && payload?.ok) setKbaDeSummary(payload.summary as KbaDeSummary); })\n      .catch(() => { if (active) setKbaDeSummary(null); });\n    return () => { active = false; };\n  }, []);';
  const approvalEffect = stockEffect + '\n  useEffect(() => {\n    let active = true;\n    fetch("/api/local-research?dataset=kba-de-approvals-summary", { cache: "no-store" })\n      .then(async (response) => { const payload = await response.json(); if (!response.ok) throw new Error(payload.error || "KBA DE одобрения недоступны."); return payload; })\n      .then((payload) => { if (active && payload?.ok) setKbaApprovalSummary(payload.summary as KbaApprovalSummary); })\n      .catch(() => { if (active) setKbaApprovalSummary(null); });\n    return () => { active = false; };\n  }, []);';
  text = replaceOnce(text, stockEffect, approvalEffect, "KBA approval summary fetch");
  text = replaceOnce(text, '  const kbaDe = kbaDeSummary;', '  const kbaDe = kbaDeSummary;\n  const kbaApproval = kbaApprovalSummary;', "KBA approval summary binding");

  const stockStat = '      <article className="research-stat"><small>KBA · агрегированные наблюдения DE</small><strong>{formatNumber(kbaDe?.counts?.vagStockObservations)}</strong><span>{formatNumber(kbaDe?.counts?.manufacturerLabels)} точных марок · {formatNumber(kbaDe?.counts?.uniqueMakeTradeNamePairs)} пар марка/имя · не vehicle fitment</span></article>';
  const approvalStat = '      <article className="research-stat"><small>KBA · одобрения типа DE</small><strong>{formatNumber(kbaApproval?.counts?.approvalRecords)}</strong><span>{formatNumber(kbaApproval?.counts?.manufacturerLabels)} точных марок · {formatNumber(kbaApproval?.counts?.distinctApprovalNumbers)} номеров · не vehicle fitment</span></article>';
  text = replaceOnce(text, stockStat, stockStat + "\n" + approvalStat, "KBA approval statistic");

  const stockBoundary = '      {kbaDe && <p>Отдельный KBA pack содержит {formatNumber(kbaDe.counts.vagStockObservations)} агрегированных наблюдений парка Германии за 2023–2026 годы. Typschlüssel показывается только как исходное поле KBA и не подтверждён как TSN. Это не индивидуальные автомобили, не VIN-комплектация, не модельный год/поколение, не код двигателя/КПП и не подтверждённая применяемость. Двигатель/КПП, ECU, DTC и ремонтные данные отсутствуют; RU/ЕАЭС применимость не выводится.</p>}';
  const approvalBoundary = '      {kbaApproval && <p>Отдельный KBA pack содержит {formatNumber(kbaApproval.counts.approvalRecords)} записей одобрений типа Германии за 2019–2026 годы. Точность: type_approval_document_metadata_only, research only. Это метаданные документов одобрения, а не список комплектаций отдельных автомобилей. Дата одобрения не является модельным годом. Нет поколений, кодов двигателя/КПП, точных пар, ECU, DTC или ремонтных процедур. Этот набор не подтверждает применимость к конкретному автомобилю и не относится к RU/ЕАЭС.</p>}';
  text = replaceOnce(text, stockBoundary, stockBoundary + "\n" + approvalBoundary, "KBA approval research boundary");

  const placeholder = 'placeholder={dataset === "kba-de" ?';
  text = replaceOnce(text, placeholder, 'placeholder={dataset === "kba-de-approvals" ? "Номер одобрения, марка, торговое имя или тип KBA…" : dataset === "kba-de" ?', "KBA approval search placeholder");

  const genericCard = '      {dataset === "generic-guidance" && (rows as unknown as GenericGuidanceRow[]).map((row) => <article className="research-result" key={row.guidanceId}>';
  const approvalCard = [
    '      {dataset === "kba-de-approvals" && (rows as unknown as KbaApprovalRow[]).map((row) => <article className="research-result" key={row.id}>',
    '        <div className="research-result-top"><div><small>KBA · GERMANY · TYPE APPROVAL METADATA</small><h3>{row.manufacturerLabel} · {row.tradeName || row.typeDesignation || "без торгового имени"}</h3></div><span className="research-candidate">DE RESEARCH ONLY</span></div>',
    '        <div className="research-data-grid">',
    '          <div><small>Номер одобрения типа</small><b>{row.approvalNumber || "—"}</b></div>',
    '          <div><small>Тип / объект одобрения</small><b>{row.typeDesignation || "—"} · {row.approvalObject || "—"}</b></div>',
    '          <div><small>Дата одобрения · не модельный год</small><b>{row.approvalDate || "—"}</b></div>',
    '          <div><small>Государство эмиссионного одобрения</small><b>{row.emissionsMemberState || "—"}</b></div>',
    '          <div><small>Двигатель / КПП / ECU</small><b>Не предоставлены · точная пара отсутствует</b></div>',
    '          <div><small>DTC / ремонт / применяемость</small><b>Не предоставлены · выполнение не разрешено</b></div>',
    '        </div>',
    '        <div className="research-warning-line">{row.warning}</div>',
    '        <details className="research-details"><summary>Построчная provenance KBA</summary>',
    '          <p>Source row {row.sourceRowNumber} · revision {row.sourceRevision} · row SHA-256 {row.sourceRecordSha256} · snapshot SHA-256 {row.sourceSnapshotSha256} · source manifest SHA-256 {row.sourceManifestSha256}</p>',
    '          <p>Рынок {row.marketScope} · статус {row.reviewStatus} · точность {row.applicabilityPrecision} · exact fitment false · exact engine/gearbox pair false · RU/ЕАЭС false</p>',
    '        </details>',
    '        <div className="research-source"><span>KBA · DL-DE BY 2.0 · DE-only · метаданные одобрений, не vehicle fitment</span><a href={row.catalogUrl} target="_blank" rel="noopener noreferrer">Открыть набор KBA</a></div>',
    '      </article>)}'
  ].join("\n");
  text = replaceOnce(text, genericCard, approvalCard + "\n" + genericCard, "KBA approval result card");

  const stockCreditEnd = 'KBA stock/type-key rows are aggregate DE research only; no exact vehicle fitment, engine/gearbox pair or RU/EAEU applicability.</p></>}';
  const approvalCredit = ' {kbaApproval && <><p><a href={kbaApproval.sourceUrl} target="_blank" rel="noopener noreferrer">Kraftfahrt-Bundesamt (KBA), Liste der erteilten Typgenehmigungen (Gesamtfahrzeug)</a> — Datenlizenz Deutschland – Namensnennung – Version 2.0 (DL-DE BY 2.0). Modified data: exact manufacturer-label candidate filter, row normalization, SQLite indexing and per-row SHA-256. Attribution: {kbaApproval.attributionText}</p><p>SHA XLSX {kbaApproval.sourceSnapshotSha256} · SHA SQLite {kbaApproval.databaseSha256} · SHA source manifest {kbaApproval.sourceManifestSha256}. DE-only approval-document metadata; no vehicle fitment or RU/EAEU applicability.</p></>}';
  text = replaceOnce(text, stockCreditEnd, stockCreditEnd + "\n" + approvalCredit, "KBA approval attribution");

  fs.writeFileSync(file, text, "utf8");
}

function patchLifecycle(desktopRoot) {
  const file = safeJoin(desktopRoot, "scripts/windows-installer-lifecycle.ps1");
  let text = fs.readFileSync(file, "utf8");
  const anchor = '  Write-Host "KBA DE aggregate stock search passed; no engine/gearbox or vehicle-fitment claim."';
  const check = [
    '  $kbaApprovalSummary = Invoke-RestMethod -Uri "$baseUrl/api/local-research?dataset=kba-de-approvals-summary" -TimeoutSec 45',
    '  if ($kbaApprovalSummary.summary.marketScope -ne "DE" -or $kbaApprovalSummary.summary.license -ne "DL-DE-BY-2.0" -or $kbaApprovalSummary.summary.rightsStatus -ne "approved_by_published_DL_DE_BY_2_0" -or $kbaApprovalSummary.summary.productionImport -ne $false -or $kbaApprovalSummary.summary.productImportAllowed -ne $false -or $kbaApprovalSummary.summary.ruEaeuApplicability -ne $false -or $kbaApprovalSummary.summary.exactEngineGearboxPair -ne $false -or $kbaApprovalSummary.summary.counts.approvalRecords -ne 918 -or $kbaApprovalSummary.summary.counts.manufacturerLabels -ne 8) { throw "KBA DE approval summary, licence or applicability boundary failed in offline desktop." }',
    '  $kbaApprovalQuery = [uri]::EscapeDataString("e1*2007/46*1892*04")',
    '  $kbaApprovalRows = Invoke-RestMethod -Uri "$baseUrl/api/local-research?dataset=kba-de-approvals&q=$kbaApprovalQuery&limit=10" -TimeoutSec 45',
    '  $kbaApprovalSample = @($kbaApprovalRows.rows | Where-Object { $_.manufacturerLabel -eq "AUDI AG" -and $_.approvalNumber -eq "e1*2007/46*1892*04" }) | Select-Object -First 1',
    '  if (-not $kbaApprovalSample -or $kbaApprovalSample.marketScope -ne "DE" -or $kbaApprovalSample.applicabilityPrecision -ne "type_approval_document_metadata_only" -or $kbaApprovalSample.reviewStatus -ne "research_only" -or $kbaApprovalSample.exactVehicleFitment -ne $false -or $kbaApprovalSample.exactEngineGearboxPair -ne $false -or $kbaApprovalSample.ruEaeuApplicability -ne $false -or $kbaApprovalSample.modelYear -ne $null -or $kbaApprovalSample.generation -ne $null -or $kbaApprovalSample.engineCode -ne $null -or $kbaApprovalSample.gearboxCode -ne $null -or $kbaApprovalSample.sourceRecordSha256 -notmatch "^[a-f0-9]{64}$") { throw "KBA DE approval search crossed its document-metadata-only boundary." }',
    '  Write-Host "KBA DE type-approval metadata search passed; no vehicle fitment or RU/EAEU claim."'
  ].join("\n");
  text = replaceOnce(text, anchor, anchor + "\n" + check, "KBA approval offline lifecycle check");
  fs.writeFileSync(file, text, "utf8");
}

function patchPackage(desktopRoot) {
  const file = safeJoin(desktopRoot, "package.json");
  const pkg = readJson(file);
  if (!pkg.scripts) fail("Desktop package scripts missing");
  if (!JSON.stringify(pkg.build?.extraResources || []).includes("data/research")) fail("Desktop package does not include offline research-data resources");
  const testFiles = ["tests/kba-de-approval-research-db.test.cjs","tests/kba-de-approval-ui-contract.test.cjs"];
  const testKeys = ["test","test:research"].filter((key) => typeof pkg.scripts[key] === "string");
  if (testKeys.length === 0) fail("Desktop package has no test script for KBA approval contract tests");
  for (const key of testKeys) {
    const command = pkg.scripts[key];
    const hasGlob = /tests\/\*\*?\/?.*\.test\.cjs|tests\/\*\.test\.cjs|node --test(\s|$)/.test(command);
    if (!hasGlob) for (const testFile of testFiles) if (!pkg.scripts[key].includes(testFile)) pkg.scripts[key] += " " + testFile;
  }
  pkg.scripts["verify:kba-de-approval-research"] = "node scripts/verify-kba-de-approval-research-pack.cjs";
  atomicJson(file, pkg);
}

function integrate(repoRoot, desktopRoot, downloadRoot, sourceRunId, sourceRunNumber, artifactSha) {
  const packRoot = locatePackRoot(downloadRoot);
  const validated = validatePack(repoRoot, packRoot);
  const researchRoot = safeJoin(desktopRoot, "data/research");
  const target = safeJoin(researchRoot, PACK_ID);
  fs.mkdirSync(researchRoot, { recursive: true });
  if (fs.existsSync(target)) fail("KBA approval research target already exists; refusing to replace existing build data.");
  fs.mkdirSync(target, { recursive: true });

  const copyNames = ["kba-de-vag-approvals.sqlite","manifest.json","source-manifest.json","ATTRIBUTION.md","LICENSE.txt","build-report.json","RIGHTS-EVIDENCE.json","source-snapshot.xlsx"];
  for (const name of copyNames) {
    const sourceFile = safeJoin(packRoot, name), targetFile = safeJoin(target, name);
    fs.copyFileSync(sourceFile, targetFile);
    if (shaFile(sourceFile) !== shaFile(targetFile)) fail("KBA approval pack copy hash mismatch: " + name);
  }

  const rel = (file) => path.relative(researchRoot, file).split(path.sep).join("/");
  const report = {
    status: "integrated_verified_research_only",
    pack_id: PACK_ID,
    source_id: SOURCE_ID,
    source_run_id: Number(sourceRunId),
    source_run_number: Number(sourceRunNumber),
    artifact_sha256: artifactSha,
    market_scope: "DE",
    rights_status: "approved_by_published_DL_DE_BY_2_0",
    source_manifest_sha256: validated.sourceHash,
    source_snapshot_sha256: validated.snapshotHash,
    pack_manifest_sha256: validated.packManifestHash,
    database_sha256: validated.databaseHash,
    source_file_sha256: validated.sourceSnapshotHash,
    source_file_bytes: validated.pack.source_file_bytes,
    counts: validated.counts,
    research_pack_ingested: true,
    product_database_ingested: false,
    production_import: false,
    product_import_allowed: false,
    ru_eaeu_applicability: false,
    exact_vehicle_fitment: false,
    exact_engine_gearbox_pair: false,
    repair_applicability: false,
    diagnostic_execution_allowed: false,
    source_snapshot_in_desktop: true
  };
  const integrationReportFile = safeJoin(target, "desktop-integration-report.json");
  atomicJson(integrationReportFile, report);

  const entry = {
    id: PACK_ID,
    source_id: SOURCE_ID,
    dataset: "KBA whole-vehicle type approval document metadata, exact manufacturer-label candidates",
    publisher: "Kraftfahrt-Bundesamt (KBA), Germany; published via GovData/Mobilithek",
    source_url: SOURCE_URL,
    catalog_url: CATALOG_URL,
    license: LICENSE_ID,
    license_url: LICENSE_URL,
    license_status: "approved_by_published_DL_DE_BY_2_0",
    rights_status: "approved_by_published_DL_DE_BY_2_0",
    market_scope: ["DE"],
    applicability_precision: "type_approval_document_metadata_only",
    review_status: "verified_research_only",
    research_pack_ingested: true,
    product_database_ingested: false,
    production_import: false,
    product_import_allowed: false,
    data_ingested: false,
    ru_eaeu_applicability: false,
    fitment_claim: false,
    exact_vehicle_fitment: false,
    exact_engine_gearbox_pair: false,
    repair_applicability: false,
    diagnostic_execution_allowed: false,
    model_year_inferred: false,
    generation_inferred: false,
    engine_codes_included: false,
    gearbox_codes_included: false,
    ecu_fitment: false,
    dtc_fitment: false,
    commercial_use_allowed: true,
    display_allowed: true,
    cache_allowed: true,
    bulk_reuse_allowed: true,
    redistribution_allowed: true,
    attribution_required: true,
    share_alike_required: false,
    database: rel(safeJoin(target, "kba-de-vag-approvals.sqlite")),
    database_sha256: validated.databaseHash,
    pack_manifest_file: rel(safeJoin(target, "manifest.json")),
    pack_manifest_sha256: validated.packManifestHash,
    source_manifest_file: rel(safeJoin(target, "source-manifest.json")),
    source_manifest_sha256: validated.sourceHash,
    attribution_file: rel(safeJoin(target, "ATTRIBUTION.md")),
    attribution_sha256: validated.attributionHash,
    license_file: rel(safeJoin(target, "LICENSE.txt")),
    license_sha256: validated.licenseHash,
    rights_evidence_file: rel(safeJoin(target, "RIGHTS-EVIDENCE.json")),
    rights_evidence_sha256: validated.rightsHash,
    build_report_file: rel(safeJoin(target, "build-report.json")),
    build_report_sha256: validated.buildReportHash,
    source_snapshot_file: rel(safeJoin(target, "source-snapshot.xlsx")),
    source_file_sha256: validated.sourceSnapshotHash,
    source_file_bytes: validated.pack.source_file_bytes,
    source_file_included_in_desktop: true,
    source_row_count: validated.pack.counts.source_rows,
    filtered_vag_row_count: validated.pack.counts.approval_records,
    source_record_hash_method: validated.pack.source_row_hash_method,
    desktop_integration_report_file: rel(integrationReportFile),
    desktop_integration_report_sha256: shaFile(integrationReportFile),
    source_revision: validated.sourceRevision,
    source_snapshot_sha256: validated.snapshotHash,
    source_run_id: Number(sourceRunId),
    source_run_number: Number(sourceRunNumber),
    source_artifact_sha256: artifactSha,
    counts: validated.pack.counts,
    limitations: [
      "Germany-only whole-vehicle type-approval document metadata; not a build sheet or individual-vehicle record.",
      "Approval date is not model year; type designation and approval number do not establish generation or exact fitment.",
      "No engine code, gearbox code, exact engine/gearbox pair, ECU, DTC, repair procedure, wiring diagram or pinout.",
      "No Russian/EAEU applicability is inferred.",
      "Source XLSX is included under DL-DE BY 2.0 with attribution and a modified-data notice."
    ]
  };

  const rootManifestFile = safeJoin(researchRoot, "manifest.json");
  const rootManifest = readJson(rootManifestFile);
  if (rootManifest.schema_version !== 1 || !Array.isArray(rootManifest.packs)) fail("Desktop research manifest schema mismatch");
  const index = rootManifest.packs.findIndex((item) => item.id === PACK_ID);
  if (index >= 0) fail("KBA approval research pack is already registered; refusing an implicit replacement.");
  rootManifest.packs.push(entry);
  atomicJson(rootManifestFile, rootManifest);

  const support = [
    ["desktop/kba-de-approval-research-db.cjs","lib/kba-de-approval-research-db.cjs"],
    ["desktop/tests/kba-de-approval-research-db.test.cjs","tests/kba-de-approval-research-db.test.cjs"],
    ["desktop/tests/kba-de-approval-ui-contract.test.cjs","tests/kba-de-approval-ui-contract.test.cjs"],
    ["desktop/scripts/verify-kba-de-approval-research-pack.cjs","scripts/verify-kba-de-approval-research-pack.cjs"]
  ];
  for (const pair of support) {
    const sourceFile = safeJoin(repoRoot, pair[0]), targetFile = safeJoin(desktopRoot, pair[1]);
    if (!fs.existsSync(sourceFile) || !fs.statSync(sourceFile).isFile()) fail("KBA approval support file missing: " + pair[0]);
    fs.mkdirSync(path.dirname(targetFile), { recursive: true });
    fs.copyFileSync(sourceFile, targetFile);
    if (shaFile(sourceFile) !== shaFile(targetFile)) fail("KBA approval support copy mismatch: " + pair[1]);
  }

  patchApi(desktopRoot);
  patchUi(desktopRoot);
  patchLifecycle(desktopRoot);
  patchPackage(desktopRoot);
  process.stdout.write(JSON.stringify({
    status: "integrated_verified_research_only",
    pack_id: PACK_ID,
    source_run_id: Number(sourceRunId),
    source_run_number: Number(sourceRunNumber),
    artifact_sha256: artifactSha,
    market_scope: ["DE"],
    source_manifest_sha256: entry.source_manifest_sha256,
    source_snapshot_sha256: entry.source_snapshot_sha256,
    database_sha256: entry.database_sha256,
    counts: { source_rows: validated.pack.counts.source_rows, approval_records: validated.pack.counts.approval_records },
    production_import: false,
    ru_eaeu_applicability: false,
    exact_engine_gearbox_pair: false
  }, null, 2) + "\n");
}

function main(argv) {
  const options = {};
  for (let i = 0; i < argv.length; i += 1) {
    const key = argv[i];
    if (!["--desktop-root","--pack-dir","--source-run-id","--source-run-number","--artifact-sha256"].includes(key) || !argv[i + 1]) fail("Invalid argument: " + key);
    options[key] = argv[++i];
  }
  if (!options["--desktop-root"] || !options["--pack-dir"] || !options["--source-run-id"] || !options["--source-run-number"] || !options["--artifact-sha256"]) fail("Missing KBA approval integration arguments");
  if (!/^\d+$/.test(options["--source-run-id"]) || !/^\d+$/.test(options["--source-run-number"]) || !/^[a-f0-9]{64}$/.test(options["--artifact-sha256"])) fail("Invalid KBA approval run/artifact provenance");
  integrate(process.cwd(), path.resolve(options["--desktop-root"]), path.resolve(options["--pack-dir"]), options["--source-run-id"], options["--source-run-number"], options["--artifact-sha256"]);
}

if (require.main === module) {
  try { main(process.argv.slice(2)); }
  catch (error) { process.stderr.write((error.stack || error.message) + "\n"); process.exitCode = 1; }
}
module.exports = { validatePack, locatePackRoot, safeJoin };

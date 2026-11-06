#!/usr/bin/env node
"use strict";
const fs = require("node:fs");
const path = require("node:path");
const crypto = require("node:crypto");
const { DatabaseSync } = require("node:sqlite");

const SOURCE_ID = "rdw-eu-vag-type-approval-open-data-nl";
const PACK_ID = "rdw-vag-nl-eu-type-approval-research";
const SOURCE_MANIFEST = "data/source-manifests/rdw-eu-vag-type-approval-open-data.json";
const SOURCE_URL = "https://data.overheid.nl/dataset/basisregistratie-voertuigen---rdw";
const TABLES = ["approval_auxiliary_rows","approval_scope","engine_designation_candidates","gearbox_classifications","registration_observations","source_file_artifacts","source_registry","source_rows"].sort();
const INDEXES = ["idx_registration_make_trade","idx_registration_make","idx_registration_trade_name","idx_registration_scope","idx_approval_number","idx_approval_variant","idx_approval_version","idx_approval_revision","idx_approval_exact_scope_key","idx_engine_designation","idx_engine_scope","idx_gearbox_classification","idx_gearbox_scope"];

function fail(message) { throw new Error(message); }
function safeJoin(root, relative) {
  const base = path.resolve(root), target = path.resolve(base, relative), rel = path.relative(base, target);
  if (!rel || rel === ".." || rel.startsWith(".." + path.sep) || path.isAbsolute(rel)) fail("Path escaped root: " + relative);
  if (fs.existsSync(target)) {
    const baseReal = fs.realpathSync(base), targetReal = fs.realpathSync(target);
    const realRel = path.relative(baseReal, targetReal);
    if (!realRel || realRel === ".." || realRel.startsWith(".." + path.sep) || path.isAbsolute(realRel)) fail("Symlink escaped root: " + relative);
  }
  return target;
}
function readJson(file) { return JSON.parse(fs.readFileSync(file, "utf8")); }
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
    path.resolve(downloadRoot, "rdw-vag-research-pack"),
    path.resolve(downloadRoot, "artifacts", "rdw-vag-research-pack"),
    path.resolve(downloadRoot, "artifacts", "rdw-vag-nl-eu-type-approval-research-pack")
  ];
  const found = candidates.find((candidate) => fs.existsSync(path.join(candidate, "manifest.json")));
  if (!found) fail("Downloaded RDW artifact does not contain manifest.json");
  return found;
}
function snapshotEntries(sourceFiles) {
  const fields = ["dataset_id","dataset_name","source_revision","sha256","byte_size","row_count","source_columns_sha256","required_columns_sha256","query_spec_sha256"];
  return sourceFiles.map((item) => Object.fromEntries(fields.map((key) => [key, item[key]]))).sort((a,b) => a.dataset_id.localeCompare(b.dataset_id));
}
function openReadOnly(file) { const db = new DatabaseSync(file, { readOnly: true }); db.exec("PRAGMA query_only=ON; PRAGMA trusted_schema=OFF;"); return db; }
function tableCount(db, table) { if (!TABLES.includes(table)) fail("Unexpected RDW table: " + table); return db.prepare('SELECT count(*) AS n FROM "' + table + '"').get().n; }

function validatePack(repoRoot, packRoot) {
  const pack = readJson(path.join(packRoot, "manifest.json"));
  const sourceFile = path.join(packRoot, "rdw-eu-vag-type-approval-open-data.json");
  const source = readJson(sourceFile);
  const buildReport = readJson(path.join(packRoot, "build-report.json"));
  const licenseFile = path.join(packRoot, "LICENSE.txt");
  const attributionFile = path.join(packRoot, "ATTRIBUTION.md");
  const databaseFile = path.join(packRoot, pack.database?.file || "rdw-vag-research.sqlite");
  const sourceHash = shaFile(sourceFile), rootSourceHash = shaFile(safeJoin(repoRoot, SOURCE_MANIFEST));
  const databaseHash = shaFile(databaseFile);
  const rights = source.rights || {}, policy = source.import_policy || {}, applicability = source.applicability_policy || {}, snapshot = source.snapshot || {};
  const licenseText = fs.readFileSync(licenseFile, "utf8"), attributionText = fs.readFileSync(attributionFile, "utf8");

  if (pack.pack_id !== PACK_ID || pack.source_id !== SOURCE_ID || pack.status !== "verified_research_only") fail("RDW pack identity/status mismatch");
  if (JSON.stringify(pack.market_scope) !== JSON.stringify(["NL"])) fail("RDW pack must be NL-only");
  if (pack.source_manifest_sha256 !== sourceHash || sourceHash !== rootSourceHash) fail("RDW pack source manifest differs from the pinned repository manifest");
  if (pack.database?.sha256 !== databaseHash || pack.database?.byte_size !== fs.statSync(databaseFile).size) fail("RDW database hash/size mismatch");
  if (pack.source_snapshot_sha256 !== source.source_snapshot_sha256 || snapshot.source_snapshot_sha256 !== pack.source_snapshot_sha256) fail("RDW aggregate snapshot hash mismatch");
  if (snapshot.status !== "filtered_research_snapshot_acquired" || JSON.stringify(snapshot.source_files) !== JSON.stringify(snapshotEntries(pack.source_files || []))) fail("RDW pinned snapshot file list mismatch");
  if (JSON.stringify(snapshot.source_revision) !== JSON.stringify(pack.source_revisions)) fail("RDW source revisions mismatch");
  if (source.data_ingested !== false || source.research_pack?.status !== "verified_research_only" || source.research_pack?.production_import !== false || source.research_pack?.ru_eaeu_applicability !== false || source.research_pack?.exact_engine_gearbox_pair !== false) fail("RDW pack crossed research-only boundary");
  if (rights.rights_status !== "approved_by_published_CC0_license" || !String(rights.data_license_status || "").includes("CC0 1.0")) fail("RDW CC0 rights evidence missing");
  for (const key of ["commercial_use_allowed","display_allowed","offline_cache_allowed","bulk_reuse_allowed","redistribution_allowed"]) if (rights[key] !== true) fail("RDW CC0 permission missing: " + key);
  if (policy.namespace !== "separate_read_only_research_pack" || policy.production_import !== false || policy.ru_eaeu_applicability !== false || policy.never_store_registration_plate !== true || policy.never_store_vin_or_holder_data !== true || policy.never_cross_join_engine_and_gearbox !== true) fail("RDW privacy/import policy mismatch");
  for (const key of ["individual_vehicle_fitment","vin_fitment","production_fitment","exact_vag_engine_code","exact_vag_gearbox_code","exact_engine_gearbox_pair","ru_eaeu_applicability","ecu_dtc_repair_applicability"]) if (applicability[key] !== false) fail("RDW applicability boundary mismatch: " + key);
  if (pack.exact_engine_gearbox_pair !== false || pack.pair_table_created !== false || buildReport.exact_engine_gearbox_pair_claim !== false) fail("RDW pack must not claim an engine/gearbox pair");
  if (!licenseText.includes("CC0 1.0") || !attributionText.includes("RDW Open Data (Netherlands)")) fail("RDW license/attribution file missing");
  if (buildReport.database_sha256 !== databaseHash || buildReport.source_snapshot_sha256 !== pack.source_snapshot_sha256) fail("RDW build report provenance mismatch");
  if (JSON.stringify(pack.search_indexes) !== JSON.stringify(INDEXES)) fail("RDW search index manifest mismatch");

  for (const item of pack.source_files || []) {
    const file = safeJoin(packRoot, item.path);
    if (!fs.statSync(file).isFile() || shaFile(file) !== item.sha256 || fs.statSync(file).size !== item.byte_size) fail("RDW source snapshot hash/size mismatch: " + item.dataset_name);
  }

  const db = openReadOnly(databaseFile);
  let counts;
  try {
    const integrity = db.prepare("PRAGMA integrity_check").all();
    if (integrity.length !== 1 || Object.values(integrity[0])[0] !== "ok") fail("RDW SQLite integrity_check failed");
    if (db.prepare("PRAGMA foreign_key_check").all().length !== 0) fail("RDW SQLite foreign_key_check failed");
    const tables = db.prepare("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name").all().map((row) => row.name).sort();
    if (JSON.stringify(tables) !== JSON.stringify(TABLES)) fail("RDW SQLite table set mismatch");
    const indexes = db.prepare("SELECT name FROM sqlite_master WHERE type='index'").all().map((row) => row.name);
    if (!INDEXES.every((name) => indexes.includes(name))) fail("RDW SQLite search indexes incomplete");
    for (const table of tables) {
      const columns = db.prepare('PRAGMA table_info("' + table + '")').all().map((row) => row.name.toLowerCase());
      if (columns.some((name) => /(vin|kenteken|plate|holder|owner|address|personal)/.test(name))) fail("Forbidden identity column in RDW table " + table);
    }
    const registry = db.prepare("SELECT source_id,license_id,rights_status,market_scope,production_import,ru_eaeu_applicability,source_manifest_sha256,verification_status FROM source_registry").all();
    if (registry.length !== 1 || registry[0].source_id !== SOURCE_ID || registry[0].license_id !== "CC0-1.0" || registry[0].rights_status !== rights.rights_status || registry[0].market_scope !== "NL" || registry[0].production_import !== 0 || registry[0].ru_eaeu_applicability !== 0 || registry[0].source_manifest_sha256 !== sourceHash || registry[0].verification_status !== "rights_cleared_research_only_not_oem_fitment") fail("RDW SQLite source_registry mismatch");
    const artifacts = db.prepare("SELECT dataset_id,dataset_name,source_revision,source_snapshot_sha256,byte_size,row_count,source_columns_sha256,required_columns_sha256,query_spec_sha256 FROM source_file_artifacts ORDER BY dataset_id").all();
    const expectedById = new Map((pack.source_files || []).map((item) => [item.dataset_id, item]));
    if (artifacts.length !== 6 || tableCount(db, "source_rows") !== pack.counts.source_rows) fail("RDW source artifact count mismatch");
    for (const item of artifacts) {
      const expected = expectedById.get(item.dataset_id);
      if (!expected || item.dataset_name !== expected.dataset_name || item.source_revision !== expected.source_revision || item.source_snapshot_sha256 !== expected.sha256 || item.byte_size !== expected.byte_size || item.row_count !== expected.row_count || item.source_columns_sha256 !== expected.source_columns_sha256 || item.required_columns_sha256 !== expected.required_columns_sha256 || item.query_spec_sha256 !== expected.query_spec_sha256) fail("RDW source file provenance mismatch: " + item.dataset_id);
    }
    const invalidScope = db.prepare(
      "SELECT (SELECT count(*) FROM approval_scope WHERE market_scope!='NL' OR exact_vehicle_fitment!=0 OR ru_eaeu_applicability!=0 OR model_year IS NOT NULL OR generation IS NOT NULL) + " +
      "(SELECT count(*) FROM registration_observations WHERE market_scope!='NL' OR verification_status!='rdw_registration_observation_not_vehicle_fitment') + " +
      "(SELECT count(*) FROM engine_designation_candidates WHERE market_scope!='NL' OR verification_status!='rdw_engine_designation_candidate_not_oem_confirmed') + " +
      "(SELECT count(*) FROM gearbox_classifications WHERE market_scope!='NL' OR verification_status!='rdw_approval_gearbox_classification_not_vag_code') + " +
      "(SELECT count(*) FROM source_rows WHERE market_scope!='NL') + " +
      "(SELECT count(*) FROM approval_auxiliary_rows a JOIN source_rows s USING(source_row_sha256) WHERE s.market_scope!='NL') AS n"
    ).get().n;
    const pairTables = db.prepare("SELECT count(*) AS n FROM sqlite_master WHERE type='table' AND lower(name) LIKE '%pair%'").get().n;
    if (invalidScope !== 0 || pairTables !== 0) fail("RDW SQLite market/applicability/pair boundary failed");
    counts = {
      sourceFiles: artifacts.length, approvalScopes: tableCount(db, "approval_scope"),
      registrationObservations: tableCount(db, "registration_observations"),
      engineCandidates: tableCount(db, "engine_designation_candidates"),
      gearboxClassifications: tableCount(db, "gearbox_classifications"),
      auxiliaryRows: tableCount(db, "approval_auxiliary_rows"), sourceRows: tableCount(db, "source_rows")
    };
    const expectedCounts = {
      sourceFiles: pack.counts.source_files, approvalScopes: pack.counts.approval_scopes,
      registrationObservations: pack.counts.registration_observations, engineCandidates: pack.counts.engine_candidates,
      gearboxClassifications: pack.counts.gearbox_classifications, auxiliaryRows: pack.counts.auxiliary_rows,
      sourceRows: pack.counts.source_rows
    };
    for (const key of Object.keys(expectedCounts)) if (counts[key] !== expectedCounts[key]) fail("RDW count mismatch: " + key);
  } finally { db.close(); }

  return {
    pack, counts, databaseFile, databaseHash, sourceHash,
    packManifestHash: shaFile(path.join(packRoot, "manifest.json")),
    attributionHash: shaFile(attributionFile), licenseHash: shaFile(licenseFile),
    buildReportHash: shaFile(path.join(packRoot, "build-report.json")),
    snapshotHash: pack.source_snapshot_sha256
  };
}

function patchApi(desktopRoot) {
  const file = safeJoin(desktopRoot, "app/api/local-research/route.ts");
  let text = fs.readFileSync(file, "utf8");
  const astraImport = 'import * as astraResearch from "../../../lib/astra-ch-tas-db.cjs";';
  if (!text.includes('from "../../../lib/rdw-vag-research-db.cjs"')) text = replaceOnce(text, astraImport, astraImport + '\nimport * as rdwResearch from "../../../lib/rdw-vag-research-db.cjs";', "RDW API import");
  const astraSummary = '    if (dataset === "astra-summary") {\n      return Response.json({ ok: true, summary: astraResearch.getAstraSummary() }, { headers });\n    }';
  text = replaceOnce(text, astraSummary, astraSummary + '\n    if (dataset === "rdw-summary") {\n      return Response.json({ ok: true, summary: rdwResearch.getRdwSummary() }, { headers });\n    }', "RDW summary route");
  const astraSearch = '    else if (dataset === "astra") rows = astraResearch.searchAstraApprovals(query, limit);';
  text = replaceOnce(text, astraSearch, astraSearch + '\n    else if (dataset === "rdw") rows = rdwResearch.searchRdwApprovals(query, limit);', "RDW search route");
  fs.writeFileSync(file, text, "utf8");
}

function patchUi(desktopRoot) {
  const file = safeJoin(desktopRoot, "components/local-research-catalog.tsx");
  let text = fs.readFileSync(file, "utf8");
  const astraType = 'type AstraSummary = {\n  counts: { approvals: number; emissionsGearboxRows: number; linkedScopeRows: number; exactScopeLinks: number; wildcardScopeLinks: number; unlinkedScopeRows: number };\n  sourceRevision: string; sourceSnapshotSha256: string; databaseSha256: string; sourceManifestSha256: string;\n  marketScope: string; rightsStatus: string; attributionText: string; sourceUrl: string; ruEaeuApplicability: false;\n};';
  const rdwTypes = astraType + '\ntype RdwSummary = { counts: { approvalScopes: number; registrationObservations: number; engineDesignationCandidates: number; gearboxClassifications: number; auxiliaryRows: number; sourceRows: number; sourceFiles: number }; marketScope: string; rightsStatus: string; attributionText: string; sourceUrl: string; licenseUrl: string; sourceSnapshotSha256: string; databaseSha256: string; sourceManifestSha256: string; warning: string };\ntype RdwRegistrationObservation = { make: string; tradeName: string; vehicleCategory: string; registrationCount: number; sourceRowSha256: string; sourceRevision: string | null; sourceFileSha256: string | null; sourceUrl: string; verificationStatus: string };\ntype RdwEngineCandidate = { engineDesignation: string; engineTypeApprovalNumber: string | null; displacementCc: number | null; cylinders: number | null; sourceRowSha256: string; sourceRevision: string | null; sourceFileSha256: string | null; sourceUrl: string; verificationStatus: string };\ntype RdwGearboxCandidate = { gearboxTypeClassification: string; sourceRowSha256: string; sourceRevision: string | null; sourceFileSha256: string | null; sourceUrl: string; verificationStatus: string };\ntype RdwRow = { id: string; typeApprovalNumber: string; variant: string; version: string; revision: string; exactScopeKey: { typeApprovalNumber: string; variant: string; version: string; revision: string }; applicabilityPrecision: string; reviewStatus: string; marketScope: string; registrationObservations: RdwRegistrationObservation[]; engineDesignationCandidates: RdwEngineCandidate[]; gearboxClassifications: RdwGearboxCandidate[]; modelYear: null; generation: null; engineCode: null; gearboxCode: null; exactVehicleFitment: false; productionFitment: false; ruEaeuApplicability: false; exactEngineGearboxPair: false; repairApplicability: false; diagnosticExecutionAllowed: false; sourceRevision: string; sourceSnapshotSha256: string; databaseSha256: string; sourceManifestSha256: string; marketWarning: string; warning: string; sourceUrl: string };';
  text = replaceOnce(text, astraType, rdwTypes, "RDW summary/row types");
  text = replaceOnce(text,
    'type Dataset = "vehicles" | "vehiclesdb" | "dtc" | "pids" | "uds" | "autodiag2" | "mechanicdb" | "wikidata" | "generic-guidance" | "wikidata-generations" | "astra";',
    'type Dataset = "vehicles" | "vehiclesdb" | "dtc" | "pids" | "uds" | "autodiag2" | "mechanicdb" | "wikidata" | "generic-guidance" | "wikidata-generations" | "astra" | "rdw";',
    "RDW dataset type");
  text = replaceOnce(text,
    '  { id: "astra", label: "ОТТС · CH", hint: "ASTRA/FEDRO · Swiss OGD · только Швейцария" },',
    '  { id: "astra", label: "ОТТС · CH", hint: "ASTRA/FEDRO · Swiss OGD · только Швейцария" },\n  { id: "rdw", label: "ОТТС · NL/EU", hint: "RDW · CC0 · Нидерланды · исследовательский слой" },',
    "RDW tab");
  text = replaceOnce(text,
    '  const [astraSummary, setAstraSummary] = useState<AstraSummary | null>(null);',
    '  const [astraSummary, setAstraSummary] = useState<AstraSummary | null>(null);\n  const [rdwSummary, setRdwSummary] = useState<RdwSummary | null>(null);',
    "RDW state");
  const astraEffect = '  useEffect(() => {\n    let active = true;\n    fetch("/api/local-research?dataset=astra-summary", { cache: "no-store" })\n      .then(async (response) => { const payload = await response.json(); if (!response.ok) throw new Error(payload.error || "ASTRA CH справочник недоступен."); return payload; })\n      .then((payload) => { if (active && payload?.ok) setAstraSummary(payload.summary as AstraSummary); })\n      .catch(() => { if (active) setAstraSummary(null); });\n    return () => { active = false; };\n  }, []);';
  const rdwEffect = astraEffect + '\n  useEffect(() => {\n    let active = true;\n    fetch("/api/local-research?dataset=rdw-summary", { cache: "no-store" })\n      .then(async (response) => { const payload = await response.json(); if (!response.ok) throw new Error(payload.error || "RDW NL/EU справочник недоступен."); return payload; })\n      .then((payload) => { if (active && payload?.ok) setRdwSummary(payload.summary as RdwSummary); })\n      .catch(() => { if (active) setRdwSummary(null); });\n    return () => { active = false; };\n  }, []);';
  text = replaceOnce(text, astraEffect, rdwEffect, "RDW summary fetch");
  text = replaceOnce(text, '  const astra = astraSummary;', '  const astra = astraSummary;\n  const rdw = rdwSummary;', "RDW summary binding");
  const astraStat = '      <article className="research-stat"><small>ОТТС / типовые одобрения CH</small><strong>{formatNumber(astra?.counts?.approvals)}</strong><span>{formatNumber(astra?.counts?.linkedScopeRows)} связей variant/version · не RU/ЕАЭС</span></article>';
  text = replaceOnce(text, astraStat, astraStat + '\n      <article className="research-stat"><small>ОТТС / одобрения NL</small><strong>{formatNumber(rdw?.counts?.approvalScopes)}</strong><span>{formatNumber(rdw?.counts?.engineDesignationCandidates)} обозначений двигателя · {formatNumber(rdw?.counts?.gearboxClassifications)} классификаций КПП · NL only</span></article>', "RDW statistic");
  const astraBoundary = '      {astra && <p>Отдельный справочник ASTRA/FEDRO содержит {formatNumber(astra.counts.approvals)} швейцарских типовых одобрений и {formatNumber(astra.counts.emissionsGearboxRows)} строк выбросов/классов КПП. Это только рынок CH: не российские/ЕАЭС ОТТС, не VIN-комплектация и не заводская применимость. engineType сохраняется как обозначение в одобрении и не подтверждает заводской код двигателя VAG; stamped marking — отдельно; chGearboxType — швейцарская классификация, не код КПП VAG. Точные связи variant/version относятся только к области швейцарского одобрения; wildcard не является точной версией.</p>}';
  text = replaceOnce(text, astraBoundary, astraBoundary + '\n      {rdw && <p>Отдельный RDW pack содержит {formatNumber(rdw.counts.approvalScopes)} точных ключей одобрения variant/version/revision для Нидерландов. Это не российские/ЕАЭС ОТТС и не применимость к конкретному автомобилю. Обозначения двигателя и классификации КПП показываются отдельными списками: их совместное присутствие в одном approval scope не подтверждает пару; это не заводские коды VAG, не модельный год, не поколение и не ремонтные данные.</p>}', "RDW research boundary");
  text = replaceOnce(text, 'placeholder={dataset === "astra" ?', 'placeholder={dataset === "rdw" ? "Номер одобрения, variant/version, модель или обозначение двигателя RDW…" : dataset === "astra" ?', "RDW search placeholder");

  const genericCard = '      {dataset === "generic-guidance" && (rows as unknown as GenericGuidanceRow[]).map((row) => <article className="research-result" key={row.guidanceId}>';
  const rdwCard = [
    '      {dataset === "rdw" && (rows as unknown as RdwRow[]).map((row) => <article className="research-result" key={row.id}>',
    '        <div className="research-result-top"><div><small>RDW OPEN DATA · NL · APPROVAL SCOPE</small><h3>{row.typeApprovalNumber}</h3></div><span className="research-candidate">NL RESEARCH ONLY</span></div>',
    '        <div className="research-data-grid">',
    '          <div><small>Variant / version / revision</small><b>{[row.variant, row.version, row.revision].join(" · ")}</b></div>',
    '          <div><small>Марка / коммерческое имя из регистрации</small><b>{row.registrationObservations.map((item) => [item.make, item.tradeName].filter(Boolean).join(" ")).filter(Boolean).join(" · ") || "—"}</b></div>',
    '          <div><small>Обозначения двигателя RDW · не коды VAG</small><b>{row.engineDesignationCandidates.map((item) => item.engineDesignation).join(" · ") || "—"}</b></div>',
    '          <div><small>Классификации КПП RDW · не коды VAG</small><b>{row.gearboxClassifications.map((item) => item.gearboxTypeClassification).join(" · ") || "—"}</b></div>',
    '          <div><small>Пара двигатель / КПП</small><b>Не подтверждена · отдельные наборы наблюдений</b></div>',
    '          <div><small>Рынок / модельный год / поколение</small><b>NL only · не предоставлены · не выведены</b></div>',
    '        </div>',
    '        <div className="research-warning-line">{row.warning}</div>',
    '        <details className="research-details"><summary>Построчная provenance RDW</summary>',
    '          <p>Точность: {row.applicabilityPrecision} · ревизии: {row.sourceRevision} · SHA snapshot {row.sourceSnapshotSha256} · SHA SQLite {row.databaseSha256} · SHA source manifest {row.sourceManifestSha256}</p>',
    '          <ul>{row.engineDesignationCandidates.map((item) => <li key={item.sourceRowSha256}>Engine designation {item.engineDesignation} · {item.verificationStatus} · rev {item.sourceRevision} · row SHA {item.sourceRowSha256} · file SHA {item.sourceFileSha256}</li>)}</ul>',
    '          <ul>{row.gearboxClassifications.map((item) => <li key={item.sourceRowSha256}>Gearbox classification {item.gearboxTypeClassification} · {item.verificationStatus} · rev {item.sourceRevision} · row SHA {item.sourceRowSha256} · file SHA {item.sourceFileSha256}</li>)}</ul>',
    '        </details>',
    '        <div className="research-source"><span>RDW · CC0 1.0 · NL-only · не vehicle fitment · не OEM DTC/repair data</span><a href={row.sourceUrl} target="_blank" rel="noopener noreferrer">Открыть каталог RDW</a></div>',
    '      </article>)}'
  ].join("\n");
  text = replaceOnce(text, genericCard, rdwCard + "\n" + genericCard, "RDW result card");

  const creditsAnchor = '      <p>SQLite SHA-256 · OBDex: {obdex?.databaseSha256 || "недоступен"}</p>';
  const credits = '      {rdw && <><p><a href={rdw.sourceUrl} target="_blank" rel="noopener noreferrer">RDW Open Data (Netherlands)</a> — CC0 1.0; отдельный NL-only research pack, не российские/ЕАЭС данные. {rdw.attributionText}</p><p>SHA snapshot {rdw.sourceSnapshotSha256} · SHA SQLite {rdw.databaseSha256} · SHA source manifest {rdw.sourceManifestSha256}. Обозначения двигателя и классификации КПП остаются раздельными; exact pair, VAG factory code, model year, generation, ECU, DTC и repair applicability не подтверждены.</p></>}';
  text = replaceOnce(text, creditsAnchor, credits + "\n" + creditsAnchor, "RDW attribution credits");
  fs.writeFileSync(file, text, "utf8");
}

function patchLifecycle(desktopRoot) {
  const file = safeJoin(desktopRoot, "scripts/windows-installer-lifecycle.ps1");
  let text = fs.readFileSync(file, "utf8");
  const anchor = '  Write-Host "ASTRA offline CH approval search passed; no VAG factory fitment or repair claims."';
  const check = [
    '  $rdwSummary = Invoke-RestMethod -Uri "$baseUrl/api/local-research?dataset=rdw-summary" -TimeoutSec 45',
    '  if ($rdwSummary.summary.marketScope -ne "NL" -or $rdwSummary.summary.rightsStatus -ne "approved_by_published_CC0_license" -or $rdwSummary.summary.productionImport -ne $false -or $rdwSummary.summary.ruEaeuApplicability -ne $false -or $rdwSummary.summary.counts.approvalScopes -ne 96519 -or $rdwSummary.summary.counts.engineDesignationCandidates -ne 93836 -or $rdwSummary.summary.counts.gearboxClassifications -ne 93548) { throw "RDW NL/EU summary or rights/market boundary failed in offline desktop." }',
    '  $rdwQuery = [uri]::EscapeDataString("e1*2018/858*00403*07")',
    '  $rdwRows = Invoke-RestMethod -Uri "$baseUrl/api/local-research?dataset=rdw&q=$rdwQuery&limit=50" -TimeoutSec 45',
    '  $rdwSample = @($rdwRows.rows | Where-Object { $_.typeApprovalNumber -eq "e1*2018/858*00403*07" -and $_.variant -eq "ACDUCAX0" -and $_.version -eq "FD6FD6DD002PR4VNB50OO" -and $_.revision -eq "0" }) | Select-Object -First 1',
    '  if (-not $rdwSample -or $rdwSample.marketScope -ne "NL" -or $rdwSample.engineCode -ne $null -or $rdwSample.gearboxCode -ne $null -or $rdwSample.exactEngineGearboxPair -ne $false -or $rdwSample.ruEaeuApplicability -ne $false -or $rdwSample.exactVehicleFitment -ne $false -or $rdwSample.repairApplicability -ne $false -or $rdwSample.diagnosticExecutionAllowed -ne $false) { throw "RDW offline search crossed its NL approval-only boundary." }',
    '  if (@($rdwSample.engineDesignationCandidates | Where-Object { $_.engineDesignation -eq "DUC" }).Count -lt 1 -or @($rdwSample.gearboxClassifications | Where-Object { $_.gearboxTypeClassification -eq "A" }).Count -lt 1) { throw "RDW engine/gearbox source observations were not kept separately and searchable." }',
    '  Write-Host "RDW NL/EU approval search passed; engine and gearbox remain separate research candidates."'
  ].join("\n");
  text = replaceOnce(text, anchor, anchor + "\n" + check, "RDW offline lifecycle check");
  fs.writeFileSync(file, text, "utf8");
}

function patchPackage(desktopRoot) {
  const file = safeJoin(desktopRoot, "package.json");
  const pkg = readJson(file);
  if (!pkg.scripts) fail("Desktop package scripts missing");
  if (!JSON.stringify(pkg.build?.extraResources || []).includes("data/research")) fail("Desktop package does not include offline research-data resources");
  const testKey = typeof pkg.scripts["test:research"] === "string" ? "test:research" : (typeof pkg.scripts.test === "string" ? "test" : null);
  if (!testKey) fail("Desktop package has no test script for RDW contract tests");
  const testCommand = pkg.scripts[testKey];
  const hasGlob = /tests\/\*\*?\/?.*\.test\.cjs|tests\/\*\.test\.cjs/.test(testCommand);
  if (!hasGlob) {
    for (const testFile of ["tests/rdw-vag-research-db.test.cjs", "tests/rdw-vag-research-ui-contract.test.cjs"]) {
      if (!pkg.scripts[testKey].includes(testFile)) pkg.scripts[testKey] += " " + testFile;
    }
  }
  pkg.scripts["verify:rdw-research"] = "node scripts/verify-rdw-vag-research-pack.cjs";
  atomicJson(file, pkg);
}
function integrate(repoRoot, desktopRoot, downloadRoot, sourceRunId, sourceRunNumber, artifactSha) {
  const packRoot = locatePackRoot(downloadRoot);
  const validated = validatePack(repoRoot, packRoot);
  const researchRoot = safeJoin(desktopRoot, "data/research");
  const target = safeJoin(researchRoot, PACK_ID);
  fs.mkdirSync(researchRoot, { recursive: true });
  if (fs.existsSync(target)) fs.rmSync(target, { recursive: true, force: true });
  fs.cpSync(packRoot, target, { recursive: true });
  const rel = (file) => path.relative(researchRoot, file).split(path.sep).join("/");
  const report = {
    status: "integrated_verified_research_only", pack_id: PACK_ID, source_id: SOURCE_ID,
    source_run_id: Number(sourceRunId), source_run_number: Number(sourceRunNumber), artifact_sha256: artifactSha,
    market_scope: ["NL"], rights_status: "approved_by_published_CC0_license",
    source_manifest_sha256: validated.sourceHash, source_snapshot_sha256: validated.snapshotHash,
    pack_manifest_sha256: validated.packManifestHash, database_sha256: validated.databaseHash,
    counts: validated.counts, production_import: false, ru_eaeu_applicability: false,
    exact_engine_gearbox_pair: false, exact_vehicle_fitment: false, repair_applicability: false,
    diagnostic_execution_allowed: false
  };
  const integrationReportFile = safeJoin(target, "desktop-integration-report.json");
  atomicJson(integrationReportFile, report);
  const entry = {
    id: PACK_ID, source_id: SOURCE_ID, dataset: "RDW filtered vehicle/type-approval research",
    publisher: "RDW (Dienst Wegverkeer), Netherlands", source_url: SOURCE_URL,
    license: "CC0 1.0", license_url: "https://creativecommons.org/publicdomain/zero/1.0/",
    license_status: "approved_by_published_CC0_license", rights_status: "approved_by_published_CC0_license",
    market_scope: ["NL"], applicability_precision: "exact_RDW_approval_variant_version_revision_scope",
    review_status: "verified_research_only", production_import: false, product_import_allowed: false,
    ru_eaeu_applicability: false, fitment_claim: false, exact_vehicle_fitment: false,
    exact_engine_gearbox_pair: false, repair_applicability: false, diagnostic_execution_allowed: false,
    ecu_dtc_repair_applicability: false, model_year_inferred: false, generation_inferred: false,
    engine_code_claim: false, gearbox_code_claim: false,
    commercial_use_allowed: true, display_allowed: true, cache_allowed: true, bulk_reuse_allowed: true,
    redistribution_allowed: true, attribution_required: false, share_alike_required: false,
    database: rel(safeJoin(target, validated.pack.database.file)), database_sha256: validated.databaseHash,
    pack_manifest_file: rel(safeJoin(target, "manifest.json")), pack_manifest_sha256: validated.packManifestHash,
    source_manifest_file: rel(safeJoin(target, "rdw-eu-vag-type-approval-open-data.json")), source_manifest_sha256: validated.sourceHash,
    attribution_file: rel(safeJoin(target, "ATTRIBUTION.md")), attribution_sha256: validated.attributionHash,
    license_file: rel(safeJoin(target, "LICENSE.txt")), license_sha256: validated.licenseHash,
    build_report_file: rel(safeJoin(target, "build-report.json")), build_report_sha256: validated.buildReportHash,
    desktop_integration_report_file: rel(integrationReportFile), desktop_integration_report_sha256: shaFile(integrationReportFile),
    source_revision: validated.pack.source_revisions, source_revisions: validated.pack.source_revisions,
    source_snapshot_sha256: validated.snapshotHash, search_indexes: validated.pack.search_indexes,
    counts: validated.pack.counts, scope_coverage: validated.pack.scope_coverage,
    source_run_id: Number(sourceRunId), source_run_number: Number(sourceRunNumber), source_artifact_sha256: artifactSha,
    limitations: [
      "Netherlands-only RDW approval research; not Russian/EAEU OTTS or market applicability.",
      "Engine designation is an RDW candidate, not a confirmed VAG factory engine code.",
      "Gearbox classification is an RDW classification, not a VAG gearbox code.",
      "Engine and gearbox observations remain separate; no exact pair is established.",
      "Approval scope is not individual vehicle fitment; no VIN, model year, generation, ECU, DTC or repair applicability."
    ]
  };
  const rootManifestFile = safeJoin(researchRoot, "manifest.json");
  const rootManifest = readJson(rootManifestFile);
  if (rootManifest.schema_version !== 1 || !Array.isArray(rootManifest.packs)) fail("Desktop research manifest schema mismatch");
  const index = rootManifest.packs.findIndex((item) => item.id === PACK_ID);
  if (index >= 0) rootManifest.packs[index] = entry; else rootManifest.packs.push(entry);
  atomicJson(rootManifestFile, rootManifest);

  const support = [
    ["desktop/rdw-vag-research-db.cjs","lib/rdw-vag-research-db.cjs"],
    ["desktop/tests/rdw-vag-research-db.test.cjs","tests/rdw-vag-research-db.test.cjs"],
    ["desktop/tests/rdw-vag-research-ui-contract.test.cjs","tests/rdw-vag-research-ui-contract.test.cjs"],
    ["desktop/scripts/verify-rdw-vag-research-pack.cjs","scripts/verify-rdw-vag-research-pack.cjs"]
  ];
  for (const pair of support) {
    const source = safeJoin(repoRoot, pair[0]), targetFile = safeJoin(desktopRoot, pair[1]);
    if (!fs.existsSync(source) || !fs.statSync(source).isFile()) fail("RDW support file missing: " + pair[0]);
    fs.mkdirSync(path.dirname(targetFile), { recursive: true });
    fs.copyFileSync(source, targetFile);
    if (shaFile(source) !== shaFile(targetFile)) fail("RDW support copy mismatch: " + pair[1]);
  }
  patchApi(desktopRoot);
  patchUi(desktopRoot);
  patchLifecycle(desktopRoot);
  patchPackage(desktopRoot);
  process.stdout.write(JSON.stringify({
    status: "integrated_verified_research_only", pack_id: PACK_ID,
    source_run_id: Number(sourceRunId), source_run_number: Number(sourceRunNumber),
    artifact_sha256: artifactSha, market_scope: ["NL"],
    source_manifest_sha256: entry.source_manifest_sha256, source_snapshot_sha256: entry.source_snapshot_sha256,
    pack_manifest_sha256: entry.pack_manifest_sha256, database_sha256: entry.database_sha256,
    desktop_integration_report_sha256: entry.desktop_integration_report_sha256, counts: entry.counts,
    production_import: false, ru_eaeu_applicability: false, exact_engine_gearbox_pair: false,
    repair_applicability: false
  }, null, 2) + "\n");
}

function main(argv) {
  const options = {};
  for (let i = 0; i < argv.length; i += 1) {
    const key = argv[i];
    if (!["--desktop-root","--pack-dir","--source-run-id","--source-run-number","--artifact-sha256"].includes(key) || !argv[i + 1]) fail("Invalid argument: " + key);
    options[key] = argv[++i];
  }
  if (!options["--desktop-root"] || !options["--pack-dir"] || !options["--source-run-id"] || !options["--source-run-number"] || !options["--artifact-sha256"]) fail("Missing RDW integration arguments");
  if (!/^\d+$/.test(options["--source-run-id"]) || !/^\d+$/.test(options["--source-run-number"]) || !/^[a-f0-9]{64}$/.test(options["--artifact-sha256"])) fail("Invalid RDW run/artifact provenance");
  integrate(process.cwd(), path.resolve(options["--desktop-root"]), path.resolve(options["--pack-dir"]), options["--source-run-id"], options["--source-run-number"], options["--artifact-sha256"]);
}
if (require.main === module) {
  try { main(process.argv.slice(2)); }
  catch (error) { process.stderr.write((error.stack || error.message) + "\n"); process.exitCode = 1; }
}
module.exports = { validatePack, locatePackRoot };

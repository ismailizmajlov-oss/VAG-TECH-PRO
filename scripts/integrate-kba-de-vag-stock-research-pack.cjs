#!/usr/bin/env node
"use strict";
const fs = require("node:fs");
const path = require("node:path");
const crypto = require("node:crypto");
const { DatabaseSync } = require("node:sqlite");

const SOURCE_ID = "kba-de-fz-hersteller-handelsnamen-pkw";
const PACK_ID = "kba-de-vag-stock-research";
const SOURCE_MANIFEST = "data/source-manifests/kba-de-fz-hersteller-handelsnamen-pkw.json";
const SOURCE_URL = "https://www.govdata.de/suche/daten/fz-hersteller-handelsnamen-pkw?ids=638594fd-195a-4e03-b91c-f5ea2eacfa39";
const LICENSE_ID = "DL-DE-BY-2.0";
const TABLES = ["federal_states","manufacturers","pack_metadata","reference_dates","source_files","source_registry","stock_observations","trade_names","type_keys"].sort();
const INDEXES = ["idx_kba_stock_manufacturer","idx_kba_stock_trade_name","idx_kba_stock_type_key","idx_kba_stock_report_date","idx_kba_stock_make_trade_date","idx_kba_stock_federal_state"];

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

  // Check the nearest existing ancestor, not only the leaf. This also rejects
  // symlinked parents when the requested destination does not exist yet.
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
    const targetRelative = path.relative(baseReal, targetReal);
    if (!targetRelative || isOutsideRoot(baseReal, targetReal)) fail("Symlink escaped root: " + relative);
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
    path.resolve(downloadRoot, "kba-de-vag-stock-research-pack"),
    path.resolve(downloadRoot, "artifacts", "kba-de-vag-stock-research-pack")
  ];
  const found = candidates.find((candidate) => fs.existsSync(path.join(candidate, "manifest.json")));
  if (!found) fail("Downloaded KBA artifact does not contain manifest.json");
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
  const source = readJson(sourceFile);
  const buildReport = readJson(path.join(packRoot, "build-report.json"));
  const licenseFile = path.join(packRoot, "LICENSE.txt");
  const attributionFile = path.join(packRoot, "ATTRIBUTION.md");
  const sourceCsv = path.join(packRoot, "source-snapshot.csv");
  const databaseFile = safeJoin(packRoot, pack.database?.path || "");
  const sourceHash = shaFile(sourceFile), rootSourceHash = shaFile(safeJoin(repoRoot, SOURCE_MANIFEST));
  const builderHash = shaFile(safeJoin(repoRoot, "scripts/build_kba_de_vag_stock_research_pack.py"));
  const databaseHash = shaFile(databaseFile), sourceCsvHash = shaFile(sourceCsv);
  const rights = source.rights || {}, snapshot = source.snapshot || {};
  const licenseText = fs.readFileSync(licenseFile, "utf8"), attributionText = fs.readFileSync(attributionFile, "utf8");

  assert(pack.pack_id === PACK_ID && pack.source_id === SOURCE_ID && pack.status === "verified_research_only", "KBA pack identity/status mismatch");
  assert(JSON.stringify(pack.market_scope) === JSON.stringify(["DE"]), "KBA pack must be DE-only");
  assert(pack.license === LICENSE_ID && pack.license_url === "https://www.govdata.de/dl-de/by-2-0", "KBA licence identity mismatch");
  assert(pack.source_manifest_sha256 === sourceHash && sourceHash === rootSourceHash, "KBA pack source manifest differs from pinned repository manifest");
  assert(pack.build_script_sha256 === builderHash, "KBA pack was built by a different or stale builder revision");
  assert(pack.database?.sha256 === databaseHash && pack.database?.byte_size === fs.statSync(databaseFile).size, "KBA SQLite hash/size mismatch");
  assert(pack.source_snapshot_sha256 === sourceCsvHash && sourceCsvHash === snapshot.source_snapshot_sha256, "KBA CSV snapshot hash mismatch");
  assert(pack.source_file?.byte_size === fs.statSync(sourceCsv).size && pack.source_file?.row_count === snapshot.source_row_count, "KBA CSV byte-size/row-count mismatch");
  assert(source.source_id === SOURCE_ID && source.data_ingested === false && source.product_import_allowed === false, "KBA source manifest product-import boundary failed");
  assert(snapshot.status === "source_snapshot_acquired_schema_verified" && snapshot.downloaded === true, "KBA source snapshot is not acquired and schema-verified");
  assert(rights.rights_status === "approved_by_published_DL_DE_BY_2_0", "KBA published licence status missing");
  for (const key of ["commercial_use_allowed","display_allowed","offline_cache_allowed","bulk_reuse_allowed","redistribution_allowed","attribution_required"]) assert(rights[key] === true, "KBA licence permission/condition missing: " + key);
  for (const key of ["production_import","product_import_allowed","data_ingested","ru_eaeu_applicability","individual_vehicle_fitment","exact_vehicle_fitment","model_year_inferred","generation_inferred","engine_codes_included","gearbox_codes_included","exact_engine_gearbox_pair","ecu_fitment","dtc_fitment","repair_applicability","diagnostic_execution_allowed"]) assert(pack[key] === false, "KBA applicability boundary failed: " + key);
  assert(pack.applicability_precision === "aggregate_stock_observation" && pack.review_status === "research_only", "KBA aggregate precision/review status mismatch");
  assert(pack.research_pack_ingested === true && pack.product_database_ingested === false && buildReport.research_pack_ingested === true && buildReport.product_database_ingested === false, "KBA research-pack ingestion must be distinct from production database import");
  assert(pack.source_record_hash_method && /^[a-f0-9]{64}$/.test(pack.build_script_sha256 || ""), "KBA row-hash method/builder hash missing");
  assert(licenseText.includes("DL-DE BY 2.0") && licenseText.includes("https://www.govdata.de/dl-de/by-2-0"), "KBA licence reference missing");
  assert(attributionText.includes("Kraftfahrt-Bundesamt (KBA)") && attributionText.includes("DL-DE BY 2.0") && attributionText.includes(SOURCE_URL) && attributionText.includes("Modified data"), "KBA attribution/modified-data notice missing");
  assert(buildReport.status === "verified_research_only" && buildReport.database_sha256 === databaseHash && buildReport.source_snapshot_sha256 === sourceCsvHash && buildReport.exact_engine_gearbox_pair_claim === false, "KBA build report provenance/boundary mismatch");
  assert(JSON.stringify(pack.search_indexes) === JSON.stringify(INDEXES), "KBA SQLite index manifest mismatch");

  const db = openReadOnly(databaseFile);
  let counts;
  try {
    const integrity = db.prepare("PRAGMA integrity_check").all();
    assert(integrity.length === 1 && Object.values(integrity[0])[0] === "ok", "KBA SQLite integrity_check failed");
    assert(db.prepare("PRAGMA foreign_key_check").all().length === 0, "KBA SQLite foreign_key_check failed");
    const tables = db.prepare("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name").all().map((row) => row.name).sort();
    assert(JSON.stringify(tables) === JSON.stringify(TABLES), "KBA SQLite table set mismatch");
    const indexes = db.prepare("SELECT name FROM sqlite_master WHERE type='index'").all().map((row) => row.name);
    assert(INDEXES.every((name) => indexes.includes(name)), "KBA SQLite search indexes incomplete");
    const views = db.prepare("SELECT name FROM sqlite_master WHERE type='view'").all().map((row) => row.name);
    assert(views.includes("v_stock_observations"), "KBA provenance view missing");
    const registry = db.prepare("SELECT source_id,license_id,rights_status,market_scope,applicability_precision,review_status,source_revision,source_manifest_sha256,source_snapshot_sha256,product_import_allowed,exact_engine_gearbox_pair,ru_eaeu_applicability FROM source_registry").get();
    assert(registry && registry.source_id === SOURCE_ID && registry.license_id === LICENSE_ID &&
      registry.rights_status === rights.rights_status && registry.market_scope === "DE" &&
      registry.applicability_precision === "aggregate_stock_observation" && registry.review_status === "research_only" &&
      registry.source_revision === pack.source_revision && registry.source_manifest_sha256 === sourceHash &&
      registry.source_snapshot_sha256 === sourceCsvHash && registry.product_import_allowed === 0 &&
      registry.exact_engine_gearbox_pair === 0 && registry.ru_eaeu_applicability === 0, "KBA SQLite source registry mismatch");
    const fileRow = db.prepare("SELECT source_id,sha256,byte_size,source_row_count,filtered_row_count,columns_sha256 FROM source_files").get();
    assert(fileRow && fileRow.source_id === SOURCE_ID && fileRow.sha256 === sourceCsvHash &&
      fileRow.byte_size === pack.source_file.byte_size && fileRow.source_row_count === pack.counts.source_rows &&
      fileRow.filtered_row_count === pack.counts.vag_stock_observations, "KBA SQLite source-file registry mismatch");
    const invalid = db.prepare("SELECT count(*) AS n FROM v_stock_observations WHERE market_scope!='DE' OR applicability_precision!='aggregate_stock_observation' OR review_status!='research_only' OR individual_vehicle_fitment!=0 OR exact_vehicle_fitment!=0 OR model_year_inferred!=0 OR generation_inferred!=0 OR engine_codes_included!=0 OR gearbox_codes_included!=0 OR exact_engine_gearbox_pair!=0 OR ecu_fitment!=0 OR dtc_fitment!=0 OR repair_applicability!=0 OR ru_eaeu_applicability!=0").get().n;
    const pairTables = db.prepare("SELECT count(*) AS n FROM sqlite_master WHERE type='table' AND lower(name) LIKE '%pair%'").get().n;
    assert(invalid === 0 && pairTables === 0, "KBA SQLite market/applicability/pair boundary failed");
    counts = {
      source_rows: fileRow.source_row_count,
      vag_stock_observations: db.prepare("SELECT count(*) AS n FROM stock_observations").get().n,
      manufacturer_labels: db.prepare("SELECT count(*) AS n FROM manufacturers").get().n,
      unique_make_trade_name_pairs: db.prepare("SELECT count(*) AS n FROM (SELECT 1 FROM stock_observations GROUP BY manufacturer_id,trade_name_id)").get().n,
      unique_make_type_key_pairs: db.prepare("SELECT count(*) AS n FROM (SELECT 1 FROM stock_observations GROUP BY manufacturer_id,type_key_id)").get().n,
      unique_make_trade_type_reference_date_tuples: db.prepare("SELECT count(*) AS n FROM (SELECT 1 FROM stock_observations GROUP BY report_date_id,manufacturer_id,trade_name_id,type_key_id)").get().n,
      federal_states: db.prepare("SELECT count(*) AS n FROM federal_states").get().n,
      reference_dates: db.prepare("SELECT iso_date FROM reference_dates ORDER BY iso_date").all().map((row) => row.iso_date)
    };
    const expected = {
      source_rows: pack.counts.source_rows, vag_stock_observations: pack.counts.vag_stock_observations,
      manufacturer_labels: pack.counts.manufacturer_labels, unique_make_trade_name_pairs: pack.counts.unique_make_trade_name_pairs,
      unique_make_type_key_pairs: pack.counts.unique_make_type_key_pairs,
      unique_make_trade_type_reference_date_tuples: pack.counts.unique_make_trade_type_reference_date_tuples,
      federal_states: pack.counts.federal_states, reference_dates: pack.counts.reference_dates
    };
    for (const key of Object.keys(expected)) assert(JSON.stringify(counts[key]) === JSON.stringify(expected[key]), "KBA count mismatch: " + key);
  } finally { db.close(); }

  return {
    pack, counts, databaseFile, databaseHash, sourceHash, sourceCsvHash,
    packManifestHash: shaFile(path.join(packRoot, "manifest.json")),
    attributionHash: shaFile(attributionFile), licenseHash: shaFile(licenseFile),
    buildReportHash: shaFile(path.join(packRoot, "build-report.json")),
    snapshotHash: pack.source_snapshot_sha256
  };
}

function patchApi(desktopRoot) {
  const file = safeJoin(desktopRoot, "app/api/local-research/route.ts");
  let text = fs.readFileSync(file, "utf8");
  const rdwImport = 'import * as rdwResearch from "../../../lib/rdw-vag-research-db.cjs";';
  if (!text.includes('from "../../../lib/kba-de-stock-research-db.cjs"')) text = replaceOnce(text, rdwImport, rdwImport + '\nimport * as kbaDeResearch from "../../../lib/kba-de-stock-research-db.cjs";', "KBA API import");
  const rdwSummary = '    if (dataset === "rdw-summary") {\n      return Response.json({ ok: true, summary: rdwResearch.getRdwSummary() }, { headers });\n    }';
  text = replaceOnce(text, rdwSummary, rdwSummary + '\n    if (dataset === "kba-de-summary") {\n      return Response.json({ ok: true, summary: kbaDeResearch.getKbaSummary() }, { headers });\n    }', "KBA summary route");
  const rdwSearch = '    else if (dataset === "rdw") rows = rdwResearch.searchRdwApprovals(query, limit);';
  text = replaceOnce(text, rdwSearch, rdwSearch + '\n    else if (dataset === "kba-de") rows = kbaDeResearch.searchKbaStock(query, limit);', "KBA search route");
  fs.writeFileSync(file, text, "utf8");
}

function patchUi(desktopRoot) {
  const file = safeJoin(desktopRoot, "components/local-research-catalog.tsx");
  let text = fs.readFileSync(file, "utf8");
  const datasetAnchor = 'type Dataset = "vehicles" | "vehiclesdb" | "dtc" | "pids" | "uds" | "autodiag2" | "mechanicdb" | "wikidata" | "generic-guidance" | "wikidata-generations" | "astra" | "rdw";';
  const kbaTypes = [
    'type KbaDeSummary = { counts: { sourceRows: number; vagStockObservations: number; manufacturerLabels: number; uniqueMakeTradeNamePairs: number; uniqueMakeTypeKeyPairs: number; uniqueMakeTradeTypeReferenceDateTuples: number; federalStates: number; referenceDates: number }; marketScope: string; rightsStatus: string; attributionText: string; sourceUrl: string; license: string; licenseUrl: string; sourceRevision: string; sourceSnapshotSha256: string; databaseSha256: string; sourceManifestSha256: string; warning: string; productionImport: false; productImportAllowed: false; ruEaeuApplicability: false; exactVehicleFitment: false; exactEngineGearboxPair: false; };',
    'type KbaDeRow = { id: string; sourceRowNumber: number; sourceObjectId: string; reportDateRaw: string; reportDate: string; manufacturer: string; tradeName: string; typeKey: string; federalState: string; vehicleCount: number; zsCountRaw: string; sourceRecordSha256: string; sourceRevision: string; sourceSnapshotSha256: string; sourceManifestSha256: string; marketScope: string; applicabilityPrecision: string; reviewStatus: string; exactVehicleFitment: false; modelYear: null; generation: null; engineCode: null; gearboxCode: null; exactEngineGearboxPair: false; ruEaeuApplicability: false; ecuFitment: false; dtcFitment: false; repairApplicability: false; sourceUrl: string; license: string; licenseUrl: string; warning: string };'
  ].join("\n");
  text = replaceOnce(text, datasetAnchor, kbaTypes + '\ntype Dataset = "vehicles" | "vehiclesdb" | "dtc" | "pids" | "uds" | "autodiag2" | "mechanicdb" | "wikidata" | "generic-guidance" | "wikidata-generations" | "astra" | "rdw" | "kba-de";', "KBA types/dataset");
  const rdwTab = '  { id: "rdw", label: "ОТТС · NL/EU", hint: "RDW · CC0 · Нидерланды · исследовательский слой" },';
  text = replaceOnce(text, rdwTab, rdwTab + '\n  { id: "kba-de", label: "KBA · DE", hint: "KBA · DL-DE BY 2.0 · статистика парка, не применяемость" },', "KBA tab");
  const rdwState = '  const [rdwSummary, setRdwSummary] = useState<RdwSummary | null>(null);';
  text = replaceOnce(text, rdwState, rdwState + '\n  const [kbaDeSummary, setKbaDeSummary] = useState<KbaDeSummary | null>(null);', "KBA state");
  const rdwEffect = '  useEffect(() => {\n    let active = true;\n    fetch("/api/local-research?dataset=rdw-summary", { cache: "no-store" })\n      .then(async (response) => { const payload = await response.json(); if (!response.ok) throw new Error(payload.error || "RDW NL/EU справочник недоступен."); return payload; })\n      .then((payload) => { if (active && payload?.ok) setRdwSummary(payload.summary as RdwSummary); })\n      .catch(() => { if (active) setRdwSummary(null); });\n    return () => { active = false; };\n  }, []);';
  const kbaEffect = rdwEffect + '\n  useEffect(() => {\n    let active = true;\n    fetch("/api/local-research?dataset=kba-de-summary", { cache: "no-store" })\n      .then(async (response) => { const payload = await response.json(); if (!response.ok) throw new Error(payload.error || "KBA DE справочник недоступен."); return payload; })\n      .then((payload) => { if (active && payload?.ok) setKbaDeSummary(payload.summary as KbaDeSummary); })\n      .catch(() => { if (active) setKbaDeSummary(null); });\n    return () => { active = false; };\n  }, []);';
  text = replaceOnce(text, rdwEffect, kbaEffect, "KBA summary fetch");
  text = replaceOnce(text, '  const rdw = rdwSummary;', '  const rdw = rdwSummary;\n  const kbaDe = kbaDeSummary;', "KBA summary binding");
  const rdwStat = '      <article className="research-stat"><small>ОТТС / одобрения NL</small><strong>{formatNumber(rdw?.counts?.approvalScopes)}</strong><span>{formatNumber(rdw?.counts?.engineDesignationCandidates)} обозначений двигателя · {formatNumber(rdw?.counts?.gearboxClassifications)} классификаций КПП · NL only</span></article>';
  text = replaceOnce(text, rdwStat, rdwStat + '\n      <article className="research-stat"><small>KBA · агрегированные наблюдения DE</small><strong>{formatNumber(kbaDe?.counts?.vagStockObservations)}</strong><span>{formatNumber(kbaDe?.counts?.manufacturerLabels)} точных марок · {formatNumber(kbaDe?.counts?.uniqueMakeTradeNamePairs)} пар марка/имя · не vehicle fitment</span></article>', "KBA statistic");
  const rdwBoundary = '      {rdw && <p>Отдельный RDW pack содержит {formatNumber(rdw.counts.approvalScopes)} точных ключей одобрения variant/version/revision для Нидерландов. Это не российские/ЕАЭС ОТТС и не применимость к конкретному автомобилю. Обозначения двигателя и классификации КПП показываются отдельными списками: их совместное присутствие в одном approval scope не подтверждает пару; это не заводские коды VAG, не модельный год, не поколение и не ремонтные данные.</p>}';
  const kbaBoundary = '      {kbaDe && <p>Отдельный KBA pack содержит {formatNumber(kbaDe.counts.vagStockObservations)} агрегированных наблюдений парка Германии за 2023–2026 годы. Typschlüssel показывается только как исходное поле KBA и не подтверждён как TSN. Это не индивидуальные автомобили, не VIN-комплектация, не модельный год/поколение, не код двигателя/КПП и не подтверждённая применяемость. Двигатель/КПП, ECU, DTC и ремонтные данные отсутствуют; RU/ЕАЭС применимость не выводится.</p>}';
  text = replaceOnce(text, rdwBoundary, rdwBoundary + '\n' + kbaBoundary, "KBA research boundary");
  text = replaceOnce(text, 'placeholder={dataset === "rdw" ? "Номер одобрения, variant/version, модель или обозначение двигателя RDW…" : dataset === "astra" ?', 'placeholder={dataset === "kba-de" ? "Марка, торговое имя, исходный Typschlüssel или федеральная земля KBA…" : dataset === "rdw" ? "Номер одобрения, variant/version, модель или обозначение двигателя RDW…" : dataset === "astra" ?', "KBA search placeholder");

  const genericCard = '      {dataset === "generic-guidance" && (rows as unknown as GenericGuidanceRow[]).map((row) => <article className="research-result" key={row.guidanceId}>';
  const kbaCard = [
    '      {dataset === "kba-de" && (rows as unknown as KbaDeRow[]).map((row) => <article className="research-result" key={row.id}>',
    '        <div className="research-result-top"><div><small>KBA · GERMANY · AGGREGATE STOCK</small><h3>{row.manufacturer} · {row.tradeName || "без торгового имени"}</h3></div><span className="research-candidate">DE RESEARCH ONLY</span></div>',
    '        <div className="research-data-grid">',
    '          <div><small>Дата статистического среза · не модельный год</small><b>{row.reportDate} · {row.federalState}</b></div>',
    '          <div><small>Typschlüssel · исходное поле KBA, не подтверждённая TSN</small><b>{row.typeKey || "—"}</b></div>',
    '          <div><small>Агрегированное количество</small><b>{formatNumber(row.vehicleCount)}</b></div>',
    '          <div><small>Точность применимости</small><b>aggregate_stock_observation · research only</b></div>',
    '          <div><small>Двигатель / КПП</small><b>Не предоставлены · точная пара отсутствует</b></div>',
    '          <div><small>ECU / DTC / ремонт</small><b>Не предоставлены · выполнение не разрешено</b></div>',
    '        </div>',
    '        <div className="research-warning-line">{row.warning}</div>',
    '        <details className="research-details"><summary>Построчная provenance KBA</summary>',
    '          <p>Source row {row.sourceRowNumber} · ObjectId {row.sourceObjectId} · revision {row.sourceRevision} · row SHA-256 {row.sourceRecordSha256} · snapshot SHA-256 {row.sourceSnapshotSha256} · source manifest SHA-256 {row.sourceManifestSha256}</p>',
    '          <p>Рынок {row.marketScope} · статус {row.reviewStatus} · точность {row.applicabilityPrecision} · exact fitment false · exact engine/gearbox pair false · RU/ЕАЭС false</p>',
    '        </details>',
    '        <div className="research-source"><span>KBA · DL-DE BY 2.0 · DE-only · агрегированная статистика, не vehicle fitment</span><a href={row.sourceUrl} target="_blank" rel="noopener noreferrer">Открыть набор KBA</a></div>',
    '      </article>)}'
  ].join("\n");
  text = replaceOnce(text, genericCard, kbaCard + "\n" + genericCard, "KBA result card");
  const creditsAnchor = '      <p>SQLite SHA-256 · OBDex: {obdex?.databaseSha256 || "недоступен"}</p>';
  const credits = '      {kbaDe && <><p><a href={kbaDe.sourceUrl} target="_blank" rel="noopener noreferrer">Kraftfahrt-Bundesamt (KBA), FZ Hersteller Handelsnamen Pkw</a> — Datenlizenz Deutschland – Namensnennung – Version 2.0 (DL-DE BY 2.0). Modified data: фильтрация восьми точных manufacturer labels, нормализация даты и добавление row SHA-256. Attribution: {kbaDe.attributionText}</p><p>SHA snapshot {kbaDe.sourceSnapshotSha256} · SHA SQLite {kbaDe.databaseSha256} · SHA source manifest {kbaDe.sourceManifestSha256}. KBA stock/type-key rows are aggregate DE research only; no exact vehicle fitment, engine/gearbox pair or RU/EAEU applicability.</p></>}';
  text = replaceOnce(text, creditsAnchor, credits + "\n" + creditsAnchor, "KBA attribution credits");
  fs.writeFileSync(file, text, "utf8");
}

function patchLifecycle(desktopRoot) {
  const file = safeJoin(desktopRoot, "scripts/windows-installer-lifecycle.ps1");
  let text = fs.readFileSync(file, "utf8");
  const anchor = '  Write-Host "RDW NL/EU approval search passed; engine and gearbox remain separate research candidates."';
  const check = [
    '  $kbaSummary = Invoke-RestMethod -Uri "$baseUrl/api/local-research?dataset=kba-de-summary" -TimeoutSec 45',
    '  if ($kbaSummary.summary.marketScope -ne "DE" -or $kbaSummary.summary.rightsStatus -ne "approved_by_published_DL_DE_BY_2_0" -or $kbaSummary.summary.productionImport -ne $false -or $kbaSummary.summary.productImportAllowed -ne $false -or $kbaSummary.summary.ruEaeuApplicability -ne $false -or $kbaSummary.summary.exactEngineGearboxPair -ne $false -or $kbaSummary.summary.counts.vagStockObservations -ne 264847 -or $kbaSummary.summary.counts.manufacturerLabels -ne 8 -or $kbaSummary.summary.counts.uniqueMakeTradeNamePairs -ne 802 -or $kbaSummary.summary.counts.uniqueMakeTypeKeyPairs -ne 4155) { throw "KBA DE summary, licence or aggregate-stock boundary failed in offline desktop." }',
    '  $kbaQuery = [uri]::EscapeDataString("GOLF")',
    '  $kbaRows = Invoke-RestMethod -Uri "$baseUrl/api/local-research?dataset=kba-de&q=$kbaQuery&limit=50" -TimeoutSec 45',
    '  $kbaSample = @($kbaRows.rows | Where-Object { $_.manufacturer -eq "VOLKSWAGEN (D)" -and $_.tradeName -eq "GOLF" -and $_.marketScope -eq "DE" }) | Select-Object -First 1',
    '  if (-not $kbaSample -or $kbaSample.applicabilityPrecision -ne "aggregate_stock_observation" -or $kbaSample.reviewStatus -ne "research_only" -or $kbaSample.exactVehicleFitment -ne $false -or $kbaSample.exactEngineGearboxPair -ne $false -or $kbaSample.ruEaeuApplicability -ne $false -or $kbaSample.modelYear -ne $null -or $kbaSample.generation -ne $null -or $kbaSample.engineCode -ne $null -or $kbaSample.gearboxCode -ne $null -or $kbaSample.vehicleCount -le 0 -or $kbaSample.sourceRecordSha256 -notmatch "^[a-f0-9]{64}$" -or $kbaSample.sourceSnapshotSha256 -notmatch "^[a-f0-9]{64}$") { throw "KBA offline search crossed its DE aggregate-stock boundary." }',
    '  Write-Host "KBA DE aggregate stock search passed; no engine/gearbox or vehicle-fitment claim."'
  ].join("\n");
  text = replaceOnce(text, anchor, anchor + "\n" + check, "KBA offline lifecycle check");
  fs.writeFileSync(file, text, "utf8");
}

function patchPackage(desktopRoot) {
  const file = safeJoin(desktopRoot, "package.json");
  const pkg = readJson(file);
  if (!pkg.scripts) fail("Desktop package scripts missing");
  if (!JSON.stringify(pkg.build?.extraResources || []).includes("data/research")) fail("Desktop package does not include offline research-data resources");
  const testFiles = ["tests/kba-de-stock-research-db.test.cjs","tests/kba-de-stock-ui-contract.test.cjs"];
  const testKeys = ["test","test:research"].filter((key) => typeof pkg.scripts[key] === "string");
  if (testKeys.length === 0) fail("Desktop package has no test script for KBA contract tests");
  for (const key of testKeys) {
    const command = pkg.scripts[key];
    const hasGlob = /tests\/\*\*?\/?.*\.test\.cjs|tests\/\*\.test\.cjs|node --test(\s|$)/.test(command);
    if (!hasGlob) for (const testFile of testFiles) if (!pkg.scripts[key].includes(testFile)) pkg.scripts[key] += " " + testFile;
  }
  pkg.scripts["verify:kba-de-stock-research"] = "node scripts/verify-kba-de-stock-research-pack.cjs";
  atomicJson(file, pkg);
}

function integrate(repoRoot, desktopRoot, downloadRoot, sourceRunId, sourceRunNumber, artifactSha) {
  const packRoot = locatePackRoot(downloadRoot);
  const validated = validatePack(repoRoot, packRoot);
  const researchRoot = safeJoin(desktopRoot, "data/research");
  const target = safeJoin(researchRoot, PACK_ID);
  fs.mkdirSync(researchRoot, { recursive: true });
  if (fs.existsSync(target)) fs.rmSync(target, { recursive: true, force: true });
  fs.mkdirSync(target, { recursive: true });
  const copyNames = ["kba-de-vag-stock-research.sqlite","manifest.json","source-manifest.json","ATTRIBUTION.md","LICENSE.txt","build-report.json"];
  for (const name of copyNames) {
    const sourceFile = safeJoin(packRoot, name), targetFile = safeJoin(target, name);
    fs.copyFileSync(sourceFile, targetFile);
    if (shaFile(sourceFile) !== shaFile(targetFile)) fail("KBA pack copy hash mismatch: " + name);
  }
  const rel = (file) => path.relative(researchRoot, file).split(path.sep).join("/");
  const report = {
    status: "integrated_verified_research_only", pack_id: PACK_ID, source_id: SOURCE_ID,
    source_run_id: Number(sourceRunId), source_run_number: Number(sourceRunNumber), artifact_sha256: artifactSha,
    market_scope: "DE", rights_status: "approved_by_published_DL_DE_BY_2_0",
    source_manifest_sha256: validated.sourceHash, source_snapshot_sha256: validated.snapshotHash,
    pack_manifest_sha256: validated.packManifestHash, database_sha256: validated.databaseHash,
    source_file_sha256: validated.sourceCsvHash, counts: validated.counts,
    research_pack_ingested: true, product_database_ingested: false,
    production_import: false, product_import_allowed: false, ru_eaeu_applicability: false,
    exact_vehicle_fitment: false, exact_engine_gearbox_pair: false, repair_applicability: false,
    diagnostic_execution_allowed: false, source_snapshot_csv_in_desktop: false
  };
  const integrationReportFile = safeJoin(target, "desktop-integration-report.json");
  atomicJson(integrationReportFile, report);
  const entry = {
    id: PACK_ID, source_id: SOURCE_ID, dataset: "KBA German passenger-car stock by exact manufacturer label, trade name and raw type key",
    publisher: "Kraftfahrt-Bundesamt (KBA), published via GovData/Mobilithek",
    source_url: SOURCE_URL, license: LICENSE_ID, license_url: "https://www.govdata.de/dl-de/by-2-0",
    license_status: "approved_by_published_DL_DE_BY_2_0", rights_status: "approved_by_published_DL_DE_BY_2_0",
    market_scope: ["DE"], applicability_precision: "aggregate_stock_observation",
    review_status: "verified_research_only", research_pack_ingested: true, product_database_ingested: false,
    production_import: false, product_import_allowed: false, data_ingested: false, ru_eaeu_applicability: false, fitment_claim: false,
    exact_vehicle_fitment: false, exact_engine_gearbox_pair: false, repair_applicability: false,
    diagnostic_execution_allowed: false, model_year_inferred: false, generation_inferred: false,
    engine_codes_included: false, gearbox_codes_included: false, ecu_fitment: false, dtc_fitment: false,
    commercial_use_allowed: true, display_allowed: true, cache_allowed: true, bulk_reuse_allowed: true,
    redistribution_allowed: true, attribution_required: true, share_alike_required: false,
    database: rel(safeJoin(target, "kba-de-vag-stock-research.sqlite")),
    database_sha256: validated.databaseHash,
    pack_manifest_file: rel(safeJoin(target, "manifest.json")),
    pack_manifest_sha256: validated.packManifestHash,
    source_manifest_file: rel(safeJoin(target, "source-manifest.json")),
    source_manifest_sha256: validated.sourceHash,
    attribution_file: rel(safeJoin(target, "ATTRIBUTION.md")),
    attribution_sha256: validated.attributionHash,
    license_file: rel(safeJoin(target, "LICENSE.txt")),
    license_sha256: validated.licenseHash,
    build_report_file: rel(safeJoin(target, "build-report.json")),
    build_report_sha256: validated.buildReportHash,
    desktop_integration_report_file: rel(integrationReportFile),
    desktop_integration_report_sha256: shaFile(integrationReportFile),
    source_revision: validated.pack.source_revision,
    source_snapshot_sha256: validated.snapshotHash,
    source_file_sha256: validated.sourceCsvHash,
    source_file_bytes: validated.pack.source_file.byte_size,
    source_file_included_in_desktop: false,
    source_row_count: validated.pack.source_file.row_count,
    filtered_vag_row_count: validated.pack.source_file.filtered_vag_row_count,
    source_record_hash_method: validated.pack.source_record_hash_method,
    counts: validated.pack.counts,
    source_run_id: Number(sourceRunId), source_run_number: Number(sourceRunNumber),
    source_artifact_sha256: artifactSha,
    limitations: [
      "Germany-only aggregate passenger-car stock observations; no individual vehicles or build sheets.",
      "Typschlüssel is preserved as a raw KBA source field; it is not promoted to HSN or confirmed TSN.",
      "Annual Berichtszeitpunkt is a stock reference date, not model year or generation.",
      "No engine code, gearbox code, engine/gearbox pair, ECU, DTC, repair procedure or exact vehicle fitment.",
      "No Russian/EAEU applicability is inferred. Source CSV is retained in the CI research artifact, not duplicated into the desktop installer."
    ]
  };
  const rootManifestFile = safeJoin(researchRoot, "manifest.json");
  const rootManifest = readJson(rootManifestFile);
  if (rootManifest.schema_version !== 1 || !Array.isArray(rootManifest.packs)) fail("Desktop research manifest schema mismatch");
  const index = rootManifest.packs.findIndex((item) => item.id === PACK_ID);
  if (index >= 0) rootManifest.packs[index] = entry; else rootManifest.packs.push(entry);
  atomicJson(rootManifestFile, rootManifest);

  const support = [
    ["desktop/kba-de-stock-research-db.cjs","lib/kba-de-stock-research-db.cjs"],
    ["desktop/tests/kba-de-stock-research-db.test.cjs","tests/kba-de-stock-research-db.test.cjs"],
    ["desktop/tests/kba-de-stock-ui-contract.test.cjs","tests/kba-de-stock-ui-contract.test.cjs"],
    ["desktop/scripts/verify-kba-de-stock-research-pack.cjs","scripts/verify-kba-de-stock-research-pack.cjs"]
  ];
  for (const pair of support) {
    const sourceFile = safeJoin(repoRoot, pair[0]), targetFile = safeJoin(desktopRoot, pair[1]);
    if (!fs.existsSync(sourceFile) || !fs.statSync(sourceFile).isFile()) fail("KBA support file missing: " + pair[0]);
    fs.mkdirSync(path.dirname(targetFile), { recursive: true });
    fs.copyFileSync(sourceFile, targetFile);
    if (shaFile(sourceFile) !== shaFile(targetFile)) fail("KBA support copy mismatch: " + pair[1]);
  }
  patchApi(desktopRoot);
  patchUi(desktopRoot);
  patchLifecycle(desktopRoot);
  patchPackage(desktopRoot);
  process.stdout.write(JSON.stringify({
    status: "integrated_verified_research_only", pack_id: PACK_ID,
    source_run_id: Number(sourceRunId), source_run_number: Number(sourceRunNumber),
    artifact_sha256: artifactSha, market_scope: ["DE"],
    source_manifest_sha256: entry.source_manifest_sha256, source_snapshot_sha256: entry.source_snapshot_sha256,
    pack_manifest_sha256: entry.pack_manifest_sha256, database_sha256: entry.database_sha256,
    desktop_integration_report_sha256: entry.desktop_integration_report_sha256,
    counts: { source_rows: validated.pack.counts.source_rows, vag_stock_observations: validated.pack.counts.vag_stock_observations },
    production_import: false, ru_eaeu_applicability: false, exact_engine_gearbox_pair: false
  }, null, 2) + "\n");
}

function main(argv) {
  const options = {};
  for (let i = 0; i < argv.length; i += 1) {
    const key = argv[i];
    if (!["--desktop-root","--pack-dir","--source-run-id","--source-run-number","--artifact-sha256"].includes(key) || !argv[i + 1]) fail("Invalid argument: " + key);
    options[key] = argv[++i];
  }
  if (!options["--desktop-root"] || !options["--pack-dir"] || !options["--source-run-id"] || !options["--source-run-number"] || !options["--artifact-sha256"]) fail("Missing KBA integration arguments");
  if (!/^\d+$/.test(options["--source-run-id"]) || !/^\d+$/.test(options["--source-run-number"]) || !/^[a-f0-9]{64}$/.test(options["--artifact-sha256"])) fail("Invalid KBA run/artifact provenance");
  integrate(process.cwd(), path.resolve(options["--desktop-root"]), path.resolve(options["--pack-dir"]), options["--source-run-id"], options["--source-run-number"], options["--artifact-sha256"]);
}
if (require.main === module) {
  try { main(process.argv.slice(2)); }
  catch (error) { process.stderr.write((error.stack || error.message) + "\n"); process.exitCode = 1; }
}
module.exports = { validatePack, locatePackRoot, safeJoin };

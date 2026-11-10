"use strict";

const fs = require("node:fs");
const path = require("node:path");
const crypto = require("node:crypto");
const { DatabaseSync } = require("node:sqlite");

const PACK_ID = "cardir-vag-owner-manual-facts-research";
const SOURCE_ID = "cardir-vag-owner-manual-facts-cc-by-4.0";
const SOURCE_URL = "https://cardir.ru/dannye/";
const LICENSE_ID = "CC-BY-4.0";
const TABLES = ["brands", "facts", "models", "pack_metadata", "source_files", "source_registry"].sort();
const INDEXES = ["idx_cardir_facts_brand_model", "idx_cardir_facts_parameter", "idx_cardir_facts_qualifier", "idx_cardir_facts_search"].sort();

function fail(message) { throw new Error(message); }
function assert(condition, message) { if (!condition) fail(message); }
function shaFile(file) { return crypto.createHash("sha256").update(fs.readFileSync(file)).digest("hex"); }
function readJson(file) { return JSON.parse(fs.readFileSync(file, "utf8").replace(/^\uFEFF/, "")); }
function atomicJson(file, value) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  const temp = file + ".tmp-" + process.pid;
  fs.writeFileSync(temp, JSON.stringify(value, null, 2) + "\n", "utf8");
  fs.renameSync(temp, file);
}
function safeJoin(root, relative) {
  if (typeof relative !== "string" || !relative || path.isAbsolute(relative)) fail("Unsafe CarDir path");
  const base = path.resolve(root);
  const target = path.resolve(base, relative);
  const rel = path.relative(base, target);
  if (!rel || rel === ".." || rel.startsWith(".." + path.sep) || path.isAbsolute(rel)) fail("CarDir path escaped root");
  return target;
}
function locatePackRoot(downloadRoot) {
  const root = path.resolve(downloadRoot);
  const queue = [{ dir: root, depth: 0 }];
  while (queue.length) {
    const item = queue.shift();
    const manifest = path.join(item.dir, "manifest.json");
    if (fs.existsSync(manifest)) {
      try {
        if (readJson(manifest).pack_id === PACK_ID) return item.dir;
      } catch (_) { /* Continue searching other artifact folders. */ }
    }
    if (item.depth >= 5) continue;
    for (const entry of fs.readdirSync(item.dir, { withFileTypes: true })) {
      if (entry.isDirectory() && !entry.isSymbolicLink()) queue.push({ dir: path.join(item.dir, entry.name), depth: item.depth + 1 });
    }
  }
  fail("CarDir research pack root was not found in the downloaded artifact.");
}
function openReadOnly(file) {
  const db = new DatabaseSync(file, { readOnly: true });
  db.exec("PRAGMA query_only=ON; PRAGMA trusted_schema=OFF;");
  return db;
}
function count(db, sql) { return db.prepare(sql).get().n; }
function replaceOnce(text, anchor, replacement, label) {
  const index = text.indexOf(anchor);
  if (index < 0) fail("CarDir integration anchor missing: " + label);
  if (text.indexOf(anchor, index + anchor.length) >= 0) fail("CarDir integration anchor is ambiguous: " + label);
  return text.slice(0, index) + replacement + text.slice(index + anchor.length);
}
function validatePack(repoRoot, packRoot, artifactSha) {
  const pack = readJson(safeJoin(packRoot, "manifest.json"));
  const source = readJson(safeJoin(packRoot, "source-manifest.json"));
  const snapshot = readJson(safeJoin(packRoot, "source-snapshot.json"));
  const report = readJson(safeJoin(packRoot, "build-report.json"));
  const databaseFile = safeJoin(packRoot, "cardir-vag-owner-manual-facts.sqlite");
  const sourceManifestFile = safeJoin(packRoot, "source-manifest.json");
  const packManifestFile = safeJoin(packRoot, "manifest.json");
  const attributionFile = safeJoin(packRoot, "ATTRIBUTION.md");
  const licenseFile = safeJoin(packRoot, "LICENSE.txt");
  const buildReportFile = safeJoin(packRoot, "build-report.json");
  const snapshotFile = safeJoin(packRoot, "source-snapshot.json");
  const rights = source.rights || {};
  const policy = source.applicability_policy || {};
  const importPolicy = source.import_policy || {};
  const attribution = fs.readFileSync(attributionFile, "utf8");
  const license = fs.readFileSync(licenseFile, "utf8");
  const sourceHash = shaFile(sourceManifestFile);
  const packHash = shaFile(packManifestFile);
  const databaseHash = shaFile(databaseFile);
  const attributionHash = shaFile(attributionFile);
  const licenseHash = shaFile(licenseFile);
  const buildReportHash = shaFile(buildReportFile);
  const snapshotManifestHash = shaFile(snapshotFile);
  const snapshotHash = pack.source_snapshot_sha256;

  assert(/^[a-f0-9]{64}$/.test(artifactSha), "CarDir workflow artifact SHA-256 is invalid");
  assert(pack.pack_id === PACK_ID && pack.source_id === SOURCE_ID, "CarDir pack/source identity mismatch");
  assert(pack.status === "verified_research_only" && pack.schema_version === 2, "CarDir pack status/schema mismatch");
  assert(pack.license.id === LICENSE_ID && pack.license.url === "https://creativecommons.org/licenses/by/4.0/", "CarDir license metadata mismatch");
  assert(pack.source_manifest_sha256 === sourceHash && pack.database.sha256 === databaseHash, "CarDir pack manifest hash mismatch");
  assert(pack.source_snapshot_sha256 === snapshotHash && /^[a-f0-9]{64}$/.test(snapshotHash), "CarDir source snapshot hash is invalid");
  assert(pack.database.integrity_check === "ok" && pack.database.foreign_key_violations === 0, "CarDir builder report database integrity failed");
  assert(pack.publisher_verification_status === "publisher_verified" && pack.technical_review_status === "not_independently_reviewed", "CarDir review status mismatch");
  assert(JSON.stringify(pack.market_scope) === JSON.stringify(["UNKNOWN"]), "CarDir market must remain UNKNOWN");
  for (const key of ["exact_engine_code_mapping","exact_gearbox_code_mapping","exact_engine_gearbox_pair","exact_vehicle_fitment","model_generation_inferred","model_year_inferred","ru_eaeu_applicability","ecu_fitment","dtc_fitment","repair_procedure","wiring_or_pinout","data_ingested","product_database_ingested","production_import","product_import_allowed"]) {
    assert(pack[key] === false, "CarDir pack unexpectedly enables " + key);
  }
  assert(source.source_id === SOURCE_ID && source.data_revision === pack.source_revision, "CarDir source revision mismatch");
  assert(source.snapshot.source_snapshot_sha256 === snapshotHash && source.snapshot.source_file_bytes === snapshot.source_file_bytes, "CarDir source snapshot mismatch");
  assert(source.snapshot.expected_source_row_count === snapshot.source_row_count && source.snapshot.expected_model_count === snapshot.model_count, "CarDir source row/model count mismatch");
  assert(source.snapshot.expected_data_updated_at === snapshot.data_updated_at, "CarDir source date mismatch");
  assert(rights.rights_status === "approved_by_published_CC_BY_4_0" && rights.license_id === LICENSE_ID, "CarDir published license approval missing");
  for (const key of ["commercial_use_allowed","display_allowed","offline_cache_allowed","bulk_reuse_allowed","redistribution_allowed","attribution_required"]) {
    assert(rights[key] === true, "CarDir license does not confirm " + key);
  }
  assert(policy.market_scope === "UNKNOWN" && policy.exact_engine_code_mapping === false && policy.exact_gearbox_code_mapping === false && policy.exact_engine_gearbox_pair === false && policy.exact_vehicle_fitment === false && policy.ru_eaeu_applicability === false, "CarDir applicability policy mismatch");
  assert(importPolicy.research_pack_allowed === true && importPolicy.research_pack_read_only === true && importPolicy.production_import === false && importPolicy.product_import_allowed === false, "CarDir import policy mismatch");
  assert(attribution.includes("CarDir") && attribution.includes("CC BY 4.0") && attribution.includes(SOURCE_URL), "CarDir attribution is incomplete");
  assert(license.includes("CC BY 4.0") && license.includes("creativecommons.org/licenses/by/4.0"), "CarDir license file is incomplete");
  assert(report.status === "verified_research_only" && report.database_sha256 === databaseHash && report.source_snapshot_sha256 === snapshotHash && report.exact_engine_gearbox_pair === false, "CarDir build report mismatch");
  assert(snapshot.source_id === SOURCE_ID && snapshot.source_snapshot_sha256 === snapshotHash && snapshot.source_row_count === 44245 && snapshot.vag_row_count === 948, "CarDir snapshot evidence mismatch");

  const db = openReadOnly(databaseFile);
  let counts;
  try {
    const integrity = db.prepare("PRAGMA integrity_check").all();
    assert(integrity.length === 1 && Object.values(integrity[0])[0] === "ok", "CarDir SQLite integrity_check failed");
    assert(db.prepare("PRAGMA foreign_key_check").all().length === 0, "CarDir SQLite foreign_key_check failed");
    const tables = db.prepare("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name").all().map((row) => row.name).sort();
    assert(JSON.stringify(tables) === JSON.stringify(TABLES), "CarDir SQLite table set mismatch");
    const indexes = db.prepare("SELECT name FROM sqlite_master WHERE type='index'").all().map((row) => row.name).sort();
    assert(INDEXES.every((name) => indexes.includes(name)), "CarDir SQLite search indexes missing");
    const registry = db.prepare("SELECT source_id,license_id,rights_status,market_scope,applicability_precision,research_pack_only,production_import,exact_engine_code,exact_gearbox_code,exact_engine_gearbox_pair,model_generation,model_year,ru_eaeu_applicability,ecu_fitment,dtc_fitment,repair_procedure FROM source_registry").get();
    assert(registry && registry.source_id === SOURCE_ID && registry.license_id === LICENSE_ID && registry.rights_status === rights.rights_status && registry.market_scope === "UNKNOWN" && registry.applicability_precision === "model_and_raw_qualifier_text" && registry.research_pack_only === 1 && registry.production_import === 0 && registry.exact_engine_code === 0 && registry.exact_gearbox_code === 0 && registry.exact_engine_gearbox_pair === 0 && registry.model_generation === 0 && registry.model_year === 0 && registry.ru_eaeu_applicability === 0 && registry.ecu_fitment === 0 && registry.dtc_fitment === 0 && registry.repair_procedure === 0, "CarDir SQLite source registry boundary failed");
    const sourceFile = db.prepare("SELECT sha256,byte_size,source_row_count,filtered_vag_row_count FROM source_files").get();
    assert(sourceFile && sourceFile.sha256 === snapshotHash && sourceFile.byte_size === snapshot.source_file_bytes && sourceFile.source_row_count === 44245 && sourceFile.filtered_vag_row_count === 948, "CarDir SQLite source-file registry mismatch");
    const invalid = count(db, "SELECT count(*) AS n FROM facts WHERE source_id!='" + SOURCE_ID + "' OR publisher_verification_status!='publisher_verified' OR technical_review_status!='not_independently_reviewed' OR market_scope!='UNKNOWN' OR model_generation IS NOT NULL OR model_year_from IS NOT NULL OR model_year_to IS NOT NULL OR engine_code IS NOT NULL OR transmission_code IS NOT NULL OR exact_engine_gearbox_pair!=0 OR production_fitment!=0 OR ecu_fitment!=0 OR dtc_fitment!=0 OR repair_procedure!=0");
    const badHashes = count(db, "SELECT count(*) AS n FROM facts WHERE length(source_row_sha256)!=64 OR source_row_sha256 GLOB '*[^0-9a-f]*'");
    assert(invalid === 0 && badHashes === 0, "CarDir fact rows crossed research-only or provenance boundary");
    counts = {
      sourceRows: snapshot.source_row_count,
      vagFacts: count(db, "SELECT count(*) AS n FROM facts"),
      vagBrands: count(db, "SELECT count(*) AS n FROM brands"),
      vagModels: count(db, "SELECT count(*) AS n FROM models"),
      parameterKeys: count(db, "SELECT count(DISTINCT parameter_key) AS n FROM facts")
    };
    assert(counts.vagFacts === 948 && counts.vagBrands === 5 && counts.vagModels === 26 && counts.parameterKeys === 19, "CarDir pinned VAG counts mismatch");
    assert(JSON.stringify(counts.vagFacts) === JSON.stringify(pack.counts.vag_facts), "CarDir pack fact count mismatch");
  } finally {
    db.close();
  }
  return {
    pack, source, snapshot, counts, databaseFile, databaseHash, sourceHash, packHash,
    attributionHash, licenseHash, buildReportHash, snapshotManifestHash, artifactSha,
    sourceSnapshotHash: snapshotHash, sourceRevision: pack.source_revision
  };
}

function patchApi(desktopRoot) {
  const file = safeJoin(desktopRoot, "app/api/local-research/route.ts");
  let text = fs.readFileSync(file, "utf8");
  const kbaImport = 'import * as kbaDeResearch from "../../../lib/kba-de-stock-research-db.cjs";';
  if (!text.includes('cardir-vag-reference-facts-db.cjs')) text = replaceOnce(text, kbaImport, kbaImport + '\nimport * as cardirResearch from "../../../lib/cardir-vag-reference-facts-db.cjs";', "CarDir API import");
  const kbaSummary = '    if (dataset === "kba-de-summary") {\n      return Response.json({ ok: true, summary: kbaDeResearch.getKbaSummary() }, { headers });\n    }';
  if (!text.includes('dataset === "cardir-summary"')) text = replaceOnce(text, kbaSummary, kbaSummary + '\n    if (dataset === "cardir-summary") {\n      return Response.json({ ok: true, summary: cardirResearch.getCardirSummary() }, { headers });\n    }', "CarDir summary route");
  const kbaSearch = '    else if (dataset === "kba-de") rows = kbaDeResearch.searchKbaStock(query, limit);';
  if (!text.includes('dataset === "cardir"')) text = replaceOnce(text, kbaSearch, kbaSearch + '\n    else if (dataset === "cardir") rows = cardirResearch.searchCardirFacts(query, limit);', "CarDir search route");
  fs.writeFileSync(file, text, "utf8");
}

function patchUi(desktopRoot) {
  const file = safeJoin(desktopRoot, "components/local-research-catalog.tsx");
  let text = fs.readFileSync(file, "utf8");
  if (!text.includes('id: "cardir"')) {
    const datasetAnchor = 'type Dataset = "vehicles" | "vehiclesdb" | "dtc" | "pids" | "uds" | "autodiag2" | "mechanicdb" | "wikidata" | "generic-guidance" | "wikidata-generations" | "astra" | "astra-targa" | "rdw" | "kba-de";';
    const types = [
      'type CardirSummary = { packId: string; counts: { sourceRows: number; vagFacts: number; vagBrands: number; vagModels: number; parameterKeys: number }; marketScope: string; rightsStatus: string; attributionText: string; sourceUrl: string; license: string; licenseUrl: string; sourceRevision: string; sourceSnapshotSha256: string; databaseSha256: string; sourceManifestSha256: string; warning: string; productionImport: false; productImportAllowed: false; ruEaeuApplicability: false; exactVehicleFitment: false; exactEngineGearboxPair: false; repairProcedure: false; ecuFitment: false; dtcFitment: false; sourceFileIncludedInDesktop: false; };',
      'type CardirRow = { sourceRowNumber: number; brand: string; model: string; parameterKey: string; parameterLabelRu: string; qualifier: string; value: string; unit: string; sourceTitle: string; sourcePage: string; sourceUrl: string; pageUrl: string; verifiedAt: string; sourceRowSha256: string; publisherVerificationStatus: string; technicalReviewStatus: string; marketScope: string; applicabilityPrecision: string; modelGeneration: string | null; modelYearFrom: number | null; modelYearTo: number | null; engineCode: string | null; transmissionCode: string | null; exactEngineGearboxPair: number; productionFitment: number; ecuFitment: number; dtcFitment: number; repairProcedure: number; sourceRevision: string; sourceSnapshotSha256: string; sourceFileSha256: string; databaseSha256: string; sourceManifestSha256: string; license: string; licenseUrl: string; attributionText: string; warning: string; exactVehicleFitment: false; ruEaeuApplicability: false; };'
    ].join("\n");
    text = replaceOnce(text, datasetAnchor, types + "\n" + datasetAnchor.replace(' | "kba-de";', ' | "kba-de" | "cardir";'), "CarDir UI types");
    const kbaTab = '  { id: "kba-de", label: "KBA · DE", hint: "KBA · DL-DE BY 2.0 · статистика парка, не применяемость" },';
    text = replaceOnce(text, kbaTab, kbaTab + '\n  { id: "cardir", label: "CarDir · справочные значения", hint: "CC BY 4.0 · руководства владельца · рынок UNKNOWN · research only" },', "CarDir tab");
    const kbaState = '  const [kbaDeSummary, setKbaDeSummary] = useState<KbaDeSummary | null>(null);';
    text = replaceOnce(text, kbaState, kbaState + '\n  const [cardirSummary, setCardirSummary] = useState<CardirSummary | null>(null);', "CarDir state");
    const kbaEffect = '  useEffect(() => {\n    let active = true;\n    fetch("/api/local-research?dataset=kba-de-summary", { cache: "no-store" })\n      .then(async (response) => { const payload = await response.json(); if (!response.ok) throw new Error(payload.error || "KBA DE справочник недоступен."); return payload; })\n      .then((payload) => { if (active && payload?.ok) setKbaDeSummary(payload.summary as KbaDeSummary); })\n      .catch(() => { if (active) setKbaDeSummary(null); });\n    return () => { active = false; };\n  }, []);';
    const cardirEffect = kbaEffect + '\n  useEffect(() => {\n    let active = true;\n    fetch("/api/local-research?dataset=cardir-summary", { cache: "no-store" })\n      .then(async (response) => { const payload = await response.json(); if (!response.ok) throw new Error(payload.error || "CarDir справочник недоступен."); return payload; })\n      .then((payload) => { if (active && payload?.ok) setCardirSummary(payload.summary as CardirSummary); })\n      .catch(() => { if (active) setCardirSummary(null); });\n    return () => { active = false; };\n  }, []);';
    text = replaceOnce(text, kbaEffect, cardirEffect, "CarDir summary fetch");
    text = replaceOnce(text, '  const kbaDe = kbaDeSummary;', '  const kbaDe = kbaDeSummary;\n  const cardir = cardirSummary;', "CarDir summary binding");
    const kbaStat = '      <article className="research-stat"><small>KBA · агрегированные наблюдения DE</small><strong>{formatNumber(kbaDe?.counts?.vagStockObservations)}</strong><span>{formatNumber(kbaDe?.counts?.manufacturerLabels)} точных марок · {formatNumber(kbaDe?.counts?.uniqueMakeTradeNamePairs)} пар марка/имя · не vehicle fitment</span></article>';
    text = replaceOnce(text, kbaStat, kbaStat + '\n      <article className="research-stat"><small>CarDir · факты из руководств владельца</small><strong>{formatNumber(cardir?.counts?.vagFacts)}</strong><span>{formatNumber(cardir?.counts?.vagModels)} моделей · {formatNumber(cardir?.counts?.parameterKeys)} параметров · рынок UNKNOWN</span></article>', "CarDir statistic");
    const kbaBoundary = '      {kbaDe && <p>Отдельный KBA pack содержит {formatNumber(kbaDe.counts.vagStockObservations)} агрегированных наблюдений парка Германии за 2023–2026 годы. Typschlüssel показывается только как исходное поле KBA и не подтверждён как TSN. Это не индивидуальные автомобили, не VIN-комплектация, не модельный год/поколение, не код двигателя/КПП и не подтверждённая применяемость. Двигатель/КПП, ECU, DTC и ремонтные данные отсутствуют; RU/ЕАЭС применимость не выводится.</p>}';
    const cardirBoundary = '      {cardir && <p>CarDir содержит {formatNumber(cardir.counts.vagFacts)} опубликованных справочных фактов из руководств владельца по {formatNumber(cardir.counts.vagModels)} моделям. CarDir не является заводской ремонтной документацией; точная применимость не подтверждена. Рынок UNKNOWN, исходный qualifier не интерпретируется как точный код двигателя/КПП, год или поколение. Значения нельзя использовать как подтверждённую спецификацию без сверки с первичным руководством конкретного автомобиля; RU/ЕАЭС применимость, точная пара двигателя/КПП, ECU, DTC и ремонтные процедуры отсутствуют.</p>}';
    text = replaceOnce(text, kbaBoundary, kbaBoundary + "\n" + cardirBoundary, "CarDir boundary");
    text = replaceOnce(text, 'placeholder={dataset === "kba-de" ?', 'placeholder={dataset === "cardir" ? "Марка, модель, параметр, значение или условие из руководства…" : dataset === "kba-de" ?', "CarDir search placeholder");
    const genericCard = '      {dataset === "generic-guidance" && (rows as unknown as GenericGuidanceRow[]).map((row) => <article className="research-result" key={row.guidanceId}>';
    const card = [
      '      {dataset === "cardir" && (rows as unknown as CardirRow[]).map((row) => <article className="research-result" key={row.sourceRowNumber}>',
      '        <div className="research-result-top"><div><small>CarDir · CC BY 4.0 · {row.brand}</small><h3>{row.model} · {row.parameterLabelRu}</h3></div><span className="research-candidate">PUBLISHER VERIFIED · NOT OEM REVIEWED</span></div>',
      '        <div className="research-data-grid">',
      '          <div><small>Значение из источника</small><b>{row.value} {row.unit}</b></div>',
      '          <div><small>Исходный параметр</small><b>{row.parameterKey}</b></div>',
      '          <div><small>Условие / модификация · без интерпретации</small><b>{row.qualifier || "Не указано"}</b></div>',
      '          <div><small>Рынок / точность</small><b>{row.marketScope} · {row.applicabilityPrecision}</b></div>',
      '          <div><small>Проверка издателя / техническая проверка</small><b>{row.publisherVerificationStatus} · {row.technicalReviewStatus}</b></div>',
      '          <div><small>Двигатель / КПП / год / поколение</small><b>Не подтверждены · точная пара отсутствует</b></div>',
      '          <div><small>Источник в руководстве</small><b>{row.sourceTitle} · стр. {row.sourcePage}</b></div>',
      '          <div><small>Дата проверки издателя</small><b>{row.verifiedAt}</b></div>',
      '        </div>',
      '        <div className="research-warning-line">{row.warning}</div>',
      '        <details className="research-details"><summary>Построчная provenance CarDir</summary>',
      '          <p>Строка {row.sourceRowNumber} · SHA строки {row.sourceRowSha256} · SHA CSV snapshot {row.sourceSnapshotSha256} · SHA SQLite {row.databaseSha256} · SHA source manifest {row.sourceManifestSha256}</p>',
      '          <p>Exact vehicle fitment false · exact engine/gearbox pair false · RU/ЕАЭС false · ECU/DTC/repair false.</p>',
      '        </details>',
      '        <div className="research-source"><span>CarDir · CC BY 4.0 · рынок UNKNOWN · не OEM repair data</span><a href={row.sourceUrl} target="_blank" rel="noopener noreferrer">Карточка источника</a> · <a href={row.pageUrl} target="_blank" rel="noopener noreferrer">Модель / руководство</a></div>',
      '      </article>)}'
    ].join("\n");
    text = replaceOnce(text, genericCard, card + "\n" + genericCard, "CarDir result card");
    const creditsAnchor = '      <p>SQLite SHA-256 · OBDex:';
    const credits = '      {cardir && <><p><a href={cardir.sourceUrl} target="_blank" rel="noopener noreferrer">CarDir owner-manual facts</a> — CC BY 4.0. Modified data: filtered to the exact VAG brand allowlist; raw model, qualifier and source fields retained. Attribution: {cardir.attributionText}</p><p>CarDir CSV snapshot SHA-256 {cardir.sourceSnapshotSha256} · SQLite SHA-256 {cardir.databaseSha256} · source-manifest SHA-256 {cardir.sourceManifestSha256}. Market UNKNOWN; no production fitment or repair authorization.</p></>}';
    text = replaceOnce(text, creditsAnchor, credits + "\n" + creditsAnchor, "CarDir attribution");
  }
  fs.writeFileSync(file, text, "utf8");
}

function patchLifecycle(desktopRoot) {
  const file = safeJoin(desktopRoot, "scripts/windows-installer-lifecycle.ps1");
  let text = fs.readFileSync(file, "utf8");
  if (!text.includes("$cardirSummary")) {
    const anchor = '  Write-Host "KBA DE aggregate stock search passed; no engine/gearbox or vehicle-fitment claim."';
    const checks = [
      '  $cardirSummary = Invoke-RestMethod -Uri "$baseUrl/api/local-research?dataset=cardir-summary" -TimeoutSec 45',
      '  if ($cardirSummary.summary.marketScope -ne "UNKNOWN" -or $cardirSummary.summary.rightsStatus -ne "approved_by_published_CC_BY_4_0" -or $cardirSummary.summary.productionImport -ne $false -or $cardirSummary.summary.productImportAllowed -ne $false -or $cardirSummary.summary.ruEaeuApplicability -ne $false -or $cardirSummary.summary.exactEngineGearboxPair -ne $false -or $cardirSummary.summary.counts.vagFacts -ne 948 -or $cardirSummary.summary.counts.vagModels -ne 26 -or $cardirSummary.summary.counts.vagBrands -ne 5 -or $cardirSummary.summary.counts.parameterKeys -ne 19) { throw "CarDir summary, license or research-only boundary failed in offline desktop." }',
      '  $cardirQuery = [uri]::EscapeDataString("Octavia")',
      '  $cardirRows = Invoke-RestMethod -Uri "$baseUrl/api/local-research?dataset=cardir&q=$cardirQuery&limit=20" -TimeoutSec 45',
      '  $cardirSample = @($cardirRows.rows | Where-Object { $_.model -eq "Octavia" -and $_.marketScope -eq "UNKNOWN" }) | Select-Object -First 1',
      '  if (-not $cardirSample -or $cardirSample.publisherVerificationStatus -ne "publisher_verified" -or $cardirSample.technicalReviewStatus -ne "not_independently_reviewed" -or $cardirSample.exactVehicleFitment -ne $false -or $cardirSample.exactEngineGearboxPair -ne 0 -or $cardirSample.productionFitment -ne 0 -or $cardirSample.ruEaeuApplicability -ne $false -or $cardirSample.modelGeneration -ne $null -or $cardirSample.modelYearFrom -ne $null -or $cardirSample.modelYearTo -ne $null -or $cardirSample.engineCode -ne $null -or $cardirSample.transmissionCode -ne $null -or $cardirSample.sourceRowSha256 -notmatch "^[a-f0-9]{64}$" -or $cardirSample.sourceSnapshotSha256 -notmatch "^[a-f0-9]{64}$" -or $cardirSample.databaseSha256 -notmatch "^[a-f0-9]{64}$") { throw "CarDir offline search crossed its research-only applicability boundary." }',
      '  Write-Host "CarDir owner-manual reference search passed; market and exact fitment remain UNKNOWN."'
    ].join("\n");
    text = replaceOnce(text, anchor, anchor + "\n" + checks, "CarDir offline lifecycle check");
  }
  fs.writeFileSync(file, text, "utf8");
}

function patchResearchPackVerifier(desktopRoot) {
  const file = safeJoin(desktopRoot, "scripts/verify-local-research-packs.cjs");
  let text = fs.readFileSync(file, "utf8");
  const countPattern = /((?:[A-Za-z_$][\w$]*\.)?packs\.length\s*(?:!==|!=|===|==)\s*)13\b/g;
  const countMatches = [...text.matchAll(countPattern)];
  assert(countMatches.length === 1, "Expected exactly one hard-coded 13-pack assertion before adding CarDir; found " + countMatches.length);
  text = text.replace(countPattern, "$1" + "14");
  const messagePattern = /Expected 13 separately licensed research packs[^"']*/;
  const messageMatch = text.match(messagePattern);
  assert(messageMatch, "Expected the 13-pack verifier diagnostic to be present");
  text = text.replace(messageMatch[0], "Expected 14 separately licensed research packs, including the DE-only KBA VAG stock research pack and the CarDir VAG owner-manual facts pack");
  assert(!/packs\.length\s*(?:!==|!=|===|==)\s*13\b/.test(text), "The stale 13-pack assertion remains after CarDir integration");
  fs.writeFileSync(file, text, "utf8");
  return { expectedResearchPackCount: 14 };
}

function patchPackage(desktopRoot) {
  const file = safeJoin(desktopRoot, "package.json");
  const pkg = readJson(file);
  assert(pkg.scripts, "Desktop package scripts missing");
  const testNames = ["tests/cardir-vag-reference-facts-db.test.cjs", "tests/cardir-vag-reference-facts-ui-contract.test.cjs"];
  const current = pkg.scripts["test:research"] || "";
  const additions = testNames.filter((name) => !current.includes(name));
  if (additions.length) pkg.scripts["test:research"] = current + " " + additions.join(" ");
  const verifier = "node scripts/verify-cardir-vag-open-data-pack.cjs";
  if (pkg.scripts["verify:local-research"] && !pkg.scripts["verify:local-research"].includes(verifier)) pkg.scripts["verify:local-research"] += " && " + verifier;
  pkg.scripts["verify:cardir-vag-owner-manual-facts"] = verifier;
  atomicJson(file, pkg);
}

function integrate(repoRoot, desktopRoot, downloadRoot, sourceRunId, sourceRunNumber, artifactSha) {
  const packRoot = locatePackRoot(downloadRoot);
  const validated = validatePack(repoRoot, packRoot, artifactSha);
  const researchRoot = safeJoin(desktopRoot, "data/research");
  const target = safeJoin(researchRoot, PACK_ID);
  fs.mkdirSync(researchRoot, { recursive: true });
  fs.rmSync(target, { recursive: true, force: true });
  fs.mkdirSync(target, { recursive: true });
  const copyNames = [
    "cardir-vag-owner-manual-facts.sqlite", "manifest.json", "source-manifest.json",
    "source-snapshot.json", "ATTRIBUTION.md", "LICENSE.txt", "build-report.json"
  ];
  for (const name of copyNames) {
    const sourceFile = safeJoin(packRoot, name);
    const targetFile = safeJoin(target, name);
    fs.copyFileSync(sourceFile, targetFile);
    assert(shaFile(sourceFile) === shaFile(targetFile), "CarDir pack copy hash mismatch: " + name);
  }
  const rel = (file) => path.relative(researchRoot, file).split(path.sep).join("/");
  const report = {
    status: "integrated_verified_research_only",
    pack_id: PACK_ID,
    source_id: SOURCE_ID,
    source_run_id: Number(sourceRunId),
    source_run_number: Number(sourceRunNumber),
    artifact_sha256: artifactSha,
    rights_status: "approved_by_published_CC_BY_4_0",
    license: LICENSE_ID,
    market_scope: ["UNKNOWN"],
    applicability_precision: "model_and_raw_qualifier_text",
    source_manifest_sha256: validated.sourceHash,
    source_snapshot_sha256: validated.sourceSnapshotHash,
    source_snapshot_manifest_sha256: validated.snapshotManifestHash,
    pack_manifest_sha256: validated.packHash,
    database_sha256: validated.databaseHash,
    source_file_sha256: validated.sourceSnapshotHash,
    source_file_bytes: validated.snapshot.source_file_bytes,
    source_file_in_desktop: false,
    counts: validated.counts,
    production_import: false,
    product_import_allowed: false,
    ru_eaeu_applicability: false,
    exact_vehicle_fitment: false,
    exact_engine_gearbox_pair: false,
    repair_procedure: false,
    ecu_fitment: false,
    dtc_fitment: false,
    diagnostic_execution_allowed: false
  };
  const integrationReportFile = safeJoin(target, "desktop-integration-report.json");
  atomicJson(integrationReportFile, report);
  const entry = {
    id: PACK_ID,
    source_id: SOURCE_ID,
    dataset: "CarDir curated VAG owner-manual reference facts",
    publisher: "CarDir",
    source_url: SOURCE_URL,
    license: "CC BY 4.0",
    license_url: "https://creativecommons.org/licenses/by/4.0/",
    license_status: "approved_by_published_CC_BY_4_0",
    rights_status: "approved_by_published_CC_BY_4_0",
    market_scope: ["UNKNOWN"],
    applicability_precision: "model_and_raw_qualifier_text",
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
    repair_procedure: false,
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
    database: rel(safeJoin(target, "cardir-vag-owner-manual-facts.sqlite")),
    database_sha256: validated.databaseHash,
    pack_manifest_file: rel(safeJoin(target, "manifest.json")),
    pack_manifest_sha256: validated.packHash,
    source_manifest_file: rel(safeJoin(target, "source-manifest.json")),
    source_manifest_sha256: validated.sourceHash,
    source_snapshot_manifest_file: rel(safeJoin(target, "source-snapshot.json")),
    source_snapshot_manifest_sha256: validated.snapshotManifestHash,
    attribution_file: rel(safeJoin(target, "ATTRIBUTION.md")),
    attribution_sha256: validated.attributionHash,
    license_file: rel(safeJoin(target, "LICENSE.txt")),
    license_sha256: validated.licenseHash,
    build_report_file: rel(safeJoin(target, "build-report.json")),
    build_report_sha256: validated.buildReportHash,
    desktop_integration_report_file: rel(integrationReportFile),
    desktop_integration_report_sha256: shaFile(integrationReportFile),
    source_revision: validated.sourceRevision,
    source_snapshot_sha256: validated.sourceSnapshotHash,
    source_file_sha256: validated.sourceSnapshotHash,
    source_file_bytes: validated.snapshot.source_file_bytes,
    source_file_included_in_desktop: false,
    source_row_count: validated.snapshot.source_row_count,
    filtered_vag_row_count: validated.snapshot.vag_row_count,
    source_record_hash_method: validated.pack.source_record_hash_method,
    counts: validated.counts,
    source_run_id: Number(sourceRunId),
    source_run_number: Number(sourceRunNumber),
    source_artifact_sha256: artifactSha,
    limitations: [
      "Market is UNKNOWN; raw model qualifiers are retained without interpretation as exact engine, gearbox, model year or generation.",
      "Publisher verification is not independent OEM technical review; values are not factory workshop procedures.",
      "No exact vehicle fitment, factory engine code, gearbox code, engine/gearbox pair, ECU, DTC, wiring, pinout or repair applicability.",
      "No Russian/EAEU applicability is inferred. The original CSV is retained in the CI research artifact but not duplicated into the desktop installer."
    ]
  };
  const rootManifestFile = safeJoin(researchRoot, "manifest.json");
  const rootManifest = readJson(rootManifestFile);
  assert(rootManifest.schema_version === 1 && Array.isArray(rootManifest.packs), "Desktop research manifest schema mismatch");
  const index = rootManifest.packs.findIndex((item) => item.id === PACK_ID);
  if (index >= 0) rootManifest.packs[index] = entry;
  else rootManifest.packs.push(entry);
  atomicJson(rootManifestFile, rootManifest);

  const support = [
    ["desktop/cardir-vag-reference-facts-db.cjs", "lib/cardir-vag-reference-facts-db.cjs"],
    ["desktop/tests/cardir-vag-reference-facts-db.test.cjs", "tests/cardir-vag-reference-facts-db.test.cjs"],
    ["desktop/tests/cardir-vag-reference-facts-ui-contract.test.cjs", "tests/cardir-vag-reference-facts-ui-contract.test.cjs"],
    ["desktop/scripts/verify-cardir-vag-open-data-pack.cjs", "scripts/verify-cardir-vag-open-data-pack.cjs"]
  ];
  for (const pair of support) {
    const sourceFile = safeJoin(repoRoot, pair[0]);
    const targetFile = safeJoin(desktopRoot, pair[1]);
    assert(fs.existsSync(sourceFile) && fs.statSync(sourceFile).isFile(), "CarDir support file missing: " + pair[0]);
    fs.mkdirSync(path.dirname(targetFile), { recursive: true });
    fs.copyFileSync(sourceFile, targetFile);
    assert(shaFile(sourceFile) === shaFile(targetFile), "CarDir support copy mismatch: " + pair[1]);
  }
  patchApi(desktopRoot);
  patchUi(desktopRoot);
  patchLifecycle(desktopRoot);
  patchResearchPackVerifier(desktopRoot);
  patchPackage(desktopRoot);
  process.stdout.write(JSON.stringify({
    status: "integrated_verified_research_only",
    pack_id: PACK_ID,
    source_run_id: Number(sourceRunId),
    source_run_number: Number(sourceRunNumber),
    artifact_sha256: artifactSha,
    source_manifest_sha256: validated.sourceHash,
    source_snapshot_sha256: validated.sourceSnapshotHash,
    pack_manifest_sha256: validated.packHash,
    database_sha256: validated.databaseHash,
    counts: validated.counts,
    market_scope: ["UNKNOWN"],
    production_import: false,
    product_import_allowed: false,
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
  for (const key of ["--desktop-root","--pack-dir","--source-run-id","--source-run-number","--artifact-sha256"]) if (!options[key]) fail("Missing CarDir integration argument " + key);
  if (!/^\d+$/.test(options["--source-run-id"]) || !/^\d+$/.test(options["--source-run-number"]) || !/^[a-f0-9]{64}$/.test(options["--artifact-sha256"])) fail("Invalid CarDir run/artifact provenance");
  integrate(process.cwd(), path.resolve(options["--desktop-root"]), path.resolve(options["--pack-dir"]), options["--source-run-id"], options["--source-run-number"], options["--artifact-sha256"]);
}
if (require.main === module) {
  try { main(process.argv.slice(2)); }
  catch (error) { process.stderr.write((error.stack || error.message) + "\n"); process.exitCode = 1; }
}
module.exports = { validatePack, locatePackRoot, safeJoin, patchResearchPackVerifier };

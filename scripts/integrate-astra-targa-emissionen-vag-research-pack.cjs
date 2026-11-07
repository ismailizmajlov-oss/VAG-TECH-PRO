"use strict";
const fs = require("node:fs");
const path = require("node:path");
const crypto = require("node:crypto");
const { DatabaseSync } = require("node:sqlite");

function fail(message) { throw new Error(message); }
function shaFile(file) { return crypto.createHash("sha256").update(fs.readFileSync(file)).digest("hex"); }
function readJson(file) { return JSON.parse(fs.readFileSync(file, "utf8")); }
function safeJoin(root, relative) {
  if (typeof relative !== "string" || !relative || path.isAbsolute(relative) || relative.includes("\\")) fail("Unsafe relative path: " + String(relative));
  const target = path.resolve(root, relative);
  const prefix = root.endsWith(path.sep) ? root : root + path.sep;
  if (target !== root && !target.startsWith(prefix)) fail("Path escapes root: " + relative);
  return target;
}
function atomicJson(file, value) {
  const temp = file + ".staging-" + process.pid + "-" + crypto.randomBytes(5).toString("hex");
  const backup = file + ".backup-" + process.pid + "-" + crypto.randomBytes(5).toString("hex");
  fs.writeFileSync(temp, JSON.stringify(value, null, 2) + "\n", { flag: "wx" });
  let moved = false;
  try {
    if (fs.existsSync(file)) { fs.renameSync(file, backup); moved = true; }
    fs.renameSync(temp, file);
    if (moved) fs.rmSync(backup, { force: true });
  } catch (error) {
    if (moved && !fs.existsSync(file) && fs.existsSync(backup)) fs.renameSync(backup, file);
    fs.rmSync(temp, { force: true });
    throw error;
  }
}
function replaceOnce(content, before, after, label) {
  if (content.includes(after)) return content;
  const index = content.indexOf(before);
  if (index < 0) fail("ASTRA TARGA integration anchor missing: " + label);
  return content.slice(0, index) + after + content.slice(index + before.length);
}
function copyRegular(source, target) {
  const stat = fs.lstatSync(source);
  if (stat.isSymbolicLink() || !stat.isFile()) fail("ASTRA TARGA resource is not a regular file: " + source);
  fs.mkdirSync(path.dirname(target), { recursive: true });
  fs.copyFileSync(source, target);
  if (shaFile(source) !== shaFile(target)) fail("ASTRA TARGA copy hash mismatch: " + target);
}
function validatePack(packDir, registryManifestPath) {
  const names = ["pack-manifest.json","astra-targa-emissionen-vag.sqlite","source-manifest.json","ATTRIBUTION.txt","field-map.json","build-report.json","final-verification.json"];
  const files = Object.fromEntries(names.map((name) => [name, path.join(packDir, name)]));
  for (const file of Object.values(files)) if (!fs.existsSync(file) || !fs.lstatSync(file).isFile() || fs.lstatSync(file).isSymbolicLink()) fail("Required ASTRA TARGA file missing or unsafe: " + file);
  if (!fs.existsSync(registryManifestPath) || !fs.lstatSync(registryManifestPath).isFile()) fail("ASTRA TARGA source-rights register manifest missing");
  const pack = readJson(files["pack-manifest.json"]);
  const source = readJson(files["source-manifest.json"]);
  const registry = readJson(registryManifestPath);
  const report = readJson(files["build-report.json"]);
  const final = readJson(files["final-verification.json"]);
  const attribution = fs.readFileSync(files["ATTRIBUTION.txt"], "utf8");
  const databaseHash = shaFile(files["astra-targa-emissionen-vag.sqlite"]);
  const sourceHash = shaFile(files["source-manifest.json"]);
  const registryHash = shaFile(registryManifestPath);
  const packHash = shaFile(files["pack-manifest.json"]);
  const sourceFileHash = pack.source_file?.file_sha256;
  const rights = source.rights || {};
  const policy = source.applicability_policy || {};
  if (pack.pack_id !== "astra-fedro-targa-emissionen-vag-research" || pack.status !== "verified_research_only" ||
      pack.source_id !== "astra-fedro-targa-emissionen-approval-variants-ch" || pack.rights_status !== "approved_by_published_ogd_terms" ||
      JSON.stringify(pack.market_scope) !== JSON.stringify(["CH"]) || pack.database?.sha256 !== databaseHash ||
      pack.source_manifest?.sha256 !== sourceHash || source.source_id !== pack.source_id ||
      source.rights?.rights_status !== "approved_by_published_ogd_terms" || registry.source_id !== pack.source_id ||
      JSON.stringify(registry.market_scope) !== JSON.stringify(["CH"]) || registry.snapshot?.file_sha256 !== sourceFileHash ||
      registry.rights?.rights_status !== "approved_by_published_ogd_terms" ||
      ["commercial_use_allowed","display_allowed","offline_cache_allowed","bulk_reuse_allowed","redistribution_allowed","attribution_required"].some((key) => rights[key] !== true) ||
      ["commercial_use_allowed","display_allowed","offline_cache_allowed","bulk_reuse_allowed","redistribution_allowed","attribution_required"].some((key) => registry.rights?.[key] !== true) ||
      policy.market_scope !== "CH only" || policy.source_defined_variant_link !== true || policy.exact_vag_factory_code_pair !== false ||
      policy.production_fitment !== false || policy.ru_eaeu_applicability !== false || policy.model_year_inferred !== false ||
      policy.generation_inferred !== false || policy.repair_procedure_applicability !== false || policy.diagnostic_execution_allowed !== false ||
      !attribution.includes("Federal Roads Office (FEDRO / ASTRA)") || !attribution.includes("Swiss Open Government Data") ||
      final.database_sha256 !== databaseHash || final.source_file_sha256 !== sourceFileHash ||
      final.exact_vag_factory_code_pair !== false || final.ru_eaeu_applicability !== false ||
      report.sqlite_integrity_check !== "ok" || report.foreign_key_violations !== 0) {
    fail("ASTRA TARGA rights, source provenance, attribution or no-fitment boundary failed");
  }
  const db = new DatabaseSync(files["astra-targa-emissionen-vag.sqlite"], { readOnly: true });
  let counts;
  try {
    db.exec("PRAGMA query_only=ON; PRAGMA trusted_schema=OFF;");
    const integrity = db.prepare("PRAGMA integrity_check").all();
    if (integrity.length !== 1 || Object.values(integrity[0])[0] !== "ok" || db.prepare("PRAGMA foreign_key_check").all().length) fail("ASTRA TARGA SQLite integrity check failed");
    const tables = db.prepare("SELECT name FROM sqlite_master WHERE type='table'").all().map((row) => row.name);
    if (!tables.includes("approval_powertrain_variant_rows") || tables.some((name) => name.toLowerCase().includes("dtc") || name.toLowerCase().includes("pair"))) fail("ASTRA TARGA table namespace contains forbidden DTC/pair data");
    counts = {
      approval_powertrain_variant_rows: db.prepare("SELECT count(*) AS n FROM approval_powertrain_variant_rows").get().n,
      source_defined_variant_link_rows: db.prepare("SELECT count(*) AS n FROM approval_powertrain_variant_rows WHERE source_defined_variant_link=1").get().n,
      exact_vag_factory_code_pair_rows: db.prepare("SELECT count(*) AS n FROM approval_powertrain_variant_rows WHERE exact_vag_factory_code_pair<>0").get().n,
      exact_vehicle_fitment_rows: db.prepare("SELECT count(*) AS n FROM approval_powertrain_variant_rows WHERE exact_vehicle_fitment<>0").get().n,
      ru_eaeu_applicability_rows: db.prepare("SELECT count(*) AS n FROM approval_powertrain_variant_rows WHERE ru_eaeu_applicability<>0").get().n
    };
    const invalid = db.prepare("SELECT count(*) AS n FROM approval_powertrain_variant_rows WHERE market_scope!='CH' OR applicability_precision!='CH_type_approval_gearbox_variant_row' OR exact_vag_factory_code_pair!=0 OR exact_vehicle_fitment!=0 OR ru_eaeu_applicability!=0 OR model_year_inferred!=0 OR generation_inferred!=0 OR engine_type_status!='raw_approval_engine_type_candidate' OR gearbox_status!='raw_approval_classification_not_vag_gearbox_code'").get().n;
    if (invalid || counts.approval_powertrain_variant_rows !== 53240 || counts.source_defined_variant_link_rows !== 53240 ||
        counts.exact_vag_factory_code_pair_rows !== 0 || counts.exact_vehicle_fitment_rows !== 0 || counts.ru_eaeu_applicability_rows !== 0) fail("ASTRA TARGA database rows crossed the CH-only candidate boundary");
  } finally { db.close(); }
  return { pack, source, registry, report, final, counts, databaseHash, sourceHash, registryHash, packHash, sourceFileHash, files };
}
function patchApi(desktopRoot) {
  const file = path.join(desktopRoot, "app/api/local-research/route.ts");
  let text = fs.readFileSync(file, "utf8");
  const astraImport = 'import * as astraResearch from "../../../lib/astra-ch-tas-db.cjs";';
  if (!text.includes('from "../../../lib/astra-targa-emissionen-db.cjs"')) {
    if (!text.includes(astraImport)) fail("ASTRA TARGA API import anchor missing");
    text = text.replace(astraImport, astraImport + '\nimport * as astraTargaResearch from "../../../lib/astra-targa-emissionen-db.cjs";');
  }
  const summary = '    if (dataset === "astra-summary") {\n      return Response.json({ ok: true, summary: astraResearch.getAstraSummary() }, { headers });\n    }';
  text = replaceOnce(text, summary, summary + '\n    if (dataset === "astra-targa-summary") {\n      return Response.json({ ok: true, summary: astraTargaResearch.getAstraTargaSummary() }, { headers });\n    }', "ASTRA TARGA summary route");
  const search = '    else if (dataset === "astra") rows = astraResearch.searchAstraApprovals(query, limit);';
  text = replaceOnce(text, search, search + '\n    else if (dataset === "astra-targa") rows = astraTargaResearch.searchAstraTargaRows(query, limit);', "ASTRA TARGA search route");
  fs.writeFileSync(file, text, "utf8");
}
function patchUi(desktopRoot) {
  const file = path.join(desktopRoot, "components/local-research-catalog.tsx");
  let text = fs.readFileSync(file, "utf8");
  text = replaceOnce(text, 'type Dataset = "vehicles" | "vehiclesdb" | "dtc" | "pids" | "uds" | "autodiag2" | "mechanicdb" | "wikidata" | "generic-guidance" | "wikidata-generations" | "astra";',
    'type Dataset = "vehicles" | "vehiclesdb" | "dtc" | "pids" | "uds" | "autodiag2" | "mechanicdb" | "wikidata" | "generic-guidance" | "wikidata-generations" | "astra" | "astra-targa";', "ASTRA TARGA dataset type");
  const astraType = 'type AstraSummary = {\n  counts: { approvals: number; emissionsGearboxRows: number; linkedScopeRows: number; exactScopeLinks: number; wildcardScopeLinks: number; unlinkedScopeRows: number };\n  sourceRevision: string; sourceSnapshotSha256: string; databaseSha256: string; sourceManifestSha256: string;\n  marketScope: string; rightsStatus: string; attributionText: string; sourceUrl: string; ruEaeuApplicability: false;\n};';
  const targaType = astraType + '\ntype AstraTargaSummary = {\n  counts: { approvalPowertrainVariantRows: number; sourceDefinedVariantLinkRows: number; exactVagFactoryCodePairRows: number; exactVehicleFitmentRows: number; ruEaeuApplicabilityRows: number };\n  sourceRevision: string; sourceFileSha256: string; databaseSha256: string; sourceManifestSha256: string;\n  marketScope: string; rightsStatus: string; attributionText: string; sourceUrl: string; productionImport: false;\n  productImportAllowed: false; ruEaeuApplicability: false; exactVagFactoryCodePair: false; note: string;\n};';
  text = replaceOnce(text, astraType, targaType, "ASTRA TARGA summary type");
  const rowAnchor = '  gearboxClassificationKind?: string; gearboxRecordSha256?: string | null;\n};';
  const rowFields = '  gearboxClassificationKind?: string; gearboxRecordSha256?: string | null;\n  engineType?: string | null; engineMake?: string | null; gearboxClassification?: string | null; type?: string | null;\n  sourceRowNumber?: number; sourceRecordLocator?: string; sourceDefinedVariantLink?: boolean;\n  exactVagFactoryCodePair?: boolean; ruEaeuApplicability?: boolean; modelYear?: null;\n  engineTypeStatus?: string; gearboxStatus?: string; homologationDate?: string | null;';
  text = replaceOnce(text, rowAnchor, rowFields, "ASTRA TARGA row fields");
  const tab = '  { id: "astra", label: "ОТТС · CH", hint: "ASTRA/FEDRO · Swiss OGD · только Швейцария" },';
  text = replaceOnce(text, tab, tab + '\n  { id: "astra-targa", label: "TARGA · варианты КПП · CH", hint: "ASTRA/FEDRO · 53 240 строк одобрений · не RU/ЕАЭС и не OEM-коды" },', "ASTRA TARGA tab");
  const state = '  const [astraSummary, setAstraSummary] = useState<AstraSummary | null>(null);';
  text = replaceOnce(text, state, state + '\n  const [astraTargaSummary, setAstraTargaSummary] = useState<AstraTargaSummary | null>(null);', "ASTRA TARGA state");
  const rowsState = '  const [rows, setRows] = useState<ResearchRow[]>([]);';
  const effect = '  useEffect(() => {\n    let active = true;\n    fetch("/api/local-research?dataset=astra-targa-summary", { cache: "no-store" })\n      .then(async (response) => { const payload = await response.json(); if (!response.ok) throw new Error(payload.error || "ASTRA TARGA справочник недоступен."); return payload; })\n      .then((payload) => { if (active && payload?.ok) setAstraTargaSummary(payload.summary as AstraTargaSummary); })\n      .catch(() => { if (active) setAstraTargaSummary(null); });\n    return () => { active = false; };\n  }, []);\n\n' + rowsState;
  text = replaceOnce(text, rowsState, effect, "ASTRA TARGA summary fetch");
  text = replaceOnce(text, '  const astra = astraSummary;', '  const astra = astraSummary;\n  const astraTarga = astraTargaSummary;', "ASTRA TARGA summary binding");
  const stat = '<article className="research-stat"><small>ОТТС / типовые одобрения CH</small><strong>{formatNumber(astra?.counts?.approvals)}</strong><span>{formatNumber(astra?.counts?.linkedScopeRows)} связей variant/version · не RU/ЕАЭС</span></article>';
  text = replaceOnce(text, stat, stat + '\n      <article className="research-stat"><small>TARGA · CH variant rows</small><strong>{formatNumber(astraTarga?.counts?.approvalPowertrainVariantRows)}</strong><span>0 подтверждённых VAG-код пар · не RU/ЕАЭС</span></article>', "ASTRA TARGA statistic");
  const boundary = '      <b>Важно: справочные кандидаты не являются подтверждённой применимостью.</b>';
  text = replaceOnce(text, boundary, boundary + '\n      <p>ASTRA TARGA — отдельный CH-only реестр строк типового одобрения, по одной строке на вариант коробки в источнике. Это не российское/ЕАЭС ОТТС и не заводская пара кодов: Motortyp и Getriebe сохраняются как исходные поля одобрения, без преобразования в VAG engine/gearbox codes. Модельный год, поколение, VIN fitment, ECU, DTC и ремонтная применимость не выводятся.</p>', "ASTRA TARGA boundary");
  const placeholder = 'dataset === "astra" ? "Номер одобрения, модель, engineType или класс КПП CH…" :';
  text = replaceOnce(text, placeholder, 'dataset === "astra-targa" ? "Номер одобрения, Motortyp, Getriebe или тип двигателя CH…" : ' + placeholder, "ASTRA TARGA search placeholder");
  const genericResults = '      {dataset === "generic-guidance" && (rows as unknown as GenericGuidanceRow[]).map((row) => <article className="research-result" key={row.guidanceId}>';
  const targaResults = [
    '      {dataset === "astra-targa" && rows.map((row) => <article className="research-result" key={String(row.id)}>',
    '        <div className="research-result-top"><div><small>ASTRA / FEDRO TARGA · {row.make} · CH · {row.approvalNumber}</small><h3>{row.type || row.approvalNumber}</h3></div><span className="research-candidate">CH APPROVAL VARIANT · NOT OEM FITMENT</span></div>',
    '        <div className="research-data-grid">',
    '          <div><small>Motortyp · исходное поле одобрения</small><b>{row.engineType || "—"}</b></div>',
    '          <div><small>Getriebe · классификация ASTRA</small><b>{row.gearboxClassification || "—"}</b></div>',
    '          <div><small>Марка двигателя из записи</small><b>{row.engineMake || "—"}</b></div>',
    '          <div><small>Объём / мощность / момент</small><b>{[row.displacementCc ? row.displacementCc + " см³" : null, row.powerKw ? row.powerKw + " кВт" : null, row.torqueNm ? row.torqueNm + " Н·м" : null].filter(Boolean).join(" · ") || "—"}</b></div>',
    '          <div><small>Дата одобрения</small><b>{row.homologationDate || "Не указана"}</b></div>',
    '          <div><small>Рынок / год / поколение</small><b>CH · год не выведен · поколение не выведено</b></div>',
    '          <div><small>Связь исходной строки</small><b>Одна source-defined approval/gearbox row</b></div>',
    '          <div><small>Заводская пара VAG / применимость</small><b>Не подтверждены · RU/ЕАЭС отсутствует</b></div>',
    '        </div>',
    '        <div className="research-warning-line">{row.warning}</div>',
    '        <div className="research-source"><span>ASTRA TARGA OGD · ревизия {row.sourceRevision} · строка {row.sourceRowNumber} · SHA записи {String(row.sourceRecordSha256).slice(0, 12)}… · SHA исходного файла {String(row.sourceFileSha256).slice(0, 12)}… · SHA SQLite {String(row.databaseSha256).slice(0, 12)}…</span>{row.sourceUrl && <a href={row.sourceUrl} target="_blank" rel="noopener noreferrer">Открыть исходный файл</a>}</div>',
    '      </article>)}',
    genericResults
  ].join("\n");
  text = replaceOnce(text, genericResults, targaResults, "ASTRA TARGA result cards");
  const credits = '      <p>SQLite SHA-256 · OBDex: {obdex?.databaseSha256 || "недоступен"}</p>';
  const attribution = '      {astraTarga && <><p><a href="https://www.astra.admin.ch/de/fahrzeugdaten" target="_blank" rel="noopener noreferrer">FEDRO / ASTRA TARGA emissions data</a> — Swiss Open Government Data; commercial use, display, offline caching and redistribution allowed with attribution. CH-only historical type-approval rows; no RU/EAEU or OEM factory-code applicability.</p><p>{astraTarga.attributionText}</p><p>Ревизия {astraTarga.sourceRevision} · SHA исходного файла {astraTarga.sourceFileSha256} · SHA SQLite {astraTarga.databaseSha256} · SHA манифеста {astraTarga.sourceManifestSha256} · строк {formatNumber(astraTarga.counts.approvalPowertrainVariantRows)} · подтверждённых VAG engine/gearbox pairs {formatNumber(astraTarga.counts.exactVagFactoryCodePairRows)}.</p></>}\n' + credits;
  text = replaceOnce(text, credits, attribution, "ASTRA TARGA attribution");
  fs.writeFileSync(file, text, "utf8");
}
function patchLifecycle(desktopRoot) {
  const file = path.join(desktopRoot, "scripts/windows-installer-lifecycle.ps1");
  let text = fs.readFileSync(file, "utf8");
  const anchor = '  Write-Output "ASTRA offline CH approval search passed; no VAG factory fitment or repair claims."';
  const check = [
    '  $targaSummary = Invoke-RestMethod -Uri "$baseUrl/api/local-research?dataset=astra-targa-summary" -TimeoutSec 30',
    '  if ($targaSummary.summary.marketScope -ne "CH" -or $targaSummary.summary.rightsStatus -ne "approved_by_published_ogd_terms" -or $targaSummary.summary.productionImport -ne $false -or $targaSummary.summary.ruEaeuApplicability -ne $false -or $targaSummary.summary.counts.approvalPowertrainVariantRows -ne 53240) { throw "ASTRA TARGA offline summary or CH-only boundary failed." }',
    '  $targaRows = Invoke-RestMethod -Uri "$baseUrl/api/local-research?dataset=astra-targa&q=1AB701&limit=10" -TimeoutSec 30',
    '  $targaSample = @($targaRows.rows | Where-Object { $_.approvalNumber -eq "1AB701" -and $_.engineType -eq "AEL" -and $_.gearboxClassification -eq "m6" }) | Select-Object -First 1',
    '  if (-not $targaSample -or $targaSample.marketScope -ne "CH" -or $targaSample.sourceDefinedVariantLink -ne $true -or $targaSample.exactVagFactoryCodePair -ne $false -or $targaSample.ruEaeuApplicability -ne $false -or $targaSample.modelYear -ne $null -or $targaSample.generation -ne $null) { throw "ASTRA TARGA offline search crossed its CH approval-only boundary." }',
    '  Write-Output "ASTRA TARGA offline CH source-row search passed; no OEM pair, RU/EAEU fitment or repair claims."'
  ].join("\n");
  text = replaceOnce(text, anchor, anchor + "\n" + check, "ASTRA TARGA offline lifecycle check");
  fs.writeFileSync(file, text, "utf8");
}
function patchResearchVerifier(desktopRoot) {
  const file = path.join(desktopRoot, "scripts/verify-local-research-packs.cjs");
  let text = fs.readFileSync(file, "utf8");
  if (text.includes("astraTargaSummary")) return;
  if (!text.includes("manifest.packs.length === 10")) fail("Run74 research verifier manifest count anchor missing");
  text = text.replace("manifest.packs.length === 10", "manifest.packs.length === 11");
  text = text.replace("Expected ten registered research packs, including the CH-only ASTRA and AutoDiag2 packs", "Expected eleven registered research packs, including separate CH-only ASTRA TAS and TARGA packs");
  const summaryLine = '  const astraSummary = require(path.join(ROOT, "lib", "astra-ch-tas-db.cjs")).getAstraSummary(RESEARCH);';
  if (!text.includes(summaryLine)) fail("Run74 ASTRA summary verifier anchor missing");
  const targaCheck = summaryLine + '\n  const astraTargaSummary = require(path.join(ROOT, "lib", "astra-targa-emissionen-db.cjs")).getAstraTargaSummary(RESEARCH);\n  assert(astraTargaSummary.id === "astra-fedro-targa-emissionen-approval-variants-ch" && astraTargaSummary.marketScope === "CH" && astraTargaSummary.productionImport === false && astraTargaSummary.productImportAllowed === false && astraTargaSummary.ruEaeuApplicability === false && astraTargaSummary.exactVagFactoryCodePair === false && astraTargaSummary.counts.approvalPowertrainVariantRows === 53240 && astraTargaSummary.counts.exactVagFactoryCodePairRows === 0, "ASTRA TARGA must remain separately namespaced CH-only research, never factory fitment");';
  text = text.replace(summaryLine, targaCheck);
  fs.writeFileSync(file, text, "utf8");
}
function integrate(repoRoot, desktopRoot, packDir, sourceRunId, artifactSha) {
  const registryManifestPath = safeJoin(desktopRoot, "data/source-manifests/astra-targa-emissionen-open-data.json");
  const validated = validatePack(packDir, registryManifestPath);
  const researchRoot = safeJoin(desktopRoot, "data/research");
  const target = safeJoin(researchRoot, "astra-targa-emissionen-vag-research");
  if (fs.existsSync(target)) fs.rmSync(target, { recursive: true, force: true });
  fs.mkdirSync(target, { recursive: true });
  const mapping = [
    ["pack-manifest.json","pack-manifest.json"],
    ["astra-targa-emissionen-vag.sqlite","astra-targa-emissionen-vag.sqlite"],
    ["source-manifest.json","source-manifest.json"],
    ["ATTRIBUTION.txt","ATTRIBUTION.txt"],
    ["field-map.json","field-map.json"],
    ["build-report.json","build-report.json"],
    ["final-verification.json","final-verification.json"]
  ];
  for (const [from,to] of mapping) copyRegular(validated.files[from], path.join(target,to));
  copyRegular(registryManifestPath, path.join(target,"source-registry-manifest.json"));
  const rel = (file) => path.relative(researchRoot,file).split(path.sep).join("/");
  const rootManifestPath = safeJoin(researchRoot,"manifest.json");
  const rootManifest = readJson(rootManifestPath);
  if (rootManifest.schema_version !== 1 || !Array.isArray(rootManifest.packs)) fail("Desktop research manifest schema mismatch");
  const files = {
    database: path.join(target,"astra-targa-emissionen-vag.sqlite"),
    packManifest: path.join(target,"pack-manifest.json"),
    sourceManifest: path.join(target,"source-manifest.json"),
    registryManifest: path.join(target,"source-registry-manifest.json"),
    attribution: path.join(target,"ATTRIBUTION.txt"),
    fieldMap: path.join(target,"field-map.json"),
    buildReport: path.join(target,"build-report.json"),
    finalVerification: path.join(target,"final-verification.json")
  };
  const entry = {
    id: SOURCE_ID, source_id: SOURCE_ID, dataset: "ASTRA / FEDRO TARGA per-gearbox type-approval rows",
    publisher: "Federal Roads Office (FEDRO / ASTRA), Swiss Confederation", source_url: SOURCE_URL,
    database: rel(files.database), database_sha256: validated.databaseHash,
    pack_manifest_file: rel(files.packManifest), pack_manifest_sha256: shaFile(files.packManifest),
    source_manifest_file: rel(files.sourceManifest), source_manifest_sha256: validated.sourceHash,
    source_registry_manifest_file: rel(files.registryManifest), source_registry_manifest_sha256: shaFile(files.registryManifest),
    attribution_file: rel(files.attribution), attribution_sha256: shaFile(files.attribution),
    field_map_file: rel(files.fieldMap), field_map_sha256: shaFile(files.fieldMap),
    build_report_file: rel(files.buildReport), build_report_sha256: shaFile(files.buildReport),
    final_verification_file: rel(files.finalVerification), final_verification_sha256: shaFile(files.finalVerification),
    license: "Swiss Open Government Data (OGD)", license_status: "approved_by_published_ogd_terms",
    rights_status: "approved_by_published_ogd_terms", market_scope: ["CH"],
    applicability_precision: "CH_type_approval_gearbox_variant_row", review_status: "verified_research_only",
    production_import: false, product_import_allowed: false, ru_eaeu_applicability: false,
    exact_vag_factory_code_pair: false, exact_vehicle_fitment: false, fitment_claim: false,
    repair_applicability: false, diagnostic_execution_allowed: false,
    commercial_use_allowed: true, display_allowed: true, cache_allowed: true, redistribution_allowed: true,
    attribution_required: true, share_alike_required: false,
    source_revision: validated.pack.source_revision, source_snapshot_sha256: validated.sourceFileHash,
    source_file_sha256: validated.sourceFileHash, counts: validated.counts,
    source_run_id: sourceRunId || null, source_artifact_sha256: artifactSha || null,
    limitations: [
      "Swiss CH-only type-approval research; never Russian/EAEU OTTS or market applicability.",
      "Motortyp is a raw approval field and is not independently confirmed as a VAG factory engine code.",
      "Getriebe is an ASTRA approval classification, not a VAG gearbox code.",
      "The source-defined row is not a production vehicle fitment or exact factory engine/gearbox code pair.",
      "No model year, generation, VIN, ECU, DTC, diagnostic test plan or repair applicability."
    ]
  };
  const index = rootManifest.packs.findIndex((item) => item.id === entry.id);
  if (index >= 0) rootManifest.packs[index] = entry; else rootManifest.packs.push(entry);
  atomicJson(rootManifestPath, rootManifest);
  const support = [
    ["desktop/astra-targa-emissionen-db.cjs","lib/astra-targa-emissionen-db.cjs"],
    ["desktop/astra-targa-emissionen-db.d.cts","lib/astra-targa-emissionen-db.d.cts"],
    ["desktop/tests/astra-targa-emissionen-db.test.cjs","tests/astra-targa-emissionen-db.test.cjs"],
    ["desktop/tests/astra-targa-emissionen-ui-contract.test.cjs","tests/astra-targa-emissionen-ui-contract.test.cjs"],
    ["desktop/scripts/verify-astra-targa-emissionen-pack.cjs","scripts/verify-astra-targa-emissionen-pack.cjs"]
  ];
  for (const [from,to] of support) {
    const source = safeJoin(repoRoot,from), targetFile = safeJoin(desktopRoot,to);
    if (!fs.existsSync(source) || !fs.lstatSync(source).isFile() || fs.lstatSync(source).isSymbolicLink()) fail("ASTRA TARGA support file missing or unsafe: " + from);
    copyRegular(source,targetFile);
  }
  patchApi(desktopRoot);
  patchUi(desktopRoot);
  patchLifecycle(desktopRoot);\n  patchResearchVerifier(desktopRoot);
  const packagePath = safeJoin(desktopRoot,"package.json");
  const pkg = readJson(packagePath);
  if (!pkg.scripts || typeof pkg.scripts["test:research"] !== "string" || typeof pkg.scripts["verify:local-research"] !== "string") fail("Desktop research scripts are missing");
  if (!JSON.stringify(pkg.build?.extraResources || []).includes("data/research")) fail("Desktop package does not include offline research resources");
  for (const file of ["tests/astra-targa-emissionen-db.test.cjs","tests/astra-targa-emissionen-ui-contract.test.cjs"]) {
    if (!pkg.scripts["test:research"].includes(file)) pkg.scripts["test:research"] += " " + file;
  }
  const verify = "node scripts/verify-astra-targa-emissionen-pack.cjs";
  if (!pkg.scripts["verify:local-research"].includes(verify)) pkg.scripts["verify:local-research"] += " && " + verify;
  fs.writeFileSync(packagePath,JSON.stringify(pkg,null,2)+"\n","utf8");
  const report = {
    status: "integrated_verified_research_only", pack_id: PACK_ID, source_id: SOURCE_ID,
    source_revision: entry.source_revision, market_scope: ["CH"], rights_status: entry.rights_status,
    source_manifest_sha256: entry.source_manifest_sha256, source_registry_manifest_sha256: entry.source_registry_manifest_sha256,
    pack_manifest_sha256: entry.pack_manifest_sha256, database_sha256: entry.database_sha256,
    source_artifact_sha256: entry.source_artifact_sha256, source_run_id: entry.source_run_id,
    counts: entry.counts, production_import: false, product_import_allowed: false,
    ru_eaeu_applicability: false, exact_vag_factory_code_pair: false, exact_vehicle_fitment: false,
    repair_applicability: false, diagnostic_execution_allowed: false
  };
  atomicJson(path.join(target,"desktop-integration-report.json"),report);
  process.stdout.write(JSON.stringify(report,null,2)+"\n");
}
function main(argv) {
  const options = {};
  for (let i=0;i<argv.length;i++) {
    const key=argv[i];
    if (!["--repo-root","--desktop-root","--pack-dir","--source-run-id","--artifact-sha256"].includes(key) || !argv[i+1]) fail("Invalid argument: "+key);
    options[key]=argv[++i];
  }
  if (!options["--repo-root"] || !options["--desktop-root"] || !options["--pack-dir"]) fail("--repo-root, --desktop-root and --pack-dir are required");
  if (options["--artifact-sha256"] && !/^[a-f0-9]{64}$/.test(options["--artifact-sha256"])) fail("Invalid artifact SHA-256");
  integrate(path.resolve(options["--repo-root"]),path.resolve(options["--desktop-root"]),path.resolve(options["--pack-dir"]),options["--source-run-id"],options["--artifact-sha256"]);
}
if (require.main === module) {
  try { main(process.argv.slice(2)); } catch (error) { process.stderr.write("ASTRA TARGA integration failed: "+error.message+"\n"); process.exitCode=1; }
}
module.exports = { validatePack, integrate, patchApi, patchUi, patchLifecycle };

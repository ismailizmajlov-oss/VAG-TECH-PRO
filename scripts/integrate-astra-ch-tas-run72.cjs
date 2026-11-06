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
  const target = path.resolve(root, relative), prefix = root.endsWith(path.sep) ? root : root + path.sep;
  if (target !== root && !target.startsWith(prefix)) fail("Path escapes root: " + relative);
  return target;
}
function copyTree(source, target) {
  const stat = fs.lstatSync(source);
  if (stat.isSymbolicLink()) fail("ASTRA pack contains a symlink: " + source);
  if (stat.isFile()) {
    fs.mkdirSync(path.dirname(target), { recursive: true });
    fs.copyFileSync(source, target);
    if (shaFile(source) !== shaFile(target)) fail("ASTRA copy hash mismatch: " + target);
    return;
  }
  if (!stat.isDirectory()) fail("Unsupported ASTRA pack entry: " + source);
  fs.mkdirSync(target, { recursive: true });
  for (const name of fs.readdirSync(source).sort()) copyTree(path.join(source, name), path.join(target, name));
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
  if (index < 0) fail("ASTRA integration anchor missing: " + label);
  return content.slice(0, index) + after + content.slice(index + before.length);
}
function validatePack(packDir, sourceManifestPath) {
  const packManifestPath = path.join(packDir, "manifest.json");
  const databasePath = path.join(packDir, "astra-ch-tas-vag-open-data.sqlite");
  const attributionPath = path.join(packDir, "ATTRIBUTION.md");
  const rightsPath = path.join(packDir, "RIGHTS.md");
  const reportPath = path.join(packDir, "build-report.json");
  for (const file of [packManifestPath, databasePath, attributionPath, rightsPath, reportPath, sourceManifestPath]) {
    if (!fs.existsSync(file) || !fs.statSync(file).isFile()) fail("Required ASTRA file missing: " + file);
  }
  const pack = readJson(packManifestPath), sourceBytes = fs.readFileSync(sourceManifestPath);
  const sourceHash = crypto.createHash("sha256").update(sourceBytes).digest("hex");
  const source = JSON.parse(sourceBytes.toString("utf8")), report = readJson(reportPath);
  const databaseHash = shaFile(databasePath), rights = source.rights || {}, policy = source.import_policy || {};
  const attribution = fs.readFileSync(attributionPath, "utf8"), rightsText = fs.readFileSync(rightsPath, "utf8");
  const requiredAttribution = "Source: Federal Roads Office (FEDRO/ASTRA), Type Approval System (TAS) open data.";
  if (pack.pack_id !== "astra-ch-tas-vag-open-data" || pack.status !== "verified_research_only" ||
      pack.source_id !== "astra-fedro-tas-type-approvals-open-data-ch" || JSON.stringify(pack.market_scope) !== JSON.stringify(["CH"]) ||
      pack.source_manifest_sha256 !== sourceHash || pack.database?.sha256 !== databaseHash || report.database_sha256 !== databaseHash ||
      pack.database?.size_bytes !== fs.statSync(databasePath).size || source.source_id !== pack.source_id ||
      JSON.stringify(source.market_scope) !== JSON.stringify(["CH"]) || rights.rights_status !== "approved_by_published_ogd_terms" ||
      rights.attribution !== requiredAttribution ||
      rights.evidence_url !== "https://opendata.astra.admin.ch/ivzod/5000-Newsletter/2026_1/Newsletter_Fahrzeugdaten_1_2026_EN.pdf" ||
      !String(rights.evidence || "").includes("2026-02-23") ||
      ["commercial_use_allowed", "display_allowed", "offline_cache_allowed", "bulk_reuse_allowed", "redistribution_allowed", "attribution_required"].some((key) => rights[key] !== true) ||
      policy.namespace !== "separate_read_only_research_pack" || policy.production_import !== false || policy.ru_eaeu_applicability !== false ||
      policy.exact_brand_match_only !== true || policy.never_cross_join_engine_and_gearbox_variants !== true ||
      !attribution.includes(requiredAttribution) || !rightsText.includes(requiredAttribution) || !rightsText.includes("CH")) {
    fail("ASTRA pack/source manifest rights, provenance, hash or CH-only boundary failed");
  }
  const db = new DatabaseSync(databasePath, { readOnly: true });
  try {
    db.exec("PRAGMA query_only=ON; PRAGMA trusted_schema=OFF;");
    const integrity = db.prepare("PRAGMA integrity_check").all();
    if (integrity.length !== 1 || Object.values(integrity[0])[0] !== "ok" || db.prepare("PRAGMA foreign_key_check").all().length) fail("ASTRA SQLite integrity/foreign-key check failed");
    const meta = Object.fromEntries(db.prepare("SELECT key,value FROM pack_metadata").all().map((row) => [row.key, row.value]));
    if (meta.pack_status !== "verified_research_only" || meta.rights_status !== rights.rights_status || meta.market_scope !== "CH" ||
        meta.production_import !== "false" || meta.ru_eaeu_applicability !== "false" || meta.repair_applicability !== "false" ||
        meta.source_revision !== pack.source_revision || meta.source_manifest_sha256 !== sourceHash) fail("ASTRA SQLite metadata mismatch");
    const counts = {
      approvals: db.prepare("SELECT count(*) AS n FROM type_approval_records").get().n,
      emissionsGearboxRows: db.prepare("SELECT count(*) AS n FROM emissions_gearbox_rows").get().n,
      linkedScopeRows: db.prepare("SELECT count(*) AS n FROM engine_gearbox_scope_links").get().n,
      exactScopeLinks: db.prepare("SELECT count(*) AS n FROM engine_gearbox_scope_links WHERE relation_precision='approval_version_exact'").get().n,
      wildcardScopeLinks: db.prepare("SELECT count(*) AS n FROM engine_gearbox_scope_links WHERE relation_precision='approval_variant_wildcard'").get().n,
      unlinkedScopeRows: db.prepare("SELECT count(*) AS n FROM emissions_gearbox_rows WHERE linked_approval_row_id IS NULL").get().n
    };
    const expected = {
      approvals: Number(pack.counts?.approval_rows?.passenger_cars?.total || 0) + Number(pack.counts?.approval_rows?.other_automobiles?.total || 0),
      emissionsGearboxRows: Number(pack.counts?.emissions_gearbox_rows?.total || 0),
      linkedScopeRows: Number(pack.counts?.linked_scope_rows || 0),
      exactScopeLinks: Number(pack.counts?.scope_link_counts?.exact || 0),
      wildcardScopeLinks: Number(pack.counts?.scope_link_counts?.wildcard || 0),
      unlinkedScopeRows: Number(pack.counts?.unlinked_scope_rows || 0)
    };
    const invalidMarket = db.prepare("SELECT (SELECT count(*) FROM type_approval_records WHERE market_scope!='CH') + (SELECT count(*) FROM emissions_gearbox_rows WHERE market_scope!='CH') + (SELECT count(*) FROM engine_gearbox_scope_links WHERE market_scope!='CH') AS n").get().n;
    const invalidClaims = db.prepare("SELECT count(*) AS n FROM engine_gearbox_scope_links WHERE factory_vag_engine_code_claim!=0 OR factory_vag_gearbox_code_claim!=0 OR production_fitment_claim!=0").get().n;
    const dtcTables = db.prepare("SELECT count(*) AS n FROM sqlite_master WHERE type='table' AND lower(name) LIKE '%dtc%'").get().n;
    if (invalidMarket || invalidClaims || dtcTables || Object.keys(expected).some((key) => expected[key] <= 0 || counts[key] !== expected[key]) ||
        counts.linkedScopeRows !== counts.exactScopeLinks + counts.wildcardScopeLinks ||
        counts.emissionsGearboxRows !== counts.linkedScopeRows + counts.unlinkedScopeRows) fail("ASTRA counts or CH-only no-factory-fitment gate failed");
    return { pack, sourceHash, databaseHash, counts };
  } finally { db.close(); }
}
function patchApi(desktopRoot) {
  const file = path.join(desktopRoot, "app/api/local-research/route.ts");
  let text = fs.readFileSync(file, "utf8");
  const genericImport = 'import * as genericGuidance from "../../../lib/generic-repair-guidance-db.cjs";';
  if (!text.includes('from "../../../lib/astra-ch-tas-db.cjs"')) {
    if (!text.includes(genericImport)) fail("ASTRA API import anchor missing");
    text = text.replace(genericImport, genericImport + '\nimport * as astraResearch from "../../../lib/astra-ch-tas-db.cjs";');
  }
  const summary = '    if (dataset === "generic-guidance-summary") {\n      return Response.json(genericGuidance.getSummary(), { headers });\n    }';
  text = replaceOnce(text, summary, summary + '\n    if (dataset === "astra-summary") {\n      return Response.json({ ok: true, summary: astraResearch.getAstraSummary() }, { headers });\n    }', "ASTRA summary route");
  const search = '    else if (dataset === "generic-guidance") rows = genericGuidance.search(query, limit);';
  text = replaceOnce(text, search, search + '\n    else if (dataset === "astra") rows = astraResearch.searchAstraApprovals(query, limit);', "ASTRA search route");
  fs.writeFileSync(file, text, "utf8");
}
function patchUi(desktopRoot) {
  const file = path.join(desktopRoot, "components/local-research-catalog.tsx");
  let text = fs.readFileSync(file, "utf8");
  text = replaceOnce(text,
    'type WikidataGenerationSummary = {\n  counts: { memberEntities: number; modelMemberLinks: number };\n};',
    'type WikidataGenerationSummary = {\n  counts: { memberEntities: number; modelMemberLinks: number };\n};\ntype AstraSummary = {\n  counts: { approvals: number; emissionsGearboxRows: number; linkedScopeRows: number; exactScopeLinks: number; wildcardScopeLinks: number; unlinkedScopeRows: number };\n  sourceRevision: string; sourceSnapshotSha256: string; databaseSha256: string; sourceManifestSha256: string;\n  marketScope: string; rightsStatus: string; attributionText: string; sourceUrl: string; ruEaeuApplicability: false;\n};',
    "ASTRA summary type");
  text = replaceOnce(text,
    'type Dataset = "vehicles" | "vehiclesdb" | "dtc" | "pids" | "uds" | "autodiag2" | "mechanicdb" | "wikidata" | "generic-guidance" | "wikidata-generations";',
    'type Dataset = "vehicles" | "vehiclesdb" | "dtc" | "pids" | "uds" | "autodiag2" | "mechanicdb" | "wikidata" | "generic-guidance" | "wikidata-generations" | "astra";',
    "ASTRA dataset type");
  text = replaceOnce(text, '  repairProcedureFitment?: boolean;\n};',
    '  repairProcedureFitment?: boolean;\n  approvalNumber?: string; typeDesignation?: string | null; variant?: string | null; version?: string | null;\n  engineTypeDesignation?: string | null; stampedEngineMarking?: string | null; fuelType?: string | null;\n  engineCapacityCc?: number | null; maximumNetPower?: string | null; driveType?: string | null;\n  gearboxNumber?: string | null; gearboxClass?: string | null; gearboxMapping?: string | null;\n  gearboxVersionScope?: string | null; gearboxScopeStatus?: string | null; relationPrecision?: string;\n  gearboxClassificationKind?: string; sourceRecordSha256?: string; gearboxRecordSha256?: string | null;\n};', "ASTRA row type");
  const tab = '  { id: "generic-guidance", label: "Общие рекомендации", hint: "ODbL · SAE/ISO · не VAG-specific" },';
  text = replaceOnce(text, tab, '  { id: "astra", label: "ОТТС · CH", hint: "ASTRA/FEDRO · Swiss OGD · только Швейцария" },\n' + tab, "ASTRA tab");
  const state = '  const [genericGuidanceSummary, setGenericGuidanceSummary] = useState<GenericGuidanceSummary | null>(null);';
  text = replaceOnce(text, state, state + '\n  const [astraSummary, setAstraSummary] = useState<AstraSummary | null>(null);', "ASTRA state");
  const rowsState = '  const [rows, setRows] = useState<ResearchRow[]>([]);';
  const effect = '  useEffect(() => {\n    let active = true;\n    fetch("/api/local-research?dataset=astra-summary", { cache: "no-store" })\n      .then(async (response) => { const payload = await response.json(); if (!response.ok) throw new Error(payload.error || "ASTRA CH справочник недоступен."); return payload; })\n      .then((payload) => { if (active && payload?.ok) setAstraSummary(payload.summary as AstraSummary); })\n      .catch(() => { if (active) setAstraSummary(null); });\n    return () => { active = false; };\n  }, []);\n\n' + rowsState;
  text = replaceOnce(text, rowsState, effect, "ASTRA summary fetch");
  const autoDiag = '  const autoDiag2 = summary.find((pack) => pack.id === "autodiag2-vag-community-candidates-odbl");';
  text = replaceOnce(text, autoDiag, autoDiag + '\n  const astra = astraSummary;', "ASTRA summary binding");
  const stat = '<article className="research-stat"><small>Общие рекомендации</small><strong>{formatNumber(genericGuidanceSummary?.counts?.genericRepairGuidance)}</strong><span>{formatNumber(genericGuidanceSummary?.counts?.genericDtcReferences)} общих DTC · ODbL-1.0</span></article>';
  text = replaceOnce(text, stat, stat + '\n      <article className="research-stat"><small>ОТТС / типовые одобрения CH</small><strong>{formatNumber(astra?.counts?.approvals)}</strong><span>{formatNumber(astra?.counts?.linkedScopeRows)} связей variant/version · не RU/ЕАЭС</span></article>', "ASTRA statistic");
  const boundary = '<p>P179/P527 — только кандидаты серий, а не подтверждённые поколения. Рынок UNKNOWN; даты — исходные утверждения, не годы выпуска. Нет точной применимости к автомобилю, двигателю, КПП, ECU, DTC или ремонтным данным.</p>';
  text = replaceOnce(text, boundary, boundary + '\n      {astra && <p>Отдельный справочник ASTRA/FEDRO содержит {formatNumber(astra.counts.approvals)} швейцарских типовых одобрений и {formatNumber(astra.counts.emissionsGearboxRows)} строк выбросов/классов КПП. Это только рынок CH: не российские/ЕАЭС ОТТС, не VIN-комплектация и не заводская применимость. engineType сохраняется как обозначение в одобрении и не подтверждает заводской код двигателя VAG; stamped marking — отдельно; chGearboxType — швейцарская классификация, не код КПП VAG. Точные связи variant/version относятся только к области швейцарского одобрения; wildcard не является точной версией.</p>}', "ASTRA boundary");
  text = replaceOnce(text, 'placeholder={dataset === "generic-guidance" ?',
    'placeholder={dataset === "astra" ? "Номер одобрения, модель, engineType или класс КПП CH…" : dataset === "generic-guidance" ?', "ASTRA placeholder");
  const genericResults = '      {dataset === "generic-guidance" && (rows as unknown as GenericGuidanceRow[]).map((row) => <article className="research-result" key={row.guidanceId}>';
  const cards = [
    '      {dataset === "astra" && rows.map((row) => <article className="research-result" key={String(row.id)}>',
    '        <div className="research-result-top"><div><small>ASTRA / FEDRO · {row.make} · CH · {row.approvalNumber}</small><h3>{row.commercialName || row.typeDesignation || row.approvalNumber}</h3></div><span className="research-candidate">CH TYPE APPROVAL</span></div>',
    '        <div className="research-data-grid">',
    '          <div><small>Тип / вариант / версия</small><b>{[row.typeDesignation, row.variant, row.version].filter(Boolean).join(" · ") || "—"}</b></div>',
    '          <div><small>Engine type · обозначение одобрения</small><b>{row.engineTypeDesignation || "—"}</b></div>',
    '          <div><small>Маркировка на двигателе</small><b>{row.stampedEngineMarking || "—"}</b></div>',
    '          <div><small>Класс КПП по CH одобрению</small><b>{row.gearboxClass || "Не связан"}</b></div>',
    '          <div><small>Область связи</small><b>{row.relationPrecision === "approval_version_exact" ? "Точная variant/version в CH одобрении" : row.relationPrecision === "approval_variant_wildcard" ? "Variant-wide · версия *" : "Не связана"}</b></div>',
    '          <div><small>Статус связи</small><b>{row.gearboxScopeStatus || "—"}</b></div>',
    '          <div><small>Объём / топливо / мощность</small><b>{[row.engineCapacityCc ? String(row.engineCapacityCc) + " см³" : null, row.fuelType, row.maximumNetPower].filter(Boolean).join(" · ") || "—"}</b></div>',
    '          <div><small>Рынок / год / VIN</small><b>CH · модельный год не задан · VIN fitment отсутствует</b></div>',
    '        </div>',
    '        <div className="research-warning-line">{row.warning}</div>',
    '        <div className="research-source"><span>FEDRO/ASTRA OGD · ревизия {row.sourceRevision} · SHA записи {String(row.sourceRecordSha256).slice(0, 12)}… · SHA БД {String(row.databaseSha256).slice(0, 12)}… · SHA манифеста {String(row.sourceManifestSha256).slice(0, 12)}…</span>{row.sourceUrl && <a href={row.sourceUrl} target="_blank" rel="noopener noreferrer">Открыть запись ASTRA</a>}</div>',
    '      </article>)}',
    genericResults
  ].join("\n");
  text = replaceOnce(text, genericResults, cards, "ASTRA result cards");
  const credits = '      <p>SQLite SHA-256 · OBDex: {obdex?.databaseSha256 || "недоступен"}</p>';
  text = replaceOnce(text, credits,
    '      {astra && <><p><a href="https://www.astra.admin.ch/de/fahrzeugdaten" target="_blank" rel="noopener noreferrer">FEDRO / ASTRA Type Approval System (TAS)</a> — Swiss Open Government Data; коммерческое использование, отображение, offline-кэширование и распространение разрешены по опубликованному OGD-уведомлению при обязательной атрибуции. Это отдельный CH-only pack, не RU/ЕАЭС.</p><p>{astra.attributionText}</p><p>Ревизия {astra.sourceRevision} · SHA snapshot {astra.sourceSnapshotSha256} · SHA SQLite {astra.databaseSha256} · SHA source manifest {astra.sourceManifestSha256} · точные scope links {formatNumber(astra.counts.exactScopeLinks)} · wildcard {formatNumber(astra.counts.wildcardScopeLinks)} · unlinked {formatNumber(astra.counts.unlinkedScopeRows)}.</p></>}\n' + credits,
    "ASTRA attribution");
  fs.writeFileSync(file, text, "utf8");
}
function patchLifecycle(desktopRoot) {
  const file = path.join(desktopRoot, "scripts/windows-installer-lifecycle.ps1");
  let text = fs.readFileSync(file, "utf8");
  const anchor = '  if (@($genericRows.rows).Count -lt 1 -or $genericRows.rows[0].vagSpecific -ne $false -or $genericRows.rows[0].diagnosticExecutionAllowed -ne $false -or $genericRows.rows[0].exactVehicleFitment -ne $false) { throw "Generic guidance is missing or was promoted to VAG fitment/executable diagnostics." }';
  const check = [
    '  $astraSummary = Invoke-RestMethod -Uri "$baseUrl/api/local-research?dataset=astra-summary" -TimeoutSec 30',
    '  if ($astraSummary.summary.marketScope -ne "CH" -or $astraSummary.summary.rightsStatus -ne "approved_by_published_ogd_terms" -or $astraSummary.summary.productionImport -ne $false -or $astraSummary.summary.ruEaeuApplicability -ne $false -or $astraSummary.summary.counts.approvals -le 0) { throw "ASTRA CH summary or rights/market boundary failed in offline desktop." }',
    '  $astraRows = Invoke-RestMethod -Uri "$baseUrl/api/local-research?dataset=astra&q=1XZ904&limit=10" -TimeoutSec 30',
    '  $astraSample = @($astraRows.rows | Where-Object { $_.approvalNumber -eq "1XZ904" -and $_.make -eq "CUPRA" -and $_.engineTypeDesignation -eq "DNPA" -and $_.gearboxClass -eq "m7a" -and $_.relationPrecision -eq "approval_variant_wildcard" }) | Select-Object -First 1',
    '  if (-not $astraSample -or $astraSample.marketScope -ne "CH" -or $astraSample.engineCode -ne $null -or $astraSample.gearboxCode -ne $null -or $astraSample.factoryVagEngineCodeClaim -ne $false -or $astraSample.factoryVagGearboxCodeClaim -ne $false -or $astraSample.productionFitmentClaim -ne $false -or $astraSample.repairApplicability -ne $false -or $astraSample.diagnosticExecutionAllowed -ne $false) { throw "ASTRA offline search crossed its CH approval-only boundary." }',
    '  Write-Output "ASTRA offline CH approval search passed; no VAG factory fitment or repair claims."'
  ].join("\n");
  text = replaceOnce(text, anchor, anchor + "\n" + check, "ASTRA offline lifecycle check");
  fs.writeFileSync(file, text, "utf8");
}
function integrate(repoRoot, desktopRoot, packDir, sourceRunId, artifactSha) {
  const bundled = path.join(packDir, "astra-ch-tas-open-data.json");
  const sourceManifestPath = fs.existsSync(bundled) ? bundled : safeJoin(repoRoot, "data/source-manifests/astra-ch-tas-open-data.json");
  const validated = validatePack(packDir, sourceManifestPath);
  const researchRoot = safeJoin(desktopRoot, "data/research");
  const target = safeJoin(researchRoot, "astra-ch-tas-vag-open-data");
  if (fs.existsSync(target)) fs.rmSync(target, { recursive: true, force: true });
  copyTree(packDir, target);
  const sourceTarget = safeJoin(target, "astra-ch-tas-open-data.json");
  if (!fs.existsSync(sourceTarget)) fs.copyFileSync(sourceManifestPath, sourceTarget);
  if (shaFile(sourceTarget) !== validated.sourceHash) fail("ASTRA source manifest copy hash mismatch");
  const rel = (file) => path.relative(researchRoot, file).split(path.sep).join("/");
  const packManifestFile = safeJoin(target, "manifest.json"), attributionFile = safeJoin(target, "ATTRIBUTION.md");
  const rightsFile = safeJoin(target, "RIGHTS.md"), databaseFile = safeJoin(target, "astra-ch-tas-vag-open-data.sqlite");
  const rootManifestPath = safeJoin(researchRoot, "manifest.json"), rootManifest = readJson(rootManifestPath);
  if (rootManifest.schema_version !== 1 || !Array.isArray(rootManifest.packs)) fail("Desktop research manifest schema mismatch");
  const entry = {
    id: "astra-fedro-tas-type-approvals-open-data-ch", source_id: "astra-fedro-tas-type-approvals-open-data-ch",
    dataset: "ASTRA / FEDRO Type Approval System (TAS)", publisher: "Federal Roads Office (FEDRO / ASTRA), Swiss Confederation",
    source_url: "https://www.astra.admin.ch/de/fahrzeugdaten", database: rel(databaseFile), database_sha256: validated.databaseHash,
    pack_manifest_file: rel(packManifestFile), pack_manifest_sha256: shaFile(packManifestFile),
    source_manifest_file: rel(sourceTarget), source_manifest_sha256: validated.sourceHash,
    attribution_file: rel(attributionFile), attribution_sha256: shaFile(attributionFile),
    rights_file: rel(rightsFile), rights_sha256: shaFile(rightsFile),
    license: "Swiss Open Government Data (OGD)", license_status: "approved_by_published_ogd_terms",
    rights_status: "approved_by_published_ogd_terms",
    rights_evidence_url: "https://opendata.astra.admin.ch/ivzod/5000-Newsletter/2026_1/Newsletter_Fahrzeugdaten_1_2026_EN.pdf",
    market_scope: ["CH"], applicability_precision: "ch_type_approval_row", review_status: "verified_research_only",
    production_import: false, ru_eaeu_applicability: false, fitment_claim: false, exact_vehicle_fitment: false,
    repair_applicability: false, diagnostic_execution_allowed: false, commercial_use_allowed: true, display_allowed: true,
    cache_allowed: true, redistribution_allowed: true, attribution_required: true, share_alike_required: false,
    source_revision: validated.pack.source_revision, source_snapshot_sha256: validated.pack.source_snapshot_sha256,
    counts: validated.counts, source_run_id: sourceRunId || null, source_artifact_sha256: artifactSha || null,
    limitations: [
      "Swiss-only type-approval research; never Russian/EAEU OTTS or market applicability.",
      "engineType is an approval designation, not automatically a VAG factory engine code.",
      "chGearboxType is a Swiss type-approval classification, not a VAG gearbox code.",
      "Variant/version links are approval-scope only; no VIN, production fitment, repair, ECU or DTC applicability."
    ]
  };
  const index = rootManifest.packs.findIndex((item) => item.id === entry.id);
  if (index >= 0) rootManifest.packs[index] = entry; else rootManifest.packs.push(entry);
  rootManifest.astra_ch_tas_pack = { id: entry.id, market_scope: "CH", production_import: false, ru_eaeu_applicability: false, database_sha256: entry.database_sha256 };
  atomicJson(rootManifestPath, rootManifest);
  const support = [
    ["desktop/astra-ch-tas-db.cjs", "lib/astra-ch-tas-db.cjs"],
    ["desktop/astra-ch-tas-db.d.cts", "lib/astra-ch-tas-db.d.cts"],
    ["desktop/tests/astra-ch-tas-db.test.cjs", "tests/astra-ch-tas-db.test.cjs"],
    ["desktop/tests/astra-ch-tas-ui-contract.test.cjs", "tests/astra-ch-tas-ui-contract.test.cjs"],
    ["desktop/scripts/verify-astra-ch-tas-pack.cjs", "scripts/verify-astra-ch-tas-pack.cjs"]
  ];
  for (const [from, to] of support) {
    const source = safeJoin(repoRoot, from), targetFile = safeJoin(desktopRoot, to);
    if (!fs.existsSync(source) || !fs.statSync(source).isFile()) fail("ASTRA support file missing: " + from);
    fs.mkdirSync(path.dirname(targetFile), { recursive: true });
    fs.copyFileSync(source, targetFile);
    if (shaFile(source) !== shaFile(targetFile)) fail("ASTRA support copy mismatch: " + to);
  }
  patchApi(desktopRoot);
  patchUi(desktopRoot);
  patchLifecycle(desktopRoot);
  const packagePath = safeJoin(desktopRoot, "package.json"), pkg = readJson(packagePath);
  if (!pkg.scripts || typeof pkg.scripts["test:research"] !== "string" || typeof pkg.scripts["verify:local-research"] !== "string") fail("Desktop research scripts are missing");
  if (!JSON.stringify(pkg.build?.extraResources || []).includes("data/research")) fail("Desktop package does not include the offline research-data resource directory");
  for (const file of ["tests/astra-ch-tas-db.test.cjs", "tests/astra-ch-tas-ui-contract.test.cjs"]) if (!pkg.scripts["test:research"].includes(file)) pkg.scripts["test:research"] += " " + file;
  const verify = "node scripts/verify-astra-ch-tas-pack.cjs";
  if (!pkg.scripts["verify:local-research"].includes(verify)) pkg.scripts["verify:local-research"] += " && " + verify;
  fs.writeFileSync(packagePath, JSON.stringify(pkg, null, 2) + "\n", "utf8");
  const result = {
    status: "integrated_verified_research_only", pack_id: entry.id, source_revision: entry.source_revision,
    market_scope: entry.market_scope, rights_status: entry.rights_status, source_manifest_sha256: entry.source_manifest_sha256,
    pack_manifest_sha256: entry.pack_manifest_sha256, database_sha256: entry.database_sha256,
    source_artifact_sha256: entry.source_artifact_sha256, source_run_id: entry.source_run_id, counts: entry.counts,
    production_import: false, ru_eaeu_applicability: false, exact_vehicle_fitment: false, repair_applicability: false
  };
  atomicJson(safeJoin(target, "desktop-integration-report.json"), result);
  process.stdout.write(JSON.stringify(result, null, 2) + "\n");
}
function main(argv) {
  const options = {};
  for (let i = 0; i < argv.length; i += 1) {
    const key = argv[i];
    if (!["--desktop-root", "--pack-dir", "--source-run-id", "--artifact-sha256"].includes(key) || !argv[i + 1]) fail("Invalid argument: " + key);
    options[key] = argv[++i];
  }
  if (!options["--desktop-root"] || !options["--pack-dir"]) fail("--desktop-root and --pack-dir are required");
  if (options["--artifact-sha256"] && !/^[a-f0-9]{64}$/.test(options["--artifact-sha256"])) fail("Invalid artifact SHA-256");
  integrate(process.cwd(), path.resolve(options["--desktop-root"]), path.resolve(options["--pack-dir"]), options["--source-run-id"], options["--artifact-sha256"]);
}
if (require.main === module) {
  try { main(process.argv.slice(2)); }
  catch (error) { process.stderr.write((error.stack || error.message) + "\n"); process.exitCode = 1; }
}
module.exports = { validatePack };

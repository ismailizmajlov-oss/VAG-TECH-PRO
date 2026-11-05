"use strict";

const fs = require("node:fs");
const path = require("node:path");
const crypto = require("node:crypto");
const { spawnSync } = require("node:child_process");

const PACK_ID = "rdw-vag-type-approval-cc0";
const SOURCE_ID = "rdw-vag-type-approval-cc0";

function fail(message) { throw new Error("[run75] " + message); }
function sha256(buffer) { return crypto.createHash("sha256").update(buffer).digest("hex"); }
function sha256File(file) { return sha256(fs.readFileSync(file)); }
function readText(file) {
  if (!fs.existsSync(file)) fail("Required file missing: " + file);
  return fs.readFileSync(file, "utf8").replace(/\r\n/g, "\n");
}
function readJson(file) {
  try { return JSON.parse(readText(file)); }
  catch (error) { fail("Invalid JSON " + file + ": " + error.message); }
}
function writeText(file, value) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, value.replace(/\r\n/g, "\n"), "utf8");
}
function writeJson(file, value) { writeText(file, JSON.stringify(value, null, 2) + "\n"); }
function replaceText(source, before, after, label) {
  if (source.includes(after)) return source;
  const count = source.split(before).length - 1;
  if (count !== 1) fail(label + ": expected exactly one anchor, found " + count);
  return source.replace(before, after);
}
function copyFile(source, target) {
  if (!fs.existsSync(source)) fail("Copy source missing: " + source);
  fs.mkdirSync(path.dirname(target), { recursive: true });
  fs.copyFileSync(source, target);
}
function copyDirectory(source, target) {
  if (!fs.existsSync(source)) fail("Pack directory missing: " + source);
  fs.mkdirSync(target, { recursive: true });
  for (const entry of fs.readdirSync(source, { withFileTypes: true })) {
    const from = path.join(source, entry.name);
    const to = path.join(target, entry.name);
    if (entry.isDirectory()) copyDirectory(from, to);
    else if (entry.isFile()) copyFile(from, to);
    else fail("Unexpected non-file pack entry: " + from);
  }
}
function run(command, args, cwd, env) {
  const result = spawnSync(command, args, { cwd, env, encoding: "utf8", stdio: "inherit" });
  if (result.error || result.status !== 0) fail(command + " " + args.join(" ") + " failed: " + (result.error ? result.error.message : result.status));
}
function number(value, label) {
  if (!Number.isSafeInteger(value) || value < 0) fail("Invalid RDW count " + label);
  return value;
}
function arg(name, fallback) {
  const index = process.argv.indexOf(name);
  return index >= 0 && process.argv[index + 1] ? process.argv[index + 1] : fallback;
}

function main() {
  const repo = process.cwd();
  const desktop = path.resolve(arg("--desktop-root", "desktop-source"));
  const pack = path.resolve(arg("--pack-dir", path.join(repo, "build", PACK_ID)));
  const research = path.join(desktop, "data", "research");
  const target = path.join(research, PACK_ID);
  if (!fs.existsSync(desktop) || !fs.existsSync(pack)) fail("Desktop root or verified RDW pack is missing");

  const manifestPath = path.join(pack, "manifest.json");
  const manifest = readJson(manifestPath);
  if (manifest.pack_id !== PACK_ID || manifest.source_id !== SOURCE_ID ||
      manifest.data_license !== "CC0-1.0" || manifest.rights_status !== "approved_by_published_license" ||
      manifest.verification_status !== "verified_source_candidate_pack_only") {
    fail("RDW pack identity, CC0 rights or candidate-only verification status mismatch");
  }
  if (manifest.exact_vehicle_fitment !== false || manifest.ru_eaeu_applicability !== false ||
      manifest.vag_factory_engine_code_verified !== false || manifest.vag_factory_gearbox_code_verified !== false ||
      manifest.diagnostic_execution_allowed !== false || manifest.no_license_plate_retained !== true ||
      manifest.no_personal_or_holder_data_retained !== true) {
    fail("RDW candidate-only, privacy or RU/EAEU boundary failed");
  }
  if (!Array.isArray(manifest.market_scope) || !manifest.market_scope.includes("EU_TYPE_APPROVAL") ||
      !manifest.market_scope.includes("NL_REGISTRATION_OBSERVATION") ||
      manifest.market_scope.some((value) => /RU|EAEU/i.test(value))) {
    fail("RDW market scope is invalid or contains RU/EAEU");
  }
  for (const key of ["vehicle_variants", "engine_candidates", "transmission_candidates",
    "approval_revision_candidates", "manufacturer_designation_candidates",
    "unique_source_row_pair_candidates", "ambiguous_or_incomplete_pair_keys"]) {
    number(manifest.counts?.[key], key);
  }
  for (const key of ["database_sha256", "source_snapshot_sha256", "metadata_bundle_sha256", "source_manifest_sha256"]) {
    if (!/^[a-f0-9]{64}$/.test(String(manifest[key] || ""))) fail("Invalid RDW hash: " + key);
  }
  if (sha256File(path.join(pack, "rdw-vag-type-approval.sqlite")) !== manifest.database_sha256) fail("RDW SQLite SHA-256 mismatch before desktop integration");
  if (sha256File(path.join(pack, "LICENSE-CC0-1.0.txt")) !== manifest.license_sha256) fail("RDW CC0 notice SHA-256 mismatch before desktop integration");
  if (sha256File(path.join(pack, "ATTRIBUTION.md")) !== manifest.attribution_sha256) fail("RDW attribution SHA-256 mismatch before desktop integration");

  const lockRepo = path.join(repo, "data", "source-manifests", "rdw-vag-type-approval.lock.json");
  const registerRepo = path.join(repo, "data", "source-manifests", "vag-factory-source-register.json");
  const lockBytes = fs.readFileSync(lockRepo);
  if (sha256(lockBytes) !== manifest.source_manifest_sha256) fail("RDW source-lock SHA-256 does not match the pack manifest");
  const register = readJson(registerRepo);
  const source = (register.sources || []).find((item) => item.source_id === SOURCE_ID);
  if (!source || source.rights?.data_license_status !== "CC0-1.0" ||
      source.rights?.commercial_use_allowed !== true || source.rights?.display_allowed !== true ||
      source.rights?.offline_cache_allowed !== true || source.rights?.bulk_reuse_allowed !== true ||
      source.rights?.redistribution_allowed !== true || source.rights?.share_alike_required !== false ||
      source.applicability?.exact_vehicle_fitment !== false || source.technical_scope?.ru_eaeu_applicability !== false) {
    fail("RDW source register does not clear the pack's rights and applicability boundaries");
  }
  source.verification_status = "verified_source_candidate_pack_only";
  source.display_status = "candidate_only_read_only";
  source.counts = manifest.counts;
  source.access.completeness_status = "verified_filtered_snapshot_only_not_full_registry";
  source.latest_verified_pack = {
    fetched_at_utc: manifest.fetched_at_utc,
    source_revision: manifest.source_revision,
    source_manifest_sha256: manifest.source_manifest_sha256,
    source_snapshot_sha256: manifest.source_snapshot_sha256,
    database_sha256: manifest.database_sha256,
    metadata_bundle_sha256: manifest.metadata_bundle_sha256,
    counts: manifest.counts
  };
  source.evidence_status = "Live RDW metadata, filtered VAG snapshots, source-row joins, privacy exclusions and SQLite integrity reverified for this Windows desktop build; EU/NL candidate evidence only.";
  fs.writeFileSync(path.join(pack, "source-lock.json"), lockBytes);
  writeJson(path.join(pack, "source-register.json"), {
    schema_version: 1,
    updated_at: manifest.fetched_at_utc,
    sources: [source]
  });
  manifest.source_register_sha256 = sha256File(path.join(pack, "source-register.json"));
  writeJson(manifestPath, manifest);

  if (fs.existsSync(target)) {
    const existing = path.join(target, "manifest.json");
    if (!fs.existsSync(existing) || readJson(existing).database_sha256 !== manifest.database_sha256) {
      fail("RDW desktop target already exists with different or unverified contents; refusing overwrite");
    }
  } else {
    copyDirectory(pack, target);
  }
  if (sha256File(path.join(target, "source-lock.json")) !== manifest.source_manifest_sha256 ||
      sha256File(path.join(target, "source-register.json")) !== manifest.source_register_sha256 ||
      sha256File(path.join(target, "rdw-vag-type-approval.sqlite")) !== manifest.database_sha256) {
    fail("RDW desktop copy hash verification failed");
  }

  copyFile(lockRepo, path.join(desktop, "data", "source-manifests", "rdw-vag-type-approval.lock.json"));
  copyFile(registerRepo, path.join(desktop, "data", "source-manifests", "vag-factory-source-register.json"));
  copyFile(path.join(repo, "docs", "research", "RDW_VAG_TYPE_APPROVAL_SOURCE_REVIEW_2026-11-05.md"),
    path.join(desktop, "docs", "research", "RDW_VAG_TYPE_APPROVAL_SOURCE_REVIEW_2026-11-05.md"));
  copyFile(path.join(repo, "lib", "rdw-type-approval-db.cjs"), path.join(desktop, "lib", "rdw-type-approval-db.cjs"));
  copyFile(path.join(repo, "lib", "rdw-type-approval-db.d.cts"), path.join(desktop, "lib", "rdw-type-approval-db.d.cts"));

  const rootManifestPath = path.join(research, "manifest.json");
  const rootManifest = readJson(rootManifestPath);
  if (!Array.isArray(rootManifest.integrated_artifacts)) rootManifest.integrated_artifacts = [];
  const artifactRecord = {
    id: PACK_ID,
    kind: "read_only_type_approval_candidates",
    source_id: SOURCE_ID,
    source_revision: manifest.source_revision,
    source_snapshot_sha256: manifest.source_snapshot_sha256,
    metadata_bundle_sha256: manifest.metadata_bundle_sha256,
    database_sha256: manifest.database_sha256,
    source_manifest_sha256: manifest.source_manifest_sha256,
    source_register_sha256: manifest.source_register_sha256,
    pack_manifest_sha256: sha256File(manifestPath),
    license: "CC0-1.0",
    market_scope: manifest.market_scope,
    applicability_precision: manifest.applicability_precision,
    display_status: "candidate_only_read_only",
    exact_vehicle_fitment: false,
    ru_eaeu_applicability: false,
    vag_factory_engine_code_verified: false,
    vag_factory_gearbox_code_verified: false,
    diagnostic_execution_allowed: false,
    counts: manifest.counts
  };
  const oldArtifact = rootManifest.integrated_artifacts.findIndex((item) => item.id === PACK_ID);
  if (oldArtifact >= 0) rootManifest.integrated_artifacts[oldArtifact] = artifactRecord;
  else rootManifest.integrated_artifacts.push(artifactRecord);
  writeJson(rootManifestPath, rootManifest);

  const researchReadme = path.join(research, "README.md");
  const rdwReadme = "\n## RDW EU type-approval candidate pack (CC0-1.0)\n\n" +
    "- Separate read-only SQLite: " + PACK_ID + "/rdw-vag-type-approval.sqlite.\n" +
    "- Official RDW filtered VAG M1 data; market scope is EU type approval plus Netherlands registration observations only.\n" +
    "- Engine values remain in namespace RDW.motorcode; transmission values remain in namespace RDW.codetypeversnellingsbak.\n" +
    "- A unique source-row pair is a candidate association, not a confirmed VAG engine/gearbox mapping or VIN fitment.\n" +
    "- No RU/EAEU OTTS, model-year/generation confirmation, ECU, DTC, repair, wiring, pinout, torque or adaptation data.\n" +
    "- CC0-1.0; live per-resource metadata, filtered query, raw snapshots, SQLite and source-lock hashes are verified at each build.\n";
  if (!fs.existsSync(researchReadme)) writeText(researchReadme, "# Local research data\n");
  let researchText = readText(researchReadme);
  if (!researchText.includes(PACK_ID)) writeText(researchReadme, researchText + rdwReadme);

  const packsDoc = path.join(desktop, "docs", "RESEARCH_DATA_PACKS.md");
  if (!fs.existsSync(packsDoc)) writeText(packsDoc, "# Research data packs\n");
  let packsText = readText(packsDoc);
  if (!packsText.includes(PACK_ID)) writeText(packsDoc, packsText + "\n## RDW EU type-approval candidate pack\n\n" + rdwReadme);

  const coreFile = path.join(desktop, "lib", "local-research-db.cjs");
  let core = readText(coreFile);
  const wrapper = [
    "const rdwTypeApprovalDbCache = new Map();",
    "function rdwTypeApprovalDbForRoot(root) {",
    "  const path = require(\"node:path\");",
    "  const researchRoot = path.resolve(root || process.env.VAG_TECH_PRO_RESEARCH_DIR || path.join(process.cwd(), \"data\", \"research\"));",
    "  if (!rdwTypeApprovalDbCache.has(researchRoot)) {",
    "    const { createRdwTypeApprovalDb } = require(\"./rdw-type-approval-db.cjs\");",
    "    const packDir = path.join(researchRoot, \"rdw-vag-type-approval-cc0\");",
    "    rdwTypeApprovalDbCache.set(researchRoot, createRdwTypeApprovalDb({",
    "      packDir,",
    "      lockPath: path.join(packDir, \"source-lock.json\"),",
    "      registerPath: path.join(packDir, \"source-register.json\")",
    "    }));",
    "  }",
    "  return rdwTypeApprovalDbCache.get(researchRoot);",
    "}",
    "function getRdwTypeApprovalSummary(root) {",
    "  return rdwTypeApprovalDbForRoot(root).getSummary();",
    "}",
    "function searchRdwTypeApprovalCandidates(query, limit = 20, root) {",
    "  const result = rdwTypeApprovalDbForRoot(root).search(query, limit);",
    "  if (result.status !== \"ready_candidate_only\") throw new Error(result.error || \"RDW candidate pack is unavailable or failed integrity checks\");",
    "  return result.results;",
    "}"
  ].join("\n");
  if (!core.includes("function getRdwTypeApprovalSummary")) {
    const anchor = "function searchVehiclesDbCandidates(query, limit = 25, root) {";
    const count = core.split(anchor).length - 1;
    if (count !== 1) fail("Local research DB RDW insertion anchor count: " + count);
    core = core.replace(anchor, wrapper + "\n\n" + anchor);
  }
  const exportAnchor = "  validateQuery,";
  const exportInsert = "  getRdwTypeApprovalSummary,\n  searchRdwTypeApprovalCandidates,\n  validateQuery,";
  if (!core.includes("  getRdwTypeApprovalSummary,")) {
    const exportAnchorCount = core.split(exportAnchor).length - 1;
    if (exportAnchorCount !== 1) fail("Local research DB export anchor count: " + exportAnchorCount);
    if (!core.includes("  searchWikidataCandidates,")) fail("Wikidata research export is missing before RDW integration");
    core = core.replace(exportAnchor, exportInsert);
  }
  writeText(coreFile, core);

  const declarationFile = path.join(desktop, "lib", "local-research-db.d.cts");
  let declaration = readText(declarationFile);
  const declarations = "\nexport function getRdwTypeApprovalSummary(root?: string): Record<string, unknown>;\n" +
    "export function searchRdwTypeApprovalCandidates(query: string, limit?: number, root?: string): Array<Record<string, unknown>>;\n";
  if (!declaration.includes("getRdwTypeApprovalSummary")) writeText(declarationFile, declaration + declarations);

  const routeFile = path.join(desktop, "app", "api", "local-research", "route.ts");
  let route = readText(routeFile);
  if (!route.includes('dataset === "rdw-summary"')) {
    const summaryAnchor = '    if (dataset === "summary") {';
    const summaryInsert = '    if (dataset === "rdw-summary") {\n      return Response.json(localResearch.getRdwTypeApprovalSummary(), { headers });\n    }\n' + summaryAnchor;
    const count = route.split(summaryAnchor).length - 1;
    if (count !== 1) fail("RDW API summary insertion anchor count: " + count);
    route = route.replace(summaryAnchor, summaryInsert);
  }
  if (!route.includes('dataset === "rdw"')) {
    const unknown = '    else return Response.json({ error: "Неизвестный локальный справочник." }, { status: 404, headers });';
    const insert = '    else if (dataset === "rdw") rows = localResearch.searchRdwTypeApprovalCandidates(query, limit);\n' + unknown;
    const count = route.split(unknown).length - 1;
    if (count !== 1) fail("RDW API search insertion anchor count: " + count);
    route = route.replace(unknown, insert);
  }
  writeText(routeFile, route);

  const uiFile = path.join(desktop, "components", "local-research-catalog.tsx");
  let ui = readText(uiFile);
  const datasetMatch = ui.match(/^type Dataset = ([^;]+);$/m);
  if (!datasetMatch) fail("Research UI Dataset type is missing");
  if (!datasetMatch[1].split("|").some((part) => part.trim() === '"rdw')) {
    ui = ui.replace(datasetMatch[0], "type Dataset = " + datasetMatch[1] + ' | "rdw";');
  }
  const rowStart = ui.indexOf("type ResearchRow = {");
  if (rowStart < 0) fail("Research UI row type is missing");
  const rowEnd = ui.indexOf("\n};", rowStart);
  if (rowEnd < 0) fail("Research UI row type closing brace is missing");
  const rowText = ui.slice(rowStart, rowEnd);
  const rowFields = [
    "make?: string;", "model?: string;", "typeApprovalNumber?: string;", "variantCode?: string;",
    "executionCode?: string;", "firstRegistrationSeen?: string | null;", "lastRegistrationSeen?: string | null;",
    "revisionNumber?: string | null;", "revisionStartDate?: string | null;", "revisionEndDate?: string | null;",
    "rdwMotorcode?: string | null;", "engineCodeNamespace?: string;", "rdwTransmissionTypeCode?: string | null;",
    "transmissionCodeNamespace?: string;", "gearCountMin?: string | null;", "gearCountMax?: string | null;",
    "pairingStatus?: string;", "engineRowCount?: number;", "transmissionRowCount?: number;",
    "manufacturerTradeName?: string | null;", "manufacturerTypeDesignation?: string | null;",
    "marketScope?: string;", "applicabilityPrecision?: string;", "verificationStatus?: string;",
    "sourceId?: string;", "sourceRevision?: string;", "pairingConfirmed?: boolean;",
    "ruEaeuApplicability?: boolean;", "vagFactoryEngineCodeVerified?: boolean;", "vagFactoryGearboxCodeVerified?: boolean;"
  ];
  const missingFields = rowFields.filter((field) => !rowText.includes(field));
  if (missingFields.length) ui = ui.slice(0, rowEnd) + "\n" + missingFields.map((field) => "  " + field).join("\n") + ui.slice(rowEnd);

  if (!ui.includes("type RdwTypeApprovalSummary")) {
    const updatedRowEnd = ui.indexOf("\n};", ui.indexOf("type ResearchRow = {")) + 3;
    const rdwTypes = [
      "type RdwTypeApprovalSummary = {",
      "  status: string; sourceId: string; sourceRevision?: string; dataLicense?: string;",
      "  sourceUrl?: string; licenseUrl?: string; marketScope?: string[]; applicabilityPrecision?: string;",
      "  verificationStatus?: string;",
      "  counts: { vehicle_variants: number; engine_candidates: number; transmission_candidates: number; approval_revision_candidates: number; manufacturer_designation_candidates: number; unique_source_row_pair_candidates: number; ambiguous_or_incomplete_pair_keys: number } | null;",
      "  databaseSha256?: string; sourceSnapshotSha256?: string; metadataBundleSha256?: string;",
      "  sourceManifestSha256?: string; sourceRegisterSha256?: string | null;",
      "  exactVehicleFitment?: false; ruEaeuApplicability?: false; vagFactoryEngineCodeVerified?: false;",
      "  vagFactoryGearboxCodeVerified?: false; diagnosticExecutionAllowed?: false; limitations?: string[]; error?: string;",
      "};"
    ].join("\n");
    ui = ui.slice(0, updatedRowEnd) + "\n\n" + rdwTypes + ui.slice(updatedRowEnd);
  }

  const genericState = 'const [genericGuidanceSummary, setGenericGuidanceSummary] = useState<GenericGuidanceSummary | null>(null);';
  const rdwState = 'const [rdwSummary, setRdwSummary] = useState<RdwTypeApprovalSummary | null>(null);';
  if (!ui.includes("setRdwSummary")) {
    if (!ui.includes(genericState)) fail("RDW UI summary state insertion anchor missing");
    ui = ui.replace(genericState, genericState + "\n  " + rdwState);
  }

  const tabsStart = ui.indexOf("const tabs:");
  const tabsEnd = ui.indexOf("\n];", tabsStart);
  if (tabsStart < 0 || tabsEnd < 0) fail("Research UI tabs array missing");
  if (!ui.includes('id: "rdw"')) ui = ui.slice(0, tabsEnd) + '\n  { id: "rdw", label: "Типовое одобрение ЕС", hint: "CC0 · RDW · не RU/ЕАЭС" },' + ui.slice(tabsEnd);

  if (!ui.includes("dataset=rdw-summary")) {
    const fetchAnchor = '    fetch("/api/local-research?dataset=generic-guidance-summary", { signal: current.signal, cache: "no-store" })';
    const fetchStart = ui.indexOf(fetchAnchor);
    const cleanup = fetchStart < 0 ? -1 : ui.indexOf("    return () => {", fetchStart);
    if (fetchStart < 0 || cleanup < 0) fail("RDW UI summary fetch insertion point missing");
    const fetchBlock = [
      '    fetch("/api/local-research?dataset=rdw-summary", { signal: current.signal, cache: "no-store" })',
      '      .then(async (response) => {',
      '        const payload = await response.json();',
      '        if (!response.ok || payload.status !== "ready_candidate_only") throw new Error(payload.error || "RDW candidate pack failed integrity verification.");',
      '        setRdwSummary(payload);',
      '      })',
      '      .catch((reason) => {',
      '        if (reason?.name !== "AbortError") setError(reason?.message || "RDW candidate pack is unavailable.");',
      '      });',
      ''
    ].join("\n");
    ui = ui.slice(0, cleanup) + fetchBlock + ui.slice(cleanup);
  }

  const statsMarker = '\n    </div>\n\n    <div className="research-boundary">';
  if (!ui.includes("rdwSummary?.counts?.vehicle_variants")) {
    const stats = '\n      <article className="research-stat"><small>RDW · варианты одобрения</small><strong>{formatNumber(rdwSummary?.counts?.vehicle_variants)}</strong><span>{formatNumber(rdwSummary?.counts?.engine_candidates)} engine · {formatNumber(rdwSummary?.counts?.transmission_candidates)} transmission candidates</span></article>' +
      '\n      <article className="research-stat"><small>RDW · связи строк</small><strong>{formatNumber(rdwSummary?.counts?.unique_source_row_pair_candidates)}</strong><span>{formatNumber(rdwSummary?.counts?.ambiguous_or_incomplete_pair_keys)} ambiguous/incomplete · candidate only</span></article>';
    ui = replaceText(ui, statsMarker, stats + statsMarker, "RDW statistics cards");
  }

  const boundaryMarker = '\n    </div>\n\n    <div className="research-tabs"';
  if (!ui.includes("RDW не является российским/ЕАЭС ОТТС")) {
    const note = '\n      {rdwSummary && <p>RDW не является российским/ЕАЭС ОТТС. Это только EU type-approval и наблюдения регистрации в Нидерландах; RDW.motorcode и RDW.codetypeversnellingsbak не являются заводскими кодами VAG. Связь строк источника не подтверждает VIN, поколение, модельный год, ECU или точную применимость и не является инструкцией по диагностике/ремонту.</p>}' + boundaryMarker;
    ui = replaceText(ui, boundaryMarker, note, "RDW scope boundary");
  }

  const placeholderFallback = ': "Марка, модель, ECU header, DID или сигнал…"';
  if (!ui.includes('dataset === "rdw" ? "Volkswagen, Golf, CAXA, e1*2007/46…')) {
    const placeholderStart = ui.indexOf('placeholder={dataset ===');
    const fallbackIndex = placeholderStart < 0 ? -1 : ui.indexOf(placeholderFallback, placeholderStart);
    if (fallbackIndex < 0) fail("RDW search placeholder fallback anchor missing");
    const replacement = ': dataset === "rdw" ? "Volkswagen, Golf, CAXA, e1*2007/46…" : "Марка, модель, ECU header, DID или сигнал…"';
    ui = ui.slice(0, fallbackIndex) + replacement + ui.slice(fallbackIndex + placeholderFallback.length);
  }

  const rdwCard = [
    '      {dataset === "rdw" && rows.map((row) => <article className="research-result" key={(row.typeApprovalNumber || "") + "-" + (row.variantCode || "") + "-" + (row.executionCode || "") + "-" + (row.revisionNumber || "")}>',
    '        <div className="research-result-top"><div><small>RDW · EU TYPE APPROVAL / NL REGISTRATION · CANDIDATE</small><h3>{row.make} {row.model}</h3></div><span className="research-candidate">КАНДИДАТ · НЕ VIN FITMENT</span></div>',
    '        <div className="research-data-grid">',
    '          <div><small>Номер типового одобрения</small><b>{row.typeApprovalNumber || "—"}</b></div>',
    '          <div><small>Variant / execution</small><b>{row.variantCode || "—"} / {row.executionCode || "—"}</b></div>',
    '          <div><small>Двигатель · namespace</small><b>{row.rdwMotorcode || "—"} · {row.engineCodeNamespace || "RDW.motorcode"}</b></div>',
    '          <div><small>Трансмиссия · namespace</small><b>{row.rdwTransmissionTypeCode || "—"} · {row.transmissionCodeNamespace || "RDW.codetypeversnellingsbak"}</b></div>',
    '          <div><small>Число передач из источника</small><b>{row.gearCountMin || "—"}–{row.gearCountMax || "—"}</b></div>',
    '          <div><small>Связь строк источника</small><b>{row.pairingStatus === "unique_source_rows_candidate" ? "Уникальная пара-кандидат" : "Неоднозначно / нет полной пары"}</b></div>',
    '          <div><small>Первая / последняя регистрация NL</small><b>{row.firstRegistrationSeen || "—"} / {row.lastRegistrationSeen || "—"}</b></div>',
    '          <div><small>Ревизия одобрения</small><b>{row.revisionNumber || "—"} · {row.revisionStartDate || "—"} — {row.revisionEndDate || "—"}</b></div>',
    '        </div>',
    '        <div className="research-warning-line">EU/NL source candidate only. Не российское/ЕАЭС ОТТС; RDW-коды не являются заводскими кодами VAG; не подтверждает VIN, поколение, модельный год, ECU или точную применимость. Не использовать как DTC-объяснение, test-plan, OEM-процедуру или основание для ремонта.</div>',
    '        <details className="research-details"><summary>Применимость и ограничения</summary><p>Статус {row.verificationStatus || "candidate"} · рынок {row.marketScope || "EU/NL"} · точность {row.applicabilityPrecision || "type_approval_variant_execution_candidate"} · source {row.sourceId || "rdw-vag-type-approval-cc0"} · ревизия {row.sourceRevision || "—"} · pairing confirmed: {String(row.pairingConfirmed === true)} · exact fitment: {String(row.exactVehicleFitment === true)} · RU/EAEU: {String(row.ruEaeuApplicability === true)} · VAG factory engine/gearbox code: {String(row.vagFactoryEngineCodeVerified === true)}/{String(row.vagFactoryGearboxCodeVerified === true)}</p></details>',
    '      </article>)}'
  ].join("\n");
  const resultsMarker = '\n    </div>}\n\n    {!rows.length';
  if (!ui.includes('dataset === "rdw" && rows.map')) ui = replaceText(ui, resultsMarker, "\n" + rdwCard + resultsMarker, "RDW result cards");

  const creditsEnd = '\n    </div>\n  </section>;';
  if (!ui.includes("rdwSummary.sourceSnapshotSha256")) {
    const credits = [
      '      {rdwSummary && <><p><a href={rdwSummary.sourceUrl} target="_blank" rel="noopener noreferrer">RDW Open Data</a> — отдельный CC0-1.0 набор для EU type-approval и Netherlands registration observations. Он не содержит российские/ЕАЭС ОТТС и не подтверждает заводские коды VAG или точную применимость.</p>',
      '        <details className="research-details"><summary>Лицензия и provenance RDW</summary>',
      '          <p>Лицензия {rdwSummary.dataLicense} · <a href={rdwSummary.licenseUrl} target="_blank" rel="noopener noreferrer">текст CC0-1.0</a> · ревизия {rdwSummary.sourceRevision} · рынок {(rdwSummary.marketScope || []).join(" · ")}</p>',
      '          <p>SHA SQLite {rdwSummary.databaseSha256} · SHA raw snapshot {rdwSummary.sourceSnapshotSha256} · SHA metadata bundle {rdwSummary.metadataBundleSha256} · SHA source lock {rdwSummary.sourceManifestSha256} · SHA source register {rdwSummary.sourceRegisterSha256 || "—"}</p>',
      '          <p>В базе {formatNumber(rdwSummary.counts?.vehicle_variants)} type-approval variants, {formatNumber(rdwSummary.counts?.engine_candidates)} RDW engine candidates, {formatNumber(rdwSummary.counts?.transmission_candidates)} RDW transmission candidates и {formatNumber(rdwSummary.counts?.unique_source_row_pair_candidates)} unique source-row pair candidates. Это не подтверждённые VAG engine/gearbox mappings.</p>',
      '          <p>{(rdwSummary.limitations || []).join(" ")}</p></details></>}'
    ].join("\n");
    ui = replaceText(ui, creditsEnd, "\n" + credits + creditsEnd, "RDW provenance footer");
  }
  writeText(uiFile, ui);

  const verifier = String.raw`"use strict";
const fs = require("node:fs");
const path = require("node:path");
const { createRdwTypeApprovalDb } = require("../lib/rdw-type-approval-db.cjs");
function fail(message) { throw new Error("[RDW verifier] " + message); }
function main() {
  const researchRoot = path.resolve(process.env.VAG_TECH_PRO_RESEARCH_DIR || path.join(__dirname, "..", "data", "research"));
  const packDir = path.join(researchRoot, "rdw-vag-type-approval-cc0");
  const db = createRdwTypeApprovalDb({
    packDir,
    lockPath: path.join(packDir, "source-lock.json"),
    registerPath: path.join(packDir, "source-register.json")
  });
  const summary = db.getSummary();
  if (summary.status !== "ready_candidate_only") fail(summary.error || "pack is not ready_candidate_only");
  if (summary.dataLicense !== "CC0-1.0" || summary.exactVehicleFitment !== false ||
      summary.ruEaeuApplicability !== false || summary.vagFactoryEngineCodeVerified !== false ||
      summary.vagFactoryGearboxCodeVerified !== false || summary.diagnosticExecutionAllowed !== false) {
    fail("summary rights/applicability boundary failed");
  }
  if (!summary.counts || summary.counts.vehicle_variants < 1 || summary.counts.engine_candidates < 1 ||
      summary.counts.transmission_candidates < 1) fail("required candidate tables are empty");
  for (const key of ["databaseSha256", "sourceSnapshotSha256", "metadataBundleSha256", "sourceManifestSha256", "sourceRegisterSha256"]) {
    if (!/^[a-f0-9]{64}$/.test(String(summary[key] || ""))) fail("missing or invalid provenance hash: " + key);
  }
  const result = db.search("VOLKSWAGEN", 20);
  if (result.status !== "ready_candidate_only" || !result.results.length) fail("offline RDW search returned no Volkswagen candidates");
  for (const row of result.results) {
    if (row.pairingConfirmed !== false || row.exactVehicleFitment !== false || row.ruEaeuApplicability !== false ||
        row.vagFactoryEngineCodeVerified !== false || row.vagFactoryGearboxCodeVerified !== false) {
      fail("candidate row was promoted beyond source-only applicability");
    }
    if (row.engineCodeNamespace !== "RDW.motorcode" || row.transmissionCodeNamespace !== "RDW.codetypeversnellingsbak") {
      fail("RDW source namespaces were lost");
    }
    if (!["EU_TYPE_APPROVAL", "NL_REGISTRATION_OBSERVATION"].includes(row.marketScope)) fail("unexpected RDW market scope");
  }
  const report = {
    schema_version: 1,
    status: "verified_candidate_only_offline",
    pack_id: "rdw-vag-type-approval-cc0",
    source_revision: summary.sourceRevision,
    market_scope: summary.marketScope,
    counts: summary.counts,
    database_sha256: summary.databaseSha256,
    source_snapshot_sha256: summary.sourceSnapshotSha256,
    metadata_bundle_sha256: summary.metadataBundleSha256,
    source_manifest_sha256: summary.sourceManifestSha256,
    source_register_sha256: summary.sourceRegisterSha256,
    offline_search_rows: result.results.length,
    exact_vehicle_fitment: false,
    ru_eaeu_applicability: false,
    vag_factory_engine_code_verified: false,
    vag_factory_gearbox_code_verified: false,
    diagnostic_execution_allowed: false
  };
  fs.writeFileSync(path.join(packDir, "desktop-integration-verification.json"), JSON.stringify(report, null, 2) + "\n", "utf8");
  process.stdout.write(JSON.stringify(report, null, 2) + "\n");
}
try { main(); } catch (error) { process.stderr.write((error.stack || error.message) + "\n"); process.exitCode = 1; }
`;
  const verifierPath = path.join(desktop, "scripts", "verify-rdw-type-approval.cjs");
  writeText(verifierPath, verifier);

  const packagePath = path.join(desktop, "package.json");
  const pkg = readJson(packagePath);
  if (!pkg.scripts?.["test:research"] || !pkg.scripts?.["verify:local-research"]) fail("Desktop research scripts missing");
  if (!pkg.scripts["test:research"].includes("rdw-type-approval-db.test.cjs")) {
    pkg.scripts["test:research"] += " tests/rdw-type-approval-db.test.cjs tests/rdw-type-approval-ui-contract.test.cjs";
  }
  if (!pkg.scripts["verify:local-research"].includes("verify-rdw-type-approval.cjs")) {
    pkg.scripts["verify:local-research"] += " && node scripts/verify-rdw-type-approval.cjs";
  }
  writeJson(packagePath, pkg);

  const dbTest = String.raw`"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const path = require("node:path");
const local = require("../lib/local-research-db.cjs");
const research = path.join(__dirname, "..", "data", "research");

test("RDW pack verifies as a separate CC0 EU/NL candidate source", () => {
  const summary = local.getRdwTypeApprovalSummary(research);
  assert.equal(summary.status, "ready_candidate_only");
  assert.equal(summary.dataLicense, "CC0-1.0");
  assert.ok(summary.counts.vehicle_variants > 0);
  assert.ok(summary.counts.engine_candidates > 0);
  assert.ok(summary.counts.transmission_candidates > 0);
  assert.equal(summary.exactVehicleFitment, false);
  assert.equal(summary.ruEaeuApplicability, false);
  assert.equal(summary.vagFactoryEngineCodeVerified, false);
  assert.equal(summary.vagFactoryGearboxCodeVerified, false);
  assert.equal(summary.diagnosticExecutionAllowed, false);
  for (const key of ["databaseSha256", "sourceSnapshotSha256", "metadataBundleSha256", "sourceManifestSha256", "sourceRegisterSha256"]) {
    assert.match(summary[key], /^[a-f0-9]{64}$/);
  }
});

test("RDW search preserves source namespaces and never claims exact fitment", () => {
  const rows = local.searchRdwTypeApprovalCandidates("VOLKSWAGEN", 20, research);
  assert.ok(rows.length > 0);
  for (const row of rows) {
    assert.equal(row.engineCodeNamespace, "RDW.motorcode");
    assert.equal(row.transmissionCodeNamespace, "RDW.codetypeversnellingsbak");
    assert.equal(row.pairingConfirmed, false);
    assert.equal(row.exactVehicleFitment, false);
    assert.equal(row.ruEaeuApplicability, false);
    assert.equal(row.vagFactoryEngineCodeVerified, false);
    assert.equal(row.vagFactoryGearboxCodeVerified, false);
    assert.ok(["EU_TYPE_APPROVAL", "NL_REGISTRATION_OBSERVATION"].includes(row.marketScope));
    assert.equal(row.applicabilityPrecision, "type_approval_variant_execution_candidate");
  }
});
`;
  writeText(path.join(desktop, "tests", "rdw-type-approval-db.test.cjs"), dbTest);

  const uiTest = String.raw`"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const root = path.join(__dirname, "..");

test("RDW appears only in a separate EU/NL candidate research tab", () => {
  const component = fs.readFileSync(path.join(root, "components", "local-research-catalog.tsx"), "utf8");
  const route = fs.readFileSync(path.join(root, "app", "api", "local-research", "route.ts"), "utf8");
  assert.match(component, /id: "rdw", label: "Типовое одобрение ЕС"/);
  assert.match(component, /RDW\.motorcode/);
  assert.match(component, /RDW\.codetypeversnellingsbak/);
  assert.match(component, /не является российским\/ЕАЭС ОТТС/);
  assert.match(component, /КАНДИДАТ · НЕ VIN FITMENT/);
  assert.match(component, /pairingConfirmed/);
  assert.match(route, /dataset === "rdw-summary"/);
  assert.match(route, /dataset === "rdw"/);
  assert.match(route, /searchRdwTypeApprovalCandidates/);
  assert.doesNotMatch(component, /RDW.*confirmed VAG engine\/gearbox/i);
});
`;
  writeText(path.join(desktop, "tests", "rdw-type-approval-ui-contract.test.cjs"), uiTest);

  const uiTestFile = path.join(desktop, "tests", "local-research-ui-contract.test.cjs");
  let uiContract = readText(uiTestFile);
  if (!uiContract.includes('id: "rdw", label: "Типовое одобрение ЕС"')) {
    uiContract += '\n\ntest("RDW type approval remains a separate EU/NL candidate-only source", () => {\n' +
      '  const component = fs.readFileSync(path.join(__dirname, "../components/local-research-catalog.tsx"), "utf8");\n' +
      '  assert.match(component, /id: "rdw", label: "Типовое одобрение ЕС"/);\n' +
      '  assert.match(component, /RDW\\.motorcode/);\n' +
      '  assert.match(component, /RDW\\.codetypeversnellingsbak/);\n' +
      '  assert.match(component, /не является российским\\/ЕАЭС ОТТС/);\n' +
      '});\n';
    writeText(uiTestFile, uiContract);
  }

  const lifePath = path.join(desktop, "scripts", "windows-installer-lifecycle.ps1");
  let life = readText(lifePath);
  if (!life.includes("api/local-research?dataset=rdw-summary")) {
    const checks = [
      '  # RDW CC0 data is an independent EU/NL candidate pack; it must work offline and must never be treated as RU/EAEU or exact VAG fitment.',
      '  $rdwSummary = Invoke-RestMethod -Uri "$baseUrl/api/local-research?dataset=rdw-summary" -TimeoutSec 30',
      '  if ($rdwSummary.status -ne "ready_candidate_only" -or $rdwSummary.dataLicense -ne "CC0-1.0" -or $rdwSummary.counts.vehicle_variants -lt 1 -or $rdwSummary.counts.engine_candidates -lt 1 -or $rdwSummary.counts.transmission_candidates -lt 1 -or $rdwSummary.ruEaeuApplicability -ne $false -or $rdwSummary.exactVehicleFitment -ne $false -or $rdwSummary.vagFactoryEngineCodeVerified -ne $false -or $rdwSummary.vagFactoryGearboxCodeVerified -ne $false) { throw "RDW offline summary or candidate-only boundary failed." }',
      '  $rdwRows = Invoke-RestMethod -Uri "$baseUrl/api/local-research?dataset=rdw&q=VOLKSWAGEN&limit=20" -TimeoutSec 30',
      '  if (@($rdwRows.rows).Count -lt 1 -or $rdwRows.rows[0].engineCodeNamespace -ne "RDW.motorcode" -or $rdwRows.rows[0].transmissionCodeNamespace -ne "RDW.codetypeversnellingsbak" -or $rdwRows.rows[0].pairingConfirmed -ne $false -or $rdwRows.rows[0].exactVehicleFitment -ne $false -or $rdwRows.rows[0].ruEaeuApplicability -ne $false) { throw "RDW offline candidate search or namespace boundary failed." }',
      '  if ($rdwRows.rows[0].vagFactoryEngineCodeVerified -ne $false -or $rdwRows.rows[0].vagFactoryGearboxCodeVerified -ne $false) { throw "RDW source codes were promoted to VAG factory codes." }',
      ''
    ].join("\n");
    const genericMarker = '  # generic_repair_guidance is a separate local SQLite pack';
    let insertion = life.indexOf(genericMarker);
    if (insertion < 0) {
      const guard = /if\s*\(\s*\$summary\.mode\s*-ne\s*["']offline_local_sqlite_admin["']\s*\)\s*\{/;
      const match = guard.exec(life);
      if (match) {
        const open = life.indexOf("{", match.index);
        let depth = 0;
        for (let i = open; i < life.length; i += 1) {
          if (life[i] === "{") depth += 1;
          else if (life[i] === "}") {
            depth -= 1;
            if (depth === 0) { insertion = i + 1; break; }
          }
        }
      }
    }
    if (insertion < 0) fail("Offline lifecycle RDW insertion point missing");
    life = life.slice(0, insertion) + "\n" + checks + life.slice(insertion);
    writeText(lifePath, life);
  }

  const env = Object.assign({}, process.env, { VAG_TECH_PRO_RESEARCH_DIR: research });
  run("node", ["--check", path.join(desktop, "lib", "rdw-type-approval-db.cjs")], desktop, env);
  run("node", ["--check", coreFile], desktop, env);
  run("node", ["scripts/verify-rdw-type-approval.cjs"], desktop, env);
  run("node", ["--test", "tests/rdw-type-approval-db.test.cjs", "tests/rdw-type-approval-ui-contract.test.cjs"], desktop, env);

  const report = readJson(path.join(target, "desktop-integration-verification.json"));
  if (report.status !== "verified_candidate_only_offline" || report.database_sha256 !== manifest.database_sha256 ||
      report.source_register_sha256 !== manifest.source_register_sha256) fail("RDW desktop integration report mismatch");
  console.log(JSON.stringify({
    status: "verified_candidate_only_desktop_integration",
    pack_id: PACK_ID,
    source_revision: manifest.source_revision,
    counts: manifest.counts,
    database_sha256: manifest.database_sha256,
    source_snapshot_sha256: manifest.source_snapshot_sha256,
    metadata_bundle_sha256: manifest.metadata_bundle_sha256,
    source_manifest_sha256: manifest.source_manifest_sha256,
    source_register_sha256: manifest.source_register_sha256,
    market_scope: manifest.market_scope,
    exact_vehicle_fitment: false,
    ru_eaeu_applicability: false,
    vag_factory_engine_code_verified: false,
    vag_factory_gearbox_code_verified: false,
    diagnostic_execution_allowed: false
  }, null, 2));
}

try { main(); }
catch (error) {
  process.stderr.write("RDW desktop integration failed: " + (error.stack || error.message) + "\n");
  process.exitCode = 1;
}

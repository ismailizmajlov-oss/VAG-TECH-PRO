"use strict";

const fs = require("node:fs");
const path = require("node:path");
const crypto = require("node:crypto");

const ROOT = path.resolve(process.cwd(), "desktop-source");
const RESEARCH = path.join(ROOT, "data", "research");
const PACK_ID = "mechanicdb-vag-dtc-candidates-odbl";
const PACK_DIR = path.join(RESEARCH, PACK_ID);
const ROOT_MANIFEST_PATH = path.join(RESEARCH, "manifest.json");
const PACK_MANIFEST_PATH = path.join(PACK_DIR, "manifest.json");
const DISPLAY_STATUS = "candidate_reference_visible_separate_namespace";
const PRODUCT_ELIGIBILITY = "candidate_reference_only_visible_separate_namespace";
const WARNING = "Community manufacturer-labelled candidate only; not OEM-confirmed and not confirmed as VAG-specific for any exact configuration. No model, generation, year, engine, gearbox, ECU, PR-code, VIN or market fitment. Do not use as a diagnostic test, executable command, repair instruction or OEM part mapping.";

function fail(message) { throw new Error(`[run59] ${message}`); }
function readText(file) {
  if (!fs.existsSync(file)) fail(`Required file missing: ${path.relative(ROOT, file)}`);
  return fs.readFileSync(file, "utf8").replace(/\r\n/g, "\n");
}
function writeText(file, value) { fs.writeFileSync(file, value.replace(/\r\n/g, "\n"), "utf8"); }
function replaceExactly(file, before, after, label) {
  const current = readText(file);
  if (current.includes(after)) return false;
  const count = current.split(before).length - 1;
  if (count !== 1) fail(`${label}: expected exactly one anchor, found ${count}`);
  writeText(file, current.replace(before, after));
  return true;
}
function replaceAllChecked(file, before, after, label, minimum = 1) {
  const current = readText(file);
  if (!current.includes(before)) {
    if (current.includes(after)) return 0;
    fail(`${label}: anchor not found`);
  }
  const count = current.split(before).length - 1;
  if (count < minimum) fail(`${label}: expected at least ${minimum} matches, found ${count}`);
  writeText(file, current.split(before).join(after));
  return count;
}
function readJson(file) { return JSON.parse(readText(file)); }
function writeJson(file, value) { fs.writeFileSync(file, `${JSON.stringify(value, null, 2)}\n`, "utf8"); }
function sha256(bytes) { return crypto.createHash("sha256").update(bytes).digest("hex"); }
function physicalLines(buffer) {
  const lines = [];
  let start = 0;
  for (let i = 0; i < buffer.length; i += 1) {
    if (buffer[i] === 0x0a) {
      lines.push(buffer.subarray(start, i + 1));
      start = i + 1;
    }
  }
  if (start < buffer.length) lines.push(buffer.subarray(start));
  return lines;
}
function updateLimitations(list) {
  if (!Array.isArray(list)) return list;
  return list.map((item) => item === "Records remain hidden pending independent technical review; no diagnostic execution, test plan, repair procedure or OEM part mapping."
    ? "Records are shown only as source-labelled candidates in a separate research tab pending independent technical review; no exact vehicle/ECU fitment, diagnostic execution, test plan, repair procedure or OEM part mapping."
    : item);
}

if (!fs.existsSync(ROOT_MANIFEST_PATH) || !fs.existsSync(PACK_MANIFEST_PATH)) fail("Research root and MechanicDB pack manifests must exist before this patch");
const rootManifest = readJson(ROOT_MANIFEST_PATH);
const packManifest = readJson(PACK_MANIFEST_PATH);
const rootPack = rootManifest.packs?.find((pack) => pack.id === PACK_ID);
if (!rootPack) fail("MechanicDB pack is not registered in the research root manifest");
if (packManifest.data_license !== "ODbL-1.0" || packManifest.rights_status !== "approved_by_published_license" ||
    packManifest.commercial_use_allowed_under_odbl !== true || packManifest.display_allowed !== true ||
    packManifest.offline_cache_allowed !== true || packManifest.redistribution_allowed_under_odbl !== true ||
    packManifest.share_alike_required !== true || packManifest.attribution_required !== true) {
  fail("Published ODbL rights evidence is incomplete; candidate browser will not be enabled");
}
if (packManifest.verification_status !== "community_reference_unverified" || packManifest.market_scope !== "UNKNOWN" ||
    packManifest.applicability_precision !== "manufacturer_make_candidate" || packManifest.exact_vehicle_fitment !== false ||
    packManifest.ecu_fitment !== false || packManifest.pr_code_fitment !== false || packManifest.diagnostic_execution_allowed !== false ||
    packManifest.repair_procedures_included !== false || packManifest.oem_part_numbers_included !== false) {
  fail("MechanicDB candidate-only safety boundary changed; refusing to expose the pack");
}
if (packManifest.counts?.manufacturer_controlled_candidates !== 2 || packManifest.counts?.audi_candidates !== 1 ||
    packManifest.counts?.volkswagen_candidates !== 1 || packManifest.counts?.generic_dtc_rows !== 0) {
  fail("MechanicDB candidate counts or namespace changed; requires a new technical review");
}

const policy = {
  status: DISPLAY_STATUS,
  purpose: "read_only_research_reference_only",
  namespace: "manufacturer_controlled_candidate",
  exposed_fields: ["dtc_code", "oem_make", "system_category", "fault_family", "short_description", "source_revision", "source_line_no", "source_line_sha256", "source_file_sha256"],
  excluded_fields: ["detailed_technical_explanation", "repair_actions", "test_plan", "ecu_fitment", "vehicle_fitment", "pr_code_fitment", "oem_part_mapping"],
  exact_vehicle_fitment: false,
  vag_oem_confirmation: false,
  diagnostic_execution_allowed: false,
  repair_procedures_included: false,
  oem_part_numbers_included: false,
  warning: WARNING,
};

packManifest.display_status = DISPLAY_STATUS;
packManifest.product_eligibility = PRODUCT_ELIGIBILITY;
packManifest.display_policy = policy;
packManifest.limitations = updateLimitations(packManifest.limitations);
writeJson(PACK_MANIFEST_PATH, packManifest);
rootPack.display_status = DISPLAY_STATUS;
rootPack.review_status = "community_reference_unverified";
rootPack.display_policy = policy;
rootPack.limitations = updateLimitations(rootPack.limitations);
rootPack.source_manifest_sha256 = sha256(fs.readFileSync(PACK_MANIFEST_PATH));
writeJson(ROOT_MANIFEST_PATH, rootManifest);

const coreDbFile = path.join(ROOT, "lib", "local-research-db.cjs");
replaceExactly(coreDbFile,
  'scope: "Two Audi/Volkswagen make-labelled community DTC candidates; market UNKNOWN; hidden pending technical review",',
  'scope: "Two Audi/Volkswagen make-labelled community DTC candidates; visible only in a separate research tab; market UNKNOWN; not OEM-confirmed",',
  "MechanicDB scope");
replaceAllChecked(coreDbFile, '"hidden_pending_technical_review"', `"${DISPLAY_STATUS}"`, "MechanicDB runtime display status", 3);
replaceExactly(coreDbFile,
  'mechanicPackManifest.display_status !== "candidate_reference_visible_separate_namespace" || mechanicPackManifest.market_scope !== "UNKNOWN" ||',
  'mechanicPackManifest.display_status !== "candidate_reference_visible_separate_namespace" || mechanicPackManifest.product_eligibility !== "candidate_reference_only_visible_separate_namespace" || mechanicPackManifest.display_policy?.exact_vehicle_fitment !== false || mechanicPackManifest.display_policy?.vag_oem_confirmation !== false || mechanicPackManifest.display_policy?.diagnostic_execution_allowed !== false || mechanicPackManifest.market_scope !== "UNKNOWN" ||',
  "MechanicDB summary display-policy gate");
replaceExactly(coreDbFile,
  'mechanicDbManifest.share_alike_required !== true || mechanicDbManifest.attribution_required !== true || mechanicDbManifest.display_status !== "candidate_reference_visible_separate_namespace" ||',
  'mechanicDbManifest.share_alike_required !== true || mechanicDbManifest.attribution_required !== true || mechanicDbManifest.display_status !== "candidate_reference_visible_separate_namespace" || mechanicDbManifest.review_status !== "community_reference_unverified" ||',
  "MechanicDB root manifest review-status gate");
replaceExactly(coreDbFile,
  'kind: "manufacturer_controlled_dtc_candidates_hidden",',
  'kind: "manufacturer_labelled_dtc_candidates_separate_namespace",',
  "MechanicDB summary kind");
replaceExactly(coreDbFile,
  'note: "Two make-labelled community candidates are stored in a separate ODbL database and remain hidden pending independent technical review. No exact vehicle/ECU fitment, test plan, repair procedure or OEM part mapping.",',
  `note: "Two make-labelled community candidates are visible only in a separate research tab. They remain community_reference_unverified; no exact vehicle/ECU fitment, diagnostic execution, test plan, repair procedure or OEM part mapping. ${WARNING}",`,
  "MechanicDB summary note");

const candidateFunction = String.raw`
function searchMechanicDbCandidates(query, limit = 25, root) {
  const q = validateQuery(query);
  const pack = verifyPackDatabaseHash(root, PACKS.mechanicdb.id, PACKS.mechanicdb.file);
  for (const [fileField, hashField] of [
    ["license_file", "license_file_sha256"],
    ["upstream_license_file", "upstream_license_file_sha256"],
    ["source_manifest_file", "source_manifest_sha256"],
    ["attribution_file", "attribution_sha256"],
    ["source_file", "source_file_sha256"],
    ["sources_file", "sources_file_sha256"],
    ["data_dictionary_file", "data_dictionary_sha256"],
    ["sha256sums_file", "sha256sums_sha256"],
  ]) verifyPackFileHash(root, PACKS.mechanicdb.id, fileField, hashField);

  const researchRoot = getResearchRoot(root);
  const packManifest = JSON.parse(fs.readFileSync(path.join(researchRoot, PACKS.mechanicdb.manifest), "utf8"));
  if (pack.display_status !== "candidate_reference_visible_separate_namespace" || pack.review_status !== "community_reference_unverified" ||
      pack.source_snapshot_sha256 !== packManifest.source_snapshot_sha256 ||
      packManifest.display_status !== "candidate_reference_visible_separate_namespace" ||
      packManifest.product_eligibility !== "candidate_reference_only_visible_separate_namespace" ||
      packManifest.verification_status !== "community_reference_unverified" ||
      packManifest.data_license !== "ODbL-1.0" || packManifest.rights_status !== "approved_by_published_license" ||
      packManifest.market_scope !== "UNKNOWN" || packManifest.applicability_precision !== "manufacturer_make_candidate" ||
      packManifest.exact_vehicle_fitment !== false || packManifest.ecu_fitment !== false || packManifest.pr_code_fitment !== false ||
      packManifest.diagnostic_execution_allowed !== false || packManifest.repair_procedures_included !== false ||
      packManifest.oem_part_numbers_included !== false) {
    throw new Error("MechanicDB candidate browser failed its display, license or non-fitment gate");
  }

  const sourceRelative = "upstream/dtc_codes.csv";
  const sourcePath = path.join(researchRoot, PACKS.mechanicdb.id, sourceRelative);
  const sourceBytes = fs.readFileSync(sourcePath);
  const sourceFileSha256 = crypto.createHash("sha256").update(sourceBytes).digest("hex");
  if (sourceBytes.length !== packManifest.source_files?.["upstream/dtc_codes.csv"]?.byte_size ||
      sourceFileSha256 !== pack.source_file_sha256 || sourceFileSha256 !== packManifest.source_files?.["upstream/dtc_codes.csv"]?.sha256) {
    throw new Error("MechanicDB source CSV size or SHA-256 mismatch");
  }
  const lines = [];
  let lineStart = 0;
  for (let index = 0; index < sourceBytes.length; index += 1) {
    if (sourceBytes[index] === 0x0a) {
      lines.push(sourceBytes.subarray(lineStart, index + 1));
      lineStart = index + 1;
    }
  }
  if (lineStart < sourceBytes.length) lines.push(sourceBytes.subarray(lineStart));

  const db = openReadOnly(root, PACKS.mechanicdb.file);
  try {
    const gate = db.prepare(\`SELECT
      count(*) AS total,
      sum(CASE WHEN namespace!='manufacturer_controlled_candidate' THEN 1 ELSE 0 END) AS generic_rows,
      sum(CASE WHEN vehicle_fitment_claim!=0 OR ecu_fitment_claim!=0 OR pr_code_claim!=0 OR diagnostic_execution_allowed!=0 OR repair_procedure_included!=0 OR oem_part_number_included!=0 THEN 1 ELSE 0 END) AS unsafe_rows
      FROM dtc_candidates\`).get();
    if (gate.total !== 2 || gate.generic_rows !== 0 || gate.unsafe_rows !== 0) throw new Error("MechanicDB candidate-only row-count/namespace gate failed");
    const pattern = likePattern(q);
    const rows = db.prepare(\`
      SELECT dtc_code, oem_make, system_category, fault_family, short_description,
        namespace, verification_status, market_scope, applicability_precision,
        vehicle_fitment_claim, ecu_fitment_claim, pr_code_claim, diagnostic_execution_allowed,
        repair_procedure_included, oem_part_number_included, source_file, source_line_no,
        source_line_sha256, source_file_sha256, source_revision
      FROM dtc_candidates
      WHERE namespace='manufacturer_controlled_candidate'
        AND verification_status='community_reference_unverified'
        AND market_scope='UNKNOWN'
        AND applicability_precision='manufacturer_make_candidate'
        AND vehicle_fitment_claim=0 AND ecu_fitment_claim=0 AND pr_code_claim=0
        AND diagnostic_execution_allowed=0 AND repair_procedure_included=0 AND oem_part_number_included=0
        AND (dtc_code LIKE ? ESCAPE '\\'
          OR oem_make LIKE ? ESCAPE '\\'
          OR system_category LIKE ? ESCAPE '\\'
          OR fault_family LIKE ? ESCAPE '\\'
          OR short_description LIKE ? ESCAPE '\\')
      ORDER BY oem_make, dtc_code
      LIMIT ?
    \`).all(pattern, pattern, pattern, pattern, pattern, clampLimit(limit));

    return rows.map((row) => {
      const line = lines[row.source_line_no - 1];
      if (!line || crypto.createHash("sha256").update(line).digest("hex") !== row.source_line_sha256 ||
          row.source_file !== sourceRelative || row.source_file_sha256 !== sourceFileSha256 ||
          row.source_revision !== packManifest.source_revision) {
        throw new Error("MechanicDB row provenance mismatch for " + row.oem_make + " " + row.dtc_code);
      }
      const evidence = packManifest.source_line_evidence?.find((item) => item.oem_make === row.oem_make &&
        item.dtc_code === row.dtc_code && item.source_file === row.source_file &&
        item.source_line_no === row.source_line_no && item.source_line_sha256 === row.source_line_sha256);
      if (!evidence) throw new Error("MechanicDB manifest line evidence missing for " + row.oem_make + " " + row.dtc_code);
      const lineText = line.toString("utf8").replace(/\r?\n$/, "").replace(/^\uFEFF/, "");
      const fields = lineText.split("|");
      if (fields[1] !== row.dtc_code || fields[4] !== row.oem_make) {
        throw new Error("MechanicDB CSV row identity mismatch for " + row.oem_make + " " + row.dtc_code);
      }
      return {
        code: row.dtc_code,
        make: row.oem_make,
        category: row.system_category,
        faultFamily: row.fault_family,
        title: row.short_description,
        descriptionStatus: "source_label_unverified",
        namespace: row.namespace,
        reviewStatus: row.verification_status,
        displayStatus: packManifest.display_status,
        marketScope: row.market_scope,
        applicabilityPrecision: row.applicability_precision,
        exactFitment: false,
        ecuFitment: false,
        prCodeFitment: false,
        diagnosticExecutionAllowed: false,
        repairProcedureIncluded: false,
        oemPartNumberIncluded: false,
        sourceRevision: row.source_revision,
        sourceFile: row.source_file,
        sourceLineNo: row.source_line_no,
        sourceLineSha256: row.source_line_sha256,
        sourceFileSha256,
        sourceSnapshotSha256: packManifest.source_snapshot_sha256,
        sourceManifestSha256: pack.source_manifest_sha256,
        databaseSha256: pack.database_sha256,
        license: packManifest.data_license,
        upstreamLicense: packManifest.upstream_license,
        documentationLicense: packManifest.documentation_license,
        sourceUrl: safeHttpsUrl(packManifest.source_repository),
        sourceFileUrl: safeHttpsUrl(packManifest.source_files?.["upstream/dtc_codes.csv"]?.source_url),
        attribution: fs.readFileSync(path.join(researchRoot, PACKS.mechanicdb.attribution), "utf8").trim(),
        warning: ${JSON.stringify(WARNING)},
      };
    });
  } finally {
    db.close();
  }
}

`.replaceAll("\\`", "`");
replaceExactly(coreDbFile, "function searchVehiclesDbCandidates(query, limit = 25, root) {", `${candidateFunction}function searchVehiclesDbCandidates(query, limit = 25, root) {`, "MechanicDB candidate search insertion");
replaceExactly(coreDbFile, "  searchUdsSignals,\n  validateQuery,", "  searchUdsSignals,\n  searchMechanicDbCandidates,\n  validateQuery,", "MechanicDB candidate search export");

const typesFile = path.join(ROOT, "lib", "local-research-db.d.cts");
replaceExactly(typesFile,
  "export function searchUdsSignals(query: string, limit?: number, root?: string): Array<Record<string, unknown>>;\n",
  "export function searchUdsSignals(query: string, limit?: number, root?: string): Array<Record<string, unknown>>;\nexport function searchMechanicDbCandidates(query: string, limit?: number, root?: string): Array<Record<string, unknown>>;\n",
  "MechanicDB TypeScript declaration");

const routeFile = path.join(ROOT, "app", "api", "local-research", "route.ts");
let routeSource = readText(routeFile);
if (!routeSource.includes("localResearch.searchMechanicDbCandidates")) {
  const unknownDatasetBranch = '    else return Response.json({ error: "Неизвестный локальный справочник."';
  const unknownDatasetIndex = routeSource.indexOf(unknownDatasetBranch);
  if (unknownDatasetIndex < 0) fail("Research API route unknown-dataset branch anchor is missing");
  const routeInsert = '    else if (dataset === "mechanicdb") rows = localResearch.searchMechanicDbCandidates(query, limit);\n';
  routeSource = routeSource.slice(0, unknownDatasetIndex) + routeInsert + routeSource.slice(unknownDatasetIndex);
  writeText(routeFile, routeSource);
}

const uiFile = path.join(ROOT, "components", "local-research-catalog.tsx");
const uiDatasetSource = readText(uiFile);
const uiDatasetMatch = uiDatasetSource.match(/type Dataset = ([^;]+);/);
if (!uiDatasetMatch) fail("MechanicDB dataset type declaration is missing");
if (!uiDatasetMatch[1].split("|").some((part) => part.trim() === '"mechanicdb"')) {
  const updatedDatasetSource = uiDatasetSource.replace(uiDatasetMatch[0], `type Dataset = ${uiDatasetMatch[1]} | "mechanicdb";`);
  writeText(uiFile, updatedDatasetSource);
}
let uiRowSource = readText(uiFile);
const rowTypeStart = uiRowSource.indexOf("type ResearchRow = {");
if (rowTypeStart < 0) fail("MechanicDB research row type declaration is missing");
const rowTypeEnd = uiRowSource.indexOf("\n};", rowTypeStart);
if (rowTypeEnd < 0) fail("MechanicDB research row type closing brace is missing");
const rowTypeText = uiRowSource.slice(rowTypeStart, rowTypeEnd);
const requiredResearchRowFields = [
  "faultFamily?: string;",
  "descriptionStatus?: string;",
  "namespace?: string;",
  "sourceLineNo?: number;",
  "sourceLineSha256?: string;",
  "sourceFileSha256?: string;",
  "sourceSnapshotSha256?: string;",
  "exactFitment?: boolean;",
  "ecuFitment?: boolean;",
  "prCodeFitment?: boolean;",
  "diagnosticExecutionAllowed?: boolean;",
  "repairProcedureIncluded?: boolean;",
  "oemPartNumberIncluded?: boolean;",
  "sourceFile?: string;",
  "sourceFileUrl?: string;",
  "upstreamLicense?: string;",
  "documentationLicense?: string;",
];
const missingResearchRowFields = requiredResearchRowFields.filter((field) => !rowTypeText.includes(field));
if (missingResearchRowFields.length) {
  uiRowSource = uiRowSource.slice(0, rowTypeEnd) + "\n" + missingResearchRowFields.map((field) => "  " + field).join("\n") + uiRowSource.slice(rowTypeEnd);
  writeText(uiFile, uiRowSource);
}
replaceExactly(uiFile,
  '  { id: "dtc", label: "Общие DTC", hint: "CC0 · SAE/ISO, не VAG-specific" },\n',
  '  { id: "dtc", label: "Общие DTC", hint: "CC0 · SAE/ISO, не VAG-specific" },\n  { id: "mechanicdb", label: "DTC · кандидаты марок", hint: "ODbL · community · не OEM" },\n',
  "MechanicDB research tab");
replaceExactly(uiFile,
  'placeholder={dataset === "vehicles" ? "Модель, поколение или описание двигателя…" : dataset === "vehiclesdb" ? "Марка или модель… например Golf" : dataset === "dtc" ? "Код DTC или описание… например P0300" : dataset === "pids" ? "PID, режим или название параметра…" : "Марка, модель, ECU header, DID или сигнал…"}',
  'placeholder={dataset === "vehicles" ? "Модель, поколение или описание двигателя…" : dataset === "vehiclesdb" ? "Марка или модель… например Golf" : dataset === "dtc" ? "Код DTC или описание… например P0300" : dataset === "mechanicdb" ? "P1128, P3000, Audi, Volkswagen…" : dataset === "pids" ? "PID, режим или название параметра…" : "Марка, модель, ECU header, DID или сигнал…"}',
  "MechanicDB search placeholder");
replaceExactly(uiFile,
  '      {mechanicDb && <p>Отдельно хранится {formatNumber(mechanicDb.counts.manufacturerCandidates)} make-labelled DTC-кандидата MechanicDB в самостоятельной базе ODbL-1.0. Записи скрыты до независимой технической проверки; рынок UNKNOWN, точная применимость к модели, поколению, двигателю, КПП и ECU отсутствует. Эти записи не входят в поиск общих DTC и не являются подтверждёнными VAG-specific кодами.</p>}',
  '      {mechanicDb && <p>{formatNumber(mechanicDb.counts.manufacturerCandidates)} make-labelled DTC-кандидата MechanicDB доступны только в отдельной исследовательской вкладке. Это community reference, а не OEM-подтверждение: рынок UNKNOWN, точная применимость к модели, поколению, двигателю, КПП и ECU отсутствует. Они не входят в поиск общих DTC и не являются подтверждёнными VAG-specific кодами.</p>}',
  "MechanicDB boundary note");
replaceExactly(uiFile,
  '      {dataset === "dtc" && rows.map((row) => <article className="research-result" key={row.code}>',
  `      {dataset === "mechanicdb" && rows.map((row) => <article className="research-result" key={row.make + "-" + row.code}>
        <div className="research-result-top"><div><small>MECHANICDB · MANUFACTURER-LABELLED COMMUNITY CANDIDATE</small><h3 className="research-code">{row.code} · {row.make}</h3></div><span className="research-candidate">НЕ OEM-ПОДТВЕРЖДЁН</span></div>
        <div className="research-data-grid"><div><small>Категория из источника</small><b>{row.category || "—"}</b></div><div><small>Группа неисправности из источника</small><b>{row.faultFamily || "—"}</b></div><div><small>Статус / рынок</small><b>{row.reviewStatus} · {row.marketScope}</b></div></div>
        <p className="research-description"><b>Описание из источника (не проверено):</b> {row.title}</p>
        <div className="research-warning-line">{row.warning}</div>
        <details className="research-details"><summary>Построчная provenance</summary><p>Ревизия {row.sourceRevision} · файл {row.sourceFile} · строка {row.sourceLineNo} · SHA строки {row.sourceLineSha256} · SHA файла {row.sourceFileSha256} · SHA БД {row.databaseSha256} · SHA манифеста {row.sourceManifestSha256} · SHA снимка {row.sourceSnapshotSha256}</p></details>
        <div className="research-source"><span>Источник: MechanicDB · ODbL-1.0 · upstream code spine MIT · share-alike и атрибуция обязательны</span>{row.sourceFileUrl && <a href={row.sourceFileUrl} target="_blank" rel="noopener noreferrer">Открыть исходную строку</a>}</div>
      </article>)}

      {dataset === "dtc" && rows.map((row) => <article className="research-result" key={row.code}>`,
  "MechanicDB research result card");
replaceExactly(uiFile,
  'Два make-labelled кандидата остаются скрыты до технической проверки; нет точной применимости, test-plan, ремонта или OEM-деталей.',
  'Два make-labelled кандидата отображаются только в отдельной вкладке как community reference; независимая техническая проверка не завершена, точной применимости, test-plan, ремонта или OEM-деталей нет.',
  "MechanicDB attribution note");

const dbTestFile = path.join(ROOT, "tests", "local-research-db.test.cjs");
replaceExactly(dbTestFile,
  '  assert.equal(mechanicDb.displayStatus, "hidden_pending_technical_review");',
  `  assert.equal(mechanicDb.displayStatus, "${DISPLAY_STATUS}");`,
  "MechanicDB summary test status");
replaceExactly(dbTestFile,
  'test("make-labelled MechanicDB DTC candidates never leak into the generic SAE/ISO search", () => {\n  assert.deepEqual(local.searchGenericDtcs("P3000", 5, root), []);\n  assert.deepEqual(local.searchGenericDtcs("P1128", 5, root), []);\n  assert.equal(typeof local.searchMechanicDbDtcs, "undefined");\n});',
  `test("MechanicDB manufacturer-labelled candidates are visible only in their separate research namespace", () => {
  assert.deepEqual(local.searchGenericDtcs("P3000", 5, root), []);
  assert.deepEqual(local.searchGenericDtcs("P1128", 5, root), []);
  assert.equal(local.searchGenericDtcs("P0300", 1, root)[0].code, "P0300");
  const vw = local.searchMechanicDbCandidates("P1128", 5, root);
  const audi = local.searchMechanicDbCandidates("P3000", 5, root);
  assert.equal(vw.length, 1);
  assert.equal(audi.length, 1);
  for (const row of [...vw, ...audi]) {
    assert.equal(row.namespace, "manufacturer_controlled_candidate");
    assert.equal(row.reviewStatus, "community_reference_unverified");
    assert.equal(row.displayStatus, "${DISPLAY_STATUS}");
    assert.equal(row.marketScope, "UNKNOWN");
    assert.equal(row.applicabilityPrecision, "manufacturer_make_candidate");
    assert.equal(row.exactFitment, false);
    assert.equal(row.ecuFitment, false);
    assert.equal(row.prCodeFitment, false);
    assert.equal(row.diagnosticExecutionAllowed, false);
    assert.equal(row.repairProcedureIncluded, false);
    assert.equal(row.oemPartNumberIncluded, false);
    assert.match(row.sourceLineSha256, /^[a-f0-9]{64}$/);
    assert.match(row.sourceFileSha256, /^[a-f0-9]{64}$/);
    assert.match(row.sourceSnapshotSha256, /^[a-f0-9]{64}$/);
    assert.match(row.sourceManifestSha256, /^[a-f0-9]{64}$/);
    assert.equal(Object.hasOwn(row, "detailedTechnicalExplanation"), false);
  }
  assert.equal(vw[0].make, "Volkswagen");
  assert.equal(vw[0].sourceLineNo, 91);
  assert.equal(audi[0].make, "Audi");
  assert.equal(audi[0].sourceLineNo, 77);
});`,
  "MechanicDB separate namespace test");

const uiTestFile = path.join(ROOT, "tests", "local-research-ui-contract.test.cjs");
replaceExactly(uiTestFile,
  '  assert.doesNotMatch(component, /id: "mechanicdb"/);',
  '  assert.match(component, /id: "mechanicdb", label: "DTC · кандидаты марок"/);\n  assert.match(component, /НЕ OEM-ПОДТВЕРЖДЁН/);\n  assert.match(component, /не являются подтверждёнными VAG-specific кодами/);\n  assert.doesNotMatch(component, /detailedTechnicalExplanation/);\n  const route = fs.readFileSync(path.join(__dirname, "..", "app", "api", "local-research", "route.ts"), "utf8");\n  assert.match(route, /dataset === "mechanicdb"/);\n  assert.match(route, /searchMechanicDbCandidates/);',
  "MechanicDB UI contract");

const verifierFile = path.join(ROOT, "scripts", "verify-local-research-packs.cjs");
replaceExactly(verifierFile,
  'mechanicSnapshot.database_sha256 === mechanicdb.database_sha256 && mechanicSnapshot.source_snapshot_sha256 === mechanicdb.source_snapshot_sha256 && mechanicSnapshot.display_status === "hidden_pending_technical_review", "MechanicDB pack hash or hidden review status mismatch");',
  `mechanicSnapshot.database_sha256 === mechanicdb.database_sha256 && mechanicSnapshot.source_snapshot_sha256 === mechanicdb.source_snapshot_sha256 && mechanicSnapshot.display_status === "${DISPLAY_STATUS}" && mechanicSnapshot.product_eligibility === "${PRODUCT_ELIGIBILITY}" && mechanicSnapshot.display_policy?.exact_vehicle_fitment === false && mechanicSnapshot.display_policy?.vag_oem_confirmation === false && mechanicSnapshot.display_policy?.diagnostic_execution_allowed === false, "MechanicDB pack hash or candidate-only display policy mismatch");`,
  "MechanicDB pack verifier display policy");
replaceExactly(verifierFile,
  '      unsafeRows: count(mechanicDb, "SELECT count(*) AS n FROM dtc_candidates WHERE vehicle_fitment_claim!=0 OR ecu_fitment_claim!=0 OR pr_code_claim!=0 OR diagnostic_execution_allowed!=0 OR repair_procedure_included!=0 OR oem_part_number_included!=0"),\n',
  '      unsafeRows: count(mechanicDb, "SELECT count(*) AS n FROM dtc_candidates WHERE vehicle_fitment_claim!=0 OR ecu_fitment_claim!=0 OR pr_code_claim!=0 OR diagnostic_execution_allowed!=0 OR repair_procedure_included!=0 OR oem_part_number_included!=0"),\n      displayStatus: mechanicSnapshot.display_status,\n      reviewStatus: mechanicSnapshot.verification_status,\n',
  "MechanicDB verifier status fields");

const packTestFile = path.join(ROOT, "tests", "local-research-packs.test.cjs");
replaceExactly(packTestFile,
  '  assert.equal(result.mechanicdb_vag_dtc_candidates.unsafeRows, 0);',
  '  assert.equal(result.mechanicdb_vag_dtc_candidates.unsafeRows, 0);\n  assert.equal(result.mechanicdb_vag_dtc_candidates.displayStatus, "' + DISPLAY_STATUS + '");\n  assert.equal(result.mechanicdb_vag_dtc_candidates.reviewStatus, "community_reference_unverified");',
  "MechanicDB pack verifier test");

// Keep any separate pack-integration test aligned with the explicit candidate-only display policy.
const integrationTest = path.join(ROOT, "tests", "mechanicdb-pack-integration.test.cjs");
if (fs.existsSync(integrationTest)) {
  replaceAllChecked(integrationTest, '"hidden_pending_technical_review"', `"${DISPLAY_STATUS}"`, "MechanicDB integration test status", 1);
  replaceAllChecked(integrationTest, "hidden pending technical review", "visible only in a separate research tab pending independent technical review", "MechanicDB integration test wording", 1);
}

const readmeFile = path.join(RESEARCH, "README.md");
replaceExactly(readmeFile,
  '| MechanicDB Audi/VW DTC sample | ODbL-1.0; upstream DTC code spine MIT | 2 make-labelled candidate rows (1 Audi, 1 Volkswagen) | Separate SQLite; hidden pending technical review; market UNKNOWN; no exact vehicle/ECU fitment, test plans, repairs or OEM parts; attribution/share-alike required |',
  '| MechanicDB Audi/VW DTC sample | ODbL-1.0; upstream DTC code spine MIT | 2 make-labelled community candidates (1 Audi, 1 Volkswagen) | Separate SQLite and separate research tab; source labels only; market UNKNOWN; no exact vehicle/ECU fitment, test plans, repairs or OEM parts; attribution/share-alike required |',
  "Research README MechanicDB table row");
replaceAllChecked(readmeFile,
  "The MechanicDB sample is not an OEM-confirmed VAG DTC corpus. Its two make-labelled rows are not shown in diagnostic search and cannot be used for a test plan or repair recommendation.",
  "The MechanicDB sample is not an OEM-confirmed VAG DTC corpus. Its two make-labelled rows are shown only in a separate research tab, never in generic DTC or verified VAG-specific search, and cannot be used for a test plan or repair recommendation.",
  "Research README MechanicDB boundary", 1);

const docsFile = path.join(ROOT, "docs", "RESEARCH_DATA_PACKS.md");
if (fs.existsSync(docsFile)) {
  const doc = readText(docsFile);
  if (doc.includes("hidden pending technical review")) {
    replaceAllChecked(docsFile, "hidden pending technical review", "visible only in a separate research tab pending independent technical review", "Research docs MechanicDB display wording", 1);
  }
}

// The candidate browser is read-only and independently checks every source line before returning it.
const local = require(path.join(ROOT, "lib", "local-research-db.cjs"));
const vwRows = local.searchMechanicDbCandidates("P1128", 5, RESEARCH);
const audiRows = local.searchMechanicDbCandidates("P3000", 5, RESEARCH);
if (vwRows.length !== 1 || audiRows.length !== 1 || vwRows[0].make !== "Volkswagen" || audiRows[0].make !== "Audi") fail("MechanicDB candidate search returned unexpected records");
if (local.searchGenericDtcs("P1128", 5, RESEARCH).length || local.searchGenericDtcs("P3000", 5, RESEARCH).length) fail("Manufacturer-labelled candidates leaked into the generic DTC namespace");
for (const row of [...vwRows, ...audiRows]) {
  if (row.exactFitment !== false || row.ecuFitment !== false || row.prCodeFitment !== false || row.diagnosticExecutionAllowed !== false || row.repairProcedureIncluded !== false || row.oemPartNumberIncluded !== false) fail("MechanicDB candidate browser exposed a prohibited fitment or execution claim");
  if (Object.hasOwn(row, "detailedTechnicalExplanation")) fail("MechanicDB detailed unverified explanation must not be exposed");
}
const verification = {
  status: "verified_candidate_reference_only",
  pack_id: PACK_ID,
  display_status: DISPLAY_STATUS,
  review_status: "community_reference_unverified",
  rows: { Audi: audiRows.length, Volkswagen: vwRows.length, generic_namespace_rows: 0 },
  source_revision: packManifest.source_revision,
  source_snapshot_sha256: packManifest.source_snapshot_sha256,
  source_manifest_sha256: rootPack.source_manifest_sha256,
  database_sha256: rootPack.database_sha256,
  exposed_fields: policy.exposed_fields,
  excluded_fields: policy.excluded_fields,
  exact_vehicle_fitment: false,
  vag_oem_confirmation: false,
  diagnostic_execution_allowed: false,
  warning: WARNING,
};
fs.writeFileSync(path.join(RESEARCH, "mechanicdb-candidate-browser-verification.json"), `${JSON.stringify(verification, null, 2)}\n`, "utf8");
console.log(JSON.stringify(verification, null, 2));
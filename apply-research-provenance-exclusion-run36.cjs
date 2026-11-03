"use strict";
const fs = require("node:fs");
const path = require("node:path");
const crypto = require("node:crypto");
const { DatabaseSync } = require("node:sqlite");

const root = path.resolve(process.cwd(), "desktop-source");
const readLf = (file) => fs.readFileSync(file, "utf8").replace(/\r\n/g, "\n");
const writeLf = (file, value) => fs.writeFileSync(file, value.replace(/\r\n/g, "\n"), "utf8");
const sha256File = (file) => crypto.createHash("sha256").update(fs.readFileSync(file)).digest("hex");
function replaceExactly(source, before, after, label) {
  if (after && source.includes(after)) return source;
  const count = source.split(before).length - 1;
  if (count !== 1) throw new Error(`${label}: expected one original block or an already-applied replacement; found ${count}`);
  return source.replace(before, after);
}
function readJson(file) { return JSON.parse(fs.readFileSync(file, "utf8")); }
function writeJson(file, value) { fs.writeFileSync(file, JSON.stringify(value, null, 2) + "\n", "utf8"); }

function excludeUnverifiedPack() {
  const researchRoot = path.join(root, "data", "research");
  const manifestPath = path.join(researchRoot, "manifest.json");
  const manifest = readJson(manifestPath);
  const pack = manifest.packs.find((item) => item.id === "vag-identity-odbl");
  if (!pack) throw new Error("VAG identity ODbL pack is missing from the research manifest");
  if (pack.license !== "ODbL-1.0" || pack.commercial_use_allowed !== true || pack.display_allowed !== true || pack.cache_allowed !== true || pack.redistribution_allowed !== true) {
    throw new Error("VAG identity source license metadata is incomplete; refusing to create the exclusion record");
  }
  const packDir = path.join(researchRoot, "vag-identity-odbl");
  fs.mkdirSync(packDir, { recursive: true });
  const licensePath = path.join(researchRoot, pack.license_file);
  const sourceManifestPath = path.join(researchRoot, pack.source_manifest_file);
  const dbPath = path.join(researchRoot, pack.database);
  fs.mkdirSync(path.dirname(dbPath), { recursive: true });
  const licenseNotice = [
    "AUDIT NOTICE ONLY — this is not a copy of the full license text.",
    "The upstream repository declares its database under the Open Database License (ODbL) v1.0.",
    "Share-Alike obligations apply to lawful redistribution of the upstream database and derivative databases.",
    "No source records from this dataset are included in this product build.",
    "Official license text: https://opendatacommons.org/licenses/odbl/1-0/",
    "Upstream provenance from autoevolution.com has not been independently verified; this pack is excluded."
  ].join("\n") + "\n";
  fs.writeFileSync(licensePath, licenseNotice, "utf8");
  const licenseSha = sha256File(licensePath);
  const sourceManifest = {
    schema_version: 1,
    dataset: pack.dataset,
    publisher: pack.publisher,
    repository_url: pack.source_url,
    revision: pack.upstream_revision,
    upstream_source: "autoevolution.com",
    license: pack.license,
    license_url: "https://opendatacommons.org/licenses/odbl/1-0/",
    license_sha256: licenseSha,
    license_file: "LICENSE-DATA",
    attribution: "Audit metadata only. Upstream candidate data is not included because its provenance has not been independently verified.",
    share_alike: "ODbL-1.0",
    share_alike_required: true,
    rights_status: pack.license_status,
    rights_review_status: "research_only_upstream_provenance_not_independently_verified",
    source_sha256: pack.source_file_sha256,
    counts: pack.counts,
    market_scope: pack.market_scope,
    applicability_precision: pack.applicability_precision,
    engine_codes_included: false,
    gearbox_codes_included: false,
    ecu_fitment_included: false,
    exact_vehicle_fitment: false,
    production_import: false,
    status: "excluded_pending_upstream_provenance_review",
    product_records_included: false
  };
  writeJson(sourceManifestPath, sourceManifest);
  const db = new DatabaseSync(dbPath);
  try {
    db.exec([
      "PRAGMA foreign_keys=OFF;",
      "CREATE TABLE IF NOT EXISTS research_sources (source_id TEXT PRIMARY KEY, source_sha256 TEXT, license TEXT, market_scope TEXT);",
      "CREATE TABLE IF NOT EXISTS make_candidates (id INTEGER PRIMARY KEY, make_name TEXT);",
      "CREATE TABLE IF NOT EXISTS model_candidates (id INTEGER PRIMARY KEY, make_name TEXT, model_name TEXT, market_scope TEXT, review_status TEXT);",
      "CREATE TABLE IF NOT EXISTS generation_candidates (id INTEGER PRIMARY KEY, model_id INTEGER, generation_name TEXT, market_scope TEXT, review_status TEXT);",
      "CREATE TABLE IF NOT EXISTS engine_variant_candidates (id INTEGER PRIMARY KEY, generation_id INTEGER, engine_label TEXT, engine_code TEXT, gearbox_code TEXT, code_extraction_status TEXT, market_scope TEXT, review_status TEXT);",
      "CREATE TABLE IF NOT EXISTS source_file_artifacts (relative_path TEXT PRIMARY KEY, sha256 TEXT);",
      "BEGIN IMMEDIATE;",
      "DELETE FROM research_sources;",
      "DELETE FROM make_candidates;",
      "DELETE FROM model_candidates;",
      "DELETE FROM generation_candidates;",
      "DELETE FROM engine_variant_candidates;",
      "DELETE FROM source_file_artifacts;",
      "COMMIT;",
      "VACUUM;"
    ].join("\n"));
    const integrity = db.prepare("PRAGMA integrity_check").get().integrity_check;
    if (integrity !== "ok") throw new Error("Excluded VAG identity placeholder integrity failed: " + integrity);
    for (const table of ["research_sources", "make_candidates", "model_candidates", "generation_candidates", "engine_variant_candidates", "source_file_artifacts"]) {
      const count = Number(db.prepare("SELECT count(*) AS n FROM " + table).get().n);
      if (count !== 0) throw new Error("Excluded VAG identity table " + table + " still contains " + count + " rows");
    }
  } finally { db.close(); }
  pack.included_in_product = false;
  pack.product_eligibility = "not_eligible_pending_upstream_provenance_review";
  pack.review_status = "excluded_pending_upstream_provenance_review";
  pack.display_status = "excluded";
  pack.exclusion_reason = "Upstream provenance from autoevolution.com has not been independently verified; no source records are included in the product.";
  pack.product_counts = { makes: 0, models: 0, generations: 0, engineVariants: 0, sourceRows: 0 };
  pack.license_file_sha256 = licenseSha;
  pack.source_manifest_sha256 = sha256File(sourceManifestPath);
  pack.database_sha256 = sha256File(dbPath);
  writeJson(manifestPath, manifest);
  const readmePath = path.join(researchRoot, "README.md");
  const readme = fs.readFileSync(readmePath, "utf8");
  const notice = "\n\nVAG identity ODbL source exclusion: the upstream provenance from autoevolution.com has not been independently verified. The installer contains only an empty SQLite schema placeholder and audit metadata; no model, generation or engine records from this source are distributed or searchable. Re-enable only after independent provenance and redistribution-rights review.\n";
  if (!readme.includes("VAG identity ODbL source exclusion:")) fs.appendFileSync(readmePath, notice, "utf8");
  return { databaseSha256: pack.database_sha256, productCounts: pack.product_counts };
}

function patchLocalResearchDb() {
  const file = path.join(root, "lib", "local-research-db.cjs");
  let source = readLf(file);
  source = source.replace(
    'scope: "VAG-group identity candidates; market UNKNOWN",',
    'scope: "Excluded from product: upstream provenance is not independently verified",'
  );
  source = replaceExactly(
    source,
    '    if (makes !== 5 || models !== 233 || generations !== 823 || engineVariants !== 5081 || sourceCount !== 5) {\n      throw new Error("VAG identity research pack failed its candidate-only count gate");\n    }',
    '    if (vagManifest.included_in_product === false) {\n      if (makes !== 0 || models !== 0 || generations !== 0 || engineVariants !== 0 || sourceCount !== 0) {\n        throw new Error("Excluded VAG identity pack must contain zero source records");\n      }\n    } else if (makes !== 5 || models !== 233 || generations !== 823 || engineVariants !== 5081 || sourceCount !== 5) {\n      throw new Error("VAG identity research pack failed its candidate-only count gate");\n    }',
    "VAG identity zero-row exclusion gate"
  );
  source = replaceExactly(
    source,
    '          scope: PACKS.vehicles.scope,\n          status: "research_only",\n          marketScope: "UNKNOWN",\n          counts: { makes, models, generations, engineVariants },',
    '          scope: PACKS.vehicles.scope,\n          status: vagManifest.included_in_product === false ? "excluded_pending_provenance_review" : "research_only",\n          includedInProduct: vagManifest.included_in_product !== false,\n          displayStatus: vagManifest.display_status || "research_only",\n          marketScope: "UNKNOWN",\n          counts: { makes, models, generations, engineVariants },',
    "VAG identity excluded summary status"
  );
  source = replaceExactly(
    source,
    '          note: "Descriptive engine and transmission labels only; no factory codes or exact pairings.",',
    '          note: vagManifest.included_in_product === false ? "Excluded from the installer and search until upstream provenance is independently verified; no source records are loaded." : "Descriptive engine and transmission labels only; no factory codes or exact pairings.",',
    "VAG identity exclusion summary note"
  );
  source = replaceExactly(
    source,
    '  const vagManifest = verifyPackDatabaseHash(root, PACKS.vehicles.id, PACKS.vehicles.file);\n  const db = openReadOnly(root, PACKS.vehicles.file);',
    '  const vagManifest = verifyPackDatabaseHash(root, PACKS.vehicles.id, PACKS.vehicles.file);\n  if (vagManifest.included_in_product !== true) return [];\n  const db = openReadOnly(root, PACKS.vehicles.file);',
    "disable VAG identity candidate search while excluded"
  );
  writeLf(file, source);
}

function patchVerifier() {
  const file = path.join(root, "scripts", "verify-local-research-packs.cjs");
  let source = readLf(file);
  source = replaceExactly(
    source,
    '      codedCandidates: count(vagDb, "SELECT count(*) AS n FROM engine_variant_candidates WHERE engine_code IS NOT NULL OR gearbox_code IS NOT NULL OR code_extraction_status!=\'not_provided\'"),\n      nonCandidateRows: count(vagDb, "SELECT count(*) AS n FROM model_candidates WHERE review_status!=\'candidate\' OR market_scope!=\'UNKNOWN\'") + count(vagDb, "SELECT count(*) AS n FROM generation_candidates WHERE review_status!=\'candidate\' OR market_scope!=\'UNKNOWN\'"),',
    '      codedCandidates: count(vagDb, "SELECT count(*) AS n FROM engine_variant_candidates WHERE engine_code IS NOT NULL OR gearbox_code IS NOT NULL OR code_extraction_status!=\'not_provided\'"),\n      nonCandidateRows: count(vagDb, "SELECT count(*) AS n FROM model_candidates WHERE review_status!=\'candidate\' OR market_scope!=\'UNKNOWN\'") + count(vagDb, "SELECT count(*) AS n FROM generation_candidates WHERE review_status!=\'candidate\' OR market_scope!=\'UNKNOWN\'"),\n      excluded: vag.included_in_product === false,',
    "VAG identity exclusion status in verifier counts"
  );
  source = replaceExactly(
    source,
    '    assert(vagCounts.sources === 5 && vagCounts.makes === 5 && vagCounts.models === 233 && vagCounts.generations === 823 && vagCounts.engineVariants === 5081 && !vagCounts.codedCandidates && !vagCounts.nonCandidateRows, `VAG identity candidate-only gate failed: ${JSON.stringify(vagCounts)}`);',
    '    assert(vag.included_in_product === false && vag.product_eligibility === "not_eligible_pending_upstream_provenance_review" && vagCounts.excluded && vagCounts.sources === 0 && vagCounts.makes === 0 && vagCounts.models === 0 && vagCounts.generations === 0 && vagCounts.engineVariants === 0 && !vagCounts.codedCandidates && !vagCounts.nonCandidateRows, `VAG identity pack must remain excluded until upstream provenance is independently verified: ${JSON.stringify(vagCounts)}`);',
    "VAG identity provenance exclusion verifier gate"
  );
  writeLf(file, source);
}

function patchResearchDbTests() {
  const file = path.join(root, "tests", "local-research-db.test.cjs");
  let source = readLf(file);
  source = replaceExactly(
    source,
    '  assert.deepEqual(vag.counts, { makes: 5, models: 233, generations: 823, engineVariants: 5081 });\n  assert.equal(vag.marketScope, "UNKNOWN");\n  assert.equal(vag.license, "ODbL-1.0");',
    '  assert.deepEqual(vag.counts, { makes: 0, models: 0, generations: 0, engineVariants: 0 });\n  assert.equal(vag.marketScope, "UNKNOWN");\n  assert.equal(vag.license, "ODbL-1.0");\n  assert.equal(vag.includedInProduct, false);\n  assert.equal(vag.status, "excluded_pending_provenance_review");\n  assert.match(vag.note, /upstream provenance is independently verified/i);',
    "VAG identity excluded summary test"
  );
  source = replaceExactly(
    source,
    '  assert.equal(local.searchVehicleCandidates("Golf", 500, root).length, 50);',
    '  assert.equal(local.searchVehicleCandidates("Golf", 500, root).length, 0);',
    "VAG identity search disabled test"
  );
  source = replaceExactly(
    source,
    'test("VAG identity search returns descriptive candidates, never factory codes or exact fitment", () => {\n  const rows = local.searchVehicleCandidates("Golf", 5, root);\n  assert.ok(rows.length > 0);\n  for (const row of rows) {\n    assert.equal(row.brand, "Volkswagen");\n    assert.equal(row.marketScope, "UNKNOWN");\n    assert.equal(row.reviewStatus, "candidate");\n    assert.equal(row.engineCode, null);\n    assert.equal(row.gearboxCode, null);\n    assert.equal(row.exactFitment, false);\n    assert.equal(row.sourceLicense, "ODbL-1.0");\n    assert.match(row.sourceUrl, /^https:\\/\\//);\n    assert.match(row.sourceSha256, /^[a-f0-9]{64}$/);\n    assert.match(row.sourceManifestSha256, /^[a-f0-9]{64}$/);\n  }\n});',
    'test("VAG identity search is disabled until upstream provenance is independently verified", () => {\n  const rows = local.searchVehicleCandidates("Golf", 5, root);\n  assert.deepEqual(rows, []);\n});',
    "VAG identity search exclusion test"
  );
  writeLf(file, source);

  const packsTest = path.join(root, "tests", "local-research-packs.test.cjs");
  let packSource = readLf(packsTest);
  packSource = replaceExactly(packSource,
    '  assert.equal(result.vag_identity.models, 233);\n  assert.equal(result.vag_identity.generations, 823);\n  assert.equal(result.vag_identity.engineVariants, 5081);\n  assert.equal(result.vag_identity.codedCandidates, 0);',
    '  assert.equal(result.vag_identity.models, 0);\n  assert.equal(result.vag_identity.generations, 0);\n  assert.equal(result.vag_identity.engineVariants, 0);\n  assert.equal(result.vag_identity.sources, 0);\n  assert.equal(result.vag_identity.excluded, true);\n  assert.equal(result.vag_identity.codedCandidates, 0);',
    "VAG identity excluded pack count test"
  );
  writeLf(packsTest, packSource);
}

function patchAutoDiag2DbAndTests() {
  const moduleFile = path.join(root, "lib", "autodiag2-research-db.cjs");
  let moduleSource = readLf(moduleFile);
  moduleSource = replaceExactly(moduleSource,
    '    unclassifiedEngineLabels: count("SELECT count(*) AS n FROM engine_candidates WHERE engine_code_quality=\\'unclassified_source_label\\'"),',
    '    unclassifiedEngineLabels: count("SELECT count(*) AS n FROM engine_candidates WHERE engine_code_quality=\\'unclassified_source_label\\'"),\n    unverifiedEngineCodeFields: count("SELECT count(*) AS n FROM engine_candidates WHERE engine_code_quality=\\'unverified_source_code_field\\'"),',
    "AutoDiag2 unverified engine source-code count"
  );
  moduleSource = replaceExactly(moduleSource,
    '        counts.engineCodeShapeCandidates !== 939 || counts.unclassifiedEngineLabels !== 144 || counts.ecus !== 179 ||\n        counts.vehicleConfigCandidates !== 3170 || counts.dtcCandidates !== 956 || counts.vehicleEcuLinkedDtcCandidates !== 0 ||\n        counts.makeLevelDtcCandidates !== 956 || counts.dtcFitmentCandidateLinks !== 0 || counts.genericDtcRows !== 0 ||',
    '        counts.engineCodeShapeCandidates !== 0 || counts.unclassifiedEngineLabels !== 0 || counts.unverifiedEngineCodeFields !== 1083 || counts.ecus !== 179 ||\n        counts.vehicleConfigCandidates !== 3170 || counts.dtcCandidates !== 0 || counts.vehicleEcuLinkedDtcCandidates !== 0 ||\n        counts.makeLevelDtcCandidates !== 0 || counts.dtcFitmentCandidateLinks !== 0 || counts.genericDtcRows !== 0 ||',
    "AutoDiag2 filtered exact-count gate"
  );
  moduleSource = replaceExactly(moduleSource,
    '        counts.genericDtcRows !== expected.generic_dtc_rows_in_pack || counts.transmissionRecords !== expected.transmission_records) {',
    '        counts.genericDtcRows !== expected.generic_dtc_rows_in_pack || counts.transmissionRecords !== expected.transmission_records ||\n        counts.unverifiedEngineCodeFields !== expected.engine_code_candidates_unverified || expected.engine_codes_verified !== 0 ||\n        packData.sourceManifest.dtc_policy_filtered !== true ||\n        packData.sourceManifest.dtc_candidate_policy?.diagnostic_execution_allowed !== false ||\n        packData.sourceManifest.dtc_candidate_policy?.repair_advice_approved !== false ||\n        packData.sourceManifest.engine_code_policy?.shape_heuristic_is_not_used_for_verification !== true) {',
    "AutoDiag2 source manifest policy parity gate"
  );
  moduleSource = replaceExactly(moduleSource,
    '      engineCodeShapeCandidates: counts.engineCodeShapeCandidates,\n      unclassifiedEngineLabels: counts.unclassifiedEngineLabels,',
    '      engineCodeShapeCandidates: counts.engineCodeShapeCandidates,\n      unclassifiedEngineLabels: counts.unclassifiedEngineLabels,\n      unverifiedEngineCodeFields: counts.unverifiedEngineCodeFields,',
    "AutoDiag2 summary unverified engine count"
  );
  moduleSource = replaceExactly(moduleSource,
    '      counts,\n    attributionText: packData.attributionText,',
    '      counts,\n    excludedDtcCounts: packData.sourceManifest.dtc_policy_removal_counts || {},\n    attributionText: packData.attributionText,',
    "AutoDiag2 summary excluded DTC counts"
  );
  writeLf(moduleFile, moduleSource);

  const testFile = path.join(root, "tests", "autodiag2-pack-integration.test.cjs");
  let testSource = readLf(testFile);
  const pairs = [
    ['  assert.equal(result.counts.engineCodeShapeCandidates, 939);', '  assert.equal(result.counts.engineCodeShapeCandidates, 0);'],
    ['  assert.equal(result.counts.unclassifiedEngineLabels, 144);', '  assert.equal(result.counts.unclassifiedEngineLabels, 0);'],
    ['  assert.equal(result.counts.dtcCandidates, 956);', '  assert.equal(result.counts.dtcCandidates, 0);'],
    ['  assert.equal(result.counts.makeLevelDtcCandidates, 956);', '  assert.equal(result.counts.makeLevelDtcCandidates, 0);'],
    ['  assert.equal(pack.counts.dtcCandidates, 956);', '  assert.equal(pack.counts.dtcCandidates, 0);']
  ];
  for (const pair of pairs) testSource = replaceExactly(testSource, pair[0], pair[1], "AutoDiag2 filtered count assertion");
  testSource = replaceExactly(testSource,
    '  assert.equal(result.counts.engines, 1083);',
    '  assert.equal(result.counts.engines, 1083);\n  assert.equal(result.counts.unverifiedEngineCodeFields, 1083);',
    "AutoDiag2 unverified code-field count"
  );
  testSource = replaceExactly(testSource,
    '  assert.equal(pack.counts.vehicleConfigCandidates, 3170);',
    '  assert.equal(pack.counts.vehicleConfigCandidates, 3170);\n  assert.equal(pack.counts.unverifiedEngineCodeFields, 1083);\n  assert.equal(pack.excludedDtcCounts.unattributed_make_level, 956);',
    "AutoDiag2 summary filter provenance counts"
  );
  const oldDtc = [
    '  const dtcRows = local.searchAutoDiag2Candidates("P1004", 10, root);',
    '  const dtc = dtcRows.find((row) => row.kind === "dtc_candidate");',
    '  assert.ok(dtc);',
    '  assert.equal(dtc.code, "P1004");',
    '  assert.equal(dtc.namespace, "manufacturer_controlled_candidate");',
    '  assert.equal(dtc.sourceScope, "make_level");',
    '  assert.deepEqual(dtc.makeLabels, ["Audi"]);',
    '  assert.equal(dtc.marketScope, "UNKNOWN");',
    '  assert.equal(dtc.reviewStatus, "community_reference_unverified");',
    '  assert.equal(dtc.exactFitment, false);',
    '  assert.equal(dtc.ecuFitment, false);',
    '  assert.equal(dtc.diagnosticExecutionAllowed, false);',
    '  assert.equal(dtc.repairAdviceApproved, false);',
    '  assert.equal(dtc.license, "ODbL-1.0");',
    '  assert.equal(dtc.contentsLicense, "DbCL-1.0");',
    '  assert.match(dtc.sourceRevision, /^[a-f0-9]{40}$/);',
    '  assert.match(dtc.databaseSha256, /^[a-f0-9]{64}$/);',
    '  assert.match(dtc.sourceManifestSha256, /^[a-f0-9]{64}$/);',
    '  assert.match(dtc.sourceArtifactZipSha256, /^[a-f0-9]{64}$/);',
    '  assert.match(dtc.warning, /not confirmed VAG-specific/i);',
    '  assert.equal(Object.hasOwn(dtc, "repairs"), false);',
    '  assert.equal(Object.hasOwn(dtc, "testPlan"), false);',
    '',
    '  const engineRows = local.searchAutoDiag2Candidates("CAXA", 20, root);'
  ].join('\n');
  const newDtc = [
    '  assert.deepEqual(local.searchAutoDiag2Candidates("P1004", 10, root), []);',
    '',
    '  const engineRows = local.searchAutoDiag2Candidates("CAXA", 20, root);'
  ].join('\n');
  testSource = replaceExactly(testSource, oldDtc, newDtc, "AutoDiag2 make-level DTC exclusion integration test");
  testSource = replaceExactly(testSource,
    '  assert.equal(config.marketScope, "UNKNOWN");',
    '  assert.equal(config.marketScope, "UNKNOWN");\n  assert.equal(config.engineLabelQuality, "unverified_source_code_field");',
    "AutoDiag2 engine label remains explicitly unverified"
  );
  testSource = replaceExactly(testSource,
    '  assert.deepEqual(local.searchGenericDtcs("P1004", 10, root), []);',
    '  assert.deepEqual(local.searchGenericDtcs("P1004", 10, root), []);\n  const generic = local.searchGenericDtcs("P0300", 10, root);\n  assert.ok(generic.length > 0);\n  assert.equal(generic[0].namespace, "generic_obd2");',
    "generic DTC remains separate from AutoDiag2 candidates"
  );
  writeLf(testFile, testSource);
}

function patchResearchUi() {
  const file = path.join(root, "components", "local-research-catalog.tsx");
  let source = readLf(file);
  if (!source.includes("excludedDtcCounts?: Record<string, number>")) {
    const typeMatch = source.match(/type SummaryPack = \{[^}]+\};/);
    if (!typeMatch) throw new Error("research summary type was not found");
    const updatedType = typeMatch[0].replace("note: string;", "note: string; includedInProduct?: boolean; excludedDtcCounts?: Record<string, number>;");
    if (updatedType === typeMatch[0]) throw new Error("research summary type could not be extended");
    source = source.replace(typeMatch[0], updatedType);
  }
  source = replaceExactly(source,
    'const [dataset, setDataset] = useState<Dataset>("vehicles");',
    'const [dataset, setDataset] = useState<Dataset>("dtc");',
    "research catalog safe default dataset"
  );
  source = replaceExactly(source,
    '  { id: "vehicles", label: "VAG · поколения и варианты", hint: "ODbL · рынок UNKNOWN · кандидаты" },\n',
    '',
    "remove unverified VAG identity tab"
  );
  source = replaceExactly(source,
    '<article className="research-stat"><small>Модели VAG-группы</small><strong>{formatNumber(vag?.counts?.models)}</strong><span>ODbL · research-only</span></article>',
    '<article className="research-stat"><small>VAG identity source</small><strong>{vag?.includedInProduct ? formatNumber(vag?.counts?.models) : "Исключён"}</strong><span>ODbL · исключён до проверки происхождения</span></article>',
    "VAG identity exclusion statistic"
  );
  source = replaceExactly(source,
    '<p>Эта локальная библиотека не подтверждает комплектацию конкретного автомобиля, код двигателя или КПП, ЭБУ, PR-коды, OEM-детали и ремонтную процедуру. ODbL-таксономия и VehiclesDB — кандидаты, а рыночные свидетельства VehiclesDB не относятся к России/ЕАЭС. UDS-сигналы — непроверенные community-кандидаты; команды не отправляются автомобилю. Для технических рекомендаций нужны отдельные первичные документы с точной применимостью.</p>',
    '<p>Эта локальная библиотека не подтверждает комплектацию конкретного автомобиля, код двигателя или КПП, ЭБУ, PR-коды, OEM-детали и ремонтную процедуру. ODbL VAG identity pack исключён до проверки происхождения upstream: источник данных ссылается на autoevolution.com, а права на исходный массив независимо не подтверждены; записи не загружаются и не ищутся. VehiclesDB содержит только зарубежные свидетельства, UDS-сигналы остаются непроверенными community-кандидатами, команды не отправляются автомобилю. Для технических рекомендаций нужны первичные документы с точной применимостью.</p>',
    "research boundary for excluded VAG identity source"
  );
  source = replaceExactly(source,
    '<p>VAG identity — ODbL-1.0: <a href="https://github.com/gor3a/vehicle-makes-models" target="_blank" rel="noopener noreferrer">gor3a/vehicle-makes-models</a>; upstream source, как заявлено издателем, — autoevolution.com. При публичном распространении адаптированной базы действует share-alike по ODbL-1.0.</p>',
    '<p>VAG identity ODbL pack не распространяется и не отображает записи: upstream provenance от autoevolution.com не прошёл независимую проверку. В продукте оставлены только лицензионные и source-manifest метаданные для аудита; повторное включение возможно после подтверждения прав на исходный массив и его кэширование.</p>',
    "research credits for excluded VAG identity source"
  );
  source = replaceExactly(source,
    '<article className="research-stat"><small>AutoDiag2 · DTC-кандидаты</small><strong>{formatNumber(autoDiag2?.counts?.dtcCandidates)}</strong><span>ODbL / DbCL · make-level · не OEM-подтверждены</span></article>',
    '<article className="research-stat"><small>AutoDiag2 · DTC-кандидаты</small><strong>{formatNumber(autoDiag2?.counts?.dtcCandidates)}</strong><span>{formatNumber(autoDiag2?.excludedDtcCounts?.unattributed_make_level)} make-level generic-ECU rows excluded · 0 retained</span></article>',
    "AutoDiag2 filtered DTC statistic"
  );
  source = replaceExactly(source,
    '{row.engineLabelQuality === "factory_code_shape_candidate" ? "Похожа на код · не подтверждена" : "Не классифицирована"}',
    '{row.engineLabelQuality === "unverified_source_code_field" ? "Поле источника · не подтверждено" : row.engineLabelQuality === "factory_code_shape_candidate" ? "Похожа на код · не подтверждена" : "Не классифицирована"}',
    "AutoDiag2 engine source-field quality label"
  );
  source = replaceExactly(source,
    '{autoDiag2 && <p>AutoDiag2 v{autoDiag2.releaseTag}: {formatNumber(autoDiag2.counts.dtcCandidates)} DTC-кандидатов уровня марки, {formatNumber(autoDiag2.counts.vehicleConfigCandidates)} конфигураций-кандидатов, {formatNumber(autoDiag2.counts.engines)} меток двигателя и {formatNumber(autoDiag2.counts.ecus)} ECU-кандидатов. Все записи — community reference, рынок UNKNOWN; точная применимость, заводская атрибуция и ECU HW/SW не подтверждены. DTC не связаны с конкретными конфигурациями: {formatNumber(autoDiag2.counts.vehicleEcuLinkedDtcCandidates)} связей. Нет КПП, тест-планов и разрешённого выполнения диагностики. Набор хранится отдельно от общих SAE/ISO DTC.</p>}',
    '{autoDiag2 && <p>AutoDiag2 v{autoDiag2.releaseTag}: {formatNumber(autoDiag2.counts.dtcCandidates)} DTC-кандидатов оставлено после фильтра атрибуции; {formatNumber(autoDiag2.excludedDtcCounts?.unattributed_make_level)} generic-ECU make-level записей исключено. Остались {formatNumber(autoDiag2.counts.vehicleConfigCandidates)} конфигураций-кандидатов, {formatNumber(autoDiag2.counts.engines)} меток двигателя, из них {formatNumber(autoDiag2.counts.unverifiedEngineCodeFields)} полей кода не подтверждены, и {formatNumber(autoDiag2.counts.ecus)} ECU-кандидатов. Рынок UNKNOWN, точная применимость не подтверждена; заводских кодов двигателя, записей КПП, тест-планов и разрешённого выполнения диагностики нет. Набор хранится отдельно от общих SAE/ISO DTC.</p>}',
    "AutoDiag2 filtered candidate boundary"
  );
  source = replaceExactly(source,
    '<p><a href="https://github.com/autodiag2/database" target="_blank" rel="noopener noreferrer">AutoDiag2/database</a> — отдельная база ODbL-1.0; индивидуальные записи/содержимое под DbCL-1.0. По опубликованным условиям разрешены коммерческое использование, отображение, офлайн-кэширование и распространение при сохранении атрибуции и share-alike. В приложение включён только набор данных, не upstream GPL-3.0-or-later source code. Данные community-contributed, не OEM-подтверждены, рынок UNKNOWN; DTC-кандидаты make-level, без привязки к автомобилю/ECU и без права на выполнение диагностики.</p>',
    '<p><a href="https://github.com/autodiag2/database" target="_blank" rel="noopener noreferrer">AutoDiag2/database</a> — отдельная база ODbL-1.0 / DbCL-1.0; коммерческое использование, отображение, офлайн-кэширование и распространение разрешены по опубликованным условиям при атрибуции и share-alike. В наборе оставлены только community vehicle/configuration/engine/ECU candidates. 956 generic-ECU make-level DTC rows исключены, 0 DTC rows retained; все 1 083 непустых source-code fields остаются непроверенными, 0 factory engine codes, 0 transmission records, рынок UNKNOWN, точная применимость и диагностическое выполнение не подтверждены.</p>',
    "AutoDiag2 rights and filtering attribution"
  );
  source = replaceExactly(source,
    '<p>SQLite SHA-256 · VAG identity: {vag?.databaseSha256 || "недоступен"}</p>',
    '<p>VAG identity ODbL source: excluded; no source records or SQLite data are shipped.</p>',
    "VAG identity no-data SHA notice"
  );
  writeLf(file, source);

  const uiTest = path.join(root, "tests", "local-research-ui-contract.test.cjs");
  let uiSource = readLf(uiTest);
  const addition = '\n\ntest("VAG identity source with unverified upstream provenance is excluded from the product UI", () => {\n  assert.match(component, /исключён до проверки происхождения/);\n  assert.match(component, /upstream provenance/);\n  assert.doesNotMatch(component, /id: "vehicles", label: "VAG · поколения и варианты"/);\n  assert.match(component, /vag\\?\\.includedInProduct/);\n});\n';
  if (!uiSource.includes("VAG identity source with unverified upstream provenance is excluded")) uiSource += addition;
  writeLf(uiTest, uiSource);
}

function writeDedicatedTest() {
  const file = path.join(root, "tests", "vag-identity-provenance-exclusion.test.cjs");
  const content = String.raw`"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { DatabaseSync } = require("node:sqlite");
const local = require("../lib/local-research-db.cjs");
const root = path.resolve(__dirname, "../data/research");

test("unverified Autoevolution-derived ODbL taxonomy is not shipped as usable data", () => {
  const manifest = JSON.parse(fs.readFileSync(path.join(root, "manifest.json"), "utf8"));
  const pack = manifest.packs.find((item) => item.id === "vag-identity-odbl");
  assert.ok(pack);
  assert.equal(pack.included_in_product, false);
  assert.equal(pack.product_eligibility, "not_eligible_pending_upstream_provenance_review");
  assert.deepEqual(pack.product_counts, { makes: 0, models: 0, generations: 0, engineVariants: 0, sourceRows: 0 });
  const sourceManifest = JSON.parse(fs.readFileSync(path.join(root, pack.source_manifest_file), "utf8"));
  assert.equal(sourceManifest.rights_review_status, "research_only_upstream_provenance_not_independently_verified");
  const db = new DatabaseSync(path.join(root, pack.database), { readOnly: true });
  try {
    db.exec("PRAGMA query_only=ON");
    for (const table of ["research_sources", "make_candidates", "model_candidates", "generation_candidates", "engine_variant_candidates", "source_file_artifacts"]) {
      assert.equal(db.prepare("SELECT count(*) AS n FROM " + table).get().n, 0, table);
    }
    assert.equal(db.prepare("PRAGMA integrity_check").get().integrity_check, "ok");
    assert.deepEqual(db.prepare("PRAGMA foreign_key_check").all(), []);
  } finally { db.close(); }
  const summary = local.getResearchSummary(root).packs.find((item) => item.id === "vag-identity-odbl");
  assert.equal(summary.includedInProduct, false);
  assert.equal(summary.status, "excluded_pending_provenance_review");
  assert.deepEqual(summary.counts, { makes: 0, models: 0, generations: 0, engineVariants: 0 });
  assert.deepEqual(local.searchVehicleCandidates("Golf", 10, root), []);
});
`;
  fs.writeFileSync(file, content, "utf8");
}

const emptying = excludeUnverifiedPack();
patchLocalResearchDb();
patchVerifier();
patchResearchDbTests();
patchAutoDiag2DbAndTests();
patchResearchUi();
writeDedicatedTest();
console.log(JSON.stringify({ status: "excluded_unverified_vag_identity_source", ...emptying }, null, 2));
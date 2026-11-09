#!/usr/bin/env node
"use strict";

const fs = require("node:fs");
const path = require("node:path");
const crypto = require("node:crypto");
const { DatabaseSync } = require("node:sqlite");

const PACK_ID = "wikipedia-vag-engine-code-candidates-cc-by-sa-4-0";
const SOURCE_ID = "wikipedia-vag-engine-code-lists-cc-by-sa-4-0";
const TARGET_DIR = "wikipedia-vag-engine-candidates";
const EXPECTED = {
  license: "CC-BY-SA-4.0",
  attributionSha256: "1bfa85c4c0c7e5182cfc122148958096a17167e7242d48e7c035f4332ee62090",
  licenseNoticeSha256: "7ea86ece96546c760f170b0db7b6007d5238307dacca9f1203ce52355eb6500e",
  wikitextSnapshotSha256: "91eda1afd5c65fd5ea1f756d6c1620a02c9457975780a5f6001c19c9e409a787",
  candidateContentSha256: "3b8fea2cdbbfb5e42694d8316face591b61996b4e5bae7887df544da776387b5",
  wikitextPageHashes: {
    "1375791889": "3ba3cec7a350b70e179c9921bfb55c6665fdd0412ee0969bb3b63b2b29eff3bb",
    "1381198237": "d359d16ea4cac498e9039ef6cd0e2bfa91d38ee5c01fd8eae3fffa1360f2e85c",
    "1383476161": "527ad0a2b8f70eab2625a4e644091a812da77308a162475164124feecea5fc4a",
    "1383504097": "c14ce9f4caa460f57d9afdfcd2e344e04c3ee51d2b5194cb3bafbcb115776bf4",
  },
  candidateRows: 241,
  uniqueCandidateCodes: 241,
  sourceDocuments: 4,
};

function fail(message) { throw new Error(message); }
function sha256(bytes) { return crypto.createHash("sha256").update(bytes).digest("hex"); }
function sha256File(file) { return sha256(fs.readFileSync(file)); }
function readJson(file) { return JSON.parse(fs.readFileSync(file, "utf8").replace(/^\uFEFF/, "")); }
function replaceOnce(source, anchor, replacement, label) {
  const count = source.split(anchor).length - 1;
  if (count !== 1) fail(label + ": expected one anchor, found " + count);
  return source.replace(anchor, replacement);
}
function parseArgs(argv) {
  const out = {};
  for (let i = 2; i < argv.length; i += 2) {
    const key = argv[i];
    if (!key.startsWith("--") || !argv[i + 1]) fail("Invalid argument near " + key);
    out[key.slice(2)] = argv[i + 1];
  }
  for (const key of ["desktop-root", "pack-dir", "build-evidence", "inner-archive", "artifact-run-id", "artifact-id", "artifact-sha256", "source-commit", "source-head-sha", "source-event", "source-ref"]) {
    if (!out[key]) fail("Missing --" + key);
  }
  if (!/^\d+$/.test(out["artifact-run-id"]) || !/^\d+$/.test(out["artifact-id"])) fail("Artifact run/id must be numeric");
  if (!/^[a-f0-9]{64}$/.test(out["artifact-sha256"])) fail("Outer artifact SHA-256 is invalid");
  if (!/^[a-f0-9]{40}$/.test(out["source-commit"]) || !/^[a-f0-9]{40}$/.test(out["source-head-sha"])) fail("Source commit/head SHA is invalid");
  if (!["pull_request", "push", "workflow_dispatch"].includes(out["source-event"])) fail("Unsupported source event");
  if (!/^refs\/(?:heads|pull)\//.test(out["source-ref"])) fail("Source ref is invalid");
  return out;
}
function verifyPack(packDir, evidenceFile, args) {
  const files = {
    manifest: path.join(packDir, "manifest.json"),
    sourceManifest: path.join(packDir, "source-manifest.json"),
    database: path.join(packDir, "wikipedia-vag-engine-candidates.sqlite"),
    attribution: path.join(packDir, "ATTRIBUTION.md"),
    licenseNotice: path.join(packDir, "LICENSE-NOTICE.txt"),
  };
  for (const file of Object.values(files)) {
    if (!fs.existsSync(file) || !fs.statSync(file).isFile()) fail("Candidate pack file missing: " + file);
  }
  const evidence = readJson(evidenceFile);
  const manifest = readJson(files.manifest);
  const sourceManifest = readJson(files.sourceManifest);
  const innerArchive = path.resolve(args["inner-archive"]);
  if (String(evidence.workflow_run_id) !== args["artifact-run-id"]) fail("Wikipedia build-evidence run ID mismatch");
  if (evidence.source_commit !== args["source-commit"] || !/^[a-f0-9]{40}$/.test(evidence.source_commit || "")) fail("Wikipedia source commit mismatch");
  if (evidence.source_head_sha !== args["source-head-sha"] || evidence.source_event !== args["source-event"] || evidence.source_ref !== args["source-ref"]) fail("Wikipedia source branch/event provenance mismatch");
  if (evidence.manifest?.pack_id !== PACK_ID || evidence.manifest?.database_sha256 !== manifest.database_sha256 || evidence.manifest?.source_snapshot_sha256 !== manifest.source_snapshot_sha256 || evidence.manifest?.source_manifest_sha256 !== manifest.source_manifest_sha256) fail("Wikipedia build-evidence manifest mismatch");
  if (!/^[a-f0-9]{64}$/.test(evidence.artifact_sha256 || "") || sha256File(innerArchive) !== evidence.artifact_sha256) fail("Wikipedia inner archive SHA-256 mismatch");
  if (manifest.pack_id !== PACK_ID || manifest.source_id !== SOURCE_ID || manifest.data_license !== EXPECTED.license ||
      manifest.rights_status !== "approved_by_published_license" || manifest.commercial_use_allowed !== true ||
      manifest.display_allowed !== true || manifest.offline_cache_allowed !== true || manifest.bulk_reuse_allowed !== true ||
      manifest.redistribution_allowed !== true || manifest.attribution_required !== true || manifest.share_alike_required !== true ||
      manifest.separate_pack_required !== true || manifest.market_scope !== "UNKNOWN" ||
      manifest.applicability_precision !== "community_engine_code_candidate_only" ||
      manifest.verification_status !== "community_reference_unverified" ||
      manifest.quality_review_status !== "not_approved_for_technical_use" || manifest.candidate_only !== true ||
      manifest.product_import_allowed !== false || manifest.exact_vehicle_fitment !== false ||
      manifest.generation_year_fitment !== false || manifest.engine_gearbox_fitment !== false ||
      manifest.ecu_fitment !== false || manifest.dtc_fitment !== false || manifest.repair_use_allowed !== false ||
      manifest.diagnostic_execution_allowed !== false) fail("Wikipedia candidate pack rights/applicability boundary mismatch");
  if (!/^[a-f0-9]{64}$/.test(manifest.source_snapshot_sha256 || "") ||
      !/^[a-f0-9]{64}$/.test(manifest.source_manifest_sha256 || "") ||
      !/^[a-f0-9]{64}$/.test(manifest.database_sha256 || "") ||
      manifest.attribution_sha256 !== EXPECTED.attributionSha256 ||
      manifest.license_notice_sha256 !== EXPECTED.licenseNoticeSha256 ||
      manifest.counts?.candidate_rows !== EXPECTED.candidateRows ||
      manifest.counts?.unique_candidate_codes !== EXPECTED.uniqueCandidateCodes ||
      manifest.counts?.source_documents !== EXPECTED.sourceDocuments) fail("Wikipedia candidate pack pinned hashes/counts mismatch");
  if (sha256File(files.sourceManifest) !== manifest.source_manifest_sha256 ||
      sha256File(files.database) !== manifest.database_sha256 ||
      sha256File(files.attribution) !== manifest.attribution_sha256 ||
      sha256File(files.licenseNotice) !== manifest.license_notice_sha256) fail("Wikipedia candidate pack file SHA-256 mismatch");
  if (!Array.isArray(manifest.pages) || manifest.pages.length !== EXPECTED.sourceDocuments ||
      !Array.isArray(sourceManifest.pages) || sourceManifest.pages.length !== EXPECTED.sourceDocuments) fail("Wikipedia pinned source page list is incomplete");
  for (const page of manifest.pages) {
    const stem = String(page.revision_id);
    if (EXPECTED.wikitextPageHashes[stem] !== page.wikitext_sha256) fail("Wikipedia pinned raw revision changed: " + stem);
    const html = path.join(packDir, "source-snapshots", stem + ".html");
    const wikitext = path.join(packDir, "source-snapshots", stem + ".wikitext");
    if (!fs.existsSync(html) || !fs.existsSync(wikitext) ||
        sha256File(html) !== page.rendered_html_sha256 ||
        sha256File(wikitext) !== page.wikitext_sha256) fail("Wikipedia source snapshot hash mismatch for revision " + stem);
  }
  const db = new DatabaseSync(files.database, { readOnly: true });
  try {
    db.exec("PRAGMA query_only=ON; PRAGMA trusted_schema=OFF;");
    if (db.prepare("PRAGMA integrity_check").all()[0]?.integrity_check !== "ok" ||
        db.prepare("PRAGMA foreign_key_check").all().length) fail("Wikipedia candidate SQLite integrity check failed");
    const source = db.prepare("SELECT * FROM source_registry WHERE source_id=?").get(SOURCE_ID);
    const candidateRows = db.prepare("SELECT candidate_code,source_revision_id,source_row_kind,source_row_number,source_row_sha256,candidate_value_text FROM engine_code_candidates ORDER BY candidate_code,source_revision_id,source_row_number").all().map((row) => [row.candidate_code,row.source_revision_id,row.source_row_kind,row.source_row_number,row.source_row_sha256,row.candidate_value_text]);
    const candidateContentSha256 = sha256(Buffer.from(JSON.stringify(candidateRows), "utf8"));
    const wikitextRows = manifest.pages.map((page) => [page.revision_id, page.wikitext_sha256]).sort((a, b) => a[0] - b[0]);
    const wikitextSnapshotSha256 = sha256(Buffer.from(JSON.stringify(wikitextRows), "utf8"));
    if (candidateContentSha256 !== EXPECTED.candidateContentSha256 || wikitextSnapshotSha256 !== EXPECTED.wikitextSnapshotSha256) fail("Wikipedia stable candidate content/Wikitext fingerprint mismatch");
    const counts = {
      sourceDocuments: db.prepare("SELECT count(*) AS n FROM source_documents").get().n,
      candidateRows: db.prepare("SELECT count(*) AS n FROM engine_code_candidates").get().n,
      uniqueCandidateCodes: db.prepare("SELECT count(DISTINCT candidate_code) AS n FROM engine_code_candidates").get().n,
      invalidCandidates: db.prepare("SELECT count(*) AS n FROM engine_code_candidates WHERE market_scope!='UNKNOWN' OR applicability_precision!='community_engine_code_candidate_only' OR review_status!='candidate' OR product_import_allowed!=0 OR exact_vehicle_fitment!=0 OR generation_year_fitment!=0 OR engine_gearbox_fitment!=0 OR ecu_fitment!=0 OR dtc_fitment!=0 OR repair_use_allowed!=0 OR diagnostic_execution_allowed!=0 OR length(source_row_sha256)!=64 OR source_snapshot_sha256!=? OR source_manifest_sha256!=?").get(manifest.source_snapshot_sha256, manifest.source_manifest_sha256).n,
    };
    if (!source || source.data_license !== EXPECTED.license || source.rights_status !== "approved_by_published_license" ||
        source.commercial_use_allowed !== 1 || source.display_allowed !== 1 || source.offline_cache_allowed !== 1 ||
        source.bulk_reuse_allowed !== 1 || source.redistribution_allowed !== 1 || source.attribution_required !== 1 ||
        source.share_alike_required !== 1 || source.separate_pack_required !== 1 ||
        source.market_scope !== "UNKNOWN" || source.applicability_precision !== "community_engine_code_candidate_only" ||
        source.review_status !== "candidate" || source.source_snapshot_sha256 !== manifest.source_snapshot_sha256 ||
        source.source_manifest_sha256 !== manifest.source_manifest_sha256 || counts.sourceDocuments !== EXPECTED.sourceDocuments ||
        counts.candidateRows !== EXPECTED.candidateRows || counts.uniqueCandidateCodes !== EXPECTED.uniqueCandidateCodes ||
        counts.invalidCandidates !== 0) fail("Wikipedia SQLite rights/count/applicability gate failed");
  } finally { db.close(); }
  return { evidence, manifest, sourceManifest, files, candidateContentSha256: EXPECTED.candidateContentSha256, wikitextSnapshotSha256: EXPECTED.wikitextSnapshotSha256 };
}

function patchDesktop(desktopRoot) {
  const apiFile = path.join(desktopRoot, "app", "api", "local-research", "route.ts");
  const uiFile = path.join(desktopRoot, "components", "local-research-catalog.tsx");
  const moduleTarget = path.join(desktopRoot, "lib", "wikipedia-engine-candidates-db.cjs");
  for (const file of [apiFile, uiFile, path.join(desktopRoot, "lib", "local-research-db.cjs")]) {
    if (!fs.existsSync(file)) fail("Desktop source file missing: " + file);
  }
  fs.copyFileSync(path.join(__dirname, "..", "desktop-patches", "wikipedia-engine-candidates-db.cjs"), moduleTarget);

  let route = fs.readFileSync(apiFile, "utf8");
  const routeImport = 'import * as astraTargaResearch from "../../../lib/astra-targa-emissionen-db.cjs";';
  if (!route.includes("wikipediaEngineResearch")) {
    route = replaceOnce(route, routeImport, routeImport + '\nimport * as wikipediaEngineResearch from "../../../lib/wikipedia-engine-candidates-db.cjs";', "Wikipedia API import");
  }
  const summaryAnchor = '    if (dataset === "summary") {\n      return Response.json(localResearch.getResearchSummary(), { headers });\n    }';
  if (!route.includes("wikipediaEngineResearch.getSummary")) {
    route = replaceOnce(route, summaryAnchor,
      '    if (dataset === "summary") {\n      const base = localResearch.getResearchSummary();\n      const wikipediaEngine = wikipediaEngineResearch.getSummary();\n      return Response.json({ ...base, packs: [...base.packs, wikipediaEngine] }, { headers });\n    }',
      "Wikipedia API summary");
  }
  const searchAnchor = '    else if (dataset === "astra-targa") rows = astraTargaResearch.searchAstraTargaRows(query, limit);';
  if (!route.includes('dataset === "wikipedia-engine-candidates"')) {
    route = replaceOnce(route, searchAnchor, searchAnchor + '\n    else if (dataset === "wikipedia-engine-candidates") rows = wikipediaEngineResearch.search(query, limit);', "Wikipedia API search");
  }
  fs.writeFileSync(apiFile, route, "utf8");

  let ui = fs.readFileSync(uiFile, "utf8");
  if (!ui.includes('"wikipedia-engine-candidates"')) {
    ui = replaceOnce(ui,
      '"astra-targa" | "rdw" | "kba-de";',
      '"astra-targa" | "rdw" | "kba-de" | "wikipedia-engine-candidates";',
      "Wikipedia dataset type");
    ui = replaceOnce(ui,
      'shareAlikeRequired?: boolean; attributionRequired?: boolean };',
      'shareAlikeRequired?: boolean; attributionRequired?: boolean; sourceRevision?: string; qualityWarnings?: string[]; productImportAllowed?: boolean; repairUseAllowed?: boolean; diagnosticExecutionAllowed?: boolean; attributionText?: string; licenseNoticeSha256?: string; sourceArtifactSha256?: string; sourceArchiveSha256?: string };',
      "Wikipedia summary type");
    ui = replaceOnce(ui,
      '  sourceLineNo?: number; sourceLineSha256?: string; sourceFileSha256?: string;',
      '  sourceLineNo?: number; sourceLineSha256?: string; sourceFileSha256?: string;\n  sourceRevisionId?: number; revisionTimestamp?: string; sourceTitle?: string; sectionHeading?: string; sourceRowKind?: string; sourceRowNumber?: number; sourceRowText?: string; candidateValueText?: string; sourceRowSha256?: string; qualityWarnings?: string[]; productImportAllowed?: boolean; engineGearboxFitment?: boolean; repairUseAllowed?: boolean; shareAlikeRequired?: boolean;',
      "Wikipedia research row type");
    ui = replaceOnce(ui,
      '  { id: "wikidata-generations", label: "Поколения · кандидаты", hint: "P179/P527 · CC0 · рынок UNKNOWN" },',
      '  { id: "wikidata-generations", label: "Поколения · кандидаты", hint: "P179/P527 · CC0 · рынок UNKNOWN" },\n  { id: "wikipedia-engine-candidates", label: "Двигатели · кандидаты кодов", hint: "Wikipedia · CC BY-SA · 241 кандидатов · не OEM" },',
      "Wikipedia tab");
    ui = replaceOnce(ui,
      'dataset === "wikidata-generations" ? "Модель, серия или QID… например Octavia" :',
      'dataset === "wikidata-generations" ? "Модель, серия или QID… например Octavia" : dataset === "wikipedia-engine-candidates" ? "Код двигателя или фрагмент исходной строки… например CHYA" :',
      "Wikipedia search placeholder");
    ui = replaceOnce(ui,
      '  const wikidata = summary.find((pack) => pack.id === "wikidata-vag-model-taxonomy-cc0");',
      '  const wikidata = summary.find((pack) => pack.id === "wikidata-vag-model-taxonomy-cc0");\n  const wikipediaEngine = summary.find((pack) => pack.id === "wikipedia-vag-engine-code-candidates-cc-by-sa-4-0");',
      "Wikipedia summary binding");
    const cardAnchor = '      <article className="research-stat"><small>Кандидаты серий Wikidata</small><strong>{formatNumber(wikidataGenerationSummary?.counts?.memberEntities)}</strong><span>{formatNumber(wikidataGenerationSummary?.counts?.modelMemberLinks)} связей P179/P527 · CC0 · рынок UNKNOWN</span></article>';
    if (!ui.includes("wikipediaEngine?.counts?.candidateRows")) {
      ui = replaceOnce(ui, cardAnchor, cardAnchor + '\n      <article className="research-stat"><small>Коды двигателей · кандидаты</small><strong>{formatNumber(wikipediaEngine?.counts?.candidateRows)}</strong><span>4 закреплённые редакции · CC BY-SA · рынок UNKNOWN · не OEM</span></article>', "Wikipedia summary card");
    }
    const renderAnchor = '      {dataset === "wikidata" && rows.map((row) => <article className="research-result" key={row.modelQid + "-" + row.manufacturerQid}>';
    const renderBlock = [
      '      {dataset === "wikipedia-engine-candidates" && rows.map((row) => <article className="research-result" key={String(row.sourceRevisionId) + "-" + row.code + "-" + String(row.sourceRowNumber)}>',
      '        <div className="research-result-top"><div><small>WIKIPEDIA · CC BY-SA 4.0 · КАНДИДАТ КОДА ДВИГАТЕЛЯ</small><h3>{row.code}</h3></div><span className="research-candidate">CANDIDATE ONLY</span></div>',
      '        <div className="research-warning-line">Не OEM-подтверждён. Это извлечённый кандидат из community-страницы; он не является применимостью, заводским подтверждением, точной связью с моделью/поколением/годом или парой двигателя и КПП. Не использовать для ремонта, диагностики или подбора деталей.</div>',
      '        <div className="research-data-grid">',
      '          <div><small>Исходная страница</small><b>{row.sourceTitle}</b></div>',
      '          <div><small>Раздел</small><b>{row.sectionHeading || "—"}</b></div>',
      '          <div><small>Редакция</small><b>{row.sourceRevisionId} · {row.revisionTimestamp}</b></div>',
      '          <div><small>Рынок / точность</small><b>{row.marketScope} · {row.applicabilityPrecision}</b></div>',
      '          <div><small>Импорт / fitment</small><b>{String(row.productImportAllowed)} · {String(row.exactVehicleFitment)} · {String(row.engineGearboxFitment)}</b></div>',
      '          <div><small>Ремонт / диагностика</small><b>{String(row.repairUseAllowed)} · {String(row.diagnosticExecutionAllowed)}</b></div>',
      '        </div>',
      '        <p className="research-description">{row.candidateValueText}</p>',
      '        <details className="research-details"><summary>Исходная строка, качество и provenance</summary><pre className="research-attribution">{row.sourceRowText}</pre>',
      '          <p>Тип строки {row.sourceRowKind} · номер строки {row.sourceRowNumber} · SHA строки {row.sourceRowSha256}</p>',
      '          <p>SHA snapshot {row.sourceSnapshotSha256} · SHA source manifest {row.sourceManifestSha256} · SHA SQLite {row.databaseSha256} · SHA pack manifest {row.packManifestSha256}</p>',
      '          <ul>{(row.qualityWarnings || []).map((warning: string) => <li key={warning}>{warning}</li>)}</ul>',
      '        </details>',
      '        <div className="research-source"><span>Wikipedia contributors · CC BY-SA 4.0 · attribution + share-alike · market UNKNOWN · no OEM fitment</span>{row.sourceUrl && <a href={row.sourceUrl} target="_blank" rel="noopener noreferrer">Открыть закреплённую редакцию</a>}</div>',
      '      </article>)}',
      ''
    ].join("\n");
    if (!ui.includes('dataset === "wikipedia-engine-candidates" && rows.map')) ui = replaceOnce(ui, renderAnchor, renderBlock + renderAnchor, "Wikipedia candidate renderer");
    const creditAnchor = '      <p>OBDb community signalsets — CC BY-SA 4.0: <a href="https://github.com/OBDb" target="_blank" rel="noopener noreferrer">OBDb</a>.';
    const creditPos = ui.indexOf(creditAnchor);
    if (creditPos < 0) fail("Wikipedia attribution insertion anchor is missing");
    if (!ui.includes("wikipediaEngine.attributionText")) {
      const insert = [
        '      {wikipediaEngine && <><p><a href="https://en.wikipedia.org/" target="_blank" rel="noopener noreferrer">Wikipedia contributors</a> — CC BY-SA 4.0. Отдельный research pack: 241 candidate rows from four pinned article revisions. Attribution and share-alike are mandatory. The source pages carry original-research, insufficient-citation and incomplete-list warnings; none of these entries is OEM-confirmed or eligible for production import.</p>',
        '        <details className="research-details"><summary>Attribution and pinned source provenance</summary><pre className="research-attribution">{wikipediaEngine.attributionText}</pre>',
        '          <p>Ревизия {wikipediaEngine.sourceRevision} · SHA snapshot {wikipediaEngine.sourceSnapshotSha256} · SHA source manifest {wikipediaEngine.sourceManifestSha256} · SHA SQLite {wikipediaEngine.databaseSha256} · SHA attribution {wikipediaEngine.attributionSha256} · SHA licence notice {wikipediaEngine.licenseNoticeSha256}</p>',
        '          <p>Импорт {String(wikipediaEngine.productImportAllowed)} · ремонт {String(wikipediaEngine.repairUseAllowed)} · диагностика {String(wikipediaEngine.diagnosticExecutionAllowed)} · share-alike {String(wikipediaEngine.shareAlikeRequired)}</p></details></>}',
        ''
      ].join("\n");
      ui = ui.slice(0, creditPos) + insert + ui.slice(creditPos);
    }
  }
  fs.writeFileSync(uiFile, ui, "utf8");

  const dbTest = [
    '"use strict";',
    'const test=require("node:test");',
    'const assert=require("node:assert/strict");',
    'const db=require("../lib/wikipedia-engine-candidates-db.cjs");',
    'test("Wikipedia engine candidate pack verifies CC BY-SA rights and candidate-only counts",()=>{',
    ' const summary=db.getSummary();',
    ' assert.equal(summary.license,"CC-BY-SA-4.0");',
    ' assert.equal(summary.marketScope,"UNKNOWN");',
    ' assert.equal(summary.applicabilityPrecision,"community_engine_code_candidate_only");',
    ' assert.equal(summary.counts.candidateRows,241);',
    ' assert.equal(summary.counts.uniqueCandidateCodes,241);',
    ' assert.equal(summary.counts.sourceDocuments,4);',
    ' assert.equal(summary.productImportAllowed,false);',
    ' assert.equal(summary.exactVehicleFitment,false);',
    ' assert.equal(summary.engineGearboxFitment,false);',
    ' assert.equal(summary.repairUseAllowed,false);',
    ' assert.equal(summary.diagnosticExecutionAllowed,false);',
    ' assert.equal(summary.attributionRequired,true);',
    ' assert.equal(summary.shareAlikeRequired,true);',
    '});',
    'test("Wikipedia engine candidate search preserves row provenance and warnings",()=>{',
    ' const rows=db.search("CHYA",10); assert.ok(rows.length>=1);',
    ' for(const row of rows){',
    '  assert.equal(row.code,"CHYA"); assert.equal(row.marketScope,"UNKNOWN");',
    '  assert.equal(row.applicabilityPrecision,"community_engine_code_candidate_only");',
    '  assert.equal(row.productImportAllowed,false); assert.equal(row.exactVehicleFitment,false);',
    '  assert.equal(row.engineGearboxFitment,false); assert.equal(row.repairUseAllowed,false);',
    '  assert.equal(row.diagnosticExecutionAllowed,false);',
    '  assert.match(row.sourceRowSha256,/^[a-f0-9]{64}$/);',
    '  assert.match(row.sourceSnapshotSha256,/^[a-f0-9]{64}$/);',
    '  assert.match(row.sourceManifestSha256,/^[a-f0-9]{64}$/);',
    '  assert.ok(Array.isArray(row.qualityWarnings));',
    ' }',
    '});',
    'test("Wikipedia candidate search validates user input",()=>{',
    ' assert.throws(()=>db.search("x"),/at least 2 characters/);',
    ' assert.throws(()=>db.search("x".repeat(101)),/too long/);',
    '});',
    ''
  ].join("\n");
  const uiTest = [
    '"use strict";',
    'const fs=require("node:fs"); const path=require("node:path"); const test=require("node:test"); const assert=require("node:assert/strict");',
    'const component=fs.readFileSync(path.join(__dirname,"../components/local-research-catalog.tsx"),"utf8");',
    'const route=fs.readFileSync(path.join(__dirname,"../app/api/local-research/route.ts"),"utf8");',
    'test("Wikipedia engine candidates are isolated as a separate CC BY-SA research tab",()=>{',
    ' assert.match(component,/wikipedia-engine-candidates/); assert.match(component,/CC BY-SA 4\\.0/);',
    ' assert.match(component,/community_engine_code_candidate_only/); assert.match(component,/UNKNOWN/);',
    ' assert.match(component,/productImportAllowed/); assert.match(component,/diagnosticExecutionAllowed/);',
    ' assert.match(component,/qualityWarnings/); assert.match(route,/wikipediaEngineResearch\\.search/);',
    ' assert.match(route,/wikipediaEngineResearch\\.getSummary/);',
    '});',
    'test("Wikipedia engine candidates are never promoted to production applicability",()=>{',
    ' assert.match(component,/не OEM-подтверждён/i); assert.match(component,/не является применимостью/i);',
    ' assert.match(component,/repairUseAllowed/); assert.match(component,/engineGearboxFitment/);',
    '});',
    ''
  ].join("\n");
  fs.writeFileSync(path.join(desktopRoot, "tests", "wikipedia-engine-candidates-db.test.cjs"), dbTest, "utf8");
  fs.writeFileSync(path.join(desktopRoot, "tests", "wikipedia-engine-candidates-ui-contract.test.cjs"), uiTest, "utf8");
  return { module: "lib/wikipedia-engine-candidates-db.cjs", api: "app/api/local-research/route.ts", ui: "components/local-research-catalog.tsx" };
}

function main() {
  const args = parseArgs(process.argv);
  const desktopRoot = path.resolve(args["desktop-root"]);
  const packDir = path.resolve(args["pack-dir"]);
  const evidenceFile = path.resolve(args["build-evidence"]);
  if (!fs.statSync(desktopRoot).isDirectory() || !fs.statSync(packDir).isDirectory()) fail("Desktop root or pack directory is missing");
  const verified = verifyPack(packDir, evidenceFile, args);
  const researchRoot = path.join(desktopRoot, "data", "research");
  const target = path.join(researchRoot, TARGET_DIR);
  fs.mkdirSync(researchRoot, { recursive: true });
  if (fs.existsSync(target)) {
    const existingDb = path.join(target, "wikipedia-vag-engine-candidates.sqlite");
    if (!fs.existsSync(existingDb) || sha256File(existingDb) !== EXPECTED.databaseSha256) fail("Existing Wikipedia pack differs; refusing overwrite");
  } else {
    fs.cpSync(packDir, target, { recursive: true, errorOnExist: true });
  }
  const provenance = {
    schema_version: 1,
    pack_id: PACK_ID,
    source_workflow_run_id: Number(args["artifact-run-id"]),
    source_artifact_id: Number(args["artifact-id"]),
    source_artifact_sha256: args["artifact-sha256"],
    source_archive_sha256: verified.evidence.artifact_sha256,
    source_commit: args["source-commit"],
    source_head_sha: args["source-head-sha"],
    source_event: args["source-event"],
    source_ref: args["source-ref"],
    source_snapshot_sha256: verified.manifest.source_snapshot_sha256,
    wikitext_snapshot_sha256: verified.wikitextSnapshotSha256,
    candidate_content_sha256: verified.candidateContentSha256,
    database_sha256: verified.manifest.database_sha256,
    source_manifest_sha256: verified.manifest.source_manifest_sha256,
    built_at_utc: verified.manifest.built_at_utc,
  };
  const provenancePath = path.join(target, "build-provenance.json");
  fs.writeFileSync(provenancePath, JSON.stringify(provenance, null, 2) + "\n", "utf8");
  const rootManifestPath = path.join(researchRoot, "manifest.json");
  const rootManifest = readJson(rootManifestPath);
  if (rootManifest.schema_version !== 1 || !Array.isArray(rootManifest.packs)) fail("Desktop research manifest schema mismatch");
  const existingEntry = rootManifest.packs.find((p) => p.id === PACK_ID);
  const relative = (name) => path.posix.join(TARGET_DIR, name);
  const entry = {
    id: PACK_ID,
    kind: "community_engine_code_candidates",
    database: relative("wikipedia-vag-engine-candidates.sqlite"),
    database_sha256: verified.manifest.database_sha256,
    license: EXPECTED.license,
    license_status: "approved_by_published_license",
    license_url: "https://creativecommons.org/licenses/by-sa/4.0/",
    commercial_use_allowed: true,
    display_allowed: true,
    cache_allowed: true,
    offline_cache_allowed: true,
    bulk_reuse_allowed: true,
    redistribution_allowed: true,
    attribution_required: true,
    share_alike_required: true,
    separate_pack_required: true,
    publisher: "Wikipedia contributors",
    dataset: "Volkswagen Group engine-code list candidates",
    source_url: "https://en.wikipedia.org/",
    source_id: SOURCE_ID,
    source_revision: verified.manifest.source_revision,
    source_snapshot_sha256: verified.manifest.source_snapshot_sha256,
    wikitext_snapshot_sha256: verified.wikitextSnapshotSha256,
    candidate_content_sha256: verified.candidateContentSha256,
    source_manifest_file: relative("source-manifest.json"),
    source_manifest_sha256: verified.manifest.source_manifest_sha256,
    pack_manifest_file: relative("manifest.json"),
    pack_manifest_sha256: sha256File(path.join(target, "manifest.json")),
    attribution_file: relative("ATTRIBUTION.md"),
    attribution_sha256: verified.manifest.attribution_sha256,
    license_notice_file: relative("LICENSE-NOTICE.txt"),
    license_notice_sha256: verified.manifest.license_notice_sha256,
    build_provenance_file: relative("build-provenance.json"),
    build_provenance_sha256: sha256File(provenancePath),
    source_artifact_sha256: args["artifact-sha256"],
    source_archive_sha256: verified.evidence.artifact_sha256,
    source_workflow_run_id: Number(args["artifact-run-id"]),
    source_artifact_id: Number(args["artifact-id"]),
    source_commit: args["source-commit"],
    source_head_sha: args["source-head-sha"],
    source_event: args["source-event"],
    source_ref: args["source-ref"],
    counts: verified.manifest.counts,
    market_scope: "UNKNOWN",
    applicability_precision: "community_engine_code_candidate_only",
    review_status: "community_reference_unverified",
    quality_review_status: "not_approved_for_technical_use",
    candidate_only: true,
    product_import_allowed: false,
    exact_vehicle_fitment: false,
    generation_year_fitment: false,
    engine_gearbox_fitment: false,
    ecu_fitment: false,
    dtc_fitment: false,
    repair_use_allowed: false,
    diagnostic_execution_allowed: false,
    included_in_product: true,
    product_eligibility: "candidate_only_not_oem_verified",
    status: "research_only",
    quality_warnings: verified.manifest.quality_warnings,
  };
  if (existingEntry) {
    if (existingEntry.database_sha256 !== entry.database_sha256 || existingEntry.pack_manifest_sha256 !== entry.pack_manifest_sha256) fail("Existing Wikipedia manifest entry differs; refusing replace");
  } else rootManifest.packs.push(entry);
  fs.writeFileSync(rootManifestPath, JSON.stringify(rootManifest, null, 2) + "\n", "utf8");
  const desktop = patchDesktop(desktopRoot);
  console.log(JSON.stringify({
    status: existingEntry ? "already_integrated" : "integrated",
    pack_id: PACK_ID,
    counts: entry.counts,
    database_sha256: entry.database_sha256,
    source_manifest_sha256: entry.source_manifest_sha256,
    source_artifact_sha256: entry.source_artifact_sha256,
    desktop,
  }, null, 2));
}
main();

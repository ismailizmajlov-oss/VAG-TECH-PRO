"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const Module = require("node:module");
const { execFileSync } = require("node:child_process");
const core = require("../lib/local-core-db.cjs");

function loadTypescript() {
  try { return require("typescript"); }
  catch {
    try {
      const globalRoot = execFileSync("npm", ["root", "-g"], { encoding: "utf8" }).trim();
      return require(path.join(globalRoot, "typescript"));
    } catch { return null; }
  }
}
const ts = loadTypescript();

test("local-core API seeds bundled CC0 Wikidata candidates once and exposes provenance to the administrator", { skip: !ts && "TypeScript is unavailable; install pinned dev dependencies" }, async (t) => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "vag-wikidata-route-"));
  const dbPath = path.join(root, "data", "vag-tech-pro.sqlite");
  const oldDb = process.env.VAG_TECH_PRO_DB_PATH;
  const oldResearch = process.env.VAG_TECH_PRO_RESEARCH_DIR;
  t.after(() => {
    if (oldDb === undefined) delete process.env.VAG_TECH_PRO_DB_PATH; else process.env.VAG_TECH_PRO_DB_PATH = oldDb;
    if (oldResearch === undefined) delete process.env.VAG_TECH_PRO_RESEARCH_DIR; else process.env.VAG_TECH_PRO_RESEARCH_DIR = oldResearch;
    fs.rmSync(root, { recursive: true, force: true });
  });
  core.initializeDatabase(dbPath);
  process.env.VAG_TECH_PRO_DB_PATH = dbPath;
  process.env.VAG_TECH_PRO_RESEARCH_DIR = path.resolve(__dirname, "../data/research");
  const routePath = path.resolve(__dirname, "../app/api/local-core/route.ts");
  const source = fs.readFileSync(routePath, "utf8");
  const compiled = ts.transpileModule(source, { compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS, esModuleInterop: true }, fileName: routePath }).outputText;
  const routeModule = new Module(routePath, module);
  routeModule.filename = routePath;
  routeModule.paths = Module._nodeModulePaths(path.dirname(routePath));
  routeModule._compile(compiled, routePath);
  const { GET } = routeModule.exports;
  const url = "http://127.0.0.1:43125/api/local-core?action=admin-summary";
  const request = () => new Request(url, { headers: { host: "127.0.0.1:43125", origin: "http://127.0.0.1:43125" } });
  const response = await GET(request());
  assert.equal(response.status, 200);
  const admin = await response.json();
  assert.equal(admin.mode, "offline_local_sqlite_admin");
  assert.equal(admin.bundledCatalogSeed.status, "applied");
  assert.equal(admin.bundledCatalogSeed.source_id, "wikidata-vag-model-taxonomy");
  assert.equal(admin.bundledCatalogSeed.models, 521);
  assert.equal(admin.bundledCatalogSeed.manufacturers, 6);
  assert.equal(admin.bundledCatalogSeed.verified_models, 0);
  assert.equal(admin.bundledCatalogSeed.exact_fitments, 0);
  assert.equal(admin.sources.length, 1);
  assert.equal(admin.sources[0].record_count, 527);
  assert.equal(admin.sources[0].market_scope, "UNKNOWN");
  assert.equal(admin.sources[0].rights_status, "approved_by_published_license");
  assert.equal(admin.reviewQueue.length, 527);
  assert.equal(admin.reviewQueue.filter((row) => row.entity_type === "vehicle_model" && row.review_status === "candidate" && row.applicability_precision === "vehicle_model_candidate").length, 521);
  assert.equal(admin.reviewQueue.filter((row) => row.entity_type === "brand" && row.review_status === "candidate" && row.applicability_precision === "manufacturer_make_candidate").length, 6);
  assert.equal(admin.importBatches.length, 1);
  assert.equal(admin.importBatches[0].package_id, "wikidata-vag-model-taxonomy-cc0-630dbed1af15");
  assert.equal(admin.importBatches[0].status, "applied");
  assert.equal(admin.importBatches[0].records_inserted, 527);
  assert.equal(admin.importBatches[0].package_sha256, "52c4b195d8200594aca1cec2de93f64f8fbe94a746dea0406715da7348e057d2");
  assert.equal(admin.bundledCatalogSeed.packageSha256, "52c4b195d8200594aca1cec2de93f64f8fbe94a746dea0406715da7348e057d2");
  assert.deepEqual(admin.moduleCoverage, []);

  const repeated = await GET(request());
  assert.equal(repeated.status, 200);
  const again = await repeated.json();
  assert.equal(again.bundledCatalogSeed.status, "applied");
  assert.equal(core.listSources(dbPath).length, 1);
  assert.equal(core.listReviewQueue(dbPath, 1000).length, 527);
});

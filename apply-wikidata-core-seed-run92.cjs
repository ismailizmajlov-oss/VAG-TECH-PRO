"use strict";
const fs = require("node:fs");
const path = require("node:path");
const crypto = require("node:crypto");

function argument(name, fallback) {
  const index = process.argv.indexOf(name);
  return index >= 0 && process.argv[index + 1] ? process.argv[index + 1] : fallback;
}
const desktopRoot = path.resolve(argument("--desktop-root", "desktop-source"));
const repoRoot = __dirname;
const required = [
  "lib/local-core-db.cjs",
  "app/api/local-core/route.ts",
  "scripts/windows-installer-lifecycle.ps1",
  "package.json",
  "data/research/wikidata-vag-model-taxonomy-cc0/manifest.json",
];
for (const relative of required) {
  if (!fs.existsSync(path.join(desktopRoot, relative))) throw new Error("Wikidata core-seed patch requires " + relative);
}

function copy(relativeSource, relativeTarget) {
  const source = path.join(repoRoot, relativeSource);
  const target = path.join(desktopRoot, relativeTarget);
  if (!fs.existsSync(source)) throw new Error("Wikidata core-seed patch source is missing: " + relativeSource);
  fs.mkdirSync(path.dirname(target), { recursive: true });
  fs.copyFileSync(source, target);
}
copy("desktop/wikidata-candidate-seed.cjs", "lib/wikidata-candidate-seed.cjs");
copy("desktop/wikidata-candidate-seed.d.cts", "lib/wikidata-candidate-seed.d.cts");
copy("desktop/tests/wikidata-core-catalog-seed.test.cjs", "tests/wikidata-core-catalog-seed.test.cjs");
copy("desktop/tests/wikidata-core-catalog-seed-route.test.cjs", "tests/wikidata-core-catalog-seed-route.test.cjs");

const routePath = path.join(desktopRoot, "app/api/local-core/route.ts");
let route = fs.readFileSync(routePath, "utf8").replace(/\r\n/g, "\n");
const importAnchor = 'import * as localCore from "../../../lib/local-core-db.cjs";';
const seedImport = 'import { seedWikidataCandidateCatalog } from "../../../lib/wikidata-candidate-seed.cjs";';
if (!route.includes(importAnchor)) throw new Error("Unexpected local-core route import contract");
if (!route.includes(seedImport)) route = route.replace(importAnchor, importAnchor + "\n" + seedImport);
if (!route.includes("function seedBundledCatalogOnce(dbPath: string)")) {
  const headerAnchor = '  "Referrer-Policy": "no-referrer",\n};';
  if (!route.includes(headerAnchor)) throw new Error("Unexpected local-core route headers");
  const helper = fs.readFileSync(path.join(repoRoot, "desktop/wikidata-seed-route-helper.ts"), "utf8");
  route = route.replace(headerAnchor, headerAnchor + "\n\n" + helper.trimEnd());
}
const getAnchor = '  if (!isLocalRequest(request)) return Response.json({ error: "Local loopback request rejected" }, { status: 403, headers });\n  const url = new URL(request.url);';
if (!route.includes("const bundledCatalogSeed = seedBundledCatalogOnce(dbPath);")) {
  if (!route.includes(getAnchor)) throw new Error("Unexpected local-core GET request guard");
  route = route.replace(getAnchor, '  if (!isLocalRequest(request)) return Response.json({ error: "Local loopback request rejected" }, { status: 403, headers });\n  const bundledCatalogSeed = seedBundledCatalogOnce(dbPath);\n  const url = new URL(request.url);');
}
const postAnchor = '  if (!isSameOriginMutation(request)) return Response.json({ error: "Cross-origin local database mutation is blocked" }, { status: 403, headers });\n  const contentType = request.headers.get("content-type") || "";';
if (!route.includes("  seedBundledCatalogOnce(dbPath);")) {
  if (!route.includes(postAnchor)) throw new Error("Unexpected local-core POST mutation guard");
  route = route.replace(postAnchor, '  if (!isSameOriginMutation(request)) return Response.json({ error: "Cross-origin local database mutation is blocked" }, { status: 403, headers });\n  seedBundledCatalogOnce(dbPath);\n  const contentType = request.headers.get("content-type") || "";');
}
route = route.replace('mode: "offline_local_sqlite",\n        schemaVersion: localCore.SCHEMA_VERSION,', 'mode: "offline_local_sqlite",\n        schemaVersion: localCore.SCHEMA_VERSION,\n        bundledCatalogSeed,');
route = route.replace('mode: "offline_local_sqlite_admin",\n      schemaVersion: localCore.SCHEMA_VERSION,', 'mode: "offline_local_sqlite_admin",\n      schemaVersion: localCore.SCHEMA_VERSION,\n      bundledCatalogSeed,');
fs.writeFileSync(routePath, route, "utf8");

const packagePath = path.join(desktopRoot, "package.json");
const packageJson = JSON.parse(fs.readFileSync(packagePath, "utf8"));
let localCoreScript = packageJson.scripts && packageJson.scripts["test:local-core"];
if (typeof localCoreScript !== "string") throw new Error("Desktop package has no test:local-core script");
for (const file of ["tests/wikidata-core-catalog-seed.test.cjs", "tests/wikidata-core-catalog-seed-route.test.cjs"]) {
  if (!localCoreScript.includes(file)) localCoreScript += " " + file;
}
packageJson.scripts["test:local-core"] = localCoreScript;
fs.writeFileSync(packagePath, JSON.stringify(packageJson, null, 2) + "\n", "utf8");

const lifecyclePath = path.join(desktopRoot, "scripts/windows-installer-lifecycle.ps1");
let lifecycle = fs.readFileSync(lifecyclePath, "utf8").replace(/\r\n/g, "\n");
const lifecycleAnchor = '  if ($summary.mode -ne "offline_local_sqlite_admin") { throw "The local SQLite API did not initialize in offline mode." }';
if (!lifecycle.includes("Bundled Wikidata core seed did not remain a candidate-only identity import.")) {
  if (!lifecycle.includes(lifecycleAnchor)) throw new Error("Unexpected Windows installer lifecycle summary check");
  const lifecycleCheck = fs.readFileSync(path.join(repoRoot, "desktop/wikidata-seed-lifecycle-check.ps1"), "utf8").trimEnd();
  lifecycle = lifecycle.replace(lifecycleAnchor, lifecycleAnchor + "\n" + lifecycleCheck);
}
fs.writeFileSync(lifecyclePath, lifecycle, "utf8");

const patchCopy = path.join(desktopRoot, "scripts/patches/apply-wikidata-core-seed-run92.cjs");
fs.mkdirSync(path.dirname(patchCopy), { recursive: true });
fs.copyFileSync(__filename, patchCopy);
const hash = (file) => crypto.createHash("sha256").update(fs.readFileSync(file)).digest("hex");
const result = {
  patch: "run92-wikidata-cc0-core-candidate-seed",
  desktop_root: desktopRoot,
  helper_sha256: hash(path.join(desktopRoot, "lib/wikidata-candidate-seed.cjs")),
  helper_declaration_sha256: hash(path.join(desktopRoot, "lib/wikidata-candidate-seed.d.cts")),
  route_sha256: hash(routePath),
  lifecycle_sha256: hash(lifecyclePath),
  package_json_sha256: hash(packagePath),
  model_candidates: 521,
  manufacturer_candidates: 6,
  imported_records: 527,
  market_scope: "UNKNOWN",
  applicability_precision: "candidate_identity_only",
  verified_models: 0,
  exact_fitments: 0,
  engine_codes: 0,
  transmission_codes: 0,
};
fs.writeFileSync(path.join(repoRoot, "wikidata-core-seed-run92.log"), JSON.stringify(result, null, 2) + "\n", "utf8");
console.log(JSON.stringify(result));

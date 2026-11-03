"use strict";
const fs = require("node:fs");
const path = require("node:path");

const root = path.resolve(process.cwd(), "desktop-source");
const mainPath = path.join(root, "electron", "main.cjs");
const testPath = path.join(root, "tests", "desktop-runtime.test.cjs");
const packagePath = path.join(root, "package.json");
const pkg = JSON.parse(fs.readFileSync(packagePath, "utf8"));
for (const name of ["test", "test:desktop", "test:local-core", "test:research", "verify:local-core", "verify:local-research", "build:desktop"]) {
  if (!pkg.scripts || typeof pkg.scripts[name] !== "string") throw new Error(`Desktop package script is missing: ${name}`);
}

function readLf(file) {
  return fs.readFileSync(file, "utf8").replace(/\r\n/g, "\n");
}
function writeLf(file, value) {
  fs.writeFileSync(file, value.replace(/\r\n/g, "\n"), { encoding: "utf8" });
}
function replaceExactly(source, before, after, label) {
  if (source.includes(after)) return source;
  const count = source.split(before).length - 1;
  if (count !== 1) throw new Error(`${label}: expected one original block or an already-applied replacement; found ${count}`);
  return source.replace(before, after);
}

let main = readLf(mainPath);
main = replaceExactly(
  main,
  "resolve(response.statusCode >= 200 && response.statusCode < 500);",
  "resolve(response.statusCode >= 200 && response.statusCode < 400);",
  "HTTP readiness status range"
);
main = replaceExactly(
  main,
  [
    '    mainWindow.webContents.on("will-navigate", (event, target) => {',
    '      try { if (new URL(target).origin !== localOrigin) event.preventDefault(); }',
    '      catch { event.preventDefault(); }',
    '    });'
  ].join("\n"),
  [
    '    const blockNonLocalNavigation = (event, target) => {',
    '      try { if (new URL(target).origin !== localOrigin) event.preventDefault(); }',
    '      catch { event.preventDefault(); }',
    '    };',
    '    mainWindow.webContents.on("will-navigate", blockNonLocalNavigation);',
    '    mainWindow.webContents.on("will-redirect", blockNonLocalNavigation);'
  ].join("\n"),
  "local-origin navigation and redirect guard"
);
if (!main.includes("response.statusCode < 400") || !main.includes('webContents.on("will-redirect", blockNonLocalNavigation)')) {
  throw new Error("Electron hardening verification failed after patch.");
}
writeLf(mainPath, main);

let tests = readLf(testPath);
tests = replaceExactly(
  tests,
  'const path = require("node:path");\n',
  'const path = require("node:path");\nconst http = require("node:http");\n',
  "HTTP test import"
);
const anchor = [
  'test("health probe rejects an unused local port", async () => {',
  '  assert.equal(await probeHttp("http://127.0.0.1:1", 200), false);',
  '});'
].join("\n");
const regressionTests = [
  anchor,
  '',
  'test("health probe rejects HTTP 4xx and 5xx responses", async () => {',
  '  for (const statusCode of [401, 404, 500, 503]) {',
  '    const server = http.createServer((_request, response) => {',
  '      response.statusCode = statusCode;',
  '      response.end("not ready");',
  '    });',
  '    await new Promise((resolve, reject) => {',
  '      server.once("error", reject);',
  '      server.listen(0, "127.0.0.1", resolve);',
  '    });',
  '    const { port } = server.address();',
  '    assert.equal(await probeHttp(`http://127.0.0.1:${port}`, 500), false, `status ${statusCode}`);',
  '    await new Promise((resolve) => server.close(resolve));',
  '  }',
  '});',
  '',
  'test("health probe accepts HTTP 2xx and 3xx responses", async () => {',
  '  for (const statusCode of [200, 302, 307]) {',
  '    const server = http.createServer((_request, response) => {',
  '      response.statusCode = statusCode;',
  '      response.end("ready");',
  '    });',
  '    await new Promise((resolve, reject) => {',
  '      server.once("error", reject);',
  '      server.listen(0, "127.0.0.1", resolve);',
  '    });',
  '    const { port } = server.address();',
  '    assert.equal(await probeHttp(`http://127.0.0.1:${port}`, 500), true, `status ${statusCode}`);',
  '    await new Promise((resolve) => server.close(resolve));',
  '  }',
  '});'
].join("\n");
if (!tests.includes('test("health probe rejects HTTP 4xx and 5xx responses"')) {
  if (!tests.includes(anchor)) throw new Error("Health probe regression-test insertion anchor not found.");
  tests = tests.replace(anchor, regressionTests);
}
const sandboxAnchor = '  assert.match(source, /sandbox:\\s*true/);';
const sandboxReplacement = `${sandboxAnchor}\n  assert.match(source, /webContents\\.on\\("will-redirect", blockNonLocalNavigation\\)/);`;
tests = replaceExactly(tests, sandboxAnchor, sandboxReplacement, "redirect guard test assertion");
if (!tests.includes('test("health probe rejects HTTP 4xx and 5xx responses"') || !tests.includes('webContents\\.on\\("will-redirect", blockNonLocalNavigation\\)')) {
  throw new Error("Electron regression test verification failed after patch.");
}
writeLf(testPath, tests);

// Defer React data-loading effects so they do not synchronously cascade state updates.
const adminPagePath = path.join(root, "app", "admin", "page.tsx");
let adminPage = readLf(adminPagePath);
adminPage = replaceExactly(
  adminPage,
  "    void loadWorkspace();",
  "    const initialLoadTimer = window.setTimeout(() => { if (active) void loadWorkspace(); }, 0);",
  "admin initial workspace load"
);
adminPage = replaceExactly(
  adminPage,
  "      active = false;\n      loadSequence.current += 1;",
  "      active = false;\n      window.clearTimeout(initialLoadTimer);\n      loadSequence.current += 1;",
  "admin initial workspace timer cleanup"
);
writeLf(adminPagePath, adminPage);

const localAdminPath = path.join(root, "components", "local-data-admin.tsx");
let localAdmin = readLf(localAdminPath);
localAdmin = replaceExactly(
  localAdmin,
  "  useEffect(() => { void refresh(); }, [refresh]);",
  [
    "  useEffect(() => {",
    "    let active = true;",
    "    const refreshTimer = window.setTimeout(() => { if (active) void refresh(); }, 0);",
    "    return () => { active = false; window.clearTimeout(refreshTimer); };",
    "  }, [refresh]);"
  ].join("\n"),
  "local admin deferred refresh effect"
);
writeLf(localAdminPath, localAdmin);

const localWorkspacePath = path.join(root, "components", "local-offline-workspace.tsx");
let localWorkspace = readLf(localWorkspacePath);
localWorkspace = replaceExactly(
  localWorkspace,
  "  useEffect(() => { void loadSummary(); }, [loadSummary]);",
  [
    "  useEffect(() => {",
    "    let active = true;",
    "    const summaryTimer = window.setTimeout(() => { if (active) void loadSummary(); }, 0);",
    "    return () => { active = false; window.clearTimeout(summaryTimer); };",
    "  }, [loadSummary]);"
  ].join("\n"),
  "local workspace deferred summary effect"
);
writeLf(localWorkspacePath, localWorkspace);

const coreTestPath = path.join(root, "tests", "local-core-db.test.cjs");
let coreTests = readLf(coreTestPath);
coreTests = replaceExactly(
  coreTests,
  "  const now = new Date().toISOString();\n  seedSourceSnapshot(db,sourceId);",
  "  seedSourceSnapshot(db,sourceId);",
  "unused test timestamp"
);
writeLf(coreTestPath, coreTests);

const uiTestPath = path.join(root, "tests", "local-data-admin-ui-contract.test.cjs");
let uiTests = readLf(uiTestPath);
const uiEffectTest = [
  "",
  'test("async React loaders are deferred from effects and cleaned up on unmount", () => {',
  '  const adminPage = read("app/admin/page.tsx");',
  '  const localAdmin = read("components/local-data-admin.tsx");',
  '  const workspace = read("components/local-offline-workspace.tsx");',
  '  assert.match(adminPage, /const initialLoadTimer = window\\.setTimeout\\(\\(\\) => \\{ if \\(active\\) void loadWorkspace\\(\\); \\}, 0\\);/);',
  '  assert.match(adminPage, /window\\.clearTimeout\\(initialLoadTimer\\)/);',
  '  assert.match(localAdmin, /const refreshTimer = window\\.setTimeout\\(\\(\\) => \\{ if \\(active\\) void refresh\\(\\); \\}, 0\\);/);',
  '  assert.match(localAdmin, /window\\.clearTimeout\\(refreshTimer\\)/);',
  '  assert.match(workspace, /const summaryTimer = window\\.setTimeout\\(\\(\\) => \\{ if \\(active\\) void loadSummary\\(\\); \\}, 0\\);/);',
  '  assert.match(workspace, /window\\.clearTimeout\\(summaryTimer\\)/);',
  '});',
  ""
].join("\n");
if (!uiTests.includes("async React loaders are deferred from effects")) uiTests += uiEffectTest;
writeLf(uiTestPath, uiTests);

for (const [file, source, required] of [
  ["admin page", adminPage, "window.clearTimeout(initialLoadTimer)"],
  ["local admin", localAdmin, "window.clearTimeout(refreshTimer)"],
  ["local workspace", localWorkspace, "window.clearTimeout(summaryTimer)"],
  ["UI regression tests", uiTests, "async React loaders are deferred from effects"]
]) {
  if (!source.includes(required)) throw new Error("React effect hardening verification failed: " + file);
}
// Resolve the desktop's heterogeneous Supabase row typing without lying about relation cardinality.
const homePagePath = path.join(root, "app", "page.tsx");
let homePage = readLf(homePagePath);
const dbRowStart = homePage.indexOf("type DbRow =");
const moduleInfoAt = dbRowStart >= 0 ? homePage.indexOf("\nconst moduleInfo", dbRowStart) : -1;
if (dbRowStart < 0 || moduleInfoAt < 0) throw new Error("Could not locate the home-page DbRow type alias");
homePage = homePage.slice(0, dbRowStart) + "type DbRow = Record<string, any>;\n" + homePage.slice(moduleInfoAt + 1);
homePage = replaceExactly(
  homePage,
  "  }, [globalQuery, catalogOnline]);",
  "  }, [globalQuery, catalogOnline, query]);",
  "home page keyboard search dependency"
);
writeLf(homePagePath, homePage);

const researchCatalogPath = path.join(root, "components", "local-research-catalog.tsx");
let researchCatalog = readLf(researchCatalogPath);
researchCatalog = researchCatalog
  .replace(/row\.affectedComponents\.length/g, "row.affectedComponents?.length")
  .replace(/row\.affectedComponents\.map/g, "row.affectedComponents?.map")
  .replace(/row\.commonCauses\.length/g, "row.commonCauses?.length")
  .replace(/row\.commonCauses\.map/g, "row.commonCauses?.map");
writeLf(researchCatalogPath, researchCatalog);

const loginPagePath = path.join(root, "app", "login", "page.tsx");
let loginPage = readLf(loginPagePath);
if (!loginPage.includes('import { useRouter } from "next/navigation";')) {
  loginPage = replaceExactly(
    loginPage,
    'import { FormEvent, useMemo, useState } from "react";',
    'import { FormEvent, useMemo, useState } from "react";\nimport { useRouter } from "next/navigation";',
    "login router import"
  );
}
if (!loginPage.includes("const router=useRouter();")) {
  loginPage = replaceExactly(
    loginPage,
    "export default function LoginPage(){",
    "export default function LoginPage(){\n const router=useRouter();",
    "login router hook"
  );
}
loginPage = replaceExactly(loginPage, 'window.location.href="/";', 'router.push("/");', "login internal navigation");
writeLf(loginPagePath, loginPage);

let coreTestsFinal = readLf(coreTestPath);
coreTestsFinal = coreTestsFinal.replace(/^\s*const now = new Date\(\)\.toISOString\(\);\r?\n(?=\s*seedSourceSnapshot)/m, "");
writeLf(coreTestPath, coreTestsFinal);

if (!homePage.includes("type DbRow = Record<string, any>;") ||
    !researchCatalog.includes("row.affectedComponents?.length") ||
    !researchCatalog.includes("row.commonCauses?.length") ||
    !loginPage.includes('router.push("/");')) {
  throw new Error("TypeScript/lint hardening verification failed");
}
console.log("Desktop hardening, React effect, TypeScript and lint fixes applied and verified.");

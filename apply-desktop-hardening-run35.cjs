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
const sourceResource = (pkg.build && Array.isArray(pkg.build.extraResources) ? pkg.build.extraResources : [])
  .find((item) => item && item.from === "data/source-manifests" && item.to === "source-manifests");
if (!sourceResource) throw new Error("Windows package must include data/source-manifests as resources/source-manifests.");
if (pkg.build.afterPack !== "scripts/verify-source-register-after-pack.cjs") throw new Error("Windows package must verify the packaged source-rights register afterPack.");
const sourceRegisterVerifierPath = path.join(root, "scripts", "verify-source-register-after-pack.cjs");
fs.mkdirSync(path.dirname(sourceRegisterVerifierPath), { recursive: true });
fs.writeFileSync(sourceRegisterVerifierPath, "\"use strict\";\nconst fs = require(\"node:fs\");\nconst path = require(\"node:path\");\nconst crypto = require(\"node:crypto\");\nfunction fail(message) { throw new Error(message); }\nfunction readRegular(file) {\n  let stat;\n  try { stat = fs.lstatSync(file); } catch (error) { fail(\"Source-register packaging file is missing: \" + file + \": \" + error.message); }\n  if (!stat.isFile() || stat.isSymbolicLink()) fail(\"Source-register packaging path is not a regular file: \" + file);\n  return fs.readFileSync(file);\n}\nasync function verify(context, sourceRoot = process.cwd()) {\n  if (!context || typeof context.appOutDir !== \"string\" || !context.appOutDir) fail(\"electron-builder afterPack context has no appOutDir\");\n  const root = path.resolve(sourceRoot);\n  const source = path.join(root, \"data\", \"source-manifests\", \"vag-factory-source-register.json\");\n  const packaged = path.join(context.appOutDir, \"resources\", \"source-manifests\", \"vag-factory-source-register.json\");\n  const sourceBytes = readRegular(source);\n  const packagedBytes = readRegular(packaged);\n  const sourceHash = crypto.createHash(\"sha256\").update(sourceBytes).digest(\"hex\");\n  const packagedHash = crypto.createHash(\"sha256\").update(packagedBytes).digest(\"hex\");\n  if (sourceHash !== packagedHash) fail(\"Packaged source-rights register SHA-256 mismatch: expected \" + sourceHash + \", got \" + packagedHash);\n  let manifest;\n  try { manifest = JSON.parse(packagedBytes.toString(\"utf8\")); } catch (error) { fail(\"Packaged source-rights register is invalid JSON: \" + error.message); }\n  if (!manifest || !Array.isArray(manifest.sources) || manifest.sources.length < 1 || typeof manifest.updated_at !== \"string\" || !manifest.updated_at.trim()) fail(\"Packaged source-rights register has an invalid schema\");\n  const seen = new Set();\n  for (const sourceEntry of manifest.sources) {\n    if (!sourceEntry || typeof sourceEntry.source_id !== \"string\" || !sourceEntry.source_id.trim() || seen.has(sourceEntry.source_id)) fail(\"Packaged source-rights register has a missing or duplicate source_id\");\n    seen.add(sourceEntry.source_id);\n    const rights = sourceEntry.rights && typeof sourceEntry.rights === \"object\" ? sourceEntry.rights : {};\n    const permission = String(rights.permission_status || \"\").toLowerCase();\n    const verification = String(sourceEntry.verification_status || \"\").toLowerCase();\n    const restricted = [\"not_cleared\", \"not_obtained\"].includes(permission) || verification.includes(\"quarantined\");\n    if (restricted && sourceEntry.data_ingested === true) fail(\"Restricted source is marked ingested in packaged register: \" + sourceEntry.source_id);\n  }\n  const result = { status: \"verified_packaged_source_register\", sha256: sourceHash, source_count: seen.size, updated_at: manifest.updated_at };\n  console.log(\"[source-register-after-pack] \" + JSON.stringify(result));\n  return result;\n}\nmodule.exports = verify;\nmodule.exports.verify = verify;\n", { encoding: "utf8" });
const sourceRegisterTestPath = path.join(root, "tests", "source-register-after-pack.test.cjs");
fs.writeFileSync(sourceRegisterTestPath, "\"use strict\";\nconst assert = require(\"node:assert/strict\");\nconst crypto = require(\"node:crypto\");\nconst fs = require(\"node:fs\");\nconst os = require(\"node:os\");\nconst path = require(\"node:path\");\nconst test = require(\"node:test\");\nconst verify = require(\"../scripts/verify-source-register-after-pack.cjs\");\nfunction fixture() {\n  const root = fs.mkdtempSync(path.join(os.tmpdir(), \"vag-source-register-pack-\"));\n  const sourceDir = path.join(root, \"data\", \"source-manifests\");\n  const appOutDir = path.join(root, \"win-unpacked\");\n  const packagedDir = path.join(appOutDir, \"resources\", \"source-manifests\");\n  fs.mkdirSync(sourceDir, { recursive: true });\n  fs.mkdirSync(packagedDir, { recursive: true });\n  const manifest = { updated_at: \"2026-11-06\", sources: [\n    { source_id: \"cc0-example\", data_ingested: true, rights: { permission_status: \"verified\" } },\n    { source_id: \"quarantined-example\", data_ingested: false, verification_status: \"quarantined\", rights: { permission_status: \"not_obtained\" } }\n  ] };\n  const bytes = Buffer.from(JSON.stringify(manifest) + \"\\n\", \"utf8\");\n  const source = path.join(sourceDir, \"vag-factory-source-register.json\");\n  const packaged = path.join(packagedDir, \"vag-factory-source-register.json\");\n  fs.writeFileSync(source, bytes);\n  fs.writeFileSync(packaged, bytes);\n  return { root, appOutDir, source, packaged, bytes };\n}\ntest(\"afterPack accepts the exact source-rights register copied into resources\", async () => {\n  const f = fixture();\n  try {\n    const result = await verify({ appOutDir: f.appOutDir }, f.root);\n    assert.equal(result.status, \"verified_packaged_source_register\");\n    assert.equal(result.source_count, 2);\n    assert.equal(result.sha256, crypto.createHash(\"sha256\").update(f.bytes).digest(\"hex\"));\n  } finally { fs.rmSync(f.root, { recursive: true, force: true }); }\n});\ntest(\"afterPack rejects a missing packaged source-rights register\", async () => {\n  const f = fixture();\n  try {\n    fs.rmSync(f.packaged);\n    await assert.rejects(() => verify({ appOutDir: f.appOutDir }, f.root), /missing/);\n  } finally { fs.rmSync(f.root, { recursive: true, force: true }); }\n});\ntest(\"afterPack rejects a modified packaged source-rights register\", async () => {\n  const f = fixture();\n  try {\n    fs.appendFileSync(f.packaged, \" \");\n    await assert.rejects(() => verify({ appOutDir: f.appOutDir }, f.root), /SHA-256 mismatch/);\n  } finally { fs.rmSync(f.root, { recursive: true, force: true }); }\n});\ntest(\"afterPack rejects quarantined data falsely marked as ingested\", async () => {\n  const f = fixture();\n  try {\n    const bad = { updated_at: \"2026-11-06\", sources: [{ source_id: \"bad\", data_ingested: true, verification_status: \"quarantined\", rights: { permission_status: \"not_obtained\" } }] };\n    const bytes = Buffer.from(JSON.stringify(bad) + \"\\n\", \"utf8\");\n    fs.writeFileSync(f.source, bytes);\n    fs.writeFileSync(f.packaged, bytes);\n    await assert.rejects(() => verify({ appOutDir: f.appOutDir }, f.root), /Restricted source is marked ingested/);\n  } finally { fs.rmSync(f.root, { recursive: true, force: true }); }\n});\n", { encoding: "utf8" });

console.log("Desktop hardening patch applied and verified.");

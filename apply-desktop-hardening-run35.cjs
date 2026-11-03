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
console.log("Desktop hardening patch applied and verified.");

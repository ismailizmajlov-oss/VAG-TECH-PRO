"use strict";
const fs = require("node:fs");
const path = require("node:path");

const root = path.resolve(process.cwd(), "desktop-source");
const packagePath = path.join(root, "package.json");
const mainPath = path.join(root, "electron", "main.cjs");
const packageJson = JSON.parse(fs.readFileSync(packagePath, "utf8"));

function readLf(file) {
  return fs.readFileSync(file, "utf8").replace(/\r\n/g, "\n");
}
function writeLf(file, value) {
  fs.writeFileSync(file, value.replace(/\r\n/g, "\n"), "utf8");
}
function replaceExactly(source, before, after, label) {
  if (source.includes(after)) return source;
  const count = source.split(before).length - 1;
  if (count !== 1) throw new Error(label + ": expected exactly one original block or an already-applied replacement; found " + count);
  return source.replace(before, after);
}
function ensureFile(file, content, label) {
  if (fs.existsSync(file)) {
    if (readLf(file) !== content.replace(/\r\n/g, "\n")) {
      throw new Error(label + ": refusing to overwrite an unexpected existing file");
    }
    return;
  }
  fs.mkdirSync(path.dirname(file), { recursive: true });
  writeLf(file, content);
}

if (!packageJson.scripts || typeof packageJson.scripts["build:desktop"] !== "string") {
  throw new Error("Desktop build script is missing.");
}
const oldBuild = "npm run build && electron-builder --win nsis --x64";
const newBuild = "npm run build && node scripts/prepare-electron-runtime.cjs && electron-builder --win nsis --x64";
if (packageJson.scripts["build:desktop"] === oldBuild) {
  packageJson.scripts["build:desktop"] = newBuild;
} else if (packageJson.scripts["build:desktop"] !== newBuild) {
  throw new Error("Unexpected build:desktop command; refusing to replace an unreviewed build pipeline.");
}

if (!packageJson.build || !Array.isArray(packageJson.build.extraResources)) {
  throw new Error("electron-builder extraResources configuration is missing.");
}
const standaloneResource = packageJson.build.extraResources.find((item) =>
  item.from === ".next/standalone" && item.to === "app-runtime"
);
if (!standaloneResource) throw new Error("Standalone app-runtime extraResources entry was not found.");
standaloneResource.filter = ["**/*", "!node_modules/**/*"];
const modulesResource = packageJson.build.extraResources.find((item) =>
  item.from === ".next/standalone/node_modules" && item.to === "app-runtime/node_modules"
);
if (!modulesResource) {
  packageJson.build.extraResources.push({
    from: ".next/standalone/node_modules",
    to: "app-runtime/node_modules",
    filter: ["**/*"]
  });
}

if (typeof packageJson.scripts["test:desktop"] !== "string") {
  throw new Error("Desktop test script is missing.");
}
const contractTest = "tests/electron-runtime-packaging-contract.test.cjs";
if (!packageJson.scripts["test:desktop"].includes(contractTest)) {
  packageJson.scripts["test:desktop"] += " " + contractTest;
}
writeLf(packagePath, JSON.stringify(packageJson, null, 2) + "\n");

const prepareRuntime = [
  '"use strict";',
  'const fs = require("node:fs");',
  'const path = require("node:path");',
  'const crypto = require("node:crypto");',
  'const { execSync } = require("node:child_process");',
  'const { createRequire } = require("node:module");',
  '',
  'const root = path.resolve(__dirname, "..");',
  'const standalone = path.join(root, ".next", "standalone");',
  'const serverEntry = path.join(standalone, "server.js");',
  'const sourceModules = path.join(root, "node_modules");',
  'const targetModules = path.join(standalone, "node_modules");',
  'function fail(message) { throw new Error("[prepare-electron-runtime] " + message); }',
  'if (!fs.existsSync(serverEntry)) fail("Next.js standalone server.js is missing: " + serverEntry);',
  'if (!fs.existsSync(sourceModules)) fail("Installed node_modules is missing: " + sourceModules);',
  'fs.mkdirSync(targetModules, { recursive: true });',
  'let listing;',
  'try {',
  '  listing = execSync("npm ls --omit=dev --all --parseable", { cwd: root, encoding: "utf8", windowsHide: true, stdio: ["ignore", "pipe", "pipe"] });',
  '} catch (error) {',
  '  const stderr = error && error.stderr ? String(error.stderr) : "";',
  '  fail("Could not enumerate the production dependency tree with npm ls --omit=dev. " + stderr.slice(-3000));',
  '}',
  'const packagePaths = new Set();',
  'for (const line of listing.split(/\\r?\\n/)) {',
  '  const candidate = line.trim();',
  '  if (!candidate) continue;',
  '  const absolute = path.resolve(candidate);',
  '  const relative = path.relative(sourceModules, absolute);',
  '  if (!relative || relative === "." || relative.startsWith("..") || path.isAbsolute(relative)) continue;',
  '  if (relative.split(path.sep).some((part) => part === ".bin" || part === ".cache")) continue;',
  '  if (!fs.existsSync(path.join(absolute, "package.json"))) continue;',
  '  packagePaths.add(relative);',
  '}',
  'if (!packagePaths.has("next")) fail("The production dependency tree does not contain the Next.js package.");',
  'const copied = [];',
  'const preserved = [];',
  'for (const relative of [...packagePaths].sort((a, b) => a.localeCompare(b))) {',
  '  const source = path.join(sourceModules, relative);',
  '  const destination = path.join(targetModules, relative);',
  '  if (!fs.existsSync(source)) fail("A listed production package disappeared: " + source);',
  '  if (fs.existsSync(destination)) { preserved.push(relative); continue; }',
  '  fs.mkdirSync(path.dirname(destination), { recursive: true });',
  '  fs.cpSync(source, destination, { recursive: true, dereference: true, force: false, errorOnExist: false });',
  '  copied.push(relative);',
  '}',
  'const runtimeRequire = createRequire(serverEntry);',
  'const resolved = {};',
  'for (const name of ["next", "react", "react-dom"]) {',
  '  try { resolved[name] = runtimeRequire.resolve(name); }',
  '  catch (error) { fail("Packaged runtime cannot resolve " + name + " from " + standalone + ": " + error.message); }',
  '}',
  'const digest = crypto.createHash("sha256").update([...packagePaths].sort().join("\\n")).digest("hex");',
  'const report = { status: "production_runtime_dependencies_ready", production_package_count: packagePaths.size, copied_package_count: copied.length, preserved_standalone_package_count: preserved.length, production_package_tree_sha256: digest, resolved, note: "Only dependencies declared in the desktop package production dependency tree are merged; development dependencies are not copied." };',
  'fs.writeFileSync(path.join(root, "runtime-preparation.json"), JSON.stringify(report, null, 2) + "\\n", "utf8");',
  'console.log(JSON.stringify(report, null, 2));'
].join("\n") + "\n";
ensureFile(path.join(root, "scripts", "prepare-electron-runtime.cjs"), prepareRuntime, "Electron runtime preparation script");

let main = readLf(mainPath);
main = replaceExactly(
  main,
  'const path = require("node:path");\n',
  'const path = require("node:path");\nconst { createRequire } = require("node:module");\n',
  "Electron runtime createRequire import"
);
main = replaceExactly(
  main,
  '    const port = await reserveLoopbackPort();',
  '    const runtimeRequire = createRequire(serverEntry);\n    for (const moduleName of ["next", "react", "react-dom"]) {\n      try { runtimeRequire.resolve(moduleName); }\n      catch { throw new Error("Packaged Next.js runtime dependency missing: " + moduleName + " (" + runtimeDirectory + ")"); }\n    }\n    const port = await reserveLoopbackPort();',
  "Electron packaged runtime dependency preflight"
);
if (!main.includes("Packaged Next.js runtime dependency missing")) {
  throw new Error("Electron runtime dependency preflight did not apply.");
}
writeLf(mainPath, main);

const testContent = [
  '"use strict";',
  'const test = require("node:test");',
  'const assert = require("node:assert/strict");',
  'const fs = require("node:fs");',
  'const path = require("node:path");',
  'const root = path.resolve(__dirname, "..");',
  'const pkg = JSON.parse(fs.readFileSync(path.join(root, "package.json"), "utf8"));',
  'const main = fs.readFileSync(path.join(root, "electron", "main.cjs"), "utf8");',
  'const preparation = fs.readFileSync(path.join(root, "scripts", "prepare-electron-runtime.cjs"), "utf8");',
  '',
  'test("Windows desktop build merges only production dependencies into the standalone runtime", () => {',
  '  assert.match(pkg.scripts["build:desktop"], /npm run build && node scripts\\/prepare-electron-runtime\\.cjs && electron-builder --win nsis --x64/);',
  '  const resources = pkg.build.extraResources;',
  '  assert.ok(resources.some((item) => item.from === ".next/standalone" && item.to === "app-runtime" && item.filter.includes("!node_modules/**/*")));',
  '  assert.ok(resources.some((item) => item.from === ".next/standalone/node_modules" && item.to === "app-runtime/node_modules"));',
  '  assert.match(preparation, /npm ls --omit=dev --all --parseable/);',
  '  assert.match(preparation, /createRequire\\(serverEntry\\)/);',
  '  assert.match(preparation, /production_runtime_dependencies_ready/);',
  '  assert.doesNotMatch(preparation, /npm install|npm ci/);',
  '});',
  '',
  'test("Electron refuses to launch a packaged server without its Next.js runtime dependencies", () => {',
  '  assert.match(main, /createRequire\\(serverEntry\\)/);',
  '  assert.match(main, /runtimeRequire\\.resolve\\(moduleName\\)/);',
  '  assert.match(main, /Packaged Next\\.js runtime dependency missing/);',
  '});'
].join("\n") + "\n";
ensureFile(path.join(root, "tests", "electron-runtime-packaging-contract.test.cjs"), testContent, "Electron runtime packaging contract test");

console.log("Electron runtime packaging patch applied and verified.");

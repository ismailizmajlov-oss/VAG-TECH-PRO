"use strict";
const fs = require("node:fs");
const path = require("node:path");

const root = path.resolve(process.cwd(), "desktop-source");
const mainPath = path.join(root, "electron", "main.cjs");
const packagePath = path.join(root, "package.json");
const routePath = path.join(root, "app", "desktop", "page.tsx");
const desktopTestPath = path.join(root, "tests", "desktop-offline-entry-run90.test.cjs");

function readLf(file) {
  return fs.readFileSync(file, "utf8").replace(/\r\n/g, "\n");
}
function writeLf(file, value) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, value.replace(/\r\n/g, "\n"), "utf8");
}
function replaceExactly(source, before, after, label) {
  if (source.includes(after)) return source;
  const count = source.split(before).length - 1;
  if (count !== 1) throw new Error(`${label}: expected one original block or an already-applied replacement; found ${count}`);
  return source.replace(before, after);
}
function ensureExactFile(file, content, label) {
  if (fs.existsSync(file)) {
    if (readLf(file) !== content.replace(/\r\n/g, "\n")) throw new Error(`${label}: refusing to overwrite unexpected existing content`);
    return;
  }
  writeLf(file, content);
}

for (const relative of [
  "components/local-offline-workspace.tsx",
  "components/local-data-admin.tsx",
  "components/local-research-catalog.tsx",
  "app/globals.css",
]) {
  if (!fs.existsSync(path.join(root, relative))) throw new Error(`Required offline desktop component is missing: ${relative}`);
}

const repoRoot = process.cwd();
const routeSourcePath = path.join(repoRoot, "desktop-offline-route-run90.tsx");
const desktopTestSourcePath = path.join(repoRoot, "desktop-offline-route-test-run90.cjs");
const route = readLf(routeSourcePath);
const desktopTest = readLf(desktopTestSourcePath);
if (!route.includes('data-theme="dark"') || /createClient|supabase|https?:\/\//i.test(route)) {
  throw new Error("Offline desktop route source must remain dark and independent of cloud authentication.");
}
if (!desktopTest.includes("LocalOfflineWorkspace") || !desktopTest.includes("desktopUrl")) {
  throw new Error("Offline desktop route test source is incomplete.");
}

let main = readLf(mainPath);
const oldUrlBlock = [
  '    const url = `http://127.0.0.1:${port}`;',
  '    await waitForServer(url, serverProcess, 45000, () => !serverExited);'
].join("\n");
const newUrlBlock = [
  '    const url = `http://127.0.0.1:${port}`;',
  '    const desktopUrl = `${url}/desktop`;',
  '    await waitForServer(desktopUrl, serverProcess, 45000, () => !serverExited);'
].join("\n");
main = replaceExactly(main, oldUrlBlock, newUrlBlock, "Electron desktop route readiness");
main = replaceExactly(main, '    await mainWindow.loadURL(url);', '    await mainWindow.loadURL(desktopUrl);', "Electron desktop route navigation");
const runtimeHelper = [
  'function buildRuntimeEnvironment(baseEnv, port, dataRoot, databasePath, researchRoot) {',
  '  const runtimeEnv = { ...baseEnv, PORT: String(port), HOSTNAME: "127.0.0.1", NODE_ENV: "production", VAG_TECH_PRO_DATA_DIR: dataRoot, VAG_TECH_PRO_DB_PATH: databasePath, VAG_TECH_PRO_RESEARCH_DIR: researchRoot, VAG_TECH_PRO_DESKTOP_OFFLINE: "1" };',
  '  for (const key of ["SUPABASE_URL", "SUPABASE_ANON_KEY", "SUPABASE_SERVICE_ROLE_KEY", "NEXT_PUBLIC_SUPABASE_URL", "NEXT_PUBLIC_SUPABASE_ANON_KEY"]) delete runtimeEnv[key];',
  '  return runtimeEnv;',
  '}',
  'let mainWindow;'
].join("\n");
main = replaceExactly(main, "let mainWindow;", runtimeHelper, "Electron offline-only runtime environment helper");
const oldRuntimeEnv = [
  '      env: { ...process.env, PORT: String(port), HOSTNAME: "127.0.0.1", NODE_ENV: "production", VAG_TECH_PRO_DATA_DIR: dataRoot, VAG_TECH_PRO_DB_PATH: process.env.VAG_TECH_PRO_DB_PATH, VAG_TECH_PRO_RESEARCH_DIR: researchRoot },'
].join("\n");
const newRuntimeEnv = [
  '      env: buildRuntimeEnvironment(process.env, port, dataRoot, process.env.VAG_TECH_PRO_DB_PATH, researchRoot),'
].join("\n");
main = replaceExactly(main, oldRuntimeEnv, newRuntimeEnv, "Electron offline-only runtime environment");
const oldExports = 'module.exports = { reserveLoopbackPort, resolveRuntimeDirectory, probeHttp, waitForServer };';
const newExports = 'module.exports = { reserveLoopbackPort, resolveRuntimeDirectory, buildRuntimeEnvironment, probeHttp, waitForServer };';
main = replaceExactly(main, oldExports, newExports, "Electron offline environment test export");
if (!main.includes('const desktopUrl = `${url}/desktop`;') || !main.includes('await mainWindow.loadURL(desktopUrl);') || !main.includes('function buildRuntimeEnvironment(') || !main.includes('VAG_TECH_PRO_DESKTOP_OFFLINE: "1"') || !main.includes('delete runtimeEnv[key]') || !main.includes('buildRuntimeEnvironment(process.env, port, dataRoot, process.env.VAG_TECH_PRO_DB_PATH, researchRoot)')) {
  throw new Error("Electron offline-only entry verification failed.");
}
writeLf(mainPath, main);

ensureExactFile(routePath, route, "Dedicated offline desktop route");
ensureExactFile(desktopTestPath, desktopTest, "Dedicated offline desktop route tests");
const packageJson = JSON.parse(readLf(packagePath));
if (!packageJson.scripts || typeof packageJson.scripts["test:desktop"] !== "string") throw new Error("Desktop test script is missing.");
const testName = "tests/desktop-offline-entry-run90.test.cjs";
if (!packageJson.scripts["test:desktop"].split(/\s+/).includes(testName)) {
  packageJson.scripts["test:desktop"] += " " + testName;
  writeLf(packagePath, JSON.stringify(packageJson, null, 2) + "\n");
}
if (!packageJson.scripts["test:desktop"].split(/\s+/).includes(testName)) throw new Error("Offline desktop route test was not registered in test:desktop.");

console.log(JSON.stringify({ status: "dedicated_offline_desktop_entry_applied", route: "app/desktop/page.tsx", electron_entry: "/desktop", cloud_credentials_removed_from_runtime: true, desktop_test_registered: true }));

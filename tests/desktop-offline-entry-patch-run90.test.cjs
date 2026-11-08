"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { execFileSync } = require("node:child_process");

const patchSource = path.resolve(__dirname, "apply-desktop-offline-entry-run90.cjs");
const routeSource = path.resolve(__dirname, "desktop-offline-route-run90.tsx");
const desktopTestSource = path.resolve(__dirname, "desktop-offline-route-test-run90.cjs");

function createFixture() {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "vag-offline-entry-run90-"));
  const desktop = path.join(root, "desktop-source");
  for (const relative of [
    "electron/main.cjs",
    "components/local-offline-workspace.tsx",
    "components/local-data-admin.tsx",
    "components/local-research-catalog.tsx",
    "app/globals.css",
  ]) {
    const file = path.join(desktop, relative);
    fs.mkdirSync(path.dirname(file), { recursive: true });
    fs.writeFileSync(file, relative === "electron/main.cjs" ? [
      '    const url = `http://127.0.0.1:${port}`;',
      '    await waitForServer(url, serverProcess, 45000, () => !serverExited);',
      '    await mainWindow.loadURL(url);',
      '      env: { ...process.env, PORT: String(port), HOSTNAME: "127.0.0.1", NODE_ENV: "production", VAG_TECH_PRO_DATA_DIR: dataRoot, VAG_TECH_PRO_DB_PATH: process.env.VAG_TECH_PRO_DB_PATH, VAG_TECH_PRO_RESEARCH_DIR: researchRoot },',
    ].join("\n") : "fixture\n", "utf8");
  }
  fs.mkdirSync(path.join(desktop, "tests"), { recursive: true });
  fs.writeFileSync(path.join(desktop, "package.json"), JSON.stringify({ scripts: { "test:desktop": "node --test tests/desktop-runtime.test.cjs" } }, null, 2), "utf8");
  fs.copyFileSync(patchSource, path.join(root, "apply-desktop-offline-entry-run90.cjs"));
  fs.copyFileSync(routeSource, path.join(root, "desktop-offline-route-run90.tsx"));
  fs.copyFileSync(desktopTestSource, path.join(root, "desktop-offline-route-test-run90.cjs"));
  return { root, desktop };
}

test("run90 creates an isolated offline route and binds Electron to it", () => {
  const fixture = createFixture();
  try {
    const script = path.join(fixture.root, "apply-desktop-offline-entry-run90.cjs");
    const output = execFileSync(process.execPath, [script], { cwd: fixture.root, encoding: "utf8" });
    assert.match(output, /dedicated_offline_desktop_entry_applied/);
    const main = fs.readFileSync(path.join(fixture.desktop, "electron/main.cjs"), "utf8");
    const route = fs.readFileSync(path.join(fixture.desktop, "app/desktop/page.tsx"), "utf8");
    const pkg = JSON.parse(fs.readFileSync(path.join(fixture.desktop, "package.json"), "utf8"));
    assert.match(main, /loadURL\(desktopUrl\)/);
    assert.match(main, /VAG_TECH_PRO_DESKTOP_OFFLINE/);
    assert.match(main, /delete runtimeEnv\[key\]/);
    assert.match(route, /LocalOfflineWorkspace/);
    assert.doesNotMatch(route, /createClient|supabase|https?:\/\//i);
    assert.ok(pkg.scripts["test:desktop"].includes("tests/desktop-offline-entry-run90.test.cjs"));
  } finally {
    fs.rmSync(fixture.root, { recursive: true, force: true });
  }
});

test("run90 is idempotent and refuses to overwrite an unexpected desktop route", () => {
  const fixture = createFixture();
  try {
    const script = path.join(fixture.root, "apply-desktop-offline-entry-run90.cjs");
    execFileSync(process.execPath, [script], { cwd: fixture.root, encoding: "utf8" });
    const routePath = path.join(fixture.desktop, "app/desktop/page.tsx");
    const expected = fs.readFileSync(routePath, "utf8");
    execFileSync(process.execPath, [script], { cwd: fixture.root, encoding: "utf8" });
    assert.equal(fs.readFileSync(routePath, "utf8"), expected);
    fs.writeFileSync(routePath, "unexpected user content\n", "utf8");
    assert.throws(() => execFileSync(process.execPath, [script], { cwd: fixture.root, encoding: "utf8", stdio: "pipe" }));
    assert.equal(fs.readFileSync(routePath, "utf8"), "unexpected user content\n");
  } finally {
    fs.rmSync(fixture.root, { recursive: true, force: true });
  }
});

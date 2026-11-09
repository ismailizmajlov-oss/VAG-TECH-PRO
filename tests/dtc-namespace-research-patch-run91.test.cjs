"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { execFileSync } = require("node:child_process");

const ROOT = path.resolve(__dirname, "..");
const SOURCE = path.join(ROOT, "desktop-source");
const PATCHER = path.join(ROOT, "apply-obdex-generic-dtc-policy-run91.cjs");

test("run91 patch is idempotent and adds fail-closed generic DTC namespace filtering", (t) => {
  const fixture = fs.mkdtempSync(path.join(os.tmpdir(), "vag-run91-dtc-policy-"));
  t.after(() => fs.rmSync(fixture, { recursive: true, force: true }));
  for (const relative of [
    "lib/local-research-db.cjs",
    "components/local-research-catalog.tsx",
    "tests/local-research-db.test.cjs",
    "tests/local-research-ui-contract.test.cjs",
  ]) {
    const from = path.join(SOURCE, relative);
    assert.ok(fs.statSync(from).isFile(), "missing desktop source fixture: " + relative);
    const to = path.join(fixture, relative);
    fs.mkdirSync(path.dirname(to), { recursive: true });
    fs.copyFileSync(from, to);
  }
  const policy = path.join(ROOT, "data", "policies", "dtc-namespace-ranges.json");
  const policyTarget = path.join(fixture, "data", "policies", "dtc-namespace-ranges.json");
  fs.mkdirSync(path.dirname(policyTarget), { recursive: true });
  fs.copyFileSync(policy, policyTarget);
  const contract = path.join(ROOT, "tests", "local-research-dtc-namespace-policy-run91.test.cjs");
  const contractTarget = path.join(fixture, "tests", "local-research-dtc-namespace-policy-run91.test.cjs");
  fs.copyFileSync(contract, contractTarget);

  const first = execFileSync(process.execPath, [PATCHER, "--desktop-root", fixture], { cwd: ROOT, encoding: "utf8" });
  assert.match(first, /"status": "applied"/);
  const dbPath = path.join(fixture, "lib", "local-research-db.cjs");
  const uiPath = path.join(fixture, "components", "local-research-catalog.tsx");
  const db = fs.readFileSync(dbPath, "utf8");
  const ui = fs.readFileSync(uiPath, "utf8");
  assert.match(db, /dtcPredicates\.allowedSql/);
  assert.match(db, /dtcsQuarantined/);
  assert.match(ui, /P34xx–P39xx/);
  const second = execFileSync(process.execPath, [PATCHER, "--desktop-root", fixture], { cwd: ROOT, encoding: "utf8" });
  assert.match(second, /"databaseChanged": false/);
  assert.match(second, /"uiChanged": false/);
  execFileSync(process.execPath, ["--test", contractTarget], { cwd: fixture, stdio: "pipe" });
});

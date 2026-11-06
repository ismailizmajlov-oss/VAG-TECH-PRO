"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const ROOT = path.join(__dirname, "..");
const ui = fs.readFileSync(path.join(ROOT, "components", "local-research-catalog.tsx"), "utf8");
const api = fs.readFileSync(path.join(ROOT, "app", "api", "local-research", "route.ts"), "utf8");
const lifecycle = fs.readFileSync(path.join(ROOT, "scripts", "windows-installer-lifecycle.ps1"), "utf8");

test("RDW research UI is explicitly NL-only and does not imply VAG fitment", () => {
  assert.match(ui, /id:\s*"rdw"/);
  assert.match(ui, /ОТТС\s*·\s*NL/i);
  assert.match(ui, /engineDesignationCandidates/);
  assert.match(ui, /gearboxClassifications/);
  assert.match(ui, /exactEngineGearboxPair/);
  assert.match(ui, /RDW/);
  assert.match(ui, /не подтверждённый заводской код VAG|не код VAG/i);
});

test("RDW local research API exposes summary and read-only approval search", () => {
  assert.match(api, /rdw-summary/);
  assert.match(api, /searchRdwApprovals/);
  assert.match(api, /getRdwSummary/);
});

test("Windows offline lifecycle verifies RDW summary and exact-scope separation", () => {
  assert.match(lifecycle, /rdw-summary/);
  assert.match(lifecycle, /e1\*2018\/858\*00403\*07/);
  assert.match(lifecycle, /ACDUCAX0/);
  assert.match(lifecycle, /FD6FD6DD002PR4VNB50OO/);
  assert.match(lifecycle, /exactEngineGearboxPair/);
});

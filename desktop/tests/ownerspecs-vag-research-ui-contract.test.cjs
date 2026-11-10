"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const root = path.resolve(__dirname, "..");
const ui = fs.readFileSync(path.join(root, "components/local-research-catalog.tsx"), "utf8");
const api = fs.readFileSync(path.join(root, "app/api/local-research/route.ts"), "utf8");
const lifecycle = fs.readFileSync(path.join(root, "scripts/windows-installer-lifecycle.ps1"), "utf8");

test("OwnerSpecs is a separate offline research tab and API dataset", () => {
  assert.match(ui, /"ownerspecs"/);
  assert.match(ui, /OwnerSpecs · поколения-кандидаты/);
  assert.match(ui, /CC BY-SA 4\.0/);
  assert.match(ui, /market UNKNOWN/);
  assert.match(api, /ownerspecs-vag-research-db\.cjs/);
  assert.match(api, /dataset === "ownerspecs-summary"/);
  assert.match(api, /dataset === "ownerspecs"/);
});

test("OwnerSpecs UI never presents critical values as confirmed repair data", () => {
  for (const field of ["sourceRowSha256","sourceSnapshotSha256","databaseSha256","sourceManifestSha256","technicalReviewStatus","applicabilityPrecision","criticalValuePublishable","provenance"]) {
    assert.ok(ui.includes(field), "missing OwnerSpecs provenance field: " + field);
  }
  assert.match(ui, /точная применимость не подтверждена/);
  assert.match(ui, /критические значения не допущены к ремонту/i);
  assert.match(ui, /Share-Alike/);
});

test("Windows offline lifecycle checks OwnerSpecs rights and candidate-only boundaries", () => {
  assert.match(lifecycle, /ownerspecs-summary/);
  assert.match(lifecycle, /dataset=ownerspecs&q=/);
  assert.match(lifecycle, /criticalValuePublishable -ne 0/);
  assert.match(lifecycle, /marketScope -ne "UNKNOWN"/);
  assert.match(lifecycle, /exactEngineGearboxPair -ne \$false/);
});

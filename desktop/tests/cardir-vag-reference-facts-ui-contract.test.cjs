"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const root = path.resolve(__dirname, "..");
const ui = fs.readFileSync(path.join(root, "components/local-research-catalog.tsx"), "utf8");
const api = fs.readFileSync(path.join(root, "app/api/local-research/route.ts"), "utf8");
const lifecycle = fs.readFileSync(path.join(root, "scripts/windows-installer-lifecycle.ps1"), "utf8");

test("CarDir is exposed as a separate offline research tab and API dataset", () => {
  assert.match(ui, /"cardir"/);
  assert.match(ui, /CarDir · справочные значения/);
  assert.match(ui, /рынок UNKNOWN/);
  assert.match(ui, /publisherVerificationStatus/);
  assert.match(ui, /technicalReviewStatus/);
  assert.match(api, /cardir-vag-reference-facts-db\.cjs/);
  assert.match(api, /dataset === "cardir-summary"/);
  assert.match(api, /dataset === "cardir"/);
});

test("CarDir UI preserves raw qualifiers and row-level source evidence", () => {
  for (const field of ["parameterLabelRu","qualifier","value","unit","sourceTitle","sourcePage","sourceUrl","pageUrl","verifiedAt","sourceRowSha256","sourceSnapshotSha256","databaseSha256","sourceManifestSha256"]) {
    assert.ok(ui.includes(field), "missing CarDir UI provenance field: " + field);
  }
  assert.match(ui, /точная применимость не подтверждена/);
  assert.match(ui, /не является заводской ремонтной документацией/);
  assert.match(ui, /CC BY 4\.0/);
});

test("Windows offline lifecycle checks CarDir pack rights, search and non-fitment boundaries", () => {
  assert.match(lifecycle, /cardir-summary/);
  assert.match(lifecycle, /dataset=cardir&q=/);
  assert.match(lifecycle, /marketScope -ne "UNKNOWN"/);
  assert.match(lifecycle, /exactEngineGearboxPair -ne 0/);
  assert.match(lifecycle, /ruEaeuApplicability -ne \$false/);
  assert.match(lifecycle, /sourceRowSha256 -notmatch/);
});

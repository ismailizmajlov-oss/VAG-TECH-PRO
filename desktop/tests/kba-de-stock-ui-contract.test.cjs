"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const ROOT = path.join(__dirname, "..");
test("KBA DE research tab exposes attribution, aggregate precision and non-fitment wording", () => {
  const ui = fs.readFileSync(path.join(ROOT, "components/local-research-catalog.tsx"), "utf8");
  const api = fs.readFileSync(path.join(ROOT, "app/api/local-research/route.ts"), "utf8");
  assert.match(ui, /"kba-de"/);
  assert.match(ui, /KBA[^"\n]*DE/);
  assert.match(ui, /aggregate_stock_observation/);
  assert.match(ui, /Typschlüssel[^<]*исходн/);
  assert.match(ui, /не подтверждён как TSN/);
  assert.match(ui, /Kraftfahrt-Bundesamt \(KBA\)/);
  assert.match(ui, /DL-DE BY 2\.0/);
  assert.match(ui, /sourceRecordSha256/);
  assert.match(ui, /sourceSnapshotSha256/);
  assert.match(ui, /exactEngineGearboxPair/);
  assert.match(ui, /ruEaeuApplicability/);
  assert.match(api, /kba-de-stock-research-db\.cjs/);
  assert.match(api, /kba-de-summary/);
  assert.match(api, /dataset === "kba-de"/);
});

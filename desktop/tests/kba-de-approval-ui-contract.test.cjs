"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const ROOT = path.join(__dirname, "..");

test("KBA approval research tab exposes DE-only scope, licence, source revision and row provenance", () => {
  const ui = fs.readFileSync(path.join(ROOT, "components", "local-research-catalog.tsx"), "utf8");
  const api = fs.readFileSync(path.join(ROOT, "app", "api", "local-research", "route.ts"), "utf8");
  assert.match(ui, /kba-de-approvals/);
  assert.match(ui, /KBA[^"\n]*одобрени/);
  assert.match(ui, /type_approval_document_metadata_only/);
  assert.match(ui, /DL-DE BY 2\.0/);
  assert.match(ui, /sourceRecordSha256/);
  assert.match(ui, /sourceSnapshotSha256/);
  assert.match(ui, /sourceManifestSha256/);
  assert.match(ui, /exactEngineGearboxPair/);
  assert.match(ui, /ruEaeuApplicability/);
  assert.match(ui, /дата одобрения[^<]*не модельный год/i);
  assert.match(ui, /не подтверждает применимость к конкретному автомобилю/i);
  assert.match(ui, /Kraftfahrt-Bundesamt \(KBA\)/);
  assert.match(api, /kba-de-approval-research-db\.cjs/);
  assert.match(api, /kba-de-approvals-summary/);
  assert.match(api, /dataset === "kba-de-approvals"/);
});

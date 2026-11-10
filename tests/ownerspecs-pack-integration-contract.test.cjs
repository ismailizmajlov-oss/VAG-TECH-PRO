"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const root = path.resolve(__dirname, "..");
const integration = fs.readFileSync(path.join(root, "scripts/integrate-ownerspecs-vag-research.cjs"), "utf8");
const workflow = fs.readFileSync(path.join(root, ".github/workflows/windows-desktop-ci-run71.yml"), "utf8");
const manifest = JSON.parse(fs.readFileSync(path.join(root, "data/source-manifests/ownerspecs-verified-vehicle-specs-cc-by-sa-4.0.json"), "utf8"));

test("OwnerSpecs desktop integration is pinned to the reviewed CC BY-SA pack", () => {
  assert.equal(manifest.snapshot.source_snapshot_sha256, "6ed73e4cd634e64501edd3b0e03405afa0aad3b8d1a103f78b839c87c8588c95");
  assert.equal(manifest.snapshot.source_file_bytes, 683533);
  assert.equal(manifest.snapshot.json_descriptor_generation_count, 111);
  assert.equal(manifest.snapshot.html_page_verified_datapoint_count, 2369);
  assert.match(integration, /ownerspecs-vag-vehicle-specs-research/);
  assert.match(integration, /vagGenerations: 20/);
  assert.match(integration, /vagFacts: 233/);
  assert.match(integration, /critical_technical_values_publishable/);
  assert.match(integration, /share_alike_required/);
});

test("Windows desktop workflow downloads the exact pinned OwnerSpecs artifact and tests integration", () => {
  assert.match(workflow, /ownerspecs-vag-research-pack/);
  assert.match(workflow, /42752686437/);
  assert.match(workflow, /441e5626796acb315ebf428e7e6acf5bdab93276335267fac639c23d21cdefe3/);
  assert.match(workflow, /integrate-ownerspecs-vag-research\.cjs/);
  assert.match(workflow, /ownerspecs-pack-integration-contract\.test\.cjs/);
});

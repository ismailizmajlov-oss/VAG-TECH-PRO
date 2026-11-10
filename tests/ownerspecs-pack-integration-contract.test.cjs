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
  assert.match(integration, /artifact:"93c4050130a8d372888ffd3126e18d4ef03de434558adfc98f7bb51e0a6918d1"/);
  assert.match(integration, /source:"6ed73e4cd634e64501edd3b0e03405afa0aad3b8d1a103f78b839c87c8588c95"/);
  assert.match(integration, /sourceManifest:"3d744c8b813508daefaebcd690d10c2cef6d0a731e87eda59015622bffeabbdc"/);
  assert.match(integration, /packManifest:"35bbe697d046891c1f49e8f5a318fa2f6f1afab087a7c20d8718ab4c02c9f6dd"/);
  assert.match(integration, /database:"572455b8054bd93600fb5ef25d38c6aa478a5bc98a0d26d678a220b008d4d683"/);
  assert.match(integration, /research_pack_source_commit==="da635dd1b17131c6f33840c1601ba1ea24dccf08"&&registered\.research_pack_artifact_id===13742090427/);
});

test("Windows desktop workflow downloads the exact pinned OwnerSpecs artifact and tests integration", () => {
  assert.match(workflow, /ownerspecs-vag-research-pack/);
  assert.match(workflow, /42770457166/);
  assert.match(workflow, /93c4050130a8d372888ffd3126e18d4ef03de434558adfc98f7bb51e0a6918d1/);
  assert.match(workflow, /integrate-ownerspecs-vag-research\.cjs/);
  assert.match(workflow, /ownerspecs-pack-integration-contract\.test\.cjs/);
});

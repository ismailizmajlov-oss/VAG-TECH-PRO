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
  assert.equal(manifest.snapshot.source_snapshot_sha256, "835fe7452b3370dbf921049a72ca365d6f69b6b63ef8a3a37b5714265272814c");
  assert.equal(manifest.snapshot.source_file_bytes, 659973);
  assert.equal(manifest.snapshot.json_descriptor_generation_count, 111);
  assert.equal(manifest.snapshot.html_page_verified_datapoint_count, 2273);
  assert.match(integration, /ownerspecs-vag-vehicle-specs-research/);
  assert.match(integration, /ownerspecs-verified-vehicle-specs-cc-by-sa-4\.0-pack3-2026-11-11\.json/);
  assert.match(integration, /vagGenerations: 20/);
  assert.match(integration, /vagFacts: 186/);
  assert.match(integration, /critical_technical_values_publishable/);
  assert.match(integration, /share_alike_required/);
  assert.match(integration, /artifact:"66c764501b3071958b9c1949f3be15908a27ee280c1e2fdd1985c5b934be8c77"/);
  assert.match(integration, /source:"d702e4572a4e640c0295c40970ef3c0da2db3703c829c5e3d96cebb4acccacc9"/);
  assert.match(integration, /sourceManifest:"ed221369ae9195cad18194602a75b17d4ab8aa5908dceb503fc2ca0bfa725697"/);
  assert.match(integration, /packManifest:"21c94e2ec39ea1b231b96d3fe5f830e5ac62ae5cfc1d8e91312de977d8819fd4"/);
  assert.match(integration, /database:"9b7da5b490d3dd805865f23389cb8cc7ca9b368137be8307adb07e0c8e683c4a"/);
  assert.match(integration, /research_pack_source_commit==="9f9aa8136e5c084def52e5fdb983ede737c817ec"&&registered\.research_pack_artifact_id===13833552555/);
});

test("Windows desktop workflow downloads the exact pinned OwnerSpecs artifact and tests integration", () => {
  assert.match(workflow, /ownerspecs-vag-research-pack/);
  assert.match(workflow, /42971572740/);
  assert.match(workflow, /66c764501b3071958b9c1949f3be15908a27ee280c1e2fdd1985c5b934be8c77/);
  assert.match(workflow, /835fe7452b3370dbf921049a72ca365d6f69b6b63ef8a3a37b5714265272814c/);
  assert.match(workflow, /integrate-ownerspecs-vag-research\.cjs/);
  assert.match(workflow, /ownerspecs-pack-integration-contract\.test\.cjs/);
});

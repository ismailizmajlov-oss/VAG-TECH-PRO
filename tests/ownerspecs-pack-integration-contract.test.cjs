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
  assert.equal(manifest.snapshot.source_snapshot_sha256, "fa53aef8eb1d8b8c028ded086cdc3f1e2fc726caa637cdc96ca860336711882f");
  assert.equal(manifest.snapshot.source_file_bytes, 659973);
  assert.equal(manifest.snapshot.json_descriptor_generation_count, 111);
  assert.equal(manifest.snapshot.html_page_verified_datapoint_count, 2273);
  assert.match(integration, /ownerspecs-vag-vehicle-specs-research/);
  assert.match(integration, /ownerspecs-verified-vehicle-specs-cc-by-sa-4\.0-2026-11-11\.json/);
  assert.match(integration, /vagGenerations: 20/);
  assert.match(integration, /vagFacts: 186/);
  assert.match(integration, /critical_technical_values_publishable/);
  assert.match(integration, /share_alike_required/);
  assert.match(integration, /artifact:"5acf0b885b01b71216266a2f9a408511e66575b09966a9a05ae0b3880e4c45e8"/);
  assert.match(integration, /source:"fa53aef8eb1d8b8c028ded086cdc3f1e2fc726caa637cdc96ca860336711882f"/);
  assert.match(integration, /sourceManifest:"a0daad6fd76fa2db22051248a81f52715074aa05b91b6dcdc15cb72a539db3ef"/);
  assert.match(integration, /packManifest:"8b07eed9f69dc763289e326a1f9c47525183abc33d840d2c5531474a115499c5"/);
  assert.match(integration, /database:"ee107718538b3ddc97c2577341c54919ec9269708ef02aad4aeaad3169360bc3"/);
  assert.match(integration, /research_pack_source_commit==="cef31ae342ef9d266ab0d873ac653c0e27acf3ee"&&registered\.research_pack_artifact_id===13835168202/);
});

test("Windows desktop workflow downloads the exact pinned OwnerSpecs artifact and tests integration", () => {
  assert.match(workflow, /ownerspecs-vag-research-pack/);
  assert.match(workflow, /42976259283/);
  assert.match(workflow, /5acf0b885b01b71216266a2f9a408511e66575b09966a9a05ae0b3880e4c45e8/);
  assert.match(workflow, /fa53aef8eb1d8b8c028ded086cdc3f1e2fc726caa637cdc96ca860336711882f/);
  assert.match(workflow, /integrate-ownerspecs-vag-research\.cjs/);
  assert.match(workflow, /ownerspecs-pack-integration-contract\.test\.cjs/);
});

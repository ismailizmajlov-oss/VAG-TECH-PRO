"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

const root = path.join(__dirname, "..");
const workflow = fs.readFileSync(path.join(root, ".github", "workflows", "windows-desktop-ci-run71.yml"), "utf8");
const packWorkflow = fs.readFileSync(path.join(root, ".github", "workflows", "build-windows-offline-data-packs.yml"), "utf8");
const wikipediaWorkflow = fs.readFileSync(path.join(root, ".github", "workflows", "build-wikipedia-vag-engine-candidates.yml"), "utf8");
const builder = fs.readFileSync(path.join(root, "scripts", "build_offline_data_pack_index.py"), "utf8");
const sync = fs.readFileSync(path.join(root, "scripts", "sync-desktop-research-manifest.cjs"), "utf8");
const patch = fs.readFileSync(path.join(root, "apply-wikipedia-engine-candidate-ui-run91.cjs"), "utf8");
const ui = fs.readFileSync(path.join(root, "wikipedia-engine-candidates-ui-run91.tsx"), "utf8");

test("Windows offline bundle builds and pins the separately licensed Wikipedia candidate pack", () => {
  assert.match(wikipediaWorkflow, /workflow_call:/);
  assert.match(wikipediaWorkflow, /CC-BY-SA-4\.0/);
  assert.match(wikipediaWorkflow, /wikipedia-vag-engine-candidates/);
  assert.match(packWorkflow, /build-wikipedia-vag-engine-candidates\.yml/);
  assert.match(packWorkflow, /wikipedia-vag-engine-candidates:/);
  assert.match(builder, /def inspect_wikipedia\(/);
  assert.match(builder, /"wikipedia-vag-engine-code-candidates-cc-by-sa-4-0"/);
  assert.match(builder, /database_count": 4/);
  assert.match(builder, /safe_extract_zip/);
  assert.match(builder, /source-artifact\.zip/);
});

test("Desktop build verifies and copies the fourth research pack without merging licenses", () => {
  assert.match(workflow, /database_count -ne 4/);
  assert.match(workflow, /wikipedia-vag-engine-code-candidates-cc-by-sa-4-0/);
  assert.match(workflow, /wikipedia-engine-candidates-db\.test\.cjs/);
  assert.match(workflow, /apply-wikipedia-engine-candidate-ui-run91\.cjs/);
  assert.match(sync, /index\.database_count !== 4/);
  assert.match(sync, /packs: index\.packs\.map/);
  assert.match(sync, /required = \["obdex-generic-cc0", "obdb-vag-signals-cc-by-sa", "vehiclesdb-vag-identity"\]/);
});

test("Candidate-only UI does not offer import or technical execution", () => {
  assert.match(ui, /ENGINE CODE CANDIDATE · NOT VERIFIED/);
  assert.match(ui, /Рынок UNKNOWN/);
  assert.match(ui, /Ремонт запрещён/);
  assert.match(ui, /Диагностика запрещена/);
  assert.match(ui, /CC BY-SA 4\.0/);
  assert.doesNotMatch(ui, /Импортировать|Добавить в каталог|Применить к автомобилю/);
  assert.match(patch, /getSummary\(researchRoot\)/);
  assert.match(patch, /showWikipediaCandidates/);
  assert.match(patch, /productImportAllowed !== false/);
  assert.match(patch, /repairUseAllowed !== false/);
  assert.match(patch, /diagnosticExecutionAllowed !== false/);
});

test("Research source remains separate from the OEM production catalog", () => {
  assert.match(builder, /community_engine_code_candidate_only/);
  assert.match(builder, /not_approved_for_technical_use/);
  assert.match(builder, /product_import_allowed/);
  assert.match(builder, /repair_use_allowed/);
  assert.match(builder, /diagnostic_execution_allowed/);
  assert.match(patch, /wikipedia-vag-engine-code-candidates-cc-by-sa-4-0/);
  assert.match(patch, /researchRoot/);
});

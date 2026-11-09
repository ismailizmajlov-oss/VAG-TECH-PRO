"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

const root = path.join(__dirname, "..");
const component = fs.readFileSync(path.join(root, "components", "wikipedia-engine-candidates.tsx"), "utf8");
const route = fs.readFileSync(path.join(root, "app", "api", "wikipedia-engine-candidates", "route.ts"), "utf8");
const reader = fs.readFileSync(path.join(root, "lib", "wikipedia-engine-candidates-db.cjs"), "utf8");

test("Wikipedia candidate UI labels the data as candidate-only and disclaims repair use", () => {
  assert.match(component, /ENGINE CODE CANDIDATE · NOT VERIFIED/);
  assert.match(component, /Рынок UNKNOWN/);
  assert.match(component, /Применимость не установлена/);
  assert.match(component, /Ремонт запрещён/);
  assert.match(component, /Диагностика запрещена/);
  assert.match(component, /CC BY-SA 4\.0/);
  assert.match(component, /qualityWarnings/);
  assert.match(component, /sourceRowSha256/);
  assert.match(component, /sourceSnapshotSha256/);
  assert.match(component, /sourceManifestSha256/);
  assert.match(component, /packManifestSha256/);
  assert.doesNotMatch(component, /Импортировать|Добавить в каталог|Применить к автомобилю/);
});

test("Wikipedia candidate route is offline, read-only and does not accept source URLs", () => {
  assert.match(route, /wikipediaCandidates\.getSummary/);
  assert.match(route, /wikipediaCandidates\.searchCandidates/);
  assert.match(route, /force-dynamic/);
  assert.match(route, /no-store/);
  assert.doesNotMatch(route, /fetch\(/);
  assert.doesNotMatch(route, /sourceUrl/);
});

test("Wikipedia candidate reader enforces CC BY-SA, pinned provenance and non-actionable flags", () => {
  assert.match(reader, /CC-BY-SA-4\.0/);
  assert.match(reader, /not_approved_for_technical_use/);
  assert.match(reader, /community_engine_code_candidate_only/);
  assert.match(reader, /product_import_allowed/);
  assert.match(reader, /diagnostic_execution_allowed/);
  assert.match(reader, /source-snapshots/);
  assert.match(reader, /source-artifact\.zip/);
  assert.match(reader, /PRAGMA integrity_check/);
  assert.match(reader, /PRAGMA foreign_key_check/);
});

"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const root = path.resolve(__dirname, "..");

test("ASTRA CH research tab is separate and visibly rejects RU/EAEU and factory-fitment claims", () => {
  const ui = fs.readFileSync(path.join(root, "components/local-research-catalog.tsx"), "utf8");
  const api = fs.readFileSync(path.join(root, "app/api/local-research/route.ts"), "utf8");
  const lifecycle = fs.readFileSync(path.join(root, "scripts/windows-installer-lifecycle.ps1"), "utf8");
  assert.match(ui, /id: "astra"/);
  assert.match(ui, /швейцарск/i);
  assert.match(ui, /engineType сохраняется как обозначение в одобрении и не подтверждает заводской код двигателя VAG/);
  assert.match(ui, /не код КПП VAG/);
  assert.match(ui, /только Швейцария|только CH/i);
  assert.match(api, /astraResearch\\.getAstraSummary/);
  assert.match(api, /astraResearch\\.searchAstraApprovals/);
  assert.match(lifecycle, /dataset=astra-summary/);
  assert.match(lifecycle, /dataset=astra&q=1XZ904/);
  assert.match(lifecycle, /ASTRA offline CH approval search passed/);
});

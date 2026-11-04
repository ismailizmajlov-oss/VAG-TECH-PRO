"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const root = path.resolve(__dirname, "..");
const component = fs.readFileSync(path.join(root, "components", "local-research-catalog.tsx"), "utf8");
const route = fs.readFileSync(path.join(root, "app", "api", "local-research", "route.ts"), "utf8");
const lifecycle = fs.readFileSync(path.join(root, "scripts", "windows-installer-lifecycle.ps1"), "utf8");

test("generic guidance has a separate offline research tab and summary", () => {
  assert.match(component, /id: "generic-guidance"/);
  assert.match(component, /genericGuidanceSummary/);
  assert.match(component, /type GenericGuidanceRow/);
  assert.match(component, /type GenericGuidanceSummary/);
  assert.match(component, /genericRepairGuidance/);
  assert.match(component, /dataset === "generic-guidance"/);
  assert.match(component, /row\.instructions/);
  assert.match(component, /row\.sourceLineSha256/);
  assert.match(component, /row\.sourceFileSha256/);
  assert.match(component, /ODbL-1\.0/);
});

test("generic guidance UI never claims VAG fitment or an actionable OEM procedure", () => {
  const start = component.indexOf('dataset === "generic-guidance" && (rows as unknown as GenericGuidanceRow[]).map');
  assert.ok(start >= 0);
  const end = component.indexOf("</article>)}", start);
  assert.ok(end > start);
  const card = component.slice(start, end);
  assert.match(card, /не VAG-specific/i);
  assert.match(card, /не OEM-процедура/i);
  assert.match(card, /не использовать как тест-план/i);
  assert.match(component, /<\\/p>\\}/);
  assert.doesNotMatch(card, /onClick|<button/);
  assert.match(card, /diagnosticExecutionAllowed/);
  assert.match(card, /exactVehicleFitment/);
});

test("local research API exposes generic guidance only through its separate dataset", () => {
  assert.match(route, /generic-repair-guidance-db\.cjs/);
  assert.match(route, /generic-guidance-summary/);
  assert.match(route, /generic-guidance/);
  assert.match(route, /genericGuidance\.search/);
});

test("Windows offline lifecycle verifies the generic pack after install and upgrade", () => {
  assert.match(lifecycle, /api\/local-research\?dataset=generic-guidance-summary/);
  assert.match(lifecycle, /api\/local-research\?dataset=generic-guidance&q=P0011/);
  assert.match(lifecycle, /generic_repair_guidance/);
  assert.match(lifecycle, /diagnosticExecutionAllowed/);
});

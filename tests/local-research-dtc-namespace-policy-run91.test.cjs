"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const ROOT = fs.existsSync(path.resolve(__dirname, "../lib/local-research-db.cjs"))
  ? path.resolve(__dirname, "..")
  : path.resolve(__dirname, "../desktop-source");
const db = fs.readFileSync(path.join(ROOT, "lib", "local-research-db.cjs"), "utf8");
const ui = fs.readFileSync(path.join(ROOT, "components", "local-research-catalog.tsx"), "utf8");

test("generic DTC research search is bound to the canonical namespace policy", () => {
  assert.match(db, /function loadDtcNamespacePolicy/);
  assert.match(db, /function genericDtcCountsFromDb/);
  assert.match(db, /dtcPredicates\.allowedSql/);
  assert.match(db, /namespacePolicyRevision/);
  assert.match(db, /dtcsQuarantined/);
  assert.match(ui, /dtcsSourceRows/);
  assert.match(ui, /dtcsQuarantined/);
  assert.match(ui, /P34xx–P39xx/);
  assert.match(ui, /namespacePolicy/);
});

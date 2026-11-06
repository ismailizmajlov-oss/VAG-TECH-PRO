#!/usr/bin/env node
"use strict";

const fs = require("node:fs");
const path = require("node:path");

function argument(name) {
  const index = process.argv.indexOf(name);
  return index >= 0 ? process.argv[index + 1] : null;
}
function replaceExactly(source, before, after, label) {
  const count = source.split(before).length - 1;
  if (count === 0 && source.includes(after)) return source;
  if (count !== 1) throw new Error(label + ": expected exactly one original block, found " + count);
  return source.replace(before, after);
}
function safeTarget(root, relative) {
  const target = path.resolve(root, relative);
  const rel = path.relative(root, target);
  if (!rel || rel === ".." || rel.startsWith(".." + path.sep) || path.isAbsolute(rel)) throw new Error("Target escaped desktop root: " + relative);
  return target;
}
function main() {
  const desktopRootArg = argument("--desktop-root");
  if (!desktopRootArg) throw new Error("Usage: node apply-local-core-test-cleanup-run75.cjs --desktop-root <desktop-source>");
  const desktopRoot = path.resolve(desktopRootArg);
  if (!fs.statSync(desktopRoot).isDirectory()) throw new Error("Desktop source root is not a directory");
  const target = safeTarget(desktopRoot, "tests/local-core-db.test.cjs");
  const original = fs.readFileSync(target, "utf8");
  const newline = original.includes("\r\n") ? "\r\n" : "\n";
  let source = original.replace(/\r\n/g, "\n");

  source = replaceExactly(source,
    'function seedExactConfiguration(dbPath, sourceId = "test-open-source", shareAlike = false) {\n  const db = new DatabaseSync(dbPath);\n  db.exec("PRAGMA foreign_keys=ON");\n',
    'function seedExactConfiguration(dbPath, sourceId = "test-open-source", shareAlike = false) {\n  const db = new DatabaseSync(dbPath);\n  try {\n  db.exec("PRAGMA foreign_keys=ON");\n',
    "seedExactConfiguration database-handle guard");

  source = replaceExactly(source,
    '  const configId = Number(db.prepare("SELECT id FROM vehicle_configurations WHERE source_record_key=\'configuration:golf7-czea-dq200\'").get().id);\n  db.close();\n  return { configId, ecuId };\n}\n',
    '  const configId = Number(db.prepare("SELECT id FROM vehicle_configurations WHERE source_record_key=\'configuration:golf7-czea-dq200\'").get().id);\n  return { configId, ecuId };\n  } finally {\n    db.close();\n  }\n}\n',
    "seedExactConfiguration finally-close");

  source = replaceExactly(source,
    '  assert.throws(() => seedExactConfiguration(isolatedPath, "test-open-source", true), /approved rights-cleared source/);\n  assert.equal(core.listVerifiedConfigurations(isolatedPath).length, 0);\n  assert.equal(core.listSources(isolatedPath)[0].verified_record_count, 0);\n',
    '  assert.throws(() => seedExactConfiguration(isolatedPath, "test-open-source", true), /approved rights-cleared source/);\n  assert.equal(core.listVerifiedConfigurations(isolatedPath).length, 0);\n  assert.equal(core.listSources(isolatedPath)[0].verified_record_count, 0);\n  assert.doesNotThrow(() => fs.rmSync(isolatedPath, { force: true }), "failed seed must close its SQLite handle before cleanup");\n',
    "Windows file-lock regression assertion");

  fs.writeFileSync(target, source.replace(/\n/g, newline), "utf8");
  console.log(JSON.stringify({ status: "patched", patch: "run75-close-test-database-on-error", target: "tests/local-core-db.test.cjs", preservesOriginalLineEndings: true }));
}
try { main(); }
catch (error) { console.error("Run75 local-core test cleanup patch failed: " + error.message); process.exitCode = 1; }

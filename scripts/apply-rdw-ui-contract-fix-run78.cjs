#!/usr/bin/env node
"use strict";

const fs = require("node:fs");
const path = require("node:path");

const BEFORE = "/не подтверждённый заводской код VAG|не код VAG/i";
const AFTER = "/это не заводские коды VAG|не подтверждённый заводской код VAG|не коды VAG/i";
const TARGET = "tests/rdw-vag-research-ui-contract.test.cjs";

function fail(message) { throw new Error(message); }
function patchUiTest(desktopRoot) {
  const root = path.resolve(desktopRoot);
  if (!fs.statSync(root).isDirectory()) fail("Desktop source root is not a directory");
  const target = path.resolve(root, TARGET);
  const relative = path.relative(root, target);
  if (!relative || relative === ".." || relative.startsWith(".." + path.sep) || path.isAbsolute(relative)) {
    fail("RDW UI contract target escaped desktop root");
  }
  const original = fs.readFileSync(target, "utf8");
  const count = original.split(BEFORE).length - 1;
  if (count === 0 && original.includes(AFTER)) return { status: "already_current", file: TARGET };
  if (count !== 1) fail("RDW UI contract wording: expected exactly one old assertion, found " + count);
  const updated = original.replace(BEFORE, AFTER);
  const temporary = target + ".run78.tmp";
  if (fs.existsSync(temporary)) fail("stale run78 temporary file exists");
  fs.writeFileSync(temporary, updated, { encoding: "utf8", flag: "wx" });
  try { fs.renameSync(temporary, target); }
  catch (error) { fs.rmSync(temporary, { force: true }); throw error; }
  return { status: "patched", file: TARGET };
}
function main() {
  const index = process.argv.indexOf("--desktop-root");
  if (index < 0 || !process.argv[index + 1]) fail("Usage: node apply-rdw-ui-contract-fix-run78.cjs --desktop-root <desktop-source>");
  console.log(JSON.stringify({ patch: "run78-rdw-ui-contract-wording", ...patchUiTest(process.argv[index + 1]) }));
}
if (require.main === module) {
  try { main(); }
  catch (error) { console.error("Run78 RDW UI contract patch failed: " + error.message); process.exitCode = 1; }
}
module.exports = { patchUiTest, BEFORE, AFTER, TARGET };

#!/usr/bin/env node
"use strict";

const fs = require("node:fs");
const path = require("node:path");

function replaceExactly(source, before, after, label) {
  const count = source.split(before).length - 1;
  if (count !== 1) throw new Error(label + ": expected one patch anchor, found " + count);
  return source.replace(before, after);
}

function main() {
  const args = process.argv.slice(2);
  const desktopIndex = args.indexOf("--desktop-root");
  if (desktopIndex < 0 || !args[desktopIndex + 1]) {
    throw new Error("Usage: node apply-technical-step-order-run85.cjs --desktop-root <path>");
  }
  const desktopRoot = path.resolve(args[desktopIndex + 1]);
  const dbPath = path.join(desktopRoot, "lib", "local-core-db.cjs");
  const testPath = path.join(desktopRoot, "tests", "local-core-db.test.cjs");
  for (const file of [dbPath, testPath]) {
    if (!fs.existsSync(file)) throw new Error("Required desktop source file is missing: " + file);
  }

  const dbOriginal = fs.readFileSync(dbPath, "utf8");
  const testOriginal = fs.readFileSync(testPath, "utf8");
  const dbEol = dbOriginal.includes("\r\n") ? "\r\n" : "\n";
  const testEol = testOriginal.includes("\r\n") ? "\r\n" : "\n";
  let db = dbOriginal;
  let tests = testOriginal;

  const allowedLine = '  const allowed = ["order", "action", "expected_result", "measurement", "acceptance_criteria", "safety_note"];';
  const orderLine = '    technicalPayloadNumber(record, step, "order", { required: true, integer: true, minimum: 1 });';
  if (!db.includes("order values must be unique and strictly increasing")) {
    db = replaceExactly(db, allowedLine, allowedLine + dbEol + "  let previousOrder = 0;", "step-order state");
    db = replaceExactly(db, orderLine, orderLine + dbEol + '    if (step.order <= previousOrder) technicalPayloadError(record, key + " order values must be unique and strictly increasing");' + dbEol + "    previousOrder = step.order;", "step-order monotonicity guard");
  }

  const testAnchor = 'test("run81 validates OEM supersession aliases and rejects self-replacement", (t) => {';
  if (!tests.includes("run85 rejects duplicate or out-of-order technical procedure steps")) {
    const newTests = [
      'test("run85 rejects duplicate or out-of-order technical procedure steps before import", (t) => {',
      "  const invalidCases = [",
      '    [{ order: 1, action: "Read measured value" }, { order: 1, action: "Compare specified value" }],',
      '    [{ order: 2, action: "Read measured value" }, { order: 1, action: "Compare specified value" }],',
      "  ];",
      "  for (const [index, steps] of invalidCases.entries()) {",
      "    const { dbPath } = fixture(t);",
      "    core.registerSource(dbPath, source());",
      '    const payload = { title: "Check boost pressure", safety_notes: ["Keep clear of moving parts"], steps };',
      '    const record = { record_type: "repair_procedure", natural_key: "run85:invalid:" + index, source_record_key: "run85:invalid:" + index,',
      '      title: "Invalid step ordering", market_scope: "ALL", applicability_precision: "unknown", payload, record_sha256: core.sha256(payload) };',
      '    assert.throws(() => core.importPackage(dbPath, packageOf([record], { package_id: "run85-invalid-steps-" + index })), /order values must be unique and strictly increasing/);',
      '    const db = new DatabaseSync(dbPath, { readOnly: true });',
      '    assert.equal(db.prepare("SELECT count(*) AS n FROM technical_records").get().n, 0);',
      '    assert.equal(db.prepare("SELECT count(*) AS n FROM import_batches").get().n, 0);',
      "    db.close();",
      "  }",
      "});",
      "",
      'test("run85 accepts sparse but strictly increasing technical step numbers", (t) => {',
      "  const { dbPath } = fixture(t);",
      "  core.registerSource(dbPath, source());",
      '  const payload = { title: "Check boost pressure", safety_notes: ["Keep clear of moving parts"],',
      '    steps: [{ order: 1, action: "Read measured value" }, { order: 3, action: "Compare specified value" }] };',
      '  const record = { record_type: "repair_procedure", natural_key: "run85:sparse-steps", source_record_key: "run85:sparse-steps",',
      '    title: "Valid sparse step order", market_scope: "ALL", applicability_precision: "unknown", payload, record_sha256: core.sha256(payload) };',
      '  const result = core.importPackage(dbPath, packageOf([record], { package_id: "run85-valid-sparse-steps" }));',
      '  assert.equal(result.status, "applied");',
      "  assert.equal(result.inserted, 1);",
      "});",
      "",
      testAnchor
    ].join(testEol);
    tests = replaceExactly(tests, testAnchor, newTests, "step-order regression tests");
  }

  fs.writeFileSync(dbPath, db, "utf8");
  fs.writeFileSync(testPath, tests, "utf8");
  console.log(JSON.stringify({
    status: "patched",
    patch: "run85-technical-step-order-validation",
    files: ["lib/local-core-db.cjs", "tests/local-core-db.test.cjs"],
    policy: "step order values must be unique and strictly increasing; sparse increasing values remain valid"
  }));
}

try {
  main();
} catch (error) {
  console.error("Run85 technical step-order patch failed: " + error.message);
  process.exitCode = 1;
}
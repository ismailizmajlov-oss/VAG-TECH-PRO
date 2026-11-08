#!/usr/bin/env node
"use strict";
const fs = require("node:fs"), path = require("node:path");
const GENERIC_PATTERN = "^(?:P0[0-9A-F]{3}|P2[0-9A-F]{3}|P34[0-9A-F]{2}|B0[0-9A-F]{3}|C0[0-9A-F]{3}|U0[0-9A-F]{3})$";
const MANUFACTURER_PATTERN = "^(?:P1[0-9A-F]{3}|P3[0-3][0-9A-F]{2}|B[12][0-9A-F]{3}|C[12][0-9A-F]{3}|U[12][0-9A-F]{3})$";
const MARKER = "// run87: quarantine unresolved P35-P39 and U3 DTC ranges";
function read(root, rel) {
  const file = path.join(root, rel);
  if (!fs.existsSync(file)) throw new Error("run87 required file is missing: " + rel);
  return fs.readFileSync(file, "utf8");
}
function write(root, rel, content) {
  const file = path.join(root, rel);
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, content, "utf8");
}
function replacePatternLine(source, name, pattern) {
  const re = new RegExp("const " + name + " = /[^\\r\\n]+/");
  if (!re.test(source)) {
    if (source.includes("const " + name + " = /" + pattern + "/")) return source;
    throw new Error("run87 could not locate DTC validator constant: " + name);
  }
  return source.replace(re, "const " + name + " = /" + pattern + "/");
}
function apply(root) {
  const corePath = "lib/local-core-db.cjs";
  const testsPath = "tests/local-core-db.test.cjs";
  const schemaPath = "data/schemas/technical-record-payloads.schema.json";
  const docsPath = "docs/LOCAL_VEHICLE_CATALOG_IMPORT.md";
  let core = read(root, corePath);
  let tests = read(root, testsPath);
  const schema = JSON.parse(read(root, schemaPath));
  let docs = read(root, docsPath);

  if (!core.includes("// run86: separate generic SAE/ISO code ranges from manufacturer-controlled OBD-II ranges")) {
    throw new Error("run87 requires the run86 namespace guard to be present");
  }
  if (core.includes(MARKER)) {
    const genericOk = core.includes("const GENERIC_OBD_DTC_CODE_RE = /" + GENERIC_PATTERN + "/");
    const manufacturerOk = core.includes("const MANUFACTURER_CONTROLLED_OBD_DTC_CODE_RE = /" + MANUFACTURER_PATTERN + "/");
    if (!genericOk || !manufacturerOk ||
        schema.$defs?.dtc_generic?.properties?.code?.pattern !== GENERIC_PATTERN ||
        schema.$defs?.dtc_vag_specific?.properties?.code?.pattern !== MANUFACTURER_PATTERN ||
        !tests.includes("run87 rejects unresolved U3 range in generic DTC records") ||
        !tests.includes("run87 rejects P35-P39 and U3 from VAG-specific DTC records")) {
      throw new Error("run87 marker exists but conservative contracts are incomplete");
    }
    return { status: "already_applied", genericPattern: GENERIC_PATTERN, manufacturerPattern: MANUFACTURER_PATTERN };
  }

  core = replacePatternLine(core, "GENERIC_OBD_DTC_CODE_RE", GENERIC_PATTERN);
  core = replacePatternLine(core, "MANUFACTURER_CONTROLLED_OBD_DTC_CODE_RE", MANUFACTURER_PATTERN);
  core = core.replace("// run86: separate generic SAE/ISO code ranges from manufacturer-controlled OBD-II ranges",
    "// run86: separate generic SAE/ISO code ranges from manufacturer-controlled OBD-II ranges\n" + MARKER);

  for (const type of ["dtc_generic", "dtc_vag_specific"]) {
    const pattern = type === "dtc_generic" ? GENERIC_PATTERN : MANUFACTURER_PATTERN;
    for (const alias of ["code", "dtc_code"]) {
      if (!schema.$defs?.[type]?.properties?.[alias]) throw new Error("run87 missing DTC schema alias: " + type + "." + alias);
      schema.$defs[type].properties[alias].pattern = pattern;
    }
  }

  const testAnchor = 'test("rejects a generic DTC record that tries to claim VAG or ECU applicability", (t) => {';
  if (!tests.includes("run87 rejects unresolved U3 range in generic DTC records")) {
    const additions = [
      'test("run87 rejects unresolved U3 range in generic DTC records", (t) => {',
      '  const { dbPath } = fixture(t);',
      '  core.registerSource(dbPath, source());',
      '  const payload = { code: "U3000", title: "Unresolved U3 family", namespace: "SAE/ISO" };',
      '  const invalid = { ...genericDtc(), natural_key: "generic:U3000", source_record_key: "obd:U3000", title: "U3000", payload, record_sha256: core.sha256(payload) };',
      '  assert.throws(() => core.importPackage(dbPath, packageOf([invalid], { package_id: "run87-generic-u3-invalid" })), /outside generic SAE\/ISO OBD-II ranges/);',
      '  const db = new DatabaseSync(dbPath, { readOnly: true });',
      '  assert.equal(db.prepare("SELECT count(*) AS n FROM technical_records").get().n, 0);',
      '  assert.equal(db.prepare("SELECT count(*) AS n FROM import_batches").get().n, 0);',
      '  db.close();',
      '});',
      '',
      'test("run87 rejects P35-P39 and U3 from VAG-specific DTC records", (t) => {',
      '  for (const code of ["P35A6", "P39AB", "U3000"]) {',
      '    const { dbPath } = fixture(t);',
      '    core.registerSource(dbPath, source());',
      '    const payload = { code, description: "Unresolved SAE/ISO or manufacturer range" };',
      '    const invalid = { record_type: "dtc_vag_specific", namespace: "vag_oem_specific", natural_key: "vag:" + code, source_record_key: "vag:" + code,',
      '      title: code, market_scope: "ALL", applicability_precision: "exact_configuration", configuration_id: 1, ecu_id: 1, payload, record_sha256: core.sha256(payload) };',
      '    assert.throws(() => core.importPackage(dbPath, packageOf([invalid], { package_id: "run87-vag-unresolved-" + code })), /outside manufacturer-controlled OBD-II ranges/);',
      '    const db = new DatabaseSync(dbPath, { readOnly: true });',
      '    assert.equal(db.prepare("SELECT count(*) AS n FROM technical_records").get().n, 0);',
      '    assert.equal(db.prepare("SELECT count(*) AS n FROM import_batches").get().n, 0);',
      '    db.close();',
      '  }',
      '});',
      '',
      testAnchor
    ].join("\n");
    if (!tests.includes(testAnchor)) throw new Error("run87 test insertion anchor is missing");
    tests = tests.replace(testAnchor, additions);
  }

  if (!docs.includes("## Conservative DTC range correction (run87)")) {
    docs += [
      "",
      "",
      "## Conservative DTC range correction (run87)",
      "",
      "The importer no longer treats P35xx-P39xx as manufacturer-controlled or U3xxx as automatically generic. P35xx-P39xx are reserved in the publicly available SAE J2012 MAR2013 allocation; U3xxx is described as manufacturer-controlled and ISO/SAE-reserved, so a prefix alone cannot establish a generic or VAG-specific assignment. Until the current SAE J2012 Digital Annex revision is licensed and checked code by code, these families are rejected from the normalized generic and VAG-specific namespaces.",
      "",
      "P30xx-P33xx remain manufacturer-controlled. P34xx is admitted only as a source-backed generic record where the pinned upstream record exists; this range guard does not itself prove that a code is assigned in the latest J2012DA. Generic P0/P2/B0/C0/U0 records remain separate from manufacturer-controlled P1/P30-P33/B1-B2/C1-C2/U1-U2 records.",
      "",
      "OBDex P3/U3 research rows remain in their isolated source-labelled research pack and do not gain VAG fitment or OEM approval. A manufacturer-controlled code range is not evidence of Volkswagen Group authorship, ECU applicability, or repair instructions.",
      ""
    ].join("\n");
  }

  write(root, corePath, core);
  write(root, testsPath, tests);
  write(root, schemaPath, JSON.stringify(schema, null, 2) + "\n");
  write(root, docsPath, docs);
  return { status: "applied", genericPattern: GENERIC_PATTERN, manufacturerPattern: MANUFACTURER_PATTERN,
    unresolved: ["P35xx-P39xx", "U3xxx"], files: [corePath, testsPath, schemaPath, docsPath] };
}
const index = process.argv.indexOf("--desktop-root");
const root = path.resolve(index >= 0 && process.argv[index + 1] ? process.argv[index + 1] : "desktop-source");
process.stdout.write(JSON.stringify(apply(root), null, 2) + "\n");

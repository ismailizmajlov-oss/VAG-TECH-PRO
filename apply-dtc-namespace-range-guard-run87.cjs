#!/usr/bin/env node
"use strict";

const fs = require("node:fs");
const path = require("node:path");

const GENERIC_PATTERN = "^(?:P0[0-9A-F]{3}|P2[0-9A-F]{3}|P34[0-9A-F]{2}|B0[0-9A-F]{3}|C0[0-9A-F]{3}|U0[0-9A-F]{3})$";
const MANUFACTURER_PATTERN = "^(?:P1[0-9A-F]{3}|P3[0-3][0-9A-F]{2}|B[12][0-9A-F]{3}|C[12][0-9A-F]{3}|U[12][0-9A-F]{3})$";
const OLD_GENERIC = "^(?:P0[0-9A-F]{3}|P2[0-9A-F]{3}|P34[0-9A-F]{2}|B0[0-9A-F]{3}|C0[0-9A-F]{3}|U0[0-9A-F]{3}|U3[0-9A-F]{3})$";
const OLD_MANUFACTURER = "^(?:P1[0-9A-F]{3}|P3(?:[0-3]|[5-9])[0-9A-F]{2}|B[12][0-9A-F]{3}|C[12][0-9A-F]{3}|U[12][0-9A-F]{3})$";
const MARKER = "// run87: conservative DTC range policy; U3xxx and P35xx-P39xx are not normalized import ranges";

function replaceOnce(value, before, after, label) {
  const count = value.split(before).length - 1;
  if (count !== 1) throw new Error(label + ": expected one patch anchor, found " + count);
  return value.replace(before, after);
}

function readText(root, relative) {
  const file = path.join(root, relative);
  if (!fs.existsSync(file)) throw new Error("run87 required file is missing: " + relative);
  return fs.readFileSync(file, "utf8");
}

function updateOemSchema(file) {
  const schema = JSON.parse(fs.readFileSync(file, "utf8"));
  if (!Array.isArray(schema.allOf)) throw new Error("OEM DTC schema allOf is missing");
  const updates = [
    ["generic_sae_iso", GENERIC_PATTERN],
    ["manufacturer_specific_vag", MANUFACTURER_PATTERN],
    ["manufacturer_specific_other", MANUFACTURER_PATTERN]
  ];
  for (const [namespace, pattern] of updates) {
    const matches = schema.allOf.filter((entry) => entry?.if?.properties?.dtc_namespace?.const === namespace);
    if (matches.length !== 1 || !matches[0]?.then?.properties?.dtc) {
      throw new Error("OEM DTC schema must have exactly one conditional for " + namespace);
    }
    matches[0].then.properties.dtc.pattern = pattern;
  }
  fs.writeFileSync(file, JSON.stringify(schema, null, 2) + "\n", "utf8");
}

function updateTechnicalPayloadSchema(file) {
  if (!fs.existsSync(file)) return false;
  const schema = JSON.parse(fs.readFileSync(file, "utf8"));
  let changed = false;
  for (const [name, pattern] of [["dtc_generic", GENERIC_PATTERN], ["dtc_vag_specific", MANUFACTURER_PATTERN]]) {
    const definition = schema.$defs?.[name];
    if (!definition?.properties) continue;
    for (const field of ["code", "dtc_code"]) {
      if (definition.properties[field]) {
        definition.properties[field].pattern = pattern;
        changed = true;
      }
    }
  }
  if (changed) fs.writeFileSync(file, JSON.stringify(schema, null, 2) + "\n", "utf8");
  return changed;
}

function apply(root) {
  const corePath = path.join(root, "lib/local-core-db.cjs");
  const testsPath = path.join(root, "tests/local-core-db.test.cjs");
  const docsPath = path.join(root, "docs/LOCAL_VEHICLE_CATALOG_IMPORT.md");
  const oemSchemaPath = path.join(root, "data/schemas/oem-dtc-index.schema.json");
  const technicalSchemaPath = path.join(root, "data/schemas/technical-record-payloads.schema.json");

  let core = readText(root, "lib/local-core-db.cjs");
  let tests = readText(root, "tests/local-core-db.test.cjs");
  let docs = readText(root, "docs/LOCAL_VEHICLE_CATALOG_IMPORT.md");
  if (!fs.existsSync(oemSchemaPath)) throw new Error("run87 OEM DTC schema is missing");

  if (core.includes(MARKER)) {
    if (!core.includes("const GENERIC_OBD_DTC_CODE_RE = /" + GENERIC_PATTERN + "/;") ||
        !core.includes("const MANUFACTURER_CONTROLLED_OBD_DTC_CODE_RE = /" + MANUFACTURER_PATTERN + "/;") ||
        !tests.includes("run87 rejects unresolved U3xxx in generic DTC namespace") ||
        !tests.includes("run87 rejects reserved P35xx-P39xx and U3xxx in VAG-specific namespace")) {
      throw new Error("run87 marker exists but code or regression tests are incomplete");
    }
    updateOemSchema(oemSchemaPath);
    updateTechnicalPayloadSchema(technicalSchemaPath);
    return { status: "already_applied", generic_pattern: GENERIC_PATTERN, manufacturer_pattern: MANUFACTURER_PATTERN };
  }

  const oldGenericDeclaration = "const GENERIC_OBD_DTC_CODE_RE = /" + OLD_GENERIC + "/;";
  const oldManufacturerDeclaration = "const MANUFACTURER_CONTROLLED_OBD_DTC_CODE_RE = /" + OLD_MANUFACTURER + "/;";
  const newDeclarations = MARKER + "\n" +
    "const GENERIC_OBD_DTC_CODE_RE = /" + GENERIC_PATTERN + "/;\n" +
    "const MANUFACTURER_CONTROLLED_OBD_DTC_CODE_RE = /" + MANUFACTURER_PATTERN + "/;";
  core = replaceOnce(core, oldGenericDeclaration, newDeclarations, "run87 generic DTC range");
  core = replaceOnce(core, oldManufacturerDeclaration, "", "run87 manufacturer DTC range");
  if (core.includes(OLD_GENERIC) || core.includes(OLD_MANUFACTURER)) {
    throw new Error("run87 obsolete DTC range fragments remain in local core");
  }

  const testAnchor = 'test("run86 rejects generic DTC ranges in VAG-specific records", (t) => {';
  if (!tests.includes(testAnchor)) throw new Error("run87 test insertion anchor is missing");
  const additions = [
    'test("run87 rejects unresolved U3xxx in generic DTC namespace", (t) => {',
    '  const { dbPath } = fixture(t);',
    '  core.registerSource(dbPath, source());',
    '  const validPayload = { code: "P34C8", title: "Generic P34 range", namespace: "SAE/ISO" };',
    '  const valid = { ...genericDtc(), natural_key: "generic:P34C8", source_record_key: "obd:P34C8", title: "P34C8", payload: validPayload, record_sha256: core.sha256(validPayload) };',
    '  const accepted = core.importPackage(dbPath, packageOf([valid], { package_id: "run87-generic-p34-valid" }));',
    '  assert.equal(accepted.inserted, 1);',
    '  const invalidPayload = { code: "U3000", title: "Unresolved U3 range", namespace: "SAE/ISO" };',
    '  const invalid = { ...valid, natural_key: "generic:U3000", source_record_key: "obd:U3000", title: "U3000", payload: invalidPayload, record_sha256: core.sha256(invalidPayload) };',
    '  assert.throws(() => core.importPackage(dbPath, packageOf([invalid], { package_id: "run87-generic-u3-invalid" })), /outside generic SAE\\/ISO OBD-II ranges/);',
    '  const db = new DatabaseSync(dbPath, { readOnly: true });',
    '  assert.equal(db.prepare("SELECT count(*) AS n FROM technical_records").get().n, 1);',
    '  assert.equal(db.prepare("SELECT count(*) AS n FROM import_batches").get().n, 1);',
    '  db.close();',
    '});',
    '',
    'test("run87 rejects reserved P35xx-P39xx and U3xxx in VAG-specific namespace", (t) => {',
    '  const { dbPath } = fixture(t);',
    '  core.registerSource(dbPath, source());',
    '  for (const code of ["P3500", "P3900", "U3000"]) {',
    '    const payload = { code, description: "Reserved or unresolved DTC range" };',
    '    const invalid = { record_type: "dtc_vag_specific", namespace: "vag_oem_specific", natural_key: "vag:" + code, source_record_key: "vag:" + code,',
    '      title: code, market_scope: "ALL", applicability_precision: "exact_configuration", configuration_id: 1, ecu_id: 1, payload, record_sha256: core.sha256(payload) };',
    '    assert.throws(() => core.importPackage(dbPath, packageOf([invalid], { package_id: "run87-vag-invalid-" + code })), /outside manufacturer-controlled OBD-II ranges/);',
    '  }',
    '  const db = new DatabaseSync(dbPath, { readOnly: true });',
    '  assert.equal(db.prepare("SELECT count(*) AS n FROM technical_records").get().n, 0);',
    '  assert.equal(db.prepare("SELECT count(*) AS n FROM import_batches").get().n, 0);',
    '  db.close();',
    '});',
    '',
    testAnchor
  ].join("\n");
  tests = replaceOnce(tests, testAnchor, additions, "run87 regression tests");

  const heading = "## DTC namespace code-range boundary (run86)";
  const sectionStart = docs.indexOf(heading);
  if (sectionStart < 0) throw new Error("run87 documentation section anchor is missing");
  const nextHeading = docs.indexOf("\n## ", sectionStart + heading.length);
  const sectionEnd = nextHeading < 0 ? docs.length : nextHeading;
  const replacement = [
    "## DTC namespace code-range boundary (run87)",
    "",
    "The normalized importer applies a conservative namespace gate: generic SAE/ISO records may use P0xxx, P2xxx, P34xx, B0xxx, C0xxx and U0xxx; manufacturer-controlled candidates may use P1xxx, P30xx–P33xx, B1xxx–B2xxx, C1xxx–C2xxx and U1xxx–U2xxx. These family boundaries are not a current DTC allocation list, and a code is imported only when it exists in the pinned source snapshot.",
    "",
    "P35xx–P39xx, B3xxx, C3xxx and U3xxx are unresolved or reserved for this importer and are rejected before transaction commit in both normalized namespaces. The current J2012DA_202607 allocation table has not been acquired under a reuse licence, so the gate does not claim that every code in an allowed family is currently assigned. A range classification is not evidence of Volkswagen Group authorship: VAG-specific records still require an identified VAG manufacturer, source-document revision and evidence locator, SHA-256, explicit storage/display/redistribution rights, exact ECU/configuration applicability and independent technical review.",
    "",
    "The upstream OBDex CC0 snapshot preserves its publisher's original family classification in a separate read-only research namespace. In particular, upstream U3xxx rows are not promoted into the normalized generic DTC index. No copyrighted SAE standard text or current digital-annex allocation table is copied into the application.",
    ""
  ].join("\n");
  docs = docs.slice(0, sectionStart) + replacement + (nextHeading < 0 ? "" : docs.slice(sectionEnd));

  updateOemSchema(oemSchemaPath);
  const technicalSchemaUpdated = updateTechnicalPayloadSchema(technicalSchemaPath);
  fs.writeFileSync(corePath, core, "utf8");
  fs.writeFileSync(testsPath, tests, "utf8");
  fs.writeFileSync(docsPath, docs, "utf8");

  return {
    status: "applied",
    generic_pattern: GENERIC_PATTERN,
    manufacturer_pattern: MANUFACTURER_PATTERN,
    technical_payload_schema_updated: technicalSchemaUpdated,
    oem_schema_updated: true,
    tests_added: 2
  };
}

const arg = process.argv.indexOf("--desktop-root");
const root = path.resolve(arg >= 0 && process.argv[arg + 1] ? process.argv[arg + 1] : "desktop-source");
console.log(JSON.stringify(apply(root)));

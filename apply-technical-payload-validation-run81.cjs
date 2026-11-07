"use strict";
const fs = require("node:fs");
const path = require("node:path");

function argumentValue(flag, fallback) {
  const index = process.argv.indexOf(flag);
  return index >= 0 && process.argv[index + 1] ? process.argv[index + 1] : fallback;
}
function replaceOnce(text, pattern, replacement, label) {
  const matches = [...text.matchAll(pattern)];
  if (matches.length !== 1) throw new Error(label + " patch anchor count was " + matches.length + "; expected exactly one");
  return text.replace(pattern, replacement);
}
const desktopRoot = path.resolve(argumentValue("--desktop-root", "desktop-source"));
const corePath = path.join(desktopRoot, "lib", "local-core-db.cjs");
const testPath = path.join(desktopRoot, "tests", "local-core-db.test.cjs");
const schemaPath = path.join(desktopRoot, "data", "schemas", "technical-record-payloads.schema.json");
for (const file of [corePath, testPath, schemaPath]) {
  if (!fs.existsSync(file)) throw new Error("Run81 required source file is missing: " + file);
}
let core = fs.readFileSync(corePath, "utf8");
if (!core.includes("// run81: renderer-aligned strict payload contract")) {
  const newDtc = [
    'case "dtc_generic": {',
    '      technicalPayloadOnlyKeys(record, payload, ["code", "dtc_code", "standard", "namespace", "description", "title", "diagnostic_notes", "possible_causes"], "payload");',
    '      for (const field of ["code", "dtc_code", "standard", "namespace", "description", "title"]) technicalPayloadString(record, payload, field);',
    '      const code = payload.code != null ? payload.code : payload.dtc_code;',
    '      if (typeof code !== "string" || !code.trim()) technicalPayloadError(record, "code or dtc_code is required");',
    '      if (payload.code != null && payload.dtc_code != null && payload.code.trim() !== payload.dtc_code.trim()) technicalPayloadError(record, "code and dtc_code must match when both are supplied");',
    '      if (!(typeof payload.description === "string" && payload.description.trim()) && !(typeof payload.title === "string" && payload.title.trim())) technicalPayloadError(record, "description or title is required");',
    '      if (Array.isArray(payload.diagnostic_notes)) technicalPayloadStringArray(record, payload, "diagnostic_notes");',
    '      else technicalPayloadString(record, payload, "diagnostic_notes");',
    '      stringArrayFields(["possible_causes"]);',
    '      break;',
    '    }',
    '    case "dtc_vag_specific": {',
    '      technicalPayloadOnlyKeys(record, payload, ["code", "dtc_code", "system", "system_name", "subsystem", "fault_type", "ecu_family", "ecu_address", "description", "long_description", "title", "diagnostic_notes", "possible_causes", "symptoms", "test_conditions", "safety_notes"], "payload");',
    '      for (const field of ["code", "dtc_code", "system", "system_name", "subsystem", "fault_type", "ecu_family", "ecu_address", "description", "long_description", "title"]) technicalPayloadString(record, payload, field);',
    '      const code = payload.code != null ? payload.code : payload.dtc_code;',
    '      if (typeof code !== "string" || !code.trim()) technicalPayloadError(record, "code or dtc_code is required");',
    '      if (payload.code != null && payload.dtc_code != null && payload.code.trim() !== payload.dtc_code.trim()) technicalPayloadError(record, "code and dtc_code must match when both are supplied");',
    '      if (!(typeof payload.description === "string" && payload.description.trim()) && !(typeof payload.long_description === "string" && payload.long_description.trim()) && !(typeof payload.title === "string" && payload.title.trim())) technicalPayloadError(record, "description, long_description or title is required");',
    '      if (Array.isArray(payload.diagnostic_notes)) technicalPayloadStringArray(record, payload, "diagnostic_notes");',
    '      else technicalPayloadString(record, payload, "diagnostic_notes");',
    '      stringArrayFields(["possible_causes", "symptoms", "test_conditions", "safety_notes"]);',
    '      break;',
    '    }',
    '    case "diagnostic_test_plan": {'
  ].join("\n");
  core = replaceOnce(core, /case "dtc_generic":\s*case "dtc_vag_specific": \{[\s\S]*?\n    \}\n    case "diagnostic_test_plan": \{/g, newDtc, "DTC payload");
  core = replaceOnce(core,
    /technicalPayloadOnlyKeys\(record, payload, \["preconditions", "steps", "expected_results", "test_conditions", "tool_requirements", "safety_notes"\], "payload"\);/g,
    'technicalPayloadOnlyKeys(record, payload, ["test_purpose", "purpose", "system", "system_name", "ecu_family", "ecu_identity_id", "preconditions", "steps", "expected_results", "test_conditions", "tool_requirements", "safety_notes"], "payload");',
    "diagnostic test plan allowed fields");
  core = replaceOnce(core,
    /technicalPayloadStringArray\(record, payload, "safety_notes", true, 1\);\s*stringArrayFields\(\["preconditions", "expected_results", "test_conditions", "tool_requirements"\]\);/g,
    'technicalPayloadStringArray(record, payload, "safety_notes", true, 1);\n      for (const field of ["test_purpose", "purpose", "system", "system_name", "ecu_family"]) technicalPayloadString(record, payload, field);\n      technicalPayloadNumber(record, payload, "ecu_identity_id", { integer: true, minimum: 1 });\n      stringArrayFields(["preconditions", "expected_results", "test_conditions", "tool_requirements"]);',
    "diagnostic test plan display metadata");
  core = replaceOnce(core,
    /technicalPayloadOnlyKeys\(record, payload, \["ecu_identity_id", "diagnostic_protocol", "hardware_revision", "software_revision", "coding_notes", "security_access_document_ref", "programming_notes"\], "payload"\);/g,
    'technicalPayloadOnlyKeys(record, payload, ["ecu_identity_id", "diagnostic_protocol", "ecu_family", "ecu_address", "hardware_revision", "software_revision", "hardware_number", "software_number", "coding_notes", "security_access_document_ref", "programming_notes"], "payload");',
    "ECU profile allowed fields");
  core = replaceOnce(core,
    /for \(const field of \["hardware_revision", "software_revision", "coding_notes", "security_access_document_ref", "programming_notes"\]\) technicalPayloadString\(record, payload, field\);/g,
    'for (const field of ["ecu_family", "ecu_address", "hardware_revision", "software_revision", "hardware_number", "software_number", "coding_notes", "security_access_document_ref", "programming_notes"]) technicalPayloadString(record, payload, field);',
    "ECU profile display metadata");
  core = core.replace("\nfunction validateRecord(record, packageInfo) {", "\n// run81: renderer-aligned strict payload contract\nfunction validateRecord(record, packageInfo) {");
  fs.writeFileSync(corePath, core, "utf8");
}

const schema = JSON.parse(fs.readFileSync(schemaPath, "utf8"));
const enumValues = schema.properties && schema.properties.record_kind && schema.properties.record_kind.enum;
if (!Array.isArray(enumValues)) throw new Error("Run81 schema record_kind enum is missing");
for (const kind of ["dtc_generic", "dtc_vag_specific"]) if (!enumValues.includes(kind)) enumValues.push(kind);
schema.$defs = schema.$defs || {};
schema.$defs.diagnostic_test_plan.properties = {
  ...schema.$defs.diagnostic_test_plan.properties,
  test_purpose: { type: "string" }, purpose: { type: "string" }, system: { type: "string" },
  system_name: { type: "string" }, ecu_family: { type: "string" }, ecu_identity_id: { type: "integer", minimum: 1 }
};
schema.$defs.ecu_profile.properties = {
  ...schema.$defs.ecu_profile.properties,
  ecu_family: { type: "string" }, ecu_address: { type: "string" },
  hardware_number: { type: "string" }, software_number: { type: "string" }
};
schema.$defs.dtc_generic = {
  type: "object",
  properties: {
    code: { type: "string", minLength: 1 }, dtc_code: { type: "string", minLength: 1 },
    standard: { type: "string" }, namespace: { type: "string" }, description: { type: "string" },
    title: { type: "string" }, diagnostic_notes: { oneOf: [{ type: "string" }, { type: "array", items: { type: "string" } }] },
    possible_causes: { type: "array", items: { type: "string" } }
  },
  allOf: [
    { anyOf: [{ required: ["code"] }, { required: ["dtc_code"] }] },
    { anyOf: [{ required: ["description"] }, { required: ["title"] }] }
  ],
  additionalProperties: false
};
schema.$defs.dtc_vag_specific = {
  type: "object",
  properties: {
    code: { type: "string", minLength: 1 }, dtc_code: { type: "string", minLength: 1 },
    system: { type: "string" }, system_name: { type: "string" }, subsystem: { type: "string" },
    fault_type: { type: "string" }, ecu_family: { type: "string" }, ecu_address: { type: "string" },
    description: { type: "string" }, long_description: { type: "string" }, title: { type: "string" },
    diagnostic_notes: { oneOf: [{ type: "string" }, { type: "array", items: { type: "string" } }] },
    possible_causes: { type: "array", items: { type: "string" } }, symptoms: { type: "array", items: { type: "string" } },
    test_conditions: { type: "array", items: { type: "string" } }, safety_notes: { type: "array", items: { type: "string" } }
  },
  allOf: [
    { anyOf: [{ required: ["code"] }, { required: ["dtc_code"] }] },
    { anyOf: [{ required: ["description"] }, { required: ["long_description"] }, { required: ["title"] }] }
  ],
  additionalProperties: false
};
schema.allOf = schema.allOf || [];
for (const kind of ["dtc_generic", "dtc_vag_specific"]) {
  if (!schema.allOf.some(rule => rule.if && rule.if.properties && rule.if.properties.record_kind && rule.if.properties.record_kind.const === kind)) {
    schema.allOf.push({ if: { properties: { record_kind: { const: kind } }, required: ["record_kind"] }, then: { properties: { payload: { $ref: "#/$defs/" + kind } } } });
  }
}
fs.writeFileSync(schemaPath, JSON.stringify(schema, null, 2) + "\n", "utf8");

let tests = fs.readFileSync(testPath, "utf8");
if (!tests.includes("run81 validates renderer metadata and DTC payload boundaries")) {
  const additions = [
    "",
    'test("run81 validates renderer metadata and DTC payload boundaries", (t) => {',
    '  const { dbPath } = fixture(t);',
    '  core.registerSource(dbPath, source());',
    '  const planPayload = { test_purpose: "Check boost pressure", system: "Engine", ecu_family: "MED17.5.25", steps: [{ order: 1, action: "Read specified and actual pressure" }], safety_notes: ["Keep clear of moving parts"] };',
    '  const plan = { record_type: "diagnostic_test_plan", natural_key: "run81:plan", source_record_key: "run81:plan", title: "Boost pressure test", market_scope: "ALL", applicability_precision: "unknown", payload: planPayload, record_sha256: core.sha256(planPayload) };',
    '  core.importPackage(dbPath, packageOf([plan], { package_id: "run81-plan-package" }));',
    '  const ecuPayload = { ecu_identity_id: 1, diagnostic_protocol: "UDS", ecu_family: "MED17.5.25", ecu_address: "01", hardware_number: "06K907425", software_number: "0001" };',
    '  const ecu = { record_type: "ecu_reference", natural_key: "run81:ecu", source_record_key: "run81:ecu", title: "MED17.5.25", market_scope: "ALL", applicability_precision: "unknown", payload: ecuPayload, record_sha256: core.sha256(ecuPayload) };',
    '  core.importPackage(dbPath, packageOf([ecu], { package_id: "run81-ecu-package" }));',
    '});',
    "",
    'test("run81 keeps generic DTC payloads separate and rejects unknown or conflicting fields", (t) => {',
    '  const { dbPath } = fixture(t);',
    '  core.registerSource(dbPath, source());',
    '  const payload = { dtc_code: "P0300", description: "Random or multiple cylinder misfire", standard: "SAE/ISO", possible_causes: ["Ignition fault"] };',
    '  const valid = { record_type: "dtc_generic", namespace: "generic_sae_iso_obd2", natural_key: "run81:generic:P0300", source_record_key: "run81:generic:P0300", title: "P0300", market_scope: "ALL", applicability_precision: "generic_standard", payload, record_sha256: core.sha256(payload) };',
    '  core.importPackage(dbPath, packageOf([valid], { package_id: "run81-generic-valid" }));',
    '  const vagLeakPayload = { ...payload, ecu_family: "MED17.5.25" };',
    '  const vagLeak = { ...valid, natural_key: "run81:generic:leak", source_record_key: "run81:generic:leak", payload: vagLeakPayload, record_sha256: core.sha256(vagLeakPayload) };',
    '  assert.throws(() => core.importPackage(dbPath, packageOf([vagLeak], { package_id: "run81-generic-vag-leak" })), /unsupported field/i);',
    '  const conflictPayload = { code: "P0300", dtc_code: "P0301", description: "Conflicting aliases" };',
    '  const conflict = { ...valid, natural_key: "run81:generic:conflict", source_record_key: "run81:generic:conflict", payload: conflictPayload, record_sha256: core.sha256(conflictPayload) };',
    '  assert.throws(() => core.importPackage(dbPath, packageOf([conflict], { package_id: "run81-generic-conflict" })), /code and dtc_code must match/i);',
    '});',
    "",
    'test("run81 JSON schema matches the renderer and strict DTC payload contract", () => {',
    '  const schemaPath = path.join(__dirname, "..", "data", "schemas", "technical-record-payloads.schema.json");',
    '  const schema = JSON.parse(fs.readFileSync(schemaPath, "utf8"));',
    '  for (const kind of ["dtc_generic", "dtc_vag_specific"]) assert.ok(schema.properties.record_kind.enum.includes(kind));',
    '  for (const field of ["test_purpose", "system", "system_name", "ecu_family"]) assert.ok(schema.$defs.diagnostic_test_plan.properties[field]);',
    '  for (const field of ["ecu_family", "ecu_address", "hardware_number", "software_number"]) assert.ok(schema.$defs.ecu_profile.properties[field]);',
    '  assert.equal(schema.$defs.dtc_generic.additionalProperties, false);',
    '  assert.equal(schema.$defs.dtc_vag_specific.additionalProperties, false);',
    '});',
    ""
  ].join("\n");
  tests += additions;
  fs.writeFileSync(testPath, tests, "utf8");
}
console.log("Run81 renderer-aligned payload validation applied.");

"use strict";
const fs = require("node:fs");
const path = require("node:path");
const crypto = require("node:crypto");

function replaceOnce(source, before, after, label) {
  const index = source.indexOf(before);
  if (index < 0 || source.indexOf(before, index + before.length) >= 0) throw new Error("Run78 patch anchor missing or ambiguous: " + label);
  return source.slice(0, index) + after + source.slice(index + before.length);
}

function patchCore(file) {
  let source = fs.readFileSync(file, "utf8").replace(/\r\n/g, "\n");
  if (source.includes("function validateTechnicalPayload(record)")) {
    if (!source.includes("  validateTechnicalPayload(record);")) throw new Error("Run78 validator is present but not enforced");
    return false;
  }
  const anchor = 'const APPLICABILITY_PRECISIONS = new Set(["exact_brand","exact_model","exact_generation","exact_engine","exact_transmission","exact_pairing","exact_ecu","exact_configuration","generic_standard","manufacturer_make_candidate","vehicle_model_candidate","generation_candidate","document_metadata_only","unknown"]);\n';
  const helper = [
    'const TECHNICAL_PAYLOAD_SCHEMA_KIND = Object.freeze({ diagnostic_test_plan: "diagnostic_test_plan", repair_procedure: "repair_procedure", wiring_diagram: "wiring_diagram", pinout: "ecu_pinout", torque_specification: "torque_specification", adaptation: "adaptation", service_interval: "service_interval", ecu_reference: "ecu_profile", oem_part: "oem_part", oem_supersession: "oem_supersession" });',
    'let cachedTechnicalPayloadSchema = null;',
    'function loadTechnicalPayloadSchema() {',
    '  const candidates = [];',
    '  if (process.env.VAG_TECH_PRO_SCHEMA_DIR) candidates.push(path.join(process.env.VAG_TECH_PRO_SCHEMA_DIR, "technical-record-payloads.schema.json"));',
    '  candidates.push(path.join(__dirname, "..", "data", "schemas", "technical-record-payloads.schema.json"));',
    '  candidates.push(path.join(process.cwd(), "data", "schemas", "technical-record-payloads.schema.json"));',
    '  for (const candidate of candidates) {',
    '    if (!fs.existsSync(candidate)) continue;',
    '    const stat = fs.statSync(candidate);',
    '    if (cachedTechnicalPayloadSchema?.path === candidate && cachedTechnicalPayloadSchema.mtimeMs === stat.mtimeMs) return cachedTechnicalPayloadSchema.schema;',
    '    const schema = JSON.parse(fs.readFileSync(candidate, "utf8"));',
    '    if (!schema || typeof schema !== "object" || !schema.$defs || schema.$schema !== "https://json-schema.org/draft/2020-12/schema") throw new Error("Unsupported technical payload schema document");',
    '    cachedTechnicalPayloadSchema = { path: candidate, mtimeMs: stat.mtimeMs, schema };',
    '    return schema;',
    '  }',
    '  throw new Error("Technical payload schema is missing; critical technical imports are blocked");',
    '}',
    'function schemaTypeMatches(value, type) {',
    '  if (type === "object") return value !== null && typeof value === "object" && !Array.isArray(value);',
    '  if (type === "array") return Array.isArray(value);',
    '  if (type === "integer") return typeof value === "number" && Number.isSafeInteger(value);',
    '  if (type === "number") return typeof value === "number" && Number.isFinite(value);',
    '  if (type === "string") return typeof value === "string";',
    '  if (type === "boolean") return typeof value === "boolean";',
    '  if (type === "null") return value === null;',
    '  return false;',
    '}',
    'function validateJsonSchemaNode(value, spec, root, at) {',
    '  if (!spec || typeof spec !== "object" || Array.isArray(spec)) return [at + ": invalid schema node"];',
    '  if (spec.$ref) { const prefix = "#/$defs/"; const key = spec.$ref.startsWith(prefix) ? spec.$ref.slice(prefix.length) : ""; if (!key || !root.$defs?.[key]) return [at + ": unresolved schema reference " + spec.$ref]; return validateJsonSchemaNode(value, root.$defs[key], root, at); }',
    '  const errors = []; const types = spec.type == null ? [] : Array.isArray(spec.type) ? spec.type : [spec.type];',
    '  if (types.length && !types.some(type => schemaTypeMatches(value, type))) return [at + ": expected " + types.join(" or ")];',
    '  if (Object.prototype.hasOwnProperty.call(spec, "const") && JSON.stringify(value) !== JSON.stringify(spec.const)) errors.push(at + ": value does not match const");',
    '  if (Array.isArray(spec.enum) && !spec.enum.some(item => JSON.stringify(item) === JSON.stringify(value))) errors.push(at + ": value is not in the allowed enum");',
    '  if (typeof value === "string") { if (Number.isInteger(spec.minLength) && value.length < spec.minLength) errors.push(at + ": string is shorter than " + spec.minLength); if (spec.pattern && !(new RegExp(spec.pattern)).test(value)) errors.push(at + ": string does not match the required pattern"); if (spec.format === "date" && !/^\d{4}-\d{2}-\d{2}$/.test(value)) errors.push(at + ": expected ISO date YYYY-MM-DD"); }',
    '  if (typeof value === "number" && Number.isFinite(value)) { if (typeof spec.minimum === "number" && value < spec.minimum) errors.push(at + ": number is below minimum " + spec.minimum); if (typeof spec.exclusiveMinimum === "number" && value <= spec.exclusiveMinimum) errors.push(at + ": number must be greater than " + spec.exclusiveMinimum); }',
    '  if (Array.isArray(value)) { if (Number.isInteger(spec.minItems) && value.length < spec.minItems) errors.push(at + ": array has fewer than " + spec.minItems + " items"); if (spec.uniqueItems && new Set(value.map(item => JSON.stringify(item))).size !== value.length) errors.push(at + ": array items must be unique"); if (spec.items) value.forEach((item, index) => errors.push(...validateJsonSchemaNode(item, spec.items, root, at + "[" + index + "]"))); }',
    '  if (value !== null && typeof value === "object" && !Array.isArray(value)) { for (const key of spec.required || []) if (!Object.prototype.hasOwnProperty.call(value, key)) errors.push(at + "." + key + ": required property is missing"); const properties = spec.properties || {}; for (const [key, child] of Object.entries(properties)) if (Object.prototype.hasOwnProperty.call(value, key)) errors.push(...validateJsonSchemaNode(value[key], child, root, at + "." + key)); if (spec.additionalProperties === false) for (const key of Object.keys(value)) if (!Object.prototype.hasOwnProperty.call(properties, key)) errors.push(at + "." + key + ": additional property is not allowed"); }',
    '  if (Array.isArray(spec.anyOf)) { const branches = spec.anyOf.map(branch => validateJsonSchemaNode(value, branch, root, at)); if (!branches.some(branchErrors => branchErrors.length === 0)) errors.push(at + ": none of the allowed schema alternatives matched"); }',
    '  return errors;',
    '}',
    'function validateTechnicalPayload(record) {',
    '  if (record.record_type === "dtc_generic" || record.record_type === "dtc_vag_specific") {',
    '    const code = record.payload.dtc ?? record.payload.code;',
    '    const saeIso = typeof code === "string" && /^[PBCU][0-9A-F]{4}$/.test(code);',
    '    const genericRange = saeIso && (code[0] === "P" ? (["0","2"].includes(code[1]) || (code[1] === "3" && code[2] === "4")) : code[1] === "0");',
    '    const manufacturerControlledRange = saeIso && (code[0] === "P" ? (code[1] === "1" || (code[1] === "3" && ["0","1","2","3"].includes(code[2]))) : (["B","C"].includes(code[0]) ? ["1","2"].includes(code[1]) : code[0] === "U" ? ["1","2"].includes(code[1]) : false));',
    '    const legacyVag = record.record_type === "dtc_vag_specific" && typeof code === "string" && /^\\d{5}$/.test(code);',
    '    const valid = record.record_type === "dtc_generic" ? genericRange : (legacyVag || manufacturerControlledRange);',
    '    if (!valid) throw new Error("DTC payload code does not match its declared generic or VAG-specific namespace for " + record.source_record_key);',
    '    return true;',
    '  }',
    '  const kind = TECHNICAL_PAYLOAD_SCHEMA_KIND[record.record_type]; if (!kind) return true;',
    '  const schema = loadTechnicalPayloadSchema(); const definition = schema.$defs[kind]; if (!definition) throw new Error("Technical payload schema is missing record kind " + kind);',
    '  const errors = validateJsonSchemaNode(record.payload, definition, schema, "$.payload"); if (errors.length) throw new Error("Technical payload schema validation failed for " + record.source_record_key + ": " + errors.slice(0, 8).join("; ")); return true;',
    '}'
  ].join("\n") + "\n";
  source = replaceOnce(source, anchor, anchor + helper, "applicability precision constants");
  const validationAnchor = '  if (record.record_type === "dtc_vag_specific") {\n    if (record.namespace !== "vag_oem_specific" || !record.configuration_id || !record.ecu_id || !["exact_configuration","exact_ecu"].includes(record.applicability_precision)) {\n      throw new Error("VAG-specific DTC records require an exact configuration and ECU applicability link");\n    }\n  }\n';
  source = replaceOnce(source, validationAnchor, validationAnchor + "  validateTechnicalPayload(record);\n", "technical record import validation hook");
  source = replaceOnce(source, "requiresSeparatePack,initializeDatabase", "requiresSeparatePack,validateTechnicalPayload,initializeDatabase", "validator export");
  fs.writeFileSync(file, source, "utf8");
  return true;
}

function patchElectron(file) {
  let source = fs.readFileSync(file, "utf8").replace(/\r\n/g, "\n");
  if (source.includes("const schemaRoot = app.isPackaged")) return false;
  source = replaceOnce(source,
    '  const researchRoot = app.isPackaged\n    ? path.join(process.resourcesPath, "research-data")\n    : path.join(app.getAppPath(), "data", "research");\n',
    '  const researchRoot = app.isPackaged\n    ? path.join(process.resourcesPath, "research-data")\n    : path.join(app.getAppPath(), "data", "research");\n  const schemaRoot = app.isPackaged\n    ? path.join(process.resourcesPath, "schemas")\n    : path.join(app.getAppPath(), "data", "schemas");\n',
    "schema resource root");
  source = replaceOnce(source, "  process.env.VAG_TECH_PRO_RESEARCH_DIR = researchRoot;\n", "  process.env.VAG_TECH_PRO_RESEARCH_DIR = researchRoot;\n  process.env.VAG_TECH_PRO_SCHEMA_DIR = schemaRoot;\n", "schema environment");
  source = replaceOnce(source, "VAG_TECH_PRO_RESEARCH_DIR: researchRoot },", "VAG_TECH_PRO_RESEARCH_DIR: researchRoot, VAG_TECH_PRO_SCHEMA_DIR: schemaRoot },", "schema environment passed to local server");
  fs.writeFileSync(file, source, "utf8");
  return true;
}

function patchTests(file) {
  let source = fs.readFileSync(file, "utf8").replace(/\r\n/g, "\n");
  if (source.includes("run78 validates technical payload schemas before opening an import transaction")) return false;
  source = replaceOnce(source, '  const payload = { torque_nm: 90, angle_deg: 90 };', '  const payload = { component: "Test fastener", torque_value: 90, torque_unit: "Nm", angle_degrees: 90, condition: "Test-only fixture" };', "legacy torque test fixture");
  const anchor = 'test("imports a valid package atomically and is idempotent for the same package hash", (t) => {\n';
  const tests = [
    'test("run78 validates technical payload schemas before opening an import transaction", (t) => {',
    '  const { dbPath } = fixture(t); core.registerSource(dbPath, source());',
    '  const payload = { component: "Crankshaft pulley bolt", torque_value: 180, torque_unit: "Nm" };',
    '  const record = { record_type: "torque_specification", natural_key: "torque:invalid", title: "Invalid torque fixture", market_scope: "ALL", applicability_precision: "document_metadata_only", source_record_key: "torque:invalid", payload, record_sha256: core.sha256(payload) };',
    '  assert.throws(() => core.importPackage(dbPath, packageOf([record])), /Technical payload schema validation failed.*condition: required property is missing/);',
    '  const db = new DatabaseSync(dbPath); assert.equal(db.prepare("SELECT count(*) AS n FROM technical_records").get().n, 0); assert.equal(db.prepare("SELECT count(*) AS n FROM import_batches").get().n, 0); db.close();',
    '});',
    '',
    'test("run78 accepts schema-valid torque, ECU and OEM supersession records", (t) => {',
    '  const { dbPath } = fixture(t); core.registerSource(dbPath, source());',
    '  const records = [',
    '    { record_type: "torque_specification", natural_key: "torque:valid", title: "Valid torque fixture", market_scope: "ALL", applicability_precision: "document_metadata_only", source_record_key: "torque:valid", payload: { component: "Crankshaft pulley bolt", fastener: "M16", torque_value: 180, torque_unit: "Nm", angle_degrees: 90, condition: "New fastener; engine cold" } },',
    '    { record_type: "ecu_reference", natural_key: "ecu:valid", title: "ECU identity fixture", market_scope: "ALL", applicability_precision: "document_metadata_only", source_record_key: "ecu:valid", payload: { ecu_family: "MED17.5.25", hardware_number: "06K907425", software_number: "0001" } },',
    '    { record_type: "oem_supersession", natural_key: "part:old-to-new", title: "OEM supersession fixture", market_scope: "ALL", applicability_precision: "document_metadata_only", source_record_key: "part:old-to-new", payload: { from_part_number: "06K109158A", to_part_number: "06K109158B", supersession_type: "replaces" } }',
    '  ].map(record => ({ ...record, record_sha256: core.sha256(record.payload) }));',
    '  const result = core.importPackage(dbPath, packageOf(records)); assert.equal(result.status, "applied"); assert.equal(result.inserted, 3);',
    '  assert.equal(core.validateTechnicalPayload(records[1]), true); assert.equal(core.validateTechnicalPayload(records[2]), true);',
    '});',
    '',
    'test("run78 validates every technical section schema mapping", () => {',
    '  const digest = "a".repeat(64); const step = { order: 1, action: "Check the documented test point" };',
    '  const fixtures = [',
    '    ["diagnostic_test_plan", { steps: [step], safety_notes: ["Use approved PPE"] }],',
    '    ["repair_procedure", { title: "Replace sensor", safety_notes: ["Disconnect the battery"], steps: [step] }],',
    '    ["wiring_diagram", { diagram_id: "EL-001", format: "SVG", diagram_resource_key: "wiring/EL-001.svg", diagram_sha256: digest }],',
    '    ["pinout", { ecu_identity_id: 1, connector_id: "T94", pin_number: "37", signal_name: "Terminal 30", measurement_condition: "Ignition off" }],',
    '    ["torque_specification", { component: "Crankshaft pulley bolt", torque_value: 180, torque_unit: "Nm", condition: "New fastener; engine cold" }],',
    '    ["adaptation", { function_name: "Basic setting", steps: [step], safety_note: "Use a regulated power supply" }],',
    '    ["service_interval", { service_item: "Engine oil service", interval_km: 15000 }],',
    '    ["ecu_reference", { ecu_family: "MED17.5.25" }],',
    '    ["oem_part", { part_number: "06K109158A" }],',
    '    ["oem_supersession", { from_part_number: "06K109158A", to_part_number: "06K109158B", supersession_type: "replaces" }]',
    '  ];',
    '  for (const [record_type, payload] of fixtures) assert.equal(core.validateTechnicalPayload({ record_type, source_record_key: "schema:" + record_type, payload }), true, record_type);',
    '  assert.throws(() => core.validateTechnicalPayload({ record_type: "wiring_diagram", source_record_key: "schema:invalid-wiring", payload: { diagram_id: "EL-002", format: "SVG" } }), /none of the allowed schema alternatives matched/);',
    '});',
    '',
    'test("run78 accepts legacy numeric VAG DTCs without relaxing the generic namespace", () => {',
    '  assert.equal(core.validateTechnicalPayload({ record_type: "dtc_vag_specific", source_record_key: "vag:17978", payload: { code: "17978" } }), true);',
    '  assert.throws(() => core.validateTechnicalPayload({ record_type: "dtc_generic", source_record_key: "generic:17978", payload: { code: "17978" } }), /DTC payload code does not match its declared generic or VAG-specific namespace/);',
    '});',
    '',
    'test("run78 keeps manufacturer-range P1 codes out of generic DTC namespace", () => {',
    '  assert.throws(() => core.validateTechnicalPayload({ record_type: "dtc_generic", source_record_key: "generic:P1A00", payload: { code: "P1A00" } }), /DTC payload code does not match its declared generic or VAG-specific namespace/);',
    '  assert.equal(core.validateTechnicalPayload({ record_type: "dtc_vag_specific", source_record_key: "vag:P1A00", payload: { code: "P1A00" } }), true);',
    '});',
    '',
    'test("run78 rejects manufacturer-controlled and mixed U3 DTCs from the generic namespace", () => {',
    '  for (const code of ["P3000","P33FF","P39FF","P35FF","B3000","C3000","U3000","U3FFF"]) {',
    '    assert.throws(() => core.validateTechnicalPayload({ record_type: "dtc_generic", source_record_key: "generic:" + code, payload: { code } }), /DTC payload code does not match its declared generic or VAG-specific namespace/);',
    '  }',
    '  assert.equal(core.validateTechnicalPayload({ record_type: "dtc_generic", source_record_key: "generic:P3400", payload: { code: "P3400" } }), true);',
    '  assert.throws(() => core.validateTechnicalPayload({ record_type: "dtc_vag_specific", source_record_key: "vag:P0300", payload: { code: "P0300" } }), /DTC payload code does not match its declared generic or VAG-specific namespace/);',
    '  assert.throws(() => core.validateTechnicalPayload({ record_type: "dtc_vag_specific", source_record_key: "vag:P3400", payload: { code: "P3400" } }), /DTC payload code does not match its declared generic or VAG-specific namespace/);',
    '  assert.equal(core.validateTechnicalPayload({ record_type: "dtc_vag_specific", source_record_key: "vag:P1A00", payload: { code: "P1A00" } }), true);',
    '  assert.equal(core.validateTechnicalPayload({ record_type: "dtc_vag_specific", source_record_key: "vag:P3000", payload: { code: "P3000" } }), true);',
    '  assert.throws(() => core.validateTechnicalPayload({ record_type: "dtc_vag_specific", source_record_key: "vag:U3000", payload: { code: "U3000" } }), /DTC payload code does not match its declared generic or VAG-specific namespace/);',
    '});',
    '',    'test("run78 rejects malformed generic DTC codes before import", (t) => {',
    '  const { dbPath } = fixture(t); core.registerSource(dbPath, source());',
    '  const payload = { code: "p0300", title: "Malformed lower-case code", namespace: "SAE/ISO" };',
    '  const record = { ...genericDtc({ payload, record_sha256: core.sha256(payload), source_record_key: "obd:invalid" }), natural_key: "generic:invalid" };',
    '  assert.throws(() => core.importPackage(dbPath, packageOf([record])), /DTC payload code does not match its declared generic or VAG-specific namespace/);',
    '  const db = new DatabaseSync(dbPath); assert.equal(db.prepare("SELECT count(*) AS n FROM technical_records").get().n, 0); assert.equal(db.prepare("SELECT count(*) AS n FROM import_batches").get().n, 0); db.close();',
    '});',
    ''
  ].join("\n");
  source = replaceOnce(source, anchor, tests + anchor, "run78 import regression tests");
  fs.writeFileSync(file, source, "utf8");
  return true;
}

function patchResearchVerification(desktopRoot) {
  const verifierFile = path.join(desktopRoot, "scripts", "verify-local-research-packs.cjs");
  const packTestsFile = path.join(desktopRoot, "tests", "local-research-packs.test.cjs");
  const dbTestsFile = path.join(desktopRoot, "tests", "local-research-db.test.cjs");
  for (const file of [verifierFile, packTestsFile, dbTestsFile]) {
    if (!fs.existsSync(file)) throw new Error("Run78 OBDex namespace verification file is missing: " + file);
  }
  let verifier = fs.readFileSync(verifierFile, "utf8").replace(/\r\n/g, "\n");
  let packTests = fs.readFileSync(packTestsFile, "utf8").replace(/\r\n/g, "\n");
  let dbTests = fs.readFileSync(dbTestsFile, "utf8").replace(/\r\n/g, "\n");
  if (verifier.includes("quarantined_dtc_rows === 174") && packTests.includes("result.obdex.quarantinedDtcRows, 174") && dbTests.includes('searchGenericDtcs("U3000"')) return false;
  verifier = replaceOnce(verifier,
    '  assert(obSnapshot.expected_counts?.generic_dtcs === 9533 && obSnapshot.expected_counts?.pids_total === 132, "OBDex expected counts mismatch");',
    '  assert(obSnapshot.expected_counts?.generic_dtcs === 9359 && obSnapshot.expected_counts?.upstream_projection_dtcs === 9533 && obSnapshot.expected_counts?.quarantined_dtc_rows === 174 && obSnapshot.expected_counts?.pids_total === 132, "OBDex expected counts/quarantine mismatch");',
    "OBDex manifest counts");
  verifier = replaceOnce(verifier,
    '  assert(obReport.database_sha256 === ob.database_sha256 && obReport.integrity_check === "ok" && obReport.vag_specific_dtc_rows === 0 && obReport.fitment_claims === 0 && obReport.production_rows === 0, "OBDex SQLite report failed its safety gate");',
    '  assert(obReport.database_sha256 === ob.database_sha256 && obReport.integrity_check === "ok" && obReport.generic_dtcs === 9359 && obReport.upstream_dtc_rows === 9533 && obReport.quarantined_dtc_rows === 174 && obReport.vag_specific_dtc_rows === 0 && obReport.fitment_claims === 0 && obReport.production_rows === 0, "OBDex SQLite report failed its namespace safety gate");',
    "OBDex report counts");
  verifier = replaceOnce(verifier,
    '      pids: count(obDb, "SELECT count(*) AS n FROM generic_pid_research WHERE verification_status=\\'source_imported_unreviewed\\' AND vehicle_fitment_claim=0"),',
    '      pids: count(obDb, "SELECT count(*) AS n FROM generic_pid_research WHERE verification_status=\\'source_imported_unreviewed\\' AND vehicle_fitment_claim=0"),\n      quarantinedDtcRows: obReport.quarantined_dtc_rows,',
    "OBDex quarantine count");
  verifier = replaceOnce(verifier,
    "obCounts.dtcs === 9533",
    "obCounts.dtcs === 9359 && obCounts.quarantinedDtcRows === 174",
    "OBDex SQLite count gate");
  verifier = verifier.replace(/^\s*const manufacturerSpecific = obCodes\.filter\(\(code\) => .*;\s*$/m,
    '    const nonGenericOrMixed = obCodes.filter((code) => /^(P1[0-9A-F]{3}|P3[0-35-9][0-9A-F]{2}|B[123][0-9A-F]{3}|C[123][0-9A-F]{3}|U[123][0-9A-F]{3})$/i.test(code));');
  verifier = verifier.replace(/^\s*assert\(manufacturerSpecific\.length === 0, .*;\s*$/m,
    '    assert(nonGenericOrMixed.length === 0, "OBDex contains non-generic or mixed/reserved DTCs in generic namespace");\n    assert(obCodes.includes("P3400") && !obCodes.includes("U3000"), "OBDex generic namespace must retain P34xx and exclude U3xxx");');
  if (!verifier.includes("const nonGenericOrMixed =") || !verifier.includes("obCodes.includes(" + '"P3400"')) throw new Error("Run78 OBDex code-family audit patch did not apply");
  packTests = replaceOnce(packTests,
    "assert.equal(result.obdex.dtcs, 9533);",
    "assert.equal(result.obdex.dtcs, 9359);\n  assert.equal(result.obdex.quarantinedDtcRows, 174);",
    "OBDex pack test counts");
  dbTests = replaceOnce(dbTests,
    "assert.deepEqual(obdex.counts, { dtcs: 9533, pids: 132 });",
    "assert.deepEqual(obdex.counts, { dtcs: 9359, pids: 132 });",
    "OBDex runtime summary count");
  dbTests = replaceOnce(dbTests,
    '  assert.equal(rows[0].code, "P0300");',
    '  assert.equal(rows[0].code, "P0300");\n  assert.deepEqual(local.searchGenericDtcs("U3000", 5, root), []);\n  assert.deepEqual(local.searchGenericDtcs("P39FF", 5, root), []);\n  assert.equal(local.searchGenericDtcs("P3400", 5, root)[0].code, "P3400");',
    "OBDex runtime generic search boundaries");
  fs.writeFileSync(verifierFile, verifier, "utf8");
  fs.writeFileSync(packTestsFile, packTests, "utf8");
  fs.writeFileSync(dbTestsFile, dbTests, "utf8");
  return true;
}

function main() {
  const index = process.argv.indexOf("--desktop-root");
  const desktopRoot = index >= 0 ? path.resolve(process.argv[index + 1] || "") : "";
  if (!desktopRoot) throw new Error("--desktop-root is required");
  const root = process.cwd();
  const files = {
    core: path.join(desktopRoot, "lib", "local-core-db.cjs"),
    electron: path.join(desktopRoot, "electron", "main.cjs"),
    tests: path.join(desktopRoot, "tests", "local-core-db.test.cjs"),
    rootSchema: path.join(root, "data", "schemas", "technical-record-payloads.schema.json"),
    desktopSchema: path.join(desktopRoot, "data", "schemas", "technical-record-payloads.schema.json"),
    researchVerifier: path.join(desktopRoot, "scripts", "verify-local-research-packs.cjs"),
    researchPackTests: path.join(desktopRoot, "tests", "local-research-packs.test.cjs"),
    researchDbTests: path.join(desktopRoot, "tests", "local-research-db.test.cjs")
  };
  for (const file of [files.core, files.electron, files.tests, files.rootSchema, files.researchVerifier, files.researchPackTests, files.researchDbTests]) if (!fs.existsSync(file)) throw new Error("Required run78 file is missing: " + file);
  const schema = JSON.parse(fs.readFileSync(files.rootSchema, "utf8"));
  const expected = ["diagnostic_test_plan","repair_procedure","wiring_diagram","ecu_pinout","torque_specification","adaptation","service_interval","ecu_profile","oem_part","oem_supersession"].sort();
  const actual = Object.keys(schema.$defs).filter(key => !["step","connection","string_list"].includes(key)).sort();
  if (JSON.stringify(actual) !== JSON.stringify(expected)) throw new Error("Root technical schema definitions do not match the run78 contract");
  fs.mkdirSync(path.dirname(files.desktopSchema), { recursive: true });
  fs.copyFileSync(files.rootSchema, files.desktopSchema);
  const changed = { core: patchCore(files.core), electron: patchElectron(files.electron), tests: patchTests(files.tests), research: patchResearchVerification(desktopRoot) };
  const hash = crypto.createHash("sha256").update(fs.readFileSync(files.desktopSchema)).digest("hex");
  process.stdout.write(JSON.stringify({ status: "patched", changed, technicalSchemaSha256: hash, genericObdexDtcCount: 9359, quarantinedU3DtcCount: 174 }) + "\n");
}

try { main(); } catch (error) { process.stderr.write(String(error.stack || error.message) + "\n"); process.exitCode = 1; }

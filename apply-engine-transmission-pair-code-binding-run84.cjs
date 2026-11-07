"use strict";
const fs = require("node:fs");
const path = require("node:path");

function replaceOnce(source, before, after, label) {
  const count = source.split(before).length - 1;
  if (count !== 1) throw new Error(`${label} anchor count=${count}; expected exactly one`);
  return source.replace(before, after);
}
function read(root, relative) {
  const file = path.join(root, relative);
  if (!fs.existsSync(file)) throw new Error(`run84 required file is missing: ${relative}`);
  return fs.readFileSync(file, "utf8");
}
function apply(root) {
  const files = {
    core: "lib/local-core-db.cjs",
    tests: "tests/local-core-db.test.cjs",
    schema: "data/schemas/vehicle-catalog-package.schema.json",
    docs: "docs/LOCAL_VEHICLE_CATALOG_IMPORT.md",
  };
  let core = read(root, files.core);
  let tests = read(root, files.tests);
  let schema = read(root, files.schema);
  let docs = read(root, files.docs);
  const marker = "// run84: pair evidence raw values must bind to referenced engine/transmission codes";

  if (core.includes(marker)) {
    if (!tests.includes("run84 rejects raw component-code mismatches") ||
        !schema.includes('"engine_code",\n                "transmission_code",\n                "pair_evidence"') ||
        !docs.includes("## Engine/transmission component-code binding (run84)")) {
      throw new Error("run84 marker exists but one or more companion contracts are missing");
    }
    return { status: "already_applied", files: Object.values(files) };
  }

  core = replaceOnce(
    core,
    "// run82: same-variant primary-document evidence is mandatory for engine/transmission pairs\nfunction validatePairEvidence(record) {",
    "// run82: same-variant primary-document evidence is mandatory for engine/transmission pairs\n" +
      marker + "\n" +
      "function normalizePairComponentCode(value) {\n" +
      "  if (typeof value !== \"string\") return null;\n" +
      "  return value.normalize(\"NFKC\").trim().toUpperCase();\n" +
      "}\n" +
      "function validatePairEvidence(record) {",
    "core pair-code normalizer insertion"
  );

  core = replaceOnce(
    core,
    '  for(const k of required)if(typeof e[k]!=="string"||!e[k].trim())throw new TypeError("pair_evidence."+k+" is required");',
    '  for(const k of required)if(typeof e[k]!=="string"||!e[k].trim())throw new TypeError("pair_evidence."+k+" is required");\n' +
      '  for (const key of ["engine_code", "transmission_code"]) {\n' +
      '    if (typeof p[key] !== "string" || !p[key].trim()) throw new TypeError("engine_transmission_pair payload " + key + " is required");\n' +
      '  }\n' +
      '  if (normalizePairComponentCode(e.raw_engine_value) !== normalizePairComponentCode(p.engine_code)) throw new Error("pair_evidence.raw_engine_value must exactly match engine_code; ambiguous code mapping is not allowed");\n' +
      '  if (normalizePairComponentCode(e.raw_transmission_value) !== normalizePairComponentCode(p.transmission_code)) throw new Error("pair_evidence.raw_transmission_value must exactly match transmission_code; ambiguous code mapping is not allowed");',
    "core raw-code binding validation"
  );

  core = replaceOnce(
    core,
    '            previous=db.prepare("SELECT id FROM engine_transmission_pairs WHERE source_id=? AND natural_key=? ORDER BY id DESC LIMIT 1").get(pkg.source_id,record.natural_key);',
    '            const referencedEngine=db.prepare("SELECT engine_code FROM engines WHERE id=?").get(engineId);\n' +
      '            const referencedTransmission=db.prepare("SELECT transmission_code FROM transmissions WHERE id=?").get(transmissionId);\n' +
      '            if(!referencedEngine||normalizePairComponentCode(referencedEngine.engine_code)!==normalizePairComponentCode(p.engine_code))throw new Error("Pair engine_code does not match the referenced engine record");\n' +
      '            if(!referencedTransmission||normalizePairComponentCode(referencedTransmission.transmission_code)!==normalizePairComponentCode(p.transmission_code))throw new Error("Pair transmission_code does not match the referenced transmission record");\n' +
      '            previous=db.prepare("SELECT id FROM engine_transmission_pairs WHERE source_id=? AND natural_key=? ORDER BY id DESC LIMIT 1").get(pkg.source_id,record.natural_key);',
    "core referenced-parent code binding"
  );

  tests = replaceOnce(
    tests,
    'catalogRecord("engine_transmission_pair","mk7:CZEA:DQ200:RU:2013-2020","pair:mk7:CZEA:DQ200","exact_pairing",{generation_natural_key:"golf:mk7",engine_natural_key:"CZEA",transmission_natural_key:"DQ200",model_year_start:2013,model_year_end:2020,pair_evidence:pairEvidenceFixture()}),',
    'catalogRecord("engine_transmission_pair","mk7:CZEA:DQ200:RU:2013-2020","pair:mk7:CZEA:DQ200","exact_pairing",{generation_natural_key:"golf:mk7",engine_natural_key:"CZEA",transmission_natural_key:"DQ200",engine_code:"CZEA",transmission_code:"DQ200",model_year_start:2013,model_year_end:2020,pair_evidence:pairEvidenceFixture()}),',
    "test fixture pair code fields"
  );

  tests = replaceOnce(
    tests,
    '  assert.ok(pair.required.includes("pair_evidence"));',
    '  assert.ok(pair.required.includes("pair_evidence"));\n  assert.ok(pair.required.includes("engine_code"));\n  assert.ok(pair.required.includes("transmission_code"));',
    "schema test required pair codes"
  );

  tests += `

test("run84 rejects raw component-code mismatches before opening the SQLite transaction", (t) => {
  const { dbPath } = fixture(t);
  core.registerSource(dbPath, source({ market_scope: "RU" }));
  for (const [field, rawField, badValue, message] of [
    ["engine_code", "raw_engine_value", "CHPA", /raw_engine_value must exactly match engine_code/],
    ["transmission_code", "raw_transmission_value", "DQ250", /raw_transmission_value must exactly match transmission_code/],
  ]) {
    const records = catalogFixtureRecords();
    const pair = records.find((item) => item.record_type === "engine_transmission_pair");
    pair.payload.pair_evidence[rawField] = badValue;
    pair.record_sha256 = core.catalogRecordSha256(pair);
    assert.throws(() => core.importPackage(dbPath, catalogPackageOf(records, { package_id: "run84-raw-mismatch-" + field })), message);
  }
  assert.equal(core.listReviewQueue(dbPath).length, 0);
});

test("run84 rejects pair links whose referenced engine or transmission code differs from the cited primary observation and rolls back", (t) => {
  for (const [recordType, field, badValue, message] of [
    ["engine", "engine_code", "CHPA", /Pair engine_code does not match the referenced engine record/],
    ["transmission", "transmission_code", "DQ250", /Pair transmission_code does not match the referenced transmission record/],
  ]) {
    const { dbPath } = fixture(t);
    core.registerSource(dbPath, source({ market_scope: "RU" }));
    const records = catalogFixtureRecords();
    const parent = records.find((item) => item.record_type === recordType);
    parent.payload[field] = badValue;
    parent.record_sha256 = core.catalogRecordSha256(parent);
    const pkg = catalogPackageOf(records, { package_id: "run84-parent-mismatch-" + recordType });
    assert.throws(() => core.importPackage(dbPath, pkg), message);
    const db = new DatabaseSync(dbPath, { readOnly: true });
    assert.equal(db.prepare("SELECT count(*) AS n FROM brands").get().n, 0);
    assert.equal(db.prepare("SELECT count(*) AS n FROM engines").get().n, 0);
    assert.equal(db.prepare("SELECT count(*) AS n FROM transmissions").get().n, 0);
    assert.equal(db.prepare("SELECT count(*) AS n FROM engine_transmission_pairs").get().n, 0);
    assert.equal(db.prepare("SELECT count(*) AS n FROM import_batches WHERE package_id=?").get(pkg.package_id).n, 0);
    db.close();
  }
});
`;

  schema = replaceOnce(
    schema,
    '                "generation_natural_key",\n                "engine_natural_key",\n                "transmission_natural_key",\n                "pair_evidence"',
    '                "generation_natural_key",\n                "engine_natural_key",\n                "transmission_natural_key",\n                "engine_code",\n                "transmission_code",\n                "pair_evidence"',
    "schema pair required engine/transmission codes"
  );

  docs += [
    "",
    "",
    "## Engine/transmission component-code binding (run84)",
    "",
    "An exact pair record must carry both canonical `engine_code` and `transmission_code` values. Each value must match the corresponding raw observation in the cited primary document after Unicode NFKC normalization, trimming and case normalization; no fuzzy matching, descriptive-name inference or unreviewed alias mapping is accepted. During the same SQLite transaction, the importer resolves the referenced engine and transmission natural keys and checks that their stored codes match the pair record. A mismatch rolls back the entire package. If an approval document uses a manufacturer designation that cannot be shown to be the exact VAG code, keep it as a separate source candidate until a separately evidenced mapping workflow exists.",
    ""
  ].join("\n");

  JSON.parse(schema);
  for (const relative of Object.values(files)) {
    const target = path.join(root, relative);
    const value = relative === files.core ? core : relative === files.tests ? tests : relative === files.schema ? schema : docs;
    fs.writeFileSync(target, value, "utf8");
  }
  return { status: "applied", files: Object.values(files) };
}

const rootArg = process.argv.indexOf("--desktop-root");
const root = path.resolve(rootArg >= 0 && process.argv[rootArg + 1] ? process.argv[rootArg + 1] : "desktop-source");
console.log(JSON.stringify(apply(root)));

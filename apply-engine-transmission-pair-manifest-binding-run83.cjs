"use strict";
const fs = require("node:fs");
const path = require("node:path");
function once(source, regex, replacement, label) {
  const count = [...source.matchAll(regex)].length;
  if (count !== 1) throw new Error(label + " anchor count=" + count);
  return source.replace(regex, replacement);
}
function read(file) {
  if (!fs.existsSync(file)) throw new Error("run83 required file is missing: " + file);
  return fs.readFileSync(file, "utf8");
}
function write(file, content) { fs.writeFileSync(file, content, "utf8"); }
const rootArg = process.argv.indexOf("--desktop-root");
const root = path.resolve(rootArg >= 0 && process.argv[rootArg + 1] ? process.argv[rootArg + 1] : "desktop-source");
const coreFile = path.join(root, "lib/local-core-db.cjs");
const testFile = path.join(root, "tests/local-core-db.test.cjs");
const schemaFile = path.join(root, "data/schemas/vehicle-catalog-package.schema.json");
const docFile = path.join(root, "docs/LOCAL_VEHICLE_CATALOG_IMPORT.md");
let core = read(coreFile);
const marker = "// run83: pair evidence must resolve to one immutable source-snapshot document entry";
if (!core.includes(marker)) {
  const helper = [
    marker,
    "function validatePairManifestBinding(record, packageInfo) {",
    "  const evidence = record.payload.pair_evidence;",
    "  const documents = packageInfo?.snapshot_manifest?.documents;",
    '  if (!Array.isArray(documents)) throw new Error("Engine/transmission pair requires snapshot_manifest.documents with its primary approval document");',
    '  const allowedTypes = new Set(["eaeu_otts", "eaeu_otsh", "oem_build_sheet", "oem_type_approval", "official_type_approval"]);',
    '  const matches = documents.filter((document) => document && document.source_id === packageInfo.source_id && document.document_id === evidence.source_document_id && document.url === evidence.source_document_url && document.sha256 === evidence.source_document_sha256 && document.revision === evidence.document_revision && document.document_type === evidence.document_type && marketScopeCovers(document.market_scope, record.market_scope) && Array.isArray(document.variant_scope_keys) && document.variant_scope_keys.includes(evidence.variant_scope_key));',
    '  if (matches.length !== 1) throw new Error("Pair evidence must resolve to exactly one document in the immutable source snapshot manifest for the same source, market and variant");',
    "  const document = matches[0];",
    '  if (typeof document.document_id !== "string" || !document.document_id.trim() || document.document_id.length > 256) throw new TypeError("Snapshot document id is invalid");',
    '  if (typeof document.url !== "string" || document.url.length > 2048) throw new TypeError("Snapshot document URL is invalid");',
    '  let url; try { url = new URL(document.url); } catch { throw new TypeError("Snapshot document URL must be a valid HTTPS URL"); }',
    '  if (url.protocol !== "https:") throw new TypeError("Snapshot document URL must use HTTPS");',
    '  if (!HASH_RE.test(document.sha256 || "")) throw new TypeError("Snapshot document SHA-256 must be a 64-character lowercase hexadecimal digest");',
    '  if (typeof document.revision !== "string" || !document.revision.trim() || document.revision.length > 128) throw new TypeError("Snapshot document revision is invalid");',
    '  if (!allowedTypes.has(document.document_type)) throw new Error("Snapshot document type is not an approved primary approval/manufacturer document type");',
    '  if (typeof document.market_scope !== "string" || !document.market_scope.trim() || document.market_scope.length > 120) throw new TypeError("Snapshot document market scope is invalid");',
    '  if (!Array.isArray(document.variant_scope_keys) || document.variant_scope_keys.length < 1 || document.variant_scope_keys.length > 10000 || document.variant_scope_keys.some((key) => typeof key !== "string" || !key.trim() || key.length > 256)) throw new TypeError("Snapshot document must list bounded exact variant scope keys");',
    "}",
    ""
  ].join("\n");
  core = once(core, /function validateCatalogRecord\(record, packageInfo\) \{/g, helper + "function validateCatalogRecord(record, packageInfo) {", "pair manifest helper");
  core = once(core, /validatePairEvidence\(record\);/g, "validatePairEvidence(record);\n    validatePairManifestBinding(record, packageInfo);", "pair manifest validation call");
  write(coreFile, core);
}
const schema = JSON.parse(read(schemaFile));
schema.properties.snapshot_manifest = {
  type: "object",
  properties: {
    documents: {
      type: "array", minItems: 1, maxItems: 10000,
      items: {
        type: "object", additionalProperties: false,
        required: ["source_id", "document_id", "url", "sha256", "revision", "document_type", "market_scope", "variant_scope_keys"],
        properties: {
          source_id: { type: "string", minLength: 1, maxLength: 180 },
          document_id: { type: "string", minLength: 1, maxLength: 256 },
          url: { type: "string", format: "uri", pattern: "^https://", maxLength: 2048 },
          sha256: { $ref: "#/$defs/sha256" },
          revision: { type: "string", minLength: 1, maxLength: 128 },
          document_type: { enum: ["eaeu_otts", "eaeu_otsh", "oem_build_sheet", "oem_type_approval", "official_type_approval"] },
          market_scope: { type: "string", minLength: 1, maxLength: 120 },
          variant_scope_keys: { type: "array", minItems: 1, maxItems: 10000, items: { type: "string", minLength: 1, maxLength: 256 } }
        }
      }
    }
  }
};
schema.allOf = [...(schema.allOf || []).filter(rule => rule?.$comment !== "run83 pair document manifest condition"), {
  $comment: "run83 pair document manifest condition",
  if: { required: ["records"], properties: { records: { contains: { required: ["record_type"], properties: { record_type: { const: "engine_transmission_pair" } } } } } },
  then: { properties: { snapshot_manifest: { required: ["documents"] } } }
}];
write(schemaFile, JSON.stringify(schema, null, 2) + "\n");
let tests = read(testFile);
const helperAnchor = /function catalogPackageOf\(records, overrides = \{\}\) \{\r?\n  const pkg = \{ package_kind: "vehicle_catalog", package_id: "test-catalog-package", source_id: "test-open-source", source_revision: "rev1", market_scope: "RU",\r?\n    source_snapshot_sha256: "b"\.repeat\(64\), license_sha256: "a"\.repeat\(64\), rights_evidence_sha256: "c"\.repeat\(64\),\r?\n    snapshot_manifest: \{ upstream_revision: "rev1", record_count: records\.length \}, records, \.\.\.overrides \};/g;
const helperReplacement = [
  "function catalogPackageOf(records, overrides = {}) {",
  '  const pair = records.find(item => item.record_type === "engine_transmission_pair");',
  "  const evidence = pair?.payload?.pair_evidence;",
  '  const sourceId = overrides.source_id || "test-open-source";',
  '  const snapshotManifest = { upstream_revision: overrides.source_revision || "rev1", record_count: records.length };',
  '  if (evidence) snapshotManifest.documents = [{ source_id: sourceId, document_id: evidence.source_document_id, url: evidence.source_document_url, sha256: evidence.source_document_sha256, revision: evidence.document_revision, document_type: evidence.document_type, market_scope: pair.market_scope, variant_scope_keys: [evidence.variant_scope_key] }];',
  "  const { snapshot_manifest: manifestOverride, ...packageOverrides } = overrides;",
  '  const pkg = { package_kind: "vehicle_catalog", package_id: "test-catalog-package", source_id: sourceId, source_revision: "rev1", market_scope: "RU",',
  '    source_snapshot_sha256: "b".repeat(64), license_sha256: "a".repeat(64), rights_evidence_sha256: "c".repeat(64),',
  "    snapshot_manifest: { ...snapshotManifest, ...(manifestOverride || {}) }, records, ...packageOverrides };"
].join("\n");
if (!tests.includes('const snapshotManifest = { upstream_revision: overrides.source_revision || "rev1", record_count: records.length };')) {
  tests = once(tests, helperAnchor, helperReplacement, "catalog package test fixture");
}
const testMarker = 'test("run83 requires exact source-snapshot document binding for every engine/transmission pair"';
if (!tests.includes(testMarker)) {
  const additions = [
    "",
    'test("run83 requires exact source-snapshot document binding for every engine/transmission pair", (t) => {',
    '  const { dbPath } = fixture(t); core.registerSource(dbPath, source({ market_scope: "RU" }));',
    "  const records = catalogFixtureRecords();",
    "  const base = catalogPackageOf(records);",
    "  assert.equal(base.snapshot_manifest.documents.length, 1);",
    '  assert.equal(base.snapshot_manifest.documents[0].source_id, base.source_id);',
    '  assert.equal(base.snapshot_manifest.documents[0].sha256, records.find(item => item.record_type === "engine_transmission_pair").payload.pair_evidence.source_document_sha256);',
    '  const missing = catalogPackageOf(records, { snapshot_manifest: { upstream_revision: "rev1", record_count: records.length, documents: [] } });',
    '  assert.throws(() => core.importPackage(dbPath, missing), /exactly one document in the immutable source snapshot manifest/);',
    '  const wrongHash = catalogPackageOf(records, { snapshot_manifest: { ...base.snapshot_manifest, documents: [{ ...base.snapshot_manifest.documents[0], sha256: "e".repeat(64) }] } });',
    '  assert.throws(() => core.importPackage(dbPath, wrongHash), /exactly one document in the immutable source snapshot manifest/);',
    '  const wrongSource = catalogPackageOf(records, { snapshot_manifest: { ...base.snapshot_manifest, documents: [{ ...base.snapshot_manifest.documents[0], source_id: "other-source" }] } });',
    '  assert.throws(() => core.importPackage(dbPath, wrongSource), /exactly one document in the immutable source snapshot manifest/);',
    '  const wrongVariant = catalogPackageOf(records, { snapshot_manifest: { ...base.snapshot_manifest, documents: [{ ...base.snapshot_manifest.documents[0], variant_scope_keys: ["variant:other"] }] } });',
    '  assert.throws(() => core.importPackage(dbPath, wrongVariant), /exactly one document in the immutable source snapshot manifest/);',
    '  const wrongMarket = catalogPackageOf(records, { snapshot_manifest: { ...base.snapshot_manifest, documents: [{ ...base.snapshot_manifest.documents[0], market_scope: "DE" }] } });',
    '  assert.throws(() => core.importPackage(dbPath, wrongMarket), /exactly one document in the immutable source snapshot manifest/);',
    '  const duplicate = catalogPackageOf(records, { snapshot_manifest: { ...base.snapshot_manifest, documents: [...base.snapshot_manifest.documents, ...base.snapshot_manifest.documents] } });',
    '  assert.throws(() => core.importPackage(dbPath, duplicate), /exactly one document in the immutable source snapshot manifest/);',
    "  assert.equal(core.listReviewQueue(dbPath).length, 0);",
    "});",
    ""
  ].join("\n");
  tests = once(tests, /\ntest\("imports a vehicle catalog as candidates and requires primary-source review plus exact engine\/transmission pairing"/g, additions + '\ntest("imports a vehicle catalog as candidates and requires primary-source review plus exact engine/transmission pairing"', "run83 manifest-binding tests");
}
const schemaTestMarker = 'test("run83 vehicle catalog schema requires document manifests whenever a package contains engine/transmission pairs"';
if (!tests.includes(schemaTestMarker)) {
  const schemaTest = [
    "",
    'test("run83 vehicle catalog schema requires document manifests whenever a package contains engine/transmission pairs", () => {',
    '  const schema = JSON.parse(fs.readFileSync(path.join(__dirname, "../data/schemas/vehicle-catalog-package.schema.json"), "utf8"));',
    '  const pair = schema.$defs.pair.allOf.find(item => item.properties?.payload).properties.payload;',
    '  assert.ok(pair.required.includes("pair_evidence"));',
    '  const documents = schema.properties.snapshot_manifest.properties.documents;',
    "  assert.ok(documents && documents.minItems === 1);",
    '  assert.ok(documents.items.required.includes("source_id"));',
    '  assert.ok(documents.items.required.includes("sha256"));',
    '  assert.ok(documents.items.required.includes("variant_scope_keys"));',
    '  assert.ok(schema.allOf.some(rule => rule.$comment === "run83 pair document manifest condition" && rule.then?.properties?.snapshot_manifest?.required?.includes("documents")));',
    "});",
    ""
  ].join("\n");
  tests = tests.replace('\ntest("imports a vehicle catalog as candidates and requires primary-source review plus exact engine/transmission pairing"', schemaTest + '\ntest("imports a vehicle catalog as candidates and requires primary-source review plus exact engine/transmission pairing"');
}
write(testFile, tests);
let docs = read(docFile);
const section = "## Pair evidence must be pinned in the immutable source snapshot manifest (run83)";
if (!docs.includes(section)) {
  docs += "\n\n" + section + "\n\nAn engine/transmission pair is rejected unless its primary approval/manufacturer document resolves to exactly one entry in the package snapshot_manifest.documents. That entry binds the document ID, HTTPS URL, SHA-256, document revision, source ID, document type, market scope and exact variant-scope keys. The manifest is included in the canonical package hash and stored with the immutable source snapshot. A URL and a syntactically valid digest supplied only inside a pair payload are not sufficient provenance. Cross-source, cross-market, cross-variant, missing and duplicate document bindings are rejected before the SQLite transaction writes catalog rows. This does not grant reuse rights: the source still must have explicit approved rights, and the pair remains a candidate until a reviewer independently checks the cited primary document.\n";
  write(docFile, docs);
}
console.log(JSON.stringify({ status: "patched", run: 83, files: ["lib/local-core-db.cjs", "tests/local-core-db.test.cjs", "data/schemas/vehicle-catalog-package.schema.json", "docs/LOCAL_VEHICLE_CATALOG_IMPORT.md"] }));

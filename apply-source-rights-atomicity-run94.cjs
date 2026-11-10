"use strict";
const fs = require("node:fs");
const path = require("node:path");
const crypto = require("node:crypto");

function argument(name, fallback) {
  const index = process.argv.indexOf(name);
  return index >= 0 && process.argv[index + 1] ? process.argv[index + 1] : fallback;
}
const desktopRoot = path.resolve(argument("--desktop-root", "desktop-source"));
const repoRoot = __dirname;
const corePath = path.join(desktopRoot, "lib/local-core-db.cjs");
const packagePath = path.join(desktopRoot, "package.json");
if (!fs.existsSync(corePath) || !fs.existsSync(packagePath)) throw new Error("Run94 requires the desktop local-core module and package.json");

function replaceExactlyOnce(text, before, after, label) {
  const first = text.indexOf(before);
  if (first < 0) throw new Error("Run94 could not find expected source anchor: " + label);
  if (text.indexOf(before, first + before.length) >= 0) throw new Error("Run94 found duplicate source anchor: " + label);
  return text.slice(0, first) + after + text.slice(first + before.length);
}

let coreSource = fs.readFileSync(corePath, "utf8").replace(/\r\n/g, "\n");
const helperAnchor = 'const OWNER_RIGHTS_CONFIRMATION = "ПОДТВЕРЖДАЮ, ЧТО ИМЕЮ ПРАВО ИСПОЛЬЗОВАТЬ ЭТОТ ИСТОЧНИК В VAG TECH PRO НА УКАЗАННЫХ УСЛОВИЯХ: КОММЕРЧЕСКОЕ ИСПОЛЬЗОВАНИЕ, ПОКАЗ, ОФЛАЙН-КЭШ, МАССОВОЕ ИСПОЛЬЗОВАНИЕ И РАСПРОСТРАНЕНИЕ";';
const helper = [
'function registerSourceIfAbsent(dbPath, source, options = {}) {',
'  const s = normalizeSource(source);',
'  const db = openDatabase(dbPath);',
'  try {',
'    const now = (options.clock || (() => new Date()))().toISOString();',
'    db.exec("BEGIN IMMEDIATE");',
'    try {',
'      const existing = db.prepare("SELECT * FROM sources WHERE source_id=?").get(s.source_id);',
'      if (existing) {',
'        db.exec("COMMIT");',
'        return { inserted: false, source: existing };',
'      }',
'      const insertSql = "INSERT INTO sources(source_id,publisher,title,source_type,source_url,revision,license_id,license_url,license_sha256,rights_status," +',
'        "commercial_use_allowed,display_allowed,offline_cache_allowed,bulk_reuse_allowed,redistribution_allowed,share_alike_required,attribution_required," +',
'        "attribution_text,market_scope,source_snapshot_sha256,rights_evidence_sha256,status,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)";',
'      db.prepare(insertSql).run(',
'        s.source_id,s.publisher,s.title,s.source_type,s.source_url||null,s.revision,s.license_id||null,s.license_url||null,s.license_sha256||null,s.rights_status,',
'        s.commercial_use_allowed,s.display_allowed,s.offline_cache_allowed,s.bulk_reuse_allowed,s.redistribution_allowed,s.share_alike_required,s.attribution_required,',
'        s.attribution_text||null,s.market_scope,s.source_snapshot_sha256||null,s.rights_evidence_sha256||null,',
'        s.rights_status.startsWith("approved_by_") ? "approved" : s.rights_status === "restricted" ? "blocked" : "candidate",now,now',
'      );',
'      db.prepare("INSERT INTO audit_events(event_type,entity_type,entity_key,details_json,created_at) VALUES(\\'source_registered\\',\\'source\\',?,?,?)")',
'        .run(s.source_id, JSON.stringify({ rightsStatus: s.rights_status, revision: s.revision, registrationMode: "insert_if_absent" }), now);',
'      const inserted = db.prepare("SELECT * FROM sources WHERE source_id=?").get(s.source_id);',
'      db.exec("COMMIT");',
'      return { inserted: true, source: inserted };',
'    } catch (error) {',
'      db.exec("ROLLBACK");',
'      throw error;',
'    }',
'  } finally {',
'    db.close();',
'  }',
'}',
''
].join("\n");
if (!coreSource.includes("function registerSourceIfAbsent(")) {
  coreSource = replaceExactlyOnce(coreSource, helperAnchor, helper + helperAnchor, "insert-only source registration helper");
}

const technicalBefore = [
'    const source = db.prepare("SELECT * FROM sources WHERE source_id=?").get(pkg.source_id);',
'    if (!source) throw new Error("Import source is not registered");',
'    if (source.status !== "approved" || !hasConfirmedRedistributionRights(source)) {',
'      throw new Error("Import blocked: source rights do not explicitly permit commercial use, display, offline cache, bulk reuse and redistribution");',
'    }',
'    if (requiresSeparatePack(source, pkg.snapshot_manifest)) {',
'      throw new Error("Import blocked: share-alike or separate-pack sources must remain in a separate licensed SQLite pack and cannot be merged into the core database");',
'    }',
'    if (source.revision !== pkg.source_revision || source.market_scope !== pkg.market_scope) throw new Error("Package revision or market scope does not match the approved source registry");',
'    if (source.source_snapshot_sha256 !== pkg.source_snapshot_sha256 || source.license_sha256 !== pkg.license_sha256 || source.rights_evidence_sha256 !== pkg.rights_evidence_sha256) throw new Error("Package source, license or rights-evidence hashes do not match the approved source registry");',
'    const now = (options.clock || (() => new Date()))().toISOString();',
'    db.exec("BEGIN IMMEDIATE");',
'    try {',
'      const prior = db.prepare("SELECT id,status FROM import_batches WHERE package_id=? AND package_sha256=?").get(pkg.package_id, computedPackageHash);'
].join("\n");
const technicalAfter = [
'    const now = (options.clock || (() => new Date()))().toISOString();',
'    db.exec("BEGIN IMMEDIATE");',
'    try {',
'      const source = db.prepare("SELECT * FROM sources WHERE source_id=?").get(pkg.source_id);',
'      if (typeof options.afterSourceRead === "function") options.afterSourceRead(source || null);',
'      if (!source) throw new Error("Import source is not registered");',
'      if (source.status !== "approved" || !hasConfirmedRedistributionRights(source)) {',
'        throw new Error("Import blocked: source rights do not explicitly permit commercial use, display, offline cache, bulk reuse and redistribution");',
'      }',
'      if (requiresSeparatePack(source, pkg.snapshot_manifest)) {',
'        throw new Error("Import blocked: share-alike or separate-pack sources must remain in a separate licensed SQLite pack and cannot be merged into the core database");',
'      }',
'      if (source.revision !== pkg.source_revision || source.market_scope !== pkg.market_scope) throw new Error("Package revision or market scope does not match the approved source registry");',
'      if (source.source_snapshot_sha256 !== pkg.source_snapshot_sha256 || source.license_sha256 !== pkg.license_sha256 || source.rights_evidence_sha256 !== pkg.rights_evidence_sha256) throw new Error("Package source, license or rights-evidence hashes do not match the approved source registry");',
'      const prior = db.prepare("SELECT id,status FROM import_batches WHERE package_id=? AND package_sha256=?").get(pkg.package_id, computedPackageHash);'
].join("\n");
coreSource = replaceExactlyOnce(coreSource, technicalBefore, technicalAfter, "technical package rights check transaction order");

const catalogBefore = [
'    const source = db.prepare("SELECT * FROM sources WHERE source_id=?").get(pkg.source_id);',
'    if (!source) throw new Error("Import source is not registered");',
'    if (source.status !== "approved" || !hasConfirmedRedistributionRights(source)) {',
'      throw new Error("Catalog import blocked: source rights do not explicitly permit commercial use, display, offline cache, bulk reuse and redistribution");',
'    }',
'    if (requiresSeparatePack(source, pkg.snapshot_manifest)) {',
'      throw new Error("Catalog import blocked: share-alike or separate-pack sources must remain in a separate licensed SQLite pack and cannot be merged into the core database");',
'    }',
'    if (source.revision !== pkg.source_revision || source.market_scope !== pkg.market_scope) throw new Error("Catalog package revision or market scope does not match the approved source registry");',
'    if (source.source_snapshot_sha256 !== pkg.source_snapshot_sha256 || source.license_sha256 !== pkg.license_sha256 || source.rights_evidence_sha256 !== pkg.rights_evidence_sha256) throw new Error("Catalog package source, license or rights-evidence hashes do not match the approved source registry");',
'    const now = (options.clock || (() => new Date()))().toISOString();',
'    db.exec("BEGIN IMMEDIATE");',
'    try {',
'      const prior = db.prepare("SELECT id,status FROM import_batches WHERE package_id=? AND package_sha256=?").get(pkg.package_id, computedPackageHash);'
].join("\n");
const catalogAfter = [
'    const now = (options.clock || (() => new Date()))().toISOString();',
'    db.exec("BEGIN IMMEDIATE");',
'    try {',
'      const source = db.prepare("SELECT * FROM sources WHERE source_id=?").get(pkg.source_id);',
'      if (typeof options.afterSourceRead === "function") options.afterSourceRead(source || null);',
'      if (!source) throw new Error("Import source is not registered");',
'      if (source.status !== "approved" || !hasConfirmedRedistributionRights(source)) {',
'        throw new Error("Catalog import blocked: source rights do not explicitly permit commercial use, display, offline cache, bulk reuse and redistribution");',
'      }',
'      if (requiresSeparatePack(source, pkg.snapshot_manifest)) {',
'        throw new Error("Catalog import blocked: share-alike or separate-pack sources must remain in a separate licensed SQLite pack and cannot be merged into the core database");',
'      }',
'      if (source.revision !== pkg.source_revision || source.market_scope !== pkg.market_scope) throw new Error("Catalog package revision or market scope does not match the approved source registry");',
'      if (source.source_snapshot_sha256 !== pkg.source_snapshot_sha256 || source.license_sha256 !== pkg.license_sha256 || source.rights_evidence_sha256 !== pkg.rights_evidence_sha256) throw new Error("Catalog package source, license or rights-evidence hashes do not match the approved source registry");',
'      const prior = db.prepare("SELECT id,status FROM import_batches WHERE package_id=? AND package_sha256=?").get(pkg.package_id, computedPackageHash);'
].join("\n");
coreSource = replaceExactlyOnce(coreSource, catalogBefore, catalogAfter, "catalog package rights check transaction order");

if (!coreSource.includes("registerSourceIfAbsent,approveSourceByOwner")) {
  coreSource = replaceExactlyOnce(coreSource, "registerSource,registerSourceCandidate,approveSourceByOwner",
    "registerSource,registerSourceIfAbsent,registerSourceCandidate,approveSourceByOwner", "export insert-only source registration helper");
}
fs.writeFileSync(corePath, coreSource, "utf8");

const testSource = path.join(repoRoot, "desktop/tests/rights-import-atomicity.test.cjs");
const testTarget = path.join(desktopRoot, "tests/rights-import-atomicity.test.cjs");
if (!fs.existsSync(testSource)) throw new Error("Run94 regression test source is missing");
fs.mkdirSync(path.dirname(testTarget), { recursive: true });
fs.copyFileSync(testSource, testTarget);

const packageJson = JSON.parse(fs.readFileSync(packagePath, "utf8"));
let localCoreScript = packageJson.scripts && packageJson.scripts["test:local-core"];
if (typeof localCoreScript !== "string") throw new Error("Desktop package has no test:local-core script");
if (!localCoreScript.includes("tests/rights-import-atomicity.test.cjs")) localCoreScript += " tests/rights-import-atomicity.test.cjs";
packageJson.scripts["test:local-core"] = localCoreScript;
fs.writeFileSync(packagePath, JSON.stringify(packageJson, null, 2) + "\n", "utf8");

const patchCopy = path.join(desktopRoot, "scripts/patches/apply-source-rights-atomicity-run94.cjs");
fs.mkdirSync(path.dirname(patchCopy), { recursive: true });
fs.copyFileSync(__filename, patchCopy);
const hash = (file) => crypto.createHash("sha256").update(fs.readFileSync(file)).digest("hex");
const result = {
  patch: "run94-source-rights-atomicity",
  local_core_sha256: hash(corePath),
  test_sha256: hash(testTarget),
  package_json_sha256: hash(packagePath),
  technical_import_lock_before_source_read: true,
  catalog_import_lock_before_source_read: true,
  source_registration_mode: "insert_if_absent",
  test_file: "tests/rights-import-atomicity.test.cjs"
};
console.log(JSON.stringify(result));

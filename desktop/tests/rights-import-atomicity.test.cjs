"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { Worker } = require("node:worker_threads");
const { DatabaseSync } = require("node:sqlite");
const core = require("../lib/local-core-db.cjs");

function fixture(t) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "vag-rights-lock-"));
  t.after(() => fs.rmSync(dir, { recursive: true, force: true }));
  const dbPath = path.join(dir, "vag-tech-pro.sqlite");
  core.initializeDatabase(dbPath);
  return { dir, dbPath };
}
function source(overrides = {}) {
  return {
    source_id: "rights-lock-test", publisher: "Test publisher", title: "Rights lock test", source_type: "test_dataset",
    source_url: "https://example.invalid/source", revision: "rev1", license_id: "CC0-1.0",
    license_url: "https://creativecommons.org/publicdomain/zero/1.0/", license_sha256: "a".repeat(64),
    rights_status: "approved_by_published_license", commercial_use_allowed: true, display_allowed: true,
    offline_cache_allowed: true, bulk_reuse_allowed: true, redistribution_allowed: true,
    share_alike_required: false, attribution_required: false, attribution_text: "Public domain",
    market_scope: "RU", source_snapshot_sha256: "b".repeat(64), rights_evidence_sha256: "c".repeat(64), ...overrides
  };
}
function technicalPackage() {
  const payload = { code: "P0300", description: "Generic test DTC record" };
  const record = { record_type: "dtc_generic", namespace: "generic_sae_iso_obd2", natural_key: "generic:P0300",
    title: "P0300 — test", market_scope: "RU", applicability_precision: "generic_standard",
    payload, record_sha256: core.sha256(payload), source_record_key: "obd:P0300" };
  const pkg = { package_id: "rights-lock-technical", source_id: "rights-lock-test", source_revision: "rev1", market_scope: "RU",
    source_snapshot_sha256: "b".repeat(64), license_sha256: "a".repeat(64), rights_evidence_sha256: "c".repeat(64),
    snapshot_manifest: { upstream_revision: "rev1", record_count: 1 }, records: [record] };
  pkg.package_sha256 = core.sha256({ package_id: pkg.package_id, source_id: pkg.source_id, source_revision: pkg.source_revision,
    market_scope: pkg.market_scope, source_snapshot_sha256: pkg.source_snapshot_sha256, license_sha256: pkg.license_sha256,
    rights_evidence_sha256: pkg.rights_evidence_sha256, snapshot_manifest: pkg.snapshot_manifest, records: pkg.records });
  return pkg;
}
function catalogPackage() {
  const record = { record_type: "brand", natural_key: "vw", source_record_key: "brand:vw", market_scope: "RU",
    applicability_precision: "exact_brand", payload: { brand_key: "vw", display_name: "Volkswagen" } };
  record.record_sha256 = core.catalogRecordSha256(record);
  const pkg = { package_kind: "vehicle_catalog", package_id: "rights-lock-catalog", source_id: "rights-lock-test",
    source_revision: "rev1", market_scope: "RU", source_snapshot_sha256: "b".repeat(64),
    license_sha256: "a".repeat(64), rights_evidence_sha256: "c".repeat(64),
    snapshot_manifest: { upstream_revision: "rev1", record_count: 1 }, records: [record] };
  pkg.package_sha256 = core.sha256({ package_kind: "vehicle_catalog", package_id: pkg.package_id, source_id: pkg.source_id,
    source_revision: pkg.source_revision, market_scope: pkg.market_scope, source_snapshot_sha256: pkg.source_snapshot_sha256,
    license_sha256: pkg.license_sha256, rights_evidence_sha256: pkg.rights_evidence_sha256,
    snapshot_manifest: pkg.snapshot_manifest, records: pkg.records });
  return pkg;
}
function waitForMessage(worker, predicate, timeoutMs = 5000) {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => { worker.off("message", listener); reject(new Error("Timed out waiting for worker message")); }, timeoutMs);
    const listener = (message) => {
      if (!predicate(message)) return;
      clearTimeout(timer);
      worker.off("message", listener);
      resolve(message);
    };
    worker.on("message", listener);
    worker.once("error", (error) => { clearTimeout(timer); worker.off("message", listener); reject(error); });
  });
}
function expectNoMessage(worker, predicate, timeoutMs = 500) {
  return new Promise((resolve) => {
    const listener = (message) => {
      if (!predicate(message)) return;
      clearTimeout(timer);
      worker.off("message", listener);
      resolve(message);
    };
    const timer = setTimeout(() => { worker.off("message", listener); resolve(null); }, timeoutMs);
    worker.on("message", listener);
  });
}
async function assertRightsReadAfterWriteLock(t, pkg, label) {
  const { dbPath } = fixture(t);
  core.registerSource(dbPath, source());
  const lockDb = new DatabaseSync(dbPath);
  let worker;
  try {
    lockDb.exec("PRAGMA busy_timeout=5000; BEGIN IMMEDIATE");
    lockDb.prepare("UPDATE sources SET status='blocked',rights_status='restricted',commercial_use_allowed=0,display_allowed=0,offline_cache_allowed=0,bulk_reuse_allowed=0,redistribution_allowed=0 WHERE source_id=?").run("rights-lock-test");

    const workerCode = [
      'const { parentPort, workerData } = require("node:worker_threads");',
      'const core = require(workerData.corePath);',
      'parentPort.postMessage({ type: "started" });',
      'try {',
      '  const importer = workerData.pkg.package_kind === "vehicle_catalog" ? core.importCatalogPackage : core.importPackage;',
      '  if (typeof importer !== "function") throw new Error("Expected import function is unavailable");',
      '  const result = importer(workerData.dbPath, workerData.pkg, {',
      '    afterSourceRead: (source) => parentPort.postMessage({ type: "source_read", status: source && source.status, rightsStatus: source && source.rights_status })',
      '  });',
      '  parentPort.postMessage({ type: "result", ok: true, result });',
      '} catch (error) {',
      '  parentPort.postMessage({ type: "result", ok: false, error: error.message });',
      '}'
    ].join("\n");
    worker = new Worker(workerCode, { eval: true, workerData: {
      corePath: path.resolve(__dirname, "../lib/local-core-db.cjs"), dbPath, pkg
    } });

    await waitForMessage(worker, (message) => message.type === "started");
    const premature = await expectNoMessage(worker, (message) => message.type === "source_read");
    assert.equal(premature, null, label + ": source rights were read before the SQLite write transaction was acquired");

    lockDb.exec("COMMIT");
    const sourceRead = await waitForMessage(worker, (message) => message.type === "source_read");
    assert.equal(sourceRead.status, "blocked");
    assert.equal(sourceRead.rightsStatus, "restricted");
    const result = await waitForMessage(worker, (message) => message.type === "result");
    assert.equal(result.ok, false, label + ": import must fail after source rights are revoked");
    assert.match(result.error, /source rights/i);

    const db = core.openDatabase(dbPath);
    try {
      assert.equal(db.prepare("SELECT count(*) AS n FROM import_batches").get().n, 0);
      assert.equal(db.prepare("SELECT count(*) AS n FROM technical_records").get().n, 0);
      assert.equal(db.prepare("SELECT count(*) AS n FROM brands").get().n, 0);
      assert.equal(db.prepare("SELECT count(*) AS n FROM vehicle_models").get().n, 0);
    } finally { db.close(); }
  } finally {
    try { lockDb.exec("ROLLBACK"); } catch {}
    try { lockDb.close(); } catch {}
    if (worker) {
      try { await worker.terminate(); } catch {}
    }
  }
}
test("technical-record import acquires the SQLite write lock before reading source rights", async (t) => {
  await assertRightsReadAfterWriteLock(t, technicalPackage(), "technical import");
});
test("vehicle-catalog import acquires the SQLite write lock before reading source rights", async (t) => {
  await assertRightsReadAfterWriteLock(t, catalogPackage(), "vehicle catalog import");
});
test("bundled source registration is insert-only and cannot overwrite a revoked source", (t) => {
  const { dbPath } = fixture(t);
  const first = core.registerSourceIfAbsent(dbPath, source());
  assert.equal(first.inserted, true);
  assert.equal(first.source.status, "approved");
  const second = core.registerSourceIfAbsent(dbPath, source());
  assert.equal(second.inserted, false);
  assert.equal(second.source.status, "approved");
  const db = core.openDatabase(dbPath);
  try {
    db.prepare("UPDATE sources SET status='blocked',rights_status='restricted',commercial_use_allowed=0,display_allowed=0,offline_cache_allowed=0,bulk_reuse_allowed=0,redistribution_allowed=0 WHERE source_id=?").run("rights-lock-test");
  } finally { db.close(); }
  const third = core.registerSourceIfAbsent(dbPath, source());
  assert.equal(third.inserted, false);
  assert.equal(third.source.status, "blocked");
  assert.equal(third.source.rights_status, "restricted");
  const after = core.openDatabase(dbPath);
  try { assert.equal(after.prepare("SELECT count(*) AS n FROM audit_events WHERE event_type='source_registered'").get().n, 1); }
  finally { after.close(); }
});

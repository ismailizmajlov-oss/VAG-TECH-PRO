"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const core = require("../lib/local-core-db.cjs");
const { seedWikidataCandidateCatalog } = require("../lib/wikidata-candidate-seed.cjs");

const researchRoot = path.resolve(__dirname, "../data/research");
const sourceId = "wikidata-vag-model-taxonomy";
const packageId = "wikidata-vag-model-taxonomy-cc0-630dbed1af15";
const snapshotSha256 = "630dbed1af15a81180fdba562824eaad8aa92352f4a8debb8a624ad37172bff4";

function withDatabase(t, label = "wikidata-core-seed") {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), label + "-"));
  const dbPath = path.join(root, "data", "vag-tech-pro.sqlite");
  core.initializeDatabase(dbPath);
  t.after(() => fs.rmSync(root, { recursive: true, force: true }));
  return { root, dbPath };
}
function readCounts(dbPath) {
  const db = core.openDatabase(dbPath);
  try {
    return {
      brands: db.prepare("SELECT count(*) AS n FROM brands").get().n,
      models: db.prepare("SELECT count(*) AS n FROM vehicle_models").get().n,
      candidateModels: db.prepare("SELECT count(*) AS n FROM vehicle_models WHERE review_status='candidate' AND market_scope='UNKNOWN' AND applicability_precision='vehicle_model_candidate'").get().n,
      verifiedModels: db.prepare("SELECT count(*) AS n FROM vehicle_models WHERE review_status='verified'").get().n,
      generations: db.prepare("SELECT count(*) AS n FROM vehicle_generations").get().n,
      engines: db.prepare("SELECT count(*) AS n FROM engines").get().n,
      transmissions: db.prepare("SELECT count(*) AS n FROM transmissions").get().n,
      pairs: db.prepare("SELECT count(*) AS n FROM engine_transmission_pairs").get().n,
      ecus: db.prepare("SELECT count(*) AS n FROM ecu_units").get().n,
      configurations: db.prepare("SELECT count(*) AS n FROM vehicle_configurations").get().n,
      technicalRecords: db.prepare("SELECT count(*) AS n FROM technical_records").get().n,
    };
  } finally { db.close(); }
}

test("bundled CC0 Wikidata taxonomy seeds only provenance-bound identity candidates and preserves user data", (t) => {
  const { dbPath } = withDatabase(t);
  const vehicle = core.saveUserVehicle(dbPath, { brand_name: "Volkswagen", model_name: "Golf", nickname: "My Golf", engine_code_declared: "CZEA", transmission_code_declared: "DQ200", notes: "must survive" });
  core.saveBookmark(dbPath, { target_type: "vehicle_candidate", target_key: "manual:my-golf", label: "Keep bookmark" });
  core.addHistory(dbPath, { query_text: "keep my search history", module_code: "CATALOG", result_count: 2 });
  const before = { vehicles: core.listUserVehicles(dbPath).length, bookmarks: core.listBookmarks(dbPath).length, history: core.listHistory(dbPath, 10).length };

  const result = seedWikidataCandidateCatalog(dbPath, researchRoot);
  assert.equal(result.status, "applied");
  assert.equal(result.inserted, 527);
  assert.equal(result.manufacturers, 6);
  assert.equal(result.models, 521);
  assert.equal(result.verified_models, 0);
  assert.equal(result.exact_fitments, 0);
  assert.equal(result.engine_codes, 0);
  assert.equal(result.transmission_codes, 0);
  assert.equal(result.packageSha256, "52c4b195d8200594aca1cec2de93f64f8fbe94a746dea0406715da7348e057d2");
  assert.equal(result.source_id, sourceId);
  assert.equal(result.source_revision, "wikidata-snapshot-630dbed1af15");
  assert.equal(result.market_scope, "UNKNOWN");
  assert.equal(result.applicability_precision, "candidate_identity_only");

  assert.deepEqual(readCounts(dbPath), { brands: 6, models: 521, candidateModels: 521, verifiedModels: 0, generations: 0, engines: 0, transmissions: 0, pairs: 0, ecus: 0, configurations: 0, technicalRecords: 0 });
  assert.equal(core.listReviewQueue(dbPath, 1000).length, 527);
  assert.deepEqual(core.getModuleCoverage(dbPath), []);
  const source = core.listSources(dbPath).find((item) => item.source_id === sourceId);
  assert.ok(source);
  assert.equal(source.status, "approved");
  assert.equal(source.rights_status, "approved_by_published_license");
  assert.equal(source.license_id, "CC0-1.0");
  assert.equal(source.market_scope, "UNKNOWN");
  assert.equal(source.source_snapshot_sha256, snapshotSha256);
  for (const key of ["commercial_use_allowed", "display_allowed", "offline_cache_allowed", "bulk_reuse_allowed", "redistribution_allowed"]) assert.equal(source[key], 1);
  assert.equal(source.share_alike_required, 0);
  assert.equal(source.attribution_required, 0);
  assert.match(source.license_sha256, /^[a-f0-9]{64}$/);
  assert.match(source.rights_evidence_sha256, /^[a-f0-9]{64}$/);

  const db = core.openDatabase(dbPath);
  try {
    const batch = db.prepare("SELECT * FROM import_batches WHERE package_id=?").get(packageId);
    assert.ok(batch);
    assert.equal(batch.status, "applied");
    assert.equal(batch.records_seen, 527);
    assert.equal(batch.records_inserted, 527);
    assert.equal(batch.records_unchanged, 0);
    assert.equal(batch.package_sha256, "52c4b195d8200594aca1cec2de93f64f8fbe94a746dea0406715da7348e057d2");
    const sample = db.prepare("SELECT * FROM vehicle_models WHERE source_id=? ORDER BY id LIMIT 1").get(sourceId);
    assert.ok(sample);
    assert.equal(sample.review_status, "candidate");
    assert.equal(sample.market_scope, "UNKNOWN");
    assert.equal(sample.applicability_precision, "vehicle_model_candidate");
    assert.equal(sample.source_snapshot_sha256, snapshotSha256);
    const payload = JSON.parse(sample.payload_json);
    assert.match(payload.model_qid, /^Q[0-9]+$/);
    assert.match(payload.source_record_sha256, /^[a-f0-9]{64}$/);
    assert.ok(payload.source_binding_sha256s.length >= 1);
    assert.equal(payload.exact_vehicle_fitment, false);
    assert.equal(payload.generation_verified, false);
    assert.equal(payload.engine_code_fitment, false);
    assert.equal(payload.transmission_code_fitment, false);
    assert.equal(payload.dtc_fitment, false);
    assert.equal(payload.repair_procedure_fitment, false);
    const brand = db.prepare("SELECT * FROM brands WHERE source_id=? ORDER BY id LIMIT 1").get(sourceId);
    assert.equal(brand.review_status, "candidate");
    assert.equal(brand.market_scope, "UNKNOWN");
    assert.equal(brand.applicability_precision, "manufacturer_make_candidate");
    assert.equal(brand.group_name, "VAG identity candidate");
  } finally { db.close(); }

  const after = { vehicles: core.listUserVehicles(dbPath).length, bookmarks: core.listBookmarks(dbPath).length, history: core.listHistory(dbPath, 10).length };
  assert.deepEqual(after, before);
  assert.equal(core.listUserVehicles(dbPath)[0].id, vehicle.id);
  assert.equal(core.listUserVehicles(dbPath)[0].notes, "must survive");
  assert.equal(core.listBookmarks(dbPath)[0].label, "Keep bookmark");
  assert.equal(core.listHistory(dbPath, 10)[0].query_text, "keep my search history");

  const repeat = seedWikidataCandidateCatalog(dbPath, researchRoot);
  assert.equal(repeat.status, "already_applied");
  assert.equal(repeat.inserted, 0);
  assert.equal(repeat.unchanged, 527);
  assert.deepEqual(readCounts(dbPath), { brands: 6, models: 521, candidateModels: 521, verifiedModels: 0, generations: 0, engines: 0, transmissions: 0, pairs: 0, ecus: 0, configurations: 0, technicalRecords: 0 });
});

test("Wikidata seed never restores or overwrites a source whose rights were revoked", (t) => {
  const { dbPath } = withDatabase(t, "wikidata-rights-revoked");
  assert.equal(seedWikidataCandidateCatalog(dbPath, researchRoot).status, "applied");
  const db = core.openDatabase(dbPath);
  try { db.prepare("UPDATE sources SET status='blocked',rights_status='restricted' WHERE source_id=?").run(sourceId); }
  finally { db.close(); }
  const result = seedWikidataCandidateCatalog(dbPath, researchRoot);
  assert.equal(result.status, "skipped");
  assert.equal(result.reason, "existing_source_metadata_conflict_or_rights_revoked");
  const after = core.openDatabase(dbPath);
  try {
    const source = after.prepare("SELECT status,rights_status FROM sources WHERE source_id=?").get(sourceId);
    assert.deepEqual({ ...source }, { status: "blocked", rights_status: "restricted" });
    assert.equal(after.prepare("SELECT count(*) AS n FROM vehicle_models WHERE source_id=?").get(sourceId).n, 521);
  } finally { after.close(); }
});

test("Wikidata seed rejects tampered snapshot bytes before source registration", (t) => {
  const { root, dbPath } = withDatabase(t, "wikidata-tampered");
  const tamperedRoot = path.join(root, "research");
  const sourcePack = path.join(researchRoot, "wikidata-vag-model-taxonomy-cc0");
  const targetPack = path.join(tamperedRoot, "wikidata-vag-model-taxonomy-cc0");
  fs.mkdirSync(targetPack, { recursive: true });
  fs.cpSync(sourcePack, targetPack, { recursive: true });
  fs.appendFileSync(path.join(targetPack, "snapshot.json"), "\n");
  assert.throws(() => seedWikidataCandidateCatalog(dbPath, tamperedRoot), /immutable pack hashes do not match/);
  assert.equal(core.listSources(dbPath).length, 0);
  assert.deepEqual(readCounts(dbPath), { brands: 0, models: 0, candidateModels: 0, verifiedModels: 0, generations: 0, engines: 0, transmissions: 0, pairs: 0, ecus: 0, configurations: 0, technicalRecords: 0 });
});

test("missing Wikidata pack is a non-destructive skip", (t) => {
  const { dbPath, root } = withDatabase(t, "wikidata-pack-missing");
  const result = seedWikidataCandidateCatalog(dbPath, path.join(root, "missing-research"));
  assert.equal(result.status, "skipped");
  assert.equal(result.reason, "wikidata_pack_missing");
  assert.equal(core.listSources(dbPath).length, 0);
  assert.deepEqual(readCounts(dbPath), { brands: 0, models: 0, candidateModels: 0, verifiedModels: 0, generations: 0, engines: 0, transmissions: 0, pairs: 0, ecus: 0, configurations: 0, technicalRecords: 0 });
});

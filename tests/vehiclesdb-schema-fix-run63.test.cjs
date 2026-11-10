"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const crypto = require("node:crypto");
const { spawnSync } = require("node:child_process");
const test = require("node:test");

const PATCH_SOURCE = path.join(__dirname, "..", "apply-vehiclesdb-schema-fix-run63.cjs");

function write(root, relative, value) {
  const file = path.join(root, relative);
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, value, "utf8");
}

function fixture(root, dynamicGate = true) {
  const gate = dynamicGate ? [
    "if (!vehiclesDbProvenance || vehiclesDbProvenance.dataset_id !== PACKS.vehiclesdb.id ||",
    "    vehiclesDbProvenance.dataset_license !== PACKS.vehiclesdb.license ||",
    "    vehiclesDbProvenance.upstream_tag !== vehiclesDbPackManifest.upstream_tag ||",
    "    vehiclesDbProvenance.upstream_manifest_sha256 !== vehiclesDbPackManifest.source_manifest_sha256 ||",
    "    vehiclesDbProvenance.source_catalog_sha256 !== vehiclesDbPackManifest.source_catalog_sha256 ||",
    "    vehiclesDbProvenance.attribution_sha256 !== vehiclesDbPackManifest.source_snapshot_sha256?.[\"ATTRIBUTION.md\"] ||",
    "    vehiclesDbProvenance.license_sha256 !== vehiclesDbPackManifest.source_snapshot_sha256?.[\"LICENSE\"] ||",
    "    vehiclesDbProvenance.lock_sha256 !== vehiclesDbPackManifest.lock_sha256 ||",
    "    vehiclesDbCounts.sources !== 14 ||",
    "    vehiclesDbCounts.models !== vehiclesDbPackManifest.counts?.models ||",
    "    vehiclesDbCounts.marketEvidence !== vehiclesDbPackManifest.counts?.market_evidence ||",
    "    vehiclesDbCounts.russianEvidence !== 0 ||",
    "    vehiclesDbPackManifest.identity_only_use !== true ||",
    "    vehiclesDbPackManifest.safety_critical_reliance !== false ||",
    "    vehiclesDbPackManifest.repair_decision_use !== false ||",
    "    vehiclesDbPackManifest.fitment_claim !== false ||",
    "    vehiclesDbPackManifest.ru_evidence_present !== false ||",
    "    vehiclesDbPackManifest.attribution?.required !== true ||",
    "    vehiclesDbPackManifest.counts?.models !== vehiclesDbCounts.models ||",
    "    vehiclesDbPackManifest.counts?.market_evidence !== vehiclesDbCounts.marketEvidence ||",
    "    !vehiclesDbPackManifest.open_data_policy_notice.includes(" + "\"not designed or warranted for safety-critical\") ||",
    "    !/Vehicle data by VehiclesDB/i.test(vehiclesDbAttribution) ||",
    "    !/UNCONDITIONAL/i.test(vehiclesDbAttribution)) {"
  ].join("\n") : [
    "if (!vehiclesDbProvenance || vehiclesDbProvenance.dataset_id !== PACKS.vehiclesdb.id ||",
    "    vehiclesDbCounts.models !== vehiclesDbPackManifest.counts?.models ||"
  ].join("\n");

  const db = [
    "const vehiclesDbProvenance = vehiclesDb.prepare(\"SELECT dataset_id, publisher, repository, upstream_tag, dataset_version, dataset_license, license_url, upstream_manifest_sha256, source_catalog_sha256, attribution_sha256, license_sha256, lock_sha256, imported_at_utc FROM dataset_provenance WHERE dataset_id=?\").get(PACKS.vehiclesdb.id);",
    gate,
    "  throw new Error(\"VehiclesDB gate failed\");",
    "}",
    "const item = {",
    "  attributionUrl: safeHttpsUrl(vehiclesDbProvenance.attribution_url),",
    "  upstreamRevision: vehiclesDbProvenance.upstream_tag,",
    "  snapshotGeneratedAt: vehiclesDbProvenance.built_at_utc,",
    "};",
    "function searchVehiclesDbCandidates(query, limit = 25, root) {",
    "  return [];",
    "}",
    "function searchUdsSignals() {}",
    ""
  ].join("\n");

  const verifier = [
    "assert(vehiclesDbSnapshot.dataset_id === \"vehiclesdb-vag-identity-cc-by-4.0\" && vehiclesDbSnapshot.dataset_license === vehiclesdb.license, \"VehiclesDB dataset manifest identity/license mismatch\");",
    "assert(vehiclesDbSnapshot.attribution?.required === true && /Vehicle data by VehiclesDB/i.test(vehiclesDbAttribution) && /UNCONDITIONAL/i.test(vehiclesDbAttribution), \"VehiclesDB attribution and upstream notices are incomplete\");",
    "const vehiclesDbProvenance = vehiclesDb.prepare(\"SELECT dataset_id, publisher, repository_url, upstream_tag, dataset_version, dataset_license, attribution_required, attribution_text, attribution_url, catalog_sqlite_sha256, upstream_manifest_sha256, license_sha256, attribution_sha256, ru_evidence_present, fitment_claim FROM dataset_provenance WHERE provenance_id=1\").get();",
    "assert(vehiclesDbProvenance && vehiclesDbProvenance.dataset_license === \"CC-BY-4.0\" && vehiclesDbProvenance.attribution_required === 1 && vehiclesDbProvenance.ru_evidence_present === 0 && vehiclesDbProvenance.fitment_claim === 0, \"VehiclesDB embedded provenance failed\");",
    "assert(vehiclesDbProvenance.catalog_sqlite_sha256 === vehiclesDbSnapshot.source_snapshot_sha256[\"catalog.sqlite\"] && vehiclesDbProvenance.upstream_manifest_sha256 === vehiclesdb.upstream_manifest_sha256 && vehiclesDbProvenance.license_sha256 === vehiclesdb.license_file_sha256 && vehiclesDbProvenance.attribution_sha256 === vehiclesdb.attribution_sha256, \"VehiclesDB embedded source hashes mismatch\");",
    "const sourceArtifacts = vehiclesDb.prepare(\"SELECT relative_path, sha256 FROM source_file_artifacts ORDER BY relative_path\").all();",
    "    for (const artifact of sourceArtifacts) {",
    "      const expected = vehiclesDbSnapshot.source_snapshot_sha256[artifact.relative_path === \"catalog.sqlite\" ? \"catalog.sqlite\" : artifact.relative_path === \"manifest.json\" ? \"manifest.json\" : artifact.relative_path === \"LICENSE\" ? \"LICENSE\" : \"ATTRIBUTION.md\"];",
    ["      assert(expected === artifact.sha256, ", String.fromCharCode(96), "VehiclesDB source artifact hash mismatch for ", String.fromCharCode(36), "{artifact.relative_path}", String.fromCharCode(96), ");"].join(""),
    "    }",
    ""
  ].join("\n");

  const tests = [
    "  assert.equal(rows[0].snapshotGeneratedAt, \"2026-11-03T07:21:36.7901580Z\");",
    "  assert.throws(() => vehiclesDb.exec(\"DELETE FROM model_candidates WHERE model_candidate_id=1\"), /readonly|read-only|query only/i);",
    "  assert.match(golf.sourceSha256, /^[a-f0-9]{64}$/);",
    ""
  ].join("\n");

  write(root, "desktop-source/lib/local-research-db.cjs", db);
  write(root, "desktop-source/scripts/verify-local-research-packs.cjs", verifier);
  write(root, "desktop-source/tests/local-research-db.test.cjs", tests);
}

function run(root) {
  return spawnSync(process.execPath, [path.join(root, "apply-vehiclesdb-schema-fix-run63.cjs")], { encoding: "utf8" });
}

test("run63 preserves the newer manifest-driven candidate/safety gate and remains idempotent", () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "vag-run63-current-gate-"));
  try {
    fs.copyFileSync(PATCH_SOURCE, path.join(root, "apply-vehiclesdb-schema-fix-run63.cjs"));
    fixture(root, true);
    const first = run(root);
    assert.equal(first.status, 0, first.stderr);
    const dbFile = path.join(root, "desktop-source/lib/local-research-db.cjs");
    const db = fs.readFileSync(dbFile, "utf8");
    assert.match(db, /vehiclesDbCounts\.models !== vehiclesDbPackManifest\.counts\?\.models/);
    assert.match(db, /vehiclesDbCounts\.marketEvidence !== vehiclesDbPackManifest\.counts\?\.market_evidence/);
    assert.match(db, /vehiclesDbPackManifest\.identity_only_use !== true/);
    assert.match(db, /vehiclesDbPackManifest\.safety_critical_reliance !== false/);
    assert.match(db, /vehiclesDbPackManifest\.repair_decision_use !== false/);
    assert.doesNotMatch(db, /vehiclesDbCounts\.models !== 260/);
    assert.doesNotMatch(db, /vehiclesDbCounts\.marketEvidence !== 1524/);
    assert.match(db, /attributionUrl: safeHttpsUrl\(packManifest\.attribution\?\.url\)/);
    assert.match(db, /identityOnlyUse: packManifest\.identity_only_use === true/);
    assert.match(db, /safetyCriticalReliance: packManifest\.safety_critical_reliance === true/);
    assert.match(db, /repairDecisionUse: packManifest\.repair_decision_use === true/);
    assert.match(db, /openDataPolicyNotice: packManifest\.open_data_policy_notice/);
    assert.match(db, /sourceRevision: packManifest\.upstream_tag/);

    const verifier = fs.readFileSync(path.join(root, "desktop-source/scripts/verify-local-research-packs.cjs"), "utf8");
    assert.match(verifier, /vehiclesDbSnapshot\.pack_id === vehiclesdb\.id/);
    assert.match(verifier, /vehiclesDbProvenance\.source_catalog_sha256/);
    assert.match(verifier, /SELECT source_path, sha256, source_role FROM source_file_artifacts/);

    const tests = fs.readFileSync(path.join(root, "desktop-source/tests/local-research-db.test.cjs"), "utf8");
    assert.match(tests, /vehiclesDbManifest\.counts\.models/);
    assert.match(tests, /vehiclesDbManifest\.counts\.market_evidence/);
    assert.match(tests, /obdexPack\.snapshot_generated_at_utc/);
    assert.match(tests, /WHERE model_id='car\/audi\/100'/);
    assert.match(tests, /candidateRecordSha256/);

    const files = [
      dbFile,
      path.join(root, "desktop-source/scripts/verify-local-research-packs.cjs"),
      path.join(root, "desktop-source/tests/local-research-db.test.cjs")
    ];
    const beforeSecond = files.map((file) => crypto.createHash("sha256").update(fs.readFileSync(file)).digest("hex"));
    const second = run(root);
    assert.equal(second.status, 0, second.stderr);
    const afterSecond = files.map((file) => crypto.createHash("sha256").update(fs.readFileSync(file)).digest("hex"));
    assert.deepEqual(afterSecond, beforeSecond);
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
});

test("run63 rejects a partial dynamic gate without writing a partially patched desktop file", () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "vag-run63-partial-gate-"));
  try {
    fs.copyFileSync(PATCH_SOURCE, path.join(root, "apply-vehiclesdb-schema-fix-run63.cjs"));
    fixture(root, false);
    const dbFile = path.join(root, "desktop-source/lib/local-research-db.cjs");
    const before = fs.readFileSync(dbFile);
    const result = run(root);
    assert.notEqual(result.status, 0);
    assert.match(result.stderr, /Expected VehiclesDB provenance and candidate-only gate block exactly once/);
    assert.deepEqual(fs.readFileSync(dbFile), before);
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
});

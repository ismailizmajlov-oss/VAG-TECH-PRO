const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const crypto = require("node:crypto");
const { spawnSync } = require("node:child_process");

const ROOT = path.resolve(__dirname, "..");
const PATCH = path.join(ROOT, "apply-vehiclesdb-revision-manifest-run89.cjs");

function write(root, relativePath, content) {
  const target = path.join(root, relativePath);
  fs.mkdirSync(path.dirname(target), { recursive: true });
  fs.writeFileSync(target, content, "utf8");
}
function fixture(root, overrides = {}) {
  const manifest = {
    pack_id: "vehiclesdb-vag-identity",
    upstream_tag: "v2026.10.4",
    dataset_version: "2026.10.4",
    source_revision: "v2026.10.4",
    data_license: "CC-BY-4.0",
    rights_status: "approved_by_published_license",
    market_scope: "foreign_market_presence_only",
    applicability_precision: "make_model_name_only",
    fitment_status: "not_established",
    fitment_claim: false,
    exact_fitment: false,
    ru_evidence_present: false,
    engine_codes_included: false,
    gearbox_codes_included: false,
    ecu_fitment_included: false,
    database_sha256: "a".repeat(64),
    ...overrides,
  };
  write(root, "data/research/vehiclesdb-vag-identity/manifest.json", JSON.stringify(manifest));
  write(root, "tests/local-research-db.test.cjs", [
    '"use strict";',
    'const path = require("node:path");',
    'const fs = require("node:fs");',
    'const root = path.resolve(__dirname, "../data/research");',
    '  assert.equal(golf.sourceRevision, "v2026.10.3");',
  ].join("\n") + "\n");
}

test("run89 binds the VehiclesDB desktop test to the pinned manifest revision", () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "vag-run89-"));
  try {
    fixture(root);
    const first = spawnSync(process.execPath, [PATCH, "--desktop-root", root], { encoding: "utf8" });
    assert.equal(first.status, 0, first.stderr);
    const source = fs.readFileSync(path.join(root, "tests/local-research-db.test.cjs"), "utf8");
    assert.match(source, /vehiclesDbManifest\.source_revision/);
    assert.doesNotMatch(source, /v2026\.10\.3/);
    const evidence = JSON.parse(fs.readFileSync(path.join(root, "data/research/vehiclesdb-vag-identity/desktop-test-revision-verification.json"), "utf8"));
    assert.equal(evidence.source_revision, "v2026.10.4");
    assert.equal(evidence.data_license, "CC-BY-4.0");
    assert.equal(evidence.market_scope, "foreign_market_presence_only");
    assert.equal(evidence.exact_fitment, false);
    const second = spawnSync(process.execPath, [PATCH, "--desktop-root", root], { encoding: "utf8" });
    assert.equal(second.status, 0, second.stderr);
    assert.equal(JSON.parse(second.stdout).patch_status, "already_current");
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
});

test("run89 refuses a VehiclesDB manifest that does not carry the published foreign-market candidate scope", () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "vag-run89-invalid-"));
  try {
    fixture(root, { exact_fitment: true });
    const before = fs.readFileSync(path.join(root, "tests/local-research-db.test.cjs"), "utf8");
    const result = spawnSync(process.execPath, [PATCH, "--desktop-root", root], { encoding: "utf8" });
    assert.notEqual(result.status, 0);
    assert.match(result.stderr, /VehiclesDB manifest rights, revision or candidate-only scope gate failed/);
    assert.equal(fs.readFileSync(path.join(root, "tests/local-research-db.test.cjs"), "utf8"), before);
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
});

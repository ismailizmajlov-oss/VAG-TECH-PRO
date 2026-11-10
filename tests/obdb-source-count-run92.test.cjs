const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const crypto = require("node:crypto");
const { spawnSync } = require("node:child_process");

const ROOT = path.resolve(__dirname, "..");
const PATCH = path.join(ROOT, "apply-obdb-38-source-count-run92.cjs");

function write(root, relativePath, content) {
  const target = path.join(root, relativePath);
  fs.mkdirSync(path.dirname(target), { recursive: true });
  fs.writeFileSync(target, content, "utf8");
}

function fixture(root, counts = { sources: 38, generations: 135, ecus: 71, commands: 18387, signals: 19799 }) {
  const sources = Array.from({ length: 38 }, (_, index) => ({
    source_id: "obdb-source-" + index,
    commit_sha: String(index + 1).padStart(40, "0"),
    market_scope: "UNKNOWN",
    applicability_precision: "vehicle_model_candidate",
    verification_status: "unverified_community_candidate",
    execution_allowed: false,
  }));
  const manifest = {
    dataset_id: "obdb-vag-signalsets-cc-by-sa",
    license_id: "CC-BY-SA-4.0",
    share_alike_required: true,
    attribution_required: true,
    commercial_use_allowed: true,
    display_allowed: true,
    cache_allowed: true,
    redistribution_allowed: true,
    counts,
    sources,
    database_file: "vag-obdb-research.sqlite",
    database_sha256: crypto.createHash("sha256").update("fixture-db").digest("hex"),
  };
  write(root, "data/research/obdb-vag-signals-cc-by-sa/vag-obdb-research.sqlite", "fixture-db");
  write(root, "data/research/obdb-vag-signals-cc-by-sa/manifest.json", JSON.stringify(manifest));
  write(root, "lib/local-research-db.cjs", "if (obdbSources !== 38 || obdbGenerations !== 135 || obdbEcus !== 71 || obdbCommands !== 18387 || obdbSignals !== 19799) fail();\n");
  write(root, "scripts/verify-local-research-packs.cjs", [
    'assert((obdbSnapshot.sources || []).length === 38, "OBDb source registry does not contain thirty-eight pinned repositories");',
    'assert(obdbCounts.sources === 38 && obdbCounts.generations === 135 && obdbCounts.ecus === 71 && obdbCounts.commands === 18387 && obdbCounts.signals === 19799 && !obdbCounts.unsafeCommands && !obdbCounts.invalidSignals, `OBDb candidate/non-execution gate failed: ${JSON.stringify(obdbCounts)}`);',
  ].join("\n") + "\n");
  write(root, "tests/local-research-db.test.cjs", "assert.deepEqual(obdb.counts, { sources: 38, generations: 135, ecus: 71, commands: 18387, signals: 19799 });\n");
  write(root, "tests/local-research-packs.test.cjs", [
    "assert.equal(result.obdb_vag_signals.sources, 38);",
    "assert.equal(result.obdb_vag_signals.commands, 18387);",
    "assert.equal(result.obdb_vag_signals.signals, 19799);",
  ].join("\n") + "\n");
}

test("run92 synchronizes all desktop OBDb count gates from the pinned 38-source manifest", () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "vag-run92-"));
  try {
    fixture(root);
    const result = spawnSync(process.execPath, [PATCH, "--desktop-root", root], { encoding: "utf8" });
    assert.equal(result.status, 0, result.stderr);
    const expected = [
      ["lib/local-research-db.cjs", "obdbSources !== 38 || obdbGenerations !== 135 || obdbEcus !== 71 || obdbCommands !== 18387 || obdbSignals !== 19799"],
      ["scripts/verify-local-research-packs.cjs", 'assert((obdbSnapshot.sources || []).length === 16, "OBDb source registry does not contain sixteen pinned repositories");'],
      ["scripts/verify-local-research-packs.cjs", "obdbCounts.sources === 38 && obdbCounts.generations === 135 && obdbCounts.ecus === 71 && obdbCounts.commands === 18387 && obdbCounts.signals === 19799"],
      ["tests/local-research-db.test.cjs", "sources: 38, generations: 135, ecus: 71, commands: 18387, signals: 19799"],
      ["tests/local-research-packs.test.cjs", "result.obdb_vag_signals.sources, 38"],
      ["tests/local-research-packs.test.cjs", "result.obdb_vag_signals.commands, 18387"],
      ["tests/local-research-packs.test.cjs", "result.obdb_vag_signals.signals, 19799"],
    ];
    for (const [file, text] of expected) assert.ok(fs.readFileSync(path.join(root, file), "utf8").includes(text), file + " was not updated");
    const evidence = JSON.parse(fs.readFileSync(path.join(root, "data/research/obdb-vag-signals-cc-by-sa/desktop-integration-count-verification.json"), "utf8"));
    assert.equal(evidence.status, "desktop_count_gates_synchronized");
    assert.deepEqual(evidence.counts, { sources: 38, generations: 135, ecus: 71, commands: 18387, signals: 19799 });
    assert.equal(new Set(evidence.patched_files.map((item) => item.path)).size, evidence.patched_files.length);
    assert.ok(evidence.patched_files.some((item) => item.path === "lib/local-research-db.cjs" && /^[a-f0-9]{64}$/.test(item.sha256)));
    assert.ok(evidence.patched_files.some((item) => item.path === "scripts/verify-local-research-packs.cjs" && /^[a-f0-9]{64}$/.test(item.sha256)));
    const second = spawnSync(process.execPath, [PATCH, "--desktop-root", root], { encoding: "utf8" });
    assert.equal(second.status, 0, second.stderr);
    const secondOutput = JSON.parse(second.stdout);
    assert.equal(secondOutput.status, "desktop_count_gates_synchronized");
    assert.deepEqual(secondOutput.counts, { sources: 38, generations: 135, ecus: 71, commands: 18387, signals: 19799 });
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
});

test("run92 fails closed when the source manifest does not match the expected verified pack counts", () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "vag-run92-invalid-"));
  try {
    fixture(root, { sources: 38, generations: 134, ecus: 71, commands: 18387, signals: 19799 });
    const before = fs.readFileSync(path.join(root, "lib/local-research-db.cjs"), "utf8");
    const result = spawnSync(process.execPath, [PATCH, "--desktop-root", root], { encoding: "utf8" });
    assert.notEqual(result.status, 0);
    assert.match(result.stderr, /OBDb manifest count mismatch for generations/);
    assert.equal(fs.readFileSync(path.join(root, "lib/local-research-db.cjs"), "utf8"), before);
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
});

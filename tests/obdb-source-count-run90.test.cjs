const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const crypto = require("node:crypto");
const { spawnSync } = require("node:child_process");

const ROOT = path.resolve(__dirname, "..");
const PATCH = path.join(ROOT, "apply-obdb-26-source-count-run90.cjs");

function write(root, relativePath, content) {
  const target = path.join(root, relativePath);
  fs.mkdirSync(path.dirname(target), { recursive: true });
  fs.writeFileSync(target, content, "utf8");
}

function fixture(root, counts = { sources: 26, generations: 115, ecus: 61, commands: 13579, signals: 14512 }) {
  const sources = Array.from({ length: 26 }, (_, index) => ({
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
  write(root, "lib/local-research-db.cjs", "if (obdbSources !== 6 || obdbGenerations !== 32 || obdbEcus !== 15 || obdbCommands !== 2315 || obdbSignals !== 2480) fail();\n");
  write(root, "scripts/verify-local-research-packs.cjs", [
    'assert((obdbSnapshot.sources || []).length === 6, "OBDb source registry does not contain six pinned repositories");',
    'assert(obdbCounts.sources === 6 && obdbCounts.generations === 32 && obdbCounts.ecus === 15 && obdbCounts.commands === 2315 && obdbCounts.signals === 2480 && !obdbCounts.unsafeCommands && !obdbCounts.invalidSignals, `OBDb candidate/non-execution gate failed: ${JSON.stringify(obdbCounts)}`);',
  ].join("\n") + "\n");
  write(root, "tests/local-research-db.test.cjs", "assert.deepEqual(obdb.counts, { sources: 6, generations: 32, ecus: 15, commands: 2315, signals: 2480 });\n");
  write(root, "tests/local-research-packs.test.cjs", [
    "assert.equal(result.obdb_vag_signals.sources, 6);",
    "assert.equal(result.obdb_vag_signals.commands, 2315);",
    "assert.equal(result.obdb_vag_signals.signals, 2480);",
  ].join("\n") + "\n");
}

test("run90 synchronizes all desktop OBDb count gates from the pinned 26-source manifest", () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "vag-run90-"));
  try {
    fixture(root);
    const result = spawnSync(process.execPath, [PATCH, "--desktop-root", root], { encoding: "utf8" });
    assert.equal(result.status, 0, result.stderr);
    const expected = [
      ["lib/local-research-db.cjs", "obdbSources !== 16 || obdbGenerations !== 82 || obdbEcus !== 44 || obdbCommands !== 7890 || obdbSignals !== 8446"],
      ["scripts/verify-local-research-packs.cjs", 'assert((obdbSnapshot.sources || []).length === 16, "OBDb source registry does not contain twenty-six pinned repositories");'],
      ["scripts/verify-local-research-packs.cjs", "obdbCounts.sources === 16 && obdbCounts.generations === 82 && obdbCounts.ecus === 44 && obdbCounts.commands === 7890 && obdbCounts.signals === 8446"],
      ["tests/local-research-db.test.cjs", "sources: 26, generations: 115, ecus: 61, commands: 13579, signals: 14512"],
      ["tests/local-research-packs.test.cjs", "result.obdb_vag_signals.sources, 16"],
      ["tests/local-research-packs.test.cjs", "result.obdb_vag_signals.commands, 7890"],
      ["tests/local-research-packs.test.cjs", "result.obdb_vag_signals.signals, 8446"],
    ];
    for (const [file, text] of expected) assert.ok(fs.readFileSync(path.join(root, file), "utf8").includes(text), file + " was not updated");
    const evidence = JSON.parse(fs.readFileSync(path.join(root, "data/research/obdb-vag-signals-cc-by-sa/desktop-integration-count-verification.json"), "utf8"));
    assert.equal(evidence.status, "desktop_count_gates_synchronized");
    assert.deepEqual(evidence.counts, { sources: 26, generations: 115, ecus: 61, commands: 13579, signals: 14512 });
    assert.equal(new Set(evidence.patched_files.map((item) => item.path)).size, evidence.patched_files.length);
    assert.ok(evidence.patched_files.some((item) => item.path === "lib/local-research-db.cjs" && /^[a-f0-9]{64}$/.test(item.sha256)));
    assert.ok(evidence.patched_files.some((item) => item.path === "scripts/verify-local-research-packs.cjs" && /^[a-f0-9]{64}$/.test(item.sha256)));
    const second = spawnSync(process.execPath, [PATCH, "--desktop-root", root], { encoding: "utf8" });
    assert.equal(second.status, 0, second.stderr);
    const secondOutput = JSON.parse(second.stdout);
    assert.equal(secondOutput.status, "desktop_count_gates_synchronized");
    assert.deepEqual(secondOutput.counts, { sources: 26, generations: 115, ecus: 61, commands: 13579, signals: 14512 });
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
});

test("run90 fails closed when the source manifest does not match the expected verified pack counts", () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "vag-run90-invalid-"));
  try {
    fixture(root, { sources: 26, generations: 114, ecus: 61, commands: 13579, signals: 14512 });
    const before = fs.readFileSync(path.join(root, "lib/local-research-db.cjs"), "utf8");
    const result = spawnSync(process.execPath, [PATCH, "--desktop-root", root], { encoding: "utf8" });
    assert.notEqual(result.status, 0);
    assert.match(result.stderr, /OBDb manifest count mismatch for generations/);
    assert.equal(fs.readFileSync(path.join(root, "lib/local-research-db.cjs"), "utf8"), before);
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
});

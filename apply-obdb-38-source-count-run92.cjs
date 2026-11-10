#!/usr/bin/env node
"use strict";

const fs = require("node:fs");
const path = require("node:path");
const crypto = require("node:crypto");

function fail(message) {
  throw new Error(message);
}

function parseArgs(argv) {
  const args = {};
  for (let i = 2; i < argv.length; i += 1) {
    const key = argv[i];
    if (key !== "--desktop-root" || !argv[i + 1]) fail("Usage: node apply-obdb-38-source-count-run92.cjs --desktop-root <path>");
    args.desktopRoot = path.resolve(argv[++i]);
  }
  if (!args.desktopRoot) fail("Missing --desktop-root");
  return args;
}

function sha256(value) {
  return crypto.createHash("sha256").update(value).digest("hex");
}

function regularFile(root, relativePath, readText = true) {
  const file = path.join(root, relativePath);
  const stat = fs.lstatSync(file);
  if (!stat.isFile() || stat.isSymbolicLink()) fail("Expected a regular non-symlink file: " + relativePath);
  return { file, stat, text: readText ? fs.readFileSync(file, "utf8") : undefined };
}

function atomicWrite(file, content, mode) {
  const temp = path.join(path.dirname(file), "." + path.basename(file) + "." + process.pid + ".run92.tmp");
  try {
    fs.writeFileSync(temp, content, { flag: "wx", mode: mode & 0o777 });
    fs.chmodSync(temp, mode & 0o777);
    fs.renameSync(temp, file);
  } finally {
    if (fs.existsSync(temp)) fs.unlinkSync(temp);
  }
}

function replaceExact(root, relativePath, oldText, newText) {
  const item = regularFile(root, relativePath);
  const oldCount = item.text.split(oldText).length - 1;
  const newCount = item.text.split(newText).length - 1;
  if (oldCount === 1 && newCount === 0) {
    const updated = item.text.replace(oldText, newText);
    atomicWrite(item.file, updated, item.stat.mode);
    return { path: relativePath, status: "updated", sha256: sha256(Buffer.from(updated, "utf8")) };
  }
  if (oldCount === 0 && newCount === 1) {
    return { path: relativePath, status: "already_current", sha256: sha256(Buffer.from(item.text, "utf8")) };
  }
  fail("Run88 exact-count patch target is stale or ambiguous in " + relativePath + " (old=" + oldCount + ", new=" + newCount + ")");
}

function validatePack(root) {
  const item = regularFile(root, "data/research/obdb-vag-signals-cc-by-sa/manifest.json");
  let manifest;
  try {
    manifest = JSON.parse(item.text);
  } catch (error) {
    fail("OBDb manifest is not valid JSON: " + error.message);
  }
  const expected = { sources: 38, generations: 135, ecus: 71, commands: 18387, signals: 19799 };
  if (manifest.dataset_id !== "obdb-vag-signalsets-cc-by-sa" ||
      manifest.license_id !== "CC-BY-SA-4.0" ||
      manifest.share_alike_required !== true ||
      manifest.attribution_required !== true ||
      manifest.commercial_use_allowed !== true ||
      manifest.display_allowed !== true ||
      manifest.cache_allowed !== true ||
      manifest.redistribution_allowed !== true ||
      !manifest.counts || !Array.isArray(manifest.sources) || manifest.sources.length !== expected.sources) {
    fail("OBDb manifest identity, rights or source-count gate failed");
  }
  for (const key of Object.keys(expected)) {
    if (manifest.counts[key] !== expected[key]) fail("OBDb manifest count mismatch for " + key + ": " + manifest.counts[key]);
  }
  const ids = new Set();
  for (const source of manifest.sources) {
    if (!source || typeof source.source_id !== "string" || !source.source_id.trim() || ids.has(source.source_id)) {
      fail("OBDb manifest has a missing or duplicate source_id");
    }
    ids.add(source.source_id);
    if (!/^[0-9a-f]{40}$/.test(source.commit_sha || "") ||
        source.market_scope !== "UNKNOWN" ||
        source.applicability_precision !== "vehicle_model_candidate" ||
        source.verification_status !== "unverified_community_candidate" ||
        source.execution_allowed !== false) {
      fail("OBDb source is not an isolated, unverified, non-executable candidate: " + source.source_id);
    }
  }
  const packRoot = path.resolve(root, "data/research/obdb-vag-signals-cc-by-sa");
  const databasePath = path.resolve(packRoot, String(manifest.database_file || ""));
  if (databasePath === packRoot || !databasePath.startsWith(packRoot + path.sep) ||
      !/^[a-f0-9]{64}$/.test(manifest.database_sha256 || "")) {
    fail("OBDb database path or SHA-256 declaration is invalid");
  }
  const database = regularFile(root, path.relative(root, databasePath), false);
  if (sha256(fs.readFileSync(database.file)) !== manifest.database_sha256) {
    fail("OBDb database SHA-256 does not match the pinned manifest");
  }
  return { manifest, manifestSha256: sha256(Buffer.from(item.text, "utf8")) };
}

function main() {
  const { desktopRoot } = parseArgs(process.argv);
  const rootStat = fs.lstatSync(desktopRoot);
  if (!rootStat.isDirectory() || rootStat.isSymbolicLink()) fail("Desktop root must be a regular non-symlink directory");
  const { manifest, manifestSha256 } = validatePack(desktopRoot);
  const targets = [
    replaceExact(
      desktopRoot,
      "lib/local-research-db.cjs",
      "obdbSources !== 38 || obdbGenerations !== 135 || obdbEcus !== 71 || obdbCommands !== 18387 || obdbSignals !== 19799",
      "obdbSources !== 38 || obdbGenerations !== 135 || obdbEcus !== 71 || obdbCommands !== 18387 || obdbSignals !== 19799"
    ),
    replaceExact(
      desktopRoot,
      "scripts/verify-local-research-packs.cjs",
      'assert((obdbSnapshot.sources || []).length === 38, "OBDb source registry does not contain thirty-eight pinned repositories");',
      'assert((obdbSnapshot.sources || []).length === 38, "OBDb source registry does not contain thirty-eight pinned repositories");'
    ),
    replaceExact(
      desktopRoot,
      "scripts/verify-local-research-packs.cjs",
      'assert(obdbCounts.sources === 38 && obdbCounts.generations === 135 && obdbCounts.ecus === 71 && obdbCounts.commands === 18387 && obdbCounts.signals === 19799 && !obdbCounts.unsafeCommands && !obdbCounts.invalidSignals, `OBDb candidate/non-execution gate failed: ${JSON.stringify(obdbCounts)}`);',
      'assert(obdbCounts.sources === 38 && obdbCounts.generations === 135 && obdbCounts.ecus === 71 && obdbCounts.commands === 18387 && obdbCounts.signals === 19799 && !obdbCounts.unsafeCommands && !obdbCounts.invalidSignals, `OBDb candidate/non-execution gate failed: ${JSON.stringify(obdbCounts)}`);'
    ),
    replaceExact(
      desktopRoot,
      "tests/local-research-db.test.cjs",
      "assert.deepEqual(obdb.counts, { sources: 38, generations: 135, ecus: 71, commands: 18387, signals: 19799 });",
      "assert.deepEqual(obdb.counts, { sources: 38, generations: 135, ecus: 71, commands: 18387, signals: 19799 });"
    ),
    replaceExact(
      desktopRoot,
      "tests/local-research-packs.test.cjs",
      "assert.equal(result.obdb_vag_signals.sources, 38);",
      "assert.equal(result.obdb_vag_signals.sources, 38);"
    ),
    replaceExact(
      desktopRoot,
      "tests/local-research-packs.test.cjs",
      "assert.equal(result.obdb_vag_signals.commands, 18387);",
      "assert.equal(result.obdb_vag_signals.commands, 18387);"
    ),
    replaceExact(
      desktopRoot,
      "tests/local-research-packs.test.cjs",
      "assert.equal(result.obdb_vag_signals.signals, 19799);",
      "assert.equal(result.obdb_vag_signals.signals, 19799);"
    ),
  ];
  const evidence = {
    schema_version: 1,
    status: "desktop_count_gates_synchronized",
    patch_id: "run92-obdb-16-source-count-sync",
    source_manifest_sha256: manifestSha256,
    database_sha256: manifest.database_sha256,
    license_id: manifest.license_id,
    share_alike_required: manifest.share_alike_required,
    market_scope: "UNKNOWN",
    verification_status: "unverified_community_candidate",
    execution_allowed: false,
    counts: manifest.counts,
    source_ids: manifest.sources.map((source) => source.source_id).sort(),
    patched_files: [...new Set(targets.map(({ path: relativePath }) => relativePath))].map((relativePath) => {
      const item = regularFile(desktopRoot, relativePath, false);
      return { path: relativePath, sha256: sha256(fs.readFileSync(item.file)) };
    }),
  };
  const evidencePath = path.join(desktopRoot, "data/research/obdb-vag-signals-cc-by-sa/desktop-integration-count-verification.json");
  if (fs.existsSync(evidencePath)) {
    const existing = fs.lstatSync(evidencePath);
    if (!existing.isFile() || existing.isSymbolicLink()) fail("Run88 evidence path is not a regular file");
    let existingEvidence;
    try {
      existingEvidence = JSON.parse(fs.readFileSync(evidencePath, "utf8"));
    } catch (error) {
      fail("Existing Run88 evidence is not valid JSON: " + error.message);
    }
    if (JSON.stringify(existingEvidence) !== JSON.stringify(evidence)) {
      fail("Existing Run88 evidence does not match the current source snapshot and patched files");
    }
  } else {
    atomicWrite(evidencePath, JSON.stringify(evidence, null, 2) + "\n", 0o644);
  }
  process.stdout.write(JSON.stringify({ status: evidence.status, counts: evidence.counts, source_manifest_sha256: manifestSha256, evidence_path: "data/research/obdb-vag-signals-cc-by-sa/desktop-integration-count-verification.json", patched_files: evidence.patched_files }, null, 2) + "\n");
}

try {
  main();
} catch (error) {
  process.stderr.write("run92-obdb-count-sync-error: " + (error && error.message ? error.message : String(error)) + "\n");
  process.exitCode = 1;
}

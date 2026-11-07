"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const os = require("node:os");
const path = require("node:path");
const fs = require("node:fs");
const { resolvePackDatabaseFile } = require("../scripts/integrate-rdw-vag-research-pack.cjs");

test("RDW integration resolves the manifest database.path field", () => {
  const root = fsTemp();
  try {
    assert.equal(
      resolvePackDatabaseFile(root, { database: { path: "rdw-vag-research.sqlite" } }),
      path.join(root, "rdw-vag-research.sqlite")
    );
  } finally {
    require("node:fs").rmSync(root, { recursive: true, force: true });
  }
});

test("RDW integration rejects legacy or missing database path fields", () => {
  const root = fsTemp();
  try {
    assert.throws(() => resolvePackDatabaseFile(root, { database: { file: "rdw-vag-research.sqlite" } }), /database path missing/);
    assert.throws(() => resolvePackDatabaseFile(root, { database: {} }), /database path missing/);
  } finally {
    require("node:fs").rmSync(root, { recursive: true, force: true });
  }
});

test("RDW integration rejects database paths escaping the pack root", () => {
  const root = fsTemp();
  try {
    assert.throws(() => resolvePackDatabaseFile(root, { database: { path: "../outside.sqlite" } }), /Path escaped root/);
    assert.throws(() => resolvePackDatabaseFile(root, { database: { path: path.resolve(root, "..", "outside.sqlite") } }), /Path escaped root/);
  } finally {
    require("node:fs").rmSync(root, { recursive: true, force: true });
  }
});


const rdwIntegrationSource = fs.readFileSync(path.join(__dirname, "../scripts/integrate-rdw-vag-research-pack.cjs"), "utf8");

test("RDW UI patch composes with the prior CH-only ASTRA TARGA tab", () => {
  assert.match(rdwIntegrationSource, /datasetTypeAnchors/);
  assert.match(rdwIntegrationSource, /"astra" \| "astra-targa"/);
  assert.match(rdwIntegrationSource, /"astra" \| "rdw"/);
  assert.match(rdwIntegrationSource, /placeholderAnchors/);
  assert.match(rdwIntegrationSource, /astra-targa.*Motortyp.*Getriebe/s);
  assert.match(rdwIntegrationSource, /dataset === "rdw"/);
});


const rdwVerifierPatchSource = fs.readFileSync(path.join(__dirname, "../scripts/apply-rdw-vag-research-verification-run31.cjs"), "utf8");

test("RDW verifier patch composes after the separate ASTRA TARGA pack", () => {
  assert.match(rdwVerifierPatchSource, /astraTargaSummary/);
  assert.match(rdwVerifierPatchSource, /manifest\.packs\.length === 11/);
  assert.match(rdwVerifierPatchSource, /manifest\.packs\.length === 12/);
  assert.match(rdwVerifierPatchSource, /astra-fedro-targa-emissionen-approval-variants-ch/);
  assert.match(rdwVerifierPatchSource, /rdw-vag-nl-eu-type-approval-research/);
});

function fsTemp() {
  return require("node:fs").mkdtempSync(path.join(os.tmpdir(), "rdw-pack-path-test-"));
}

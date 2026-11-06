"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const os = require("node:os");
const path = require("node:path");
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

function fsTemp() {
  return require("node:fs").mkdtempSync(path.join(os.tmpdir(), "rdw-pack-path-test-"));
}

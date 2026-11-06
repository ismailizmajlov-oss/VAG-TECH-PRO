"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { patchUiTest, AFTER, TARGET } = require("../scripts/apply-rdw-ui-contract-fix-run78.cjs");

function fixture(contents) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "rdw-ui-contract-run78-"));
  fs.mkdirSync(path.join(root, "tests"), { recursive: true });
  fs.writeFileSync(path.join(root, TARGET), contents, "utf8");
  return root;
}

test("run78 accepts the actual explicit non-OEM wording and is idempotent", () => {
  const root = fixture('assert.match(ui, /не подтверждённый заводской код VAG|не код VAG/i);\n');
  try {
    assert.equal(patchUiTest(root).status, "patched");
    const patched = fs.readFileSync(path.join(root, TARGET), "utf8");
    assert.ok(patched.includes(AFTER));
    assert.equal(patchUiTest(root).status, "already_current");
    assert.equal(fs.readFileSync(path.join(root, TARGET), "utf8"), patched);
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
});

test("run78 fails closed when the source assertion is unexpectedly different", () => {
  const root = fixture('assert.match(ui, /different phrase/i);\n');
  try {
    assert.throws(() => patchUiTest(root), /expected exactly one old assertion/);
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
});

test("run78 refuses a missing target test file", () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "rdw-ui-contract-run78-"));
  try {
    assert.throws(() => patchUiTest(root), /ENOENT/);
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
});

"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { patchResearchPackVerifier } = require("../scripts/integrate-cardir-vag-owner-manual-facts.cjs");

test("CarDir integration updates the separately licensed offline research-pack count", () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "vag-tech-pro-cardir-pack-count-"));
  try {
    const scripts = path.join(root, "scripts");
    fs.mkdirSync(scripts, { recursive: true });
    const verifier = path.join(scripts, "verify-local-research-packs.cjs");
    fs.writeFileSync(verifier, [
      '"use strict";',
      'const manifest = { packs: [] };',
      'if (manifest.packs.length !== 13) throw new Error("Expected 13 separately licensed research packs, including the DE-only KBA VAG stock research pack");',
      ''
    ].join("\n"), "utf8");
    const result = patchResearchPackVerifier(root);
    const updated = fs.readFileSync(verifier, "utf8");
    assert.deepEqual(result, { expectedResearchPackCount: 14 });
    assert.match(updated, /manifest\.packs\.length !== 14/);
    assert.match(updated, /Expected 14 separately licensed research packs/);
    assert.match(updated, /CarDir VAG owner-manual facts pack/);
    assert.doesNotMatch(updated, /packs\.length !== 13/);
    assert.doesNotMatch(updated, /Expected 13 separately licensed research packs/);
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
});

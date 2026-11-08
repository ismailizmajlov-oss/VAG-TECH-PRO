"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");

const patch = require("../scripts/apply-kba-de-approval-research-verification-run1.cjs").patch;

test("KBA approval verifier patch adds the fourteenth isolated pack and is idempotent", () => {
  const temp = fs.mkdtempSync(path.join(os.tmpdir(), "vag-kba-approval-verifier-"));
  try {
    const root = path.join(temp, "desktop-source");
    const scripts = path.join(root, "scripts");
    const tests = path.join(root, "tests");
    fs.mkdirSync(scripts, { recursive: true });
    fs.mkdirSync(tests, { recursive: true });

    const verifier = [
      'const assert = require("node:assert/strict");',
      'const path = require("node:path");',
      'const ROOT = __dirname;',
      'const RESEARCH = path.join(ROOT, "..", "data", "research");',
      'function verify() {',
      '  const manifest = { schema_version: 1, packs: Array.from({ length: 13 }, (_, index) => ({ id: "pack-" + index })) };',
      '  assert(manifest.schema_version === 1 && Array.isArray(manifest.packs) && manifest.packs.length === 13, "Expected 13 separately licensed research packs, including the DE-only KBA VAG stock research pack");',
      '  const byId = Object.fromEntries(manifest.packs.map((pack) => [pack.id, pack]));',
      '  const ob = byId["ob"]; const vag = byId["vag"]; const obdb = byId["obdb"]; const vehiclesdb = byId["vehiclesdb"]; const mechanicdb = byId["mechanicdb"]; const wikidata = byId["wikidata"];',
      '  const astra = byId["astra"]; const targa = byId["targa"]; const rdw = byId["rdw"];',
      '  const kbaDe = byId["kba-de-vag-stock-research"];',
      '  assert(ob && vag && obdb && vehiclesdb && mechanicdb && wikidata && astra && targa && rdw && kbaDe, "Required generic, candidate, CH-only ASTRA TAS/TARGA and NL-only RDW packs must be registered");',
      '  const kbaDeSummary = require(path.join(ROOT, "lib", "kba-de-stock-research-db.cjs")).getKbaSummary(RESEARCH);',
      '  assert(kbaDeSummary.id === kbaDe.id && kbaDeSummary.marketScope === "DE" && kbaDeSummary.license === "DL-DE-BY-2.0" && kbaDeSummary.rightsStatus === "approved_by_published_DL_DE_BY_2_0" && kbaDeSummary.researchPackIngested === true && kbaDeSummary.productDatabaseIngested === false && kbaDeSummary.productionImport === false && kbaDeSummary.productImportAllowed === false && kbaDeSummary.ruEaeuApplicability === false && kbaDeSummary.exactVehicleFitment === false && kbaDeSummary.exactEngineGearboxPair === false && kbaDeSummary.repairApplicability === false && kbaDeSummary.diagnosticExecutionAllowed === false, "KBA stock pack boundary");',
      '  return {',
      '    kba_de_vag_stock: { marketScope: kbaDeSummary.marketScope },',
      '    production_fitment_rows_added: 0,',
      '  };',
      '}'
    ].join("\n");
    const testSource = [
      'const assert = require("node:assert/strict");',
      'function testResult(result) {',
      '  assert.equal(result.mechanicdb_vag_dtc_candidates.displayStatus, "candidate_reference_visible_separate_namespace");',
      '}'
    ].join("\n");
    fs.writeFileSync(path.join(scripts, "verify-local-research-packs.cjs"), verifier, "utf8");
    fs.writeFileSync(path.join(tests, "local-research-packs.test.cjs"), testSource, "utf8");

    const first = patch(root);
    assert.equal(first.manifestPackCount, 14);
    const patchedVerifier = fs.readFileSync(path.join(scripts, "verify-local-research-packs.cjs"), "utf8");
    const patchedTests = fs.readFileSync(path.join(tests, "local-research-packs.test.cjs"), "utf8");
    assert.match(patchedVerifier, /manifest\.packs\.length === 14/);
    assert.match(patchedVerifier, /kba-de-vag-type-approval-research/);
    assert.match(patchedVerifier, /getKbaApprovalSummary/);
    assert.match(patchedVerifier, /approvalRecords === 918/);
    assert.match(patchedVerifier, /distinctRowHashes === 918/);
    assert.match(patchedVerifier, /kba_de_vag_approvals:/);
    assert.match(patchedTests, /result\.kba_de_vag_approvals/);
    assert.match(patchedTests, /approvalRecords: 918/);
    assert.match(patchedTests, /distinctRowHashes: 918/);

    const second = patch(root);
    assert.equal(second.manifestPackCount, 14);
    assert.equal(fs.readFileSync(path.join(scripts, "verify-local-research-packs.cjs"), "utf8"), patchedVerifier);
    assert.equal(fs.readFileSync(path.join(tests, "local-research-packs.test.cjs"), "utf8"), patchedTests);
  } finally {
    fs.rmSync(temp, { recursive: true, force: true });
  }
});

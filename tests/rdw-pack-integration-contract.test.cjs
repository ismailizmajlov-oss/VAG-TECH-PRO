"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const os = require("node:os");
const path = require("node:path");
const fs = require("node:fs");
const { execFileSync } = require("node:child_process");
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
  assert.match(rdwVerifierPatchSource, /manifest\\.packs\\.length === \\(\\d\\+\\)/);
  assert.match(rdwVerifierPatchSource, /expectedPackCount = currentPackCount \\+ 1/);
  assert.doesNotMatch(rdwVerifierPatchSource, /manifest\\.packs\\.length === 11/);
  assert.doesNotMatch(rdwVerifierPatchSource, /manifest\\.packs\\.length === 12/);
  assert.match(rdwVerifierPatchSource, /astra-fedro-targa-emissionen-approval-variants-ch/);
  assert.match(rdwVerifierPatchSource, /rdw-vag-nl-eu-type-approval-research/);
  assert.ok(rdwVerifierPatchSource.includes('.join("\\n")'), "RDW verifier patch must join inserted lines with actual newline escapes");
  assert.ok(!rdwVerifierPatchSource.includes('.join("\\\\n")'), "RDW verifier patch must not emit literal backslash-n text");
});

test("RDW verifier patch increments an existing TARGA-era pack count and is idempotent", () => {
  const root = fsTemp();
  try {
    const desktopRoot = path.join(root, "desktop-source");
    const scriptsDir = path.join(desktopRoot, "scripts");
    const testsDir = path.join(desktopRoot, "tests");
    fs.mkdirSync(scriptsDir, { recursive: true });
    fs.mkdirSync(testsDir, { recursive: true });
    const targaAssertion = '  assert(astraTargaSummary.id === "astra-fedro-targa-emissionen-approval-variants-ch" && astraTargaSummary.marketScope === "CH" && astraTargaSummary.productionImport === false && astraTargaSummary.productImportAllowed === false && astraTargaSummary.ruEaeuApplicability === false && astraTargaSummary.exactVagFactoryCodePair === false && astraTargaSummary.counts.approvalPowertrainVariantRows === 53240 && astraTargaSummary.counts.exactVagFactoryCodePairRows === 0, "ASTRA TARGA must remain separately namespaced CH-only research, never factory fitment");';
    const verifier = [
      'const assert = require("node:assert/strict");',
      'const path = require("node:path");',
      'const ROOT = __dirname;',
      'function verify() {',
      '  const manifest = { schema_version: 1, packs: Array.from({ length: 12 }, (_, index) => ({ id: "pack-" + index })) };',
      '  assert(manifest.schema_version === 1 && Array.isArray(manifest.packs) && manifest.packs.length === 12, "Expected twelve registered research packs, including separate CH-only ASTRA TAS and TARGA packs");',
      '  const packIds = manifest.packs.map((pack) => pack.id);',
      '  assert(packIds.every((id) => typeof id === "string" && id.length > 0) && new Set(packIds).size === packIds.length, "Research pack IDs must be non-empty and unique");',
      '  const byId = Object.fromEntries(manifest.packs.map((pack) => [pack.id, pack]));',
      '  const ob = byId["ob"]; const vag = byId["vag"]; const obdb = byId["obdb"]; const vehiclesdb = byId["vehiclesdb"]; const mechanicdb = byId["mechanicdb"]; const wikidata = byId["wikidata"];',
      '  const astra = byId["astra-fedro-tas-type-approvals-open-data-ch"];',
      '  assert(wikidataGenerations, "Wikidata generation candidate pack must be registered");',
      '  assert(ob && vag && obdb && vehiclesdb && mechanicdb && wikidata && astra, "Required generic, candidate and CH-only research packs must be registered");',
      targaAssertion,
      '  return {',
      '    astra_ch_tas: {',
      '      marketScope: astraSummary.marketScope,',
      '      approvals: astraSummary.counts.approvals,',
      '      emissionsGearboxRows: astraSummary.counts.emissionsGearboxRows,',
      '      linkedScopeRows: astraSummary.counts.linkedScopeRows,',
      '      exactScopeLinks: astraSummary.counts.exactScopeLinks,',
      '      wildcardScopeLinks: astraSummary.counts.wildcardScopeLinks,',
      '      unlinkedScopeRows: astraSummary.counts.unlinkedScopeRows,',
      '      productionImport: astraSummary.productionImport,',
      '      ruEaeuApplicability: astraSummary.ruEaeuApplicability,',
      '      exactVehicleFitment: astraSummary.exactVehicleFitment,',
      '      repairApplicability: astraSummary.repairApplicability,',
      '      diagnosticExecutionAllowed: astraSummary.diagnosticExecutionAllowed,',
      '      databaseSha256: astraSummary.databaseSha256,',
      '    },',
      '    production_fitment_rows_added: 0,',
      '  };',
      '}',
      ''
    ].join("\n");
    const testSource = [
      'const assert = require("node:assert/strict");',
      'function testResult(result) {',
      '  assert.deepEqual(result.astra_ch_tas, {',
      '    marketScope: "CH",',
      '    approvals: 45215,',
      '    emissionsGearboxRows: 53414,',
      '    linkedScopeRows: 33909,',
      '    exactScopeLinks: 5420,',
      '    wildcardScopeLinks: 28489,',
      '    unlinkedScopeRows: 19505,',
      '    productionImport: false,',
      '    ruEaeuApplicability: false,',
      '    exactVehicleFitment: false,',
      '    repairApplicability: false,',
      '    diagnosticExecutionAllowed: false,',
      '    databaseSha256: "161800c884f6cdcc3b52c8cc87df51a2d853e7cbc640dea18847f40c0576b7f5"',
      '  });',
      '  assert.equal(result.mechanicdb_vag_dtc_candidates.displayStatus, "candidate_reference_visible_separate_namespace");',
      '}',
      ''
    ].join("\n");
    fs.writeFileSync(path.join(scriptsDir, "verify-local-research-packs.cjs"), verifier, "utf8");
    fs.writeFileSync(path.join(testsDir, "local-research-packs.test.cjs"), testSource, "utf8");
    const patchPath = path.join(__dirname, "../scripts/apply-rdw-vag-research-verification-run31.cjs");
    execFileSync(process.execPath, [patchPath, "--desktop-root", desktopRoot], { encoding: "utf8" });
    const patchedVerifier = fs.readFileSync(path.join(scriptsDir, "verify-local-research-packs.cjs"), "utf8");
    const patchedTest = fs.readFileSync(path.join(testsDir, "local-research-packs.test.cjs"), "utf8");
    assert.match(patchedVerifier, /manifest\.packs\.length === 13/);
    assert.match(patchedVerifier, /rdw-vag-nl-eu-type-approval-research/);
    assert.match(patchedVerifier, /rdw_nl_eu:/);
    assert.match(patchedTest, /result\.rdw_nl_eu/);
    execFileSync(process.execPath, [patchPath, "--desktop-root", desktopRoot], { encoding: "utf8" });
    assert.equal(fs.readFileSync(path.join(scriptsDir, "verify-local-research-packs.cjs"), "utf8"), patchedVerifier);
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
});

function fsTemp() {
  return require("node:fs").mkdtempSync(path.join(os.tmpdir(), "rdw-pack-path-test-"));
}

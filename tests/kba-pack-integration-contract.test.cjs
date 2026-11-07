"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { safeJoin } = require("../scripts/integrate-kba-de-vag-stock-research-pack.cjs");
const { execFileSync } = require("node:child_process");

const ROOT = path.join(__dirname, "..");
function read(relative) { return fs.readFileSync(path.join(ROOT, relative), "utf8"); }

test("KBA path guard rejects lexical traversal and symlinked ancestors before a leaf exists", (t) => {
  const temp = fs.mkdtempSync(path.join(os.tmpdir(), "vag-kba-path-guard-"));
  try {
    const root = path.join(temp, "root");
    const outside = path.join(temp, "outside");
    fs.mkdirSync(root);
    fs.mkdirSync(outside);
    assert.throws(() => safeJoin(root, "../outside/new.sqlite"), /Path escaped root/);

    const link = path.join(root, "linked");
    try {
      fs.symlinkSync(outside, link, process.platform === "win32" ? "junction" : "dir");
    } catch (error) {
      if (process.platform === "win32" && ["EPERM", "EACCES", "ENOTSUP"].includes(error.code)) {
        t.skip("Windows runner does not permit creating a directory junction in this environment");
        return;
      }
      throw error;
    }
    assert.throws(() => safeJoin(root, "linked/new/deep.sqlite"), /Symlink ancestor escaped root/);
    assert.equal(safeJoin(root, "fresh/new/deep.sqlite"), path.join(root, "fresh", "new", "deep.sqlite"));
  } finally {
    fs.rmSync(temp, { recursive: true, force: true });
  }
});


test("KBA pack builder pins the public licence, exact labels and DE aggregate-only boundary", () => {
  const builder = read("scripts/build_kba_de_vag_stock_research_pack.py");
  assert.match(builder, /DL-DE-BY-2\.0/);
  assert.match(builder, /approved_by_published_DL_DE_BY_2_0/);
  assert.match(builder, /EXACT_LABELS/);
  assert.match(builder, /source_record_sha256/);
  assert.match(builder, /research_pack_ingested/);
  assert.match(builder, /product_database_ingested/);
  assert.match(builder, /exact_engine_gearbox_pair/);
  assert.match(builder, /ru_eaeu_applicability/);
  assert.match(builder, /source-row SHA-256/);
  assert.match(builder, /temporal_coverage_observed/);
  assert.match(builder, /source_csv\.stat\(\)\.st_size/);
});

test("KBA desktop integration verifies pack hashes and keeps it out of production fitment", () => {
  const integration = read("scripts/integrate-kba-de-vag-stock-research-pack.cjs");
  assert.match(integration, /source_manifest_sha256/);
  assert.match(integration, /source_snapshot_sha256/);
  assert.match(integration, /database_sha256/);
  assert.match(integration, /source_run_id/);
  assert.match(integration, /market_scope: \["DE"\]/);
  assert.match(integration, /product_import_allowed: false/);
  assert.match(integration, /research_pack_ingested: true/);
  assert.match(integration, /product_database_ingested: false/);
  assert.match(integration, /exact_engine_gearbox_pair: false/);
  assert.match(integration, /source_snapshot_csv_in_desktop: false/);
  assert.match(integration, /kba-de-stock-research-db\.cjs/);
  assert.match(integration, /kba-de-summary/);
  assert.match(integration, /Typschlüssel/);
  assert.match(integration, /not confirmed TSN|не подтверждённая TSN/);
});

test("KBA desktop integration composes after the ASTRA TARGA and RDW research tabs", () => {
  const integration = read("scripts/integrate-kba-de-vag-stock-research-pack.cjs");
  assert.match(integration, /datasetAnchors = \[/);
  assert.match(integration, /"astra" \| "astra-targa" \| "rdw"/);
  assert.match(integration, /"astra" \| "rdw"/);
  assert.match(integration, /placeholderAnchors = \[/);
  assert.match(integration, /dataset === "astra-targa"/);
  assert.match(integration, /dataset === "kba-de"/);
});

test("KBA runtime reader is read-only and verifies the source/DB licence chain", () => {
  const reader = read("desktop/kba-de-stock-research-db.cjs");
  assert.match(reader, /new DatabaseSync\(file, \{ readOnly: true \}\)/);
  assert.match(reader, /PRAGMA integrity_check/);
  assert.match(reader, /source_manifest_sha256/);
  assert.match(reader, /source_snapshot_sha256/);
  assert.match(reader, /DL-DE-BY-2\.0/);
  assert.match(reader, /marketScope: "DE"/);
  assert.match(reader, /exactEngineGearboxPair: false/);
  assert.match(reader, /ruEaeuApplicability: false/);
  assert.match(reader, /searchKbaStock/);

  const verifier = read("desktop/scripts/verify-kba-de-stock-research-pack.cjs");
  assert.ok(verifier.includes('require("../lib/kba-de-stock-research-db.cjs")'));
  assert.ok(!verifier.includes('require("../kba-de-stock-research-db.cjs")'));
});

test("KBA research verifier registers the thirteenth isolated pack after TARGA and RDW", () => {
  const patch = read("scripts/apply-kba-de-vag-research-verification-run1.cjs");
  assert.ok(patch.includes("/manifest\\.packs\\.length === (\\d+)/g"));
  assert.ok(patch.includes("expectedPackCount = currentPackCount + 1"));
  assert.match(patch, /rdw-vag-nl-eu-type-approval-research/);
  assert.match(patch, /rdwCountAssertion/);
  assert.match(patch, /rdwBinding/);
  assert.match(patch, /kbaBinding/);
  assert.match(patch, /kba-de-vag-stock-research/);
  assert.match(patch, /kbaDeSummary\.marketScope === "DE"/);
  assert.match(patch, /researchPackIngested === true/);
  assert.match(patch, /productDatabaseIngested === false/);
  assert.match(patch, /productDatabaseIngested: false,\\n\s+productionImport/);
  assert.match(patch, /vagStockObservations === 264847/);
  assert.match(patch, /exactEngineGearboxPair === false/);
  assert.match(patch, /ruEaeuApplicability === false/);
});

test("KBA verifier patch accepts the RDW revision, appends its reader before assertions, and is idempotent", () => {
  const temp = fs.mkdtempSync(path.join(os.tmpdir(), "vag-kba-verifier-patch-"));
  try {
    const desktopRoot = path.join(temp, "desktop-source");
    const scriptsDir = path.join(desktopRoot, "scripts");
    const testsDir = path.join(desktopRoot, "tests");
    fs.mkdirSync(scriptsDir, { recursive: true });
    fs.mkdirSync(testsDir, { recursive: true });
    const rdwCountAssertion = '  assert(rdwSummary.counts.approvalScopes === 96519 && rdwSummary.counts.registrationObservations === 102662 && rdwSummary.counts.engineDesignationCandidates === 93836 && rdwSummary.counts.gearboxClassifications === 93548 && rdwSummary.counts.sourceRows === 604785 && rdwSummary.sourceSnapshotSha256 === "896a34b9b8377f2ed20c34d7e0e33b4cf2ce1958e2cdd2b7326ee8c3157b0706" && rdwSummary.databaseSha256 === rdw.database_sha256 && rdwSummary.sourceManifestSha256 === rdw.source_manifest_sha256, "RDW snapshot, database or source manifest provenance/counts changed");';
    const verifier = [
      'const assert = require("node:assert/strict");',
      'const path = require("node:path");',
      'const ROOT = __dirname;',
      'function verify() {',
      '  const manifest = { schema_version: 1, packs: Array.from({ length: 12 }, (_, index) => ({ id: "pack-" + index })) };',
      '  assert(manifest.schema_version === 1 && Array.isArray(manifest.packs) && manifest.packs.length === 12, "Expected 12 separately licensed research packs, including the NL-only RDW approval research pack");',
      '  const packIds = manifest.packs.map((pack) => pack.id);',
      '  assert(packIds.every((id) => typeof id === "string" && id.length > 0) && new Set(packIds).size === packIds.length, "Research pack IDs must be non-empty and unique");',
      '  const byId = Object.fromEntries(manifest.packs.map((pack) => [pack.id, pack]));',
      '  const ob = byId["ob"]; const vag = byId["vag"]; const obdb = byId["obdb"]; const vehiclesdb = byId["vehiclesdb"]; const mechanicdb = byId["mechanicdb"]; const wikidata = byId["wikidata"];',
      '  const astra = byId["astra-fedro-tas-type-approvals-open-data-ch"];',
      '  const targa = byId["astra-fedro-targa-emissionen-approval-variants-ch"];',
      '  const rdw = byId["rdw-vag-nl-eu-type-approval-research"];',
      '  assert(wikidataGenerations, "Wikidata generation candidate pack must be registered");',
      '  assert(ob && vag && obdb && vehiclesdb && mechanicdb && wikidata && astra && targa && rdw, "Required generic, candidate, CH-only ASTRA TAS/TARGA and NL-only RDW packs must be registered");',
      rdwCountAssertion,
      '  return {',
      '    rdw_nl_eu: {',
      '      marketScope: rdwSummary.marketScope,',
      '      approvalScopes: rdwSummary.counts.approvalScopes,',
      '      registrationObservations: rdwSummary.counts.registrationObservations,',
      '      engineDesignationCandidates: rdwSummary.counts.engineDesignationCandidates,',
      '      gearboxClassifications: rdwSummary.counts.gearboxClassifications,',
      '      sourceRows: rdwSummary.counts.sourceRows,',
      '      sourceFiles: rdwSummary.counts.sourceFiles,',
      '      productionImport: rdwSummary.productionImport,',
      '      ruEaeuApplicability: rdwSummary.ruEaeuApplicability,',
      '      exactVehicleFitment: rdwSummary.exactVehicleFitment,',
      '      exactEngineGearboxPair: rdwSummary.exactEngineGearboxPair,',
      '      repairApplicability: rdwSummary.repairApplicability,',
      '      diagnosticExecutionAllowed: rdwSummary.diagnosticExecutionAllowed,',
      '      sourceSnapshotSha256: rdwSummary.sourceSnapshotSha256,',
      '      sourceManifestSha256: rdwSummary.sourceManifestSha256,',
      '      databaseSha256: rdwSummary.databaseSha256,',
      '    },',
      '      production_fitment_rows_added: 0,',
      '  };',
      '}',
      ''
    ].join("\n");
    const testSource = [
      'const assert = require("node:assert/strict");',
      'function testResult(result) {',
      '  assert.match(result.rdw_nl_eu.sourceManifestSha256, /^[a-f0-9]{64}$/);',
      '  assert.match(result.rdw_nl_eu.databaseSha256, /^[a-f0-9]{64}$/);',
      '  assert.equal(result.mechanicdb_vag_dtc_candidates.displayStatus, "candidate_reference_visible_separate_namespace");',
      '}',
      ''
    ].join("\n");
    fs.writeFileSync(path.join(scriptsDir, "verify-local-research-packs.cjs"), verifier, "utf8");
    fs.writeFileSync(path.join(testsDir, "local-research-packs.test.cjs"), testSource, "utf8");
    const patch = require("../scripts/apply-kba-de-vag-research-verification-run1.cjs").patch;
    const result = patch(desktopRoot);
    assert.equal(result.manifestPackCount, 13);
    const patchedVerifier = fs.readFileSync(path.join(scriptsDir, "verify-local-research-packs.cjs"), "utf8");
    const patchedTest = fs.readFileSync(path.join(testsDir, "local-research-packs.test.cjs"), "utf8");
    assert.match(patchedVerifier, /manifest\.packs\.length === 13/);
    assert.match(patchedVerifier, /const kbaDe = byId\["kba-de-vag-stock-research"\]/);
    assert.match(patchedVerifier, /&& rdw && kbaDe,/);
    assert.ok(patchedVerifier.indexOf("const kbaDeSummary =") < patchedVerifier.indexOf("assert(kbaDeSummary.id ==="));
    assert.match(patchedVerifier, /kba_de_vag_stock:/);
    assert.match(patchedTest, /result\.kba_de_vag_stock/);
    const second = patch(desktopRoot);
    assert.equal(second.manifestPackCount, 13);
    assert.equal(fs.readFileSync(path.join(scriptsDir, "verify-local-research-packs.cjs"), "utf8"), patchedVerifier);
  } finally {
    fs.rmSync(temp, { recursive: true, force: true });
  }
});

test("KBA workflow builds the research pack on Windows and retains source snapshot provenance", () => {
  const workflow = read(".github/workflows/build-kba-de-vag-stock-research-pack.yml");
  assert.match(workflow, /runs-on: windows-2025/);
  assert.match(workflow, /build_kba_de_vag_stock_research_pack\.py/);
  assert.match(workflow, /source-download\.csv/);
  assert.match(workflow, /kba-de-vag-stock-research-pack/);
  assert.match(workflow, /retention-days: 90/);
  assert.match(workflow, /exact_engine_gearbox_pair/);
});

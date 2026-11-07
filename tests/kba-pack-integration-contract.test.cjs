"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { safeJoin } = require("../scripts/integrate-kba-de-vag-stock-research-pack.cjs");

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

test("KBA research verifier registers a twelfth isolated pack and checks its counts", () => {
  const patch = read("scripts/apply-kba-de-vag-research-verification-run1.cjs");
  assert.match(patch, /manifest\.packs\.length === 12/);
  assert.match(patch, /kba-de-vag-stock-research/);
  assert.match(patch, /kbaDeSummary\.marketScope === "DE"/);
  assert.match(patch, /researchPackIngested === true/);
  assert.match(patch, /productDatabaseIngested === false/);
  assert.match(patch, /productDatabaseIngested: false,\\n\\s+productionImport/);
  assert.match(patch, /vagStockObservations === 264847/);
  assert.match(patch, /exactEngineGearboxPair === false/);
  assert.match(patch, /ruEaeuApplicability === false/);
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

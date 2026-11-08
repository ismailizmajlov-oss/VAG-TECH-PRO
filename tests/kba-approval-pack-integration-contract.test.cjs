"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { safeJoin } = require("../scripts/integrate-kba-de-approval-research-pack.cjs");

const ROOT = path.join(__dirname, "..");
function read(relative) { return fs.readFileSync(path.join(ROOT, relative), "utf8"); }

test("KBA approval integration path guard rejects traversal and symlinked ancestors", (t) => {
  const temp = fs.mkdtempSync(path.join(os.tmpdir(), "vag-kba-approval-path-"));
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
      if (process.platform === "win32" && ["EPERM","EACCES","ENOTSUP"].includes(error.code)) {
        t.skip("Windows runner does not permit creating a directory junction");
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

test("KBA approval integration pins the published licence, source revision, XLSX and SQLite hashes", () => {
  const integration = read("scripts/integrate-kba-de-approval-research-pack.cjs");
  assert.match(integration, /DL-DE-BY-2\.0/);
  assert.match(integration, /approved_by_published_DL_DE_BY_2_0/);
  assert.match(integration, /source_manifest_sha256/);
  assert.match(integration, /source_snapshot_sha256/);
  assert.match(integration, /database_sha256/);
  assert.match(integration, /source_record_sha256/);
  assert.match(integration, /source-snapshot\.xlsx/);
  assert.match(integration, /research_pack_ingested: true/);
  assert.match(integration, /product_database_ingested: false/);
  assert.match(integration, /product_import_allowed: false/);
  assert.match(integration, /ru_eaeu_applicability: false/);
  assert.match(integration, /exact_engine_gearbox_pair: false/);
  assert.match(integration, /refusing to replace existing build data/);
});

test("KBA approval SQLite reader is read-only and fails closed on scope or provenance changes", () => {
  const reader = read("desktop/kba-de-approval-research-db.cjs");
  assert.match(reader, /new DatabaseSync\(file, \{ readOnly: true \}\)/);
  assert.match(reader, /PRAGMA integrity_check/);
  assert.match(reader, /source_record_sha256/);
  assert.match(reader, /source_manifest_sha256/);
  assert.match(reader, /DL-DE-BY-2\.0/);
  assert.match(reader, /marketScope: "DE"/);
  assert.match(reader, /type_approval_document_metadata_only/);
  assert.match(reader, /exactEngineGearboxPair: false/);
  assert.match(reader, /ruEaeuApplicability: false/);
  assert.match(reader, /searchKbaApprovals/);
  assert.match(reader, /source_file_included_in_desktop === true/);
  assert.match(reader, /model_year IS NOT NULL/);
  assert.match(reader, /gearbox_code IS NOT NULL/);
});

test("KBA approval desktop integration exposes a separate metadata-only tab and offline lifecycle check", () => {
  const integration = read("scripts/integrate-kba-de-approval-research-pack.cjs");
  assert.match(integration, /kba-de-approvals-summary/);
  assert.match(integration, /dataset === "kba-de-approvals"/);
  assert.match(integration, /type_approval_document_metadata_only/);
  assert.match(integration, /Дата одобрения · не модельный год/);
  assert.match(integration, /sourceRecordSha256/);
  assert.match(integration, /exactEngineGearboxPair/);
  assert.match(integration, /ruEaeuApplicability/);
  assert.match(integration, /KBA DE type-approval metadata search passed/);
  assert.match(integration, /KBA · DE approvals/);
  assert.match(integration, /manufacturerLabelMappingStatus/);
  assert.doesNotMatch(integration, /KBA · ОТТС DE/);
});

test("KBA approval verifier patch is included as a separate idempotent run", () => {
  const patch = read("scripts/apply-kba-de-approval-research-verification-run1.cjs");
  assert.match(patch, /manifest\.packs\.length === 14/);
  assert.match(patch, /kba-de-vag-type-approval-research/);
  assert.match(patch, /getKbaApprovalSummary/);
  assert.match(patch, /approvalRecords === 918/);
  assert.match(patch, /kba_de_vag_approvals:/);
  assert.match(patch, /Expected 14 separately licensed research packs/);
});

test("KBA approval pack builder publishes a reusable, attributed DE-only research artifact", () => {
  const workflow = read(".github/workflows/build-kba-de-vag-approval-research-pack.yml");
  assert.match(workflow, /runs-on: windows-2025/);
  assert.match(workflow, /build_kba_de_vag_approval_research_pack\.py/);
  const builder = read("scripts/build_kba_de_vag_approval_research_pack.py");
  assert.match(builder, /kba-de-vag-approvals\.sqlite/);
  assert.match(workflow, /RIGHTS-EVIDENCE\.json/);
  assert.match(workflow, /retention-days: 90/);
});

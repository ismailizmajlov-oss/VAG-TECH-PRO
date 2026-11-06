"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const path = require("node:path");
const { getAstraSummary, searchAstraApprovals } = require("../lib/astra-ch-tas-db.cjs");
const root = process.env.VAG_TECH_PRO_RESEARCH_DIR || path.resolve(__dirname, "../data/research");

test("ASTRA CH pack verifies rights, provenance, SQLite integrity and manifest counts", () => {
  const summary = getAstraSummary(root);
  assert.equal(summary.marketScope, "CH");
  assert.equal(summary.rightsStatus, "approved_by_published_ogd_terms");
  assert.equal(summary.productionImport, false);
  assert.equal(summary.ruEaeuApplicability, false);
  assert.equal(summary.exactVehicleFitment, false);
  assert.equal(summary.repairApplicability, false);
  assert.equal(summary.diagnosticExecutionAllowed, false);
  assert.ok(summary.counts.approvals > 0);
  assert.ok(summary.counts.emissionsGearboxRows > 0);
  assert.equal(summary.counts.linkedScopeRows, summary.counts.exactScopeLinks + summary.counts.wildcardScopeLinks);
  assert.equal(summary.counts.emissionsGearboxRows, summary.counts.linkedScopeRows + summary.counts.unlinkedScopeRows);
  assert.match(summary.attributionText, /Federal Roads Office/);
  assert.match(summary.databaseSha256, /^[a-f0-9]{64}$/);
});

test("ASTRA search keeps approval engine designation, stamped marking and Swiss gearbox class separate", () => {
  const rows = searchAstraApprovals("1XZ904", 10, root);
  const row = rows.find((item) => item.make === "CUPRA" && item.engineTypeDesignation === "DNPA");
  assert.ok(row, "expected pinned 1XZ904 CUPRA sample");
  assert.equal(row.stampedEngineMarking, "DNP");
  assert.equal(row.gearboxClass, "m7a");
  assert.equal(row.gearboxVersionScope, "CXDNPAX0/*");
  assert.equal(row.relationPrecision, "approval_variant_wildcard");
  assert.equal(row.marketScope, "CH");
  assert.equal(row.engineCode, null);
  assert.equal(row.gearboxCode, null);
  assert.equal(row.factoryVagEngineCodeClaim, false);
  assert.equal(row.factoryVagGearboxCodeClaim, false);
  assert.equal(row.productionFitmentClaim, false);
  assert.equal(row.repairApplicability, false);
  assert.equal(row.diagnosticExecutionAllowed, false);
  assert.match(row.warning, /не код КПП VAG/);
  assert.ok(new URL(row.sourceUrl).hostname === "astra.admin.ch" || new URL(row.sourceUrl).hostname.endsWith(".astra.admin.ch"));
});

test("ASTRA search supports engine and gearbox-class lookup without widening market", () => {
  assert.ok(searchAstraApprovals("DNPA", 10, root).some((row) => row.engineTypeDesignation === "DNPA" && row.marketScope === "CH"));
  const rows = searchAstraApprovals("m7a", 10, root);
  assert.ok(rows.length > 0);
  assert.ok(rows.every((row) => row.marketScope === "CH" && row.gearboxCode === null));
  assert.equal(searchAstraApprovals("1XZ904", 1, root).length, 1);
});

test("ASTRA search rejects invalid query lengths", () => {
  assert.throws(() => searchAstraApprovals("A", 10, root), /минимум два символа/);
  assert.throws(() => searchAstraApprovals("x".repeat(101), 10, root), /длинный/);
});

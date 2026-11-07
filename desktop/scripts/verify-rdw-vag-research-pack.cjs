"use strict";

const assert = require("node:assert/strict");
const path = require("node:path");
const rdw = require("../lib/rdw-vag-research-db.cjs");

const root = process.argv[2] ? path.resolve(process.argv[2]) : path.join(process.cwd(), "data", "research");
const summary = rdw.getRdwSummary(root);
const rows = rdw.searchRdwApprovals("e1*2018/858*00403*07", 50, root);
const sample = rows.find((item) =>
  item.typeApprovalNumber === "e1*2018/858*00403*07" &&
  item.variant === "ACDUCAX0" &&
  item.version === "FD6FD6DD002PR4VNB50OO" &&
  item.revision === "0"
);
assert.ok(sample, "RDW offline verification sample was not found");
assert.ok(sample.engineDesignationCandidates.some((item) => item.engineDesignation === "DUC"));
assert.ok(sample.gearboxClassifications.some((item) => item.gearboxTypeClassification === "A"));
assert.equal(sample.exactEngineGearboxPair, false);
assert.equal(sample.ruEaeuApplicability, false);
assert.equal(summary.productionImport, false);
assert.equal(summary.marketScope, "NL");
console.log(JSON.stringify({ status: "verified_research_only", summary, sample }, null, 2));

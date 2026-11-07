"use strict";

const { getCardirSummary } = require("../cardir-vag-reference-facts-db.cjs");

try {
  const summary = getCardirSummary(process.argv[2]);
  if (summary.counts.vagFacts !== 773 || summary.counts.vagModels !== 24 || summary.counts.vagBrands !== 4 || summary.counts.parameterKeys !== 19) {
    throw new Error("CarDir research pack counts do not match the pinned snapshot.");
  }
  process.stdout.write(JSON.stringify({
    status: "verified_research_only",
    packId: summary.packId,
    counts: summary.counts,
    marketScope: summary.marketScope,
    rightsStatus: summary.rightsStatus,
    databaseSha256: summary.databaseSha256,
    sourceSnapshotSha256: summary.sourceSnapshotSha256,
    sourceManifestSha256: summary.sourceManifestSha256,
    productionImport: false,
    productImportAllowed: false,
    ruEaeuApplicability: false,
    exactEngineGearboxPair: false
  }, null, 2) + "\n");
} catch (error) {
  process.stderr.write((error.stack || error.message) + "\n");
  process.exitCode = 1;
}

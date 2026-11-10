"use strict";

const { getOwnerSpecsSummary } = require("../lib/ownerspecs-vag-research-db.cjs");

try {
  const summary = getOwnerSpecsSummary(process.argv[2]);
  if (summary.counts.vagGenerations !== 20 || summary.counts.vagFacts !== 233 ||
      summary.counts.sourceGenerations !== 111 || summary.counts.sourceFacts !== 2369 ||
      summary.marketScope !== "UNKNOWN" || summary.productionImport !== false ||
      summary.productImportAllowed !== false || summary.criticalTechnicalValuesPublishable !== false ||
      summary.exactEngineGearboxPair !== false || summary.ruEaeuApplicability !== false) {
    throw new Error("OwnerSpecs research pack counts or candidate-only boundary mismatch");
  }
  process.stdout.write(JSON.stringify({
    status: "verified_research_only", packId: summary.packId, counts: summary.counts,
    marketScope: summary.marketScope, rightsStatus: summary.rightsStatus,
    databaseSha256: summary.databaseSha256, sourceSnapshotSha256: summary.sourceSnapshotSha256,
    sourceManifestSha256: summary.sourceManifestSha256, productionImport: false,
    productImportAllowed: false, criticalTechnicalValuesPublishable: false,
    exactEngineGearboxPair: false, ruEaeuApplicability: false
  }, null, 2) + "\n");
} catch (error) {
  process.stderr.write((error.stack || error.message) + "\n");
  process.exitCode = 1;
}

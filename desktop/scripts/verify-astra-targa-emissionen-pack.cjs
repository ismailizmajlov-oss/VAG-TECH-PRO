"use strict";
const { getAstraTargaSummary, searchAstraTargaRows } = require("../lib/astra-targa-emissionen-db.cjs");
const summary = getAstraTargaSummary();
if (summary.marketScope !== "CH" || summary.productionImport !== false || summary.productImportAllowed !== false ||
    summary.ruEaeuApplicability !== false || summary.exactVagFactoryCodePair !== false ||
    summary.counts.approvalPowertrainVariantRows !== 53240 || summary.counts.exactVagFactoryCodePairRows !== 0) {
  throw new Error("ASTRA TARGA pack failed its research-only verification contract.");
}
const rows = searchAstraTargaRows("1AB701", 10);
if (!rows.some((row) => row.approvalNumber === "1AB701" && row.engineType === "AEL" && row.gearboxClassification === "m6" &&
    row.marketScope === "CH" && row.sourceDefinedVariantLink === true && row.exactVagFactoryCodePair === false &&
    row.ruEaeuApplicability === false)) {
  throw new Error("ASTRA TARGA source-row lookup failed or was promoted to OEM fitment.");
}
process.stdout.write(JSON.stringify({ status: "verified_research_only", pack_id: summary.id, counts: summary.counts, database_sha256: summary.databaseSha256 }) + "\n");

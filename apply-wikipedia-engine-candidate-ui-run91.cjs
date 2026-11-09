"use strict";

const fs = require("node:fs");
const path = require("node:path");

function fail(message) { throw new Error(message); }
function copyRegular(source, target) {
  const stat = fs.lstatSync(source);
  if (!stat.isFile() || stat.isSymbolicLink()) fail("Patch input must be a regular file: " + source);
  fs.mkdirSync(path.dirname(target), { recursive: true });
  fs.copyFileSync(source, target);
  if (fs.readFileSync(source).length !== fs.readFileSync(target).length) fail("Copied patch input size mismatch: " + target);
}
function replaceExactly(source, before, after, label) {
  if (source.includes(after)) return source;
  const first = source.indexOf(before);
  if (first < 0 || source.indexOf(before, first + before.length) >= 0) {
    fail("Expected exactly one patch anchor for " + label);
  }
  return source.slice(0, first) + after + source.slice(first + before.length);
}
function parseArgs(argv) {
  const result = {};
  for (let index = 0; index < argv.length; index += 1) {
    const key = argv[index];
    if (key !== "--desktop-root") fail("Unknown argument: " + key);
    if (!argv[index + 1] || argv[index + 1].startsWith("--")) fail("--desktop-root requires a value");
    result.desktopRoot = path.resolve(argv[++index]);
  }
  if (!result.desktopRoot) fail("--desktop-root is required");
  return result;
}
function main() {
  const args = parseArgs(process.argv.slice(2));
  const desktopRoot = args.desktopRoot;
  const repoRoot = __dirname;
  const files = [
    ["wikipedia-engine-candidates-db-run91.cjs", "lib/wikipedia-engine-candidates-db.cjs"],
    ["wikipedia-engine-candidates-route-run91.ts", "app/api/wikipedia-engine-candidates/route.ts"],
    ["wikipedia-engine-candidates-ui-run91.tsx", "components/wikipedia-engine-candidates.tsx"],
    ["wikipedia-engine-candidates-db-run91.test.cjs", "tests/wikipedia-engine-candidates-db.test.cjs"],
    ["wikipedia-engine-candidates-ui-run91.test.cjs", "tests/wikipedia-engine-candidates-ui.test.cjs"],
  ];
  for (const [sourceRelative, targetRelative] of files) {
    copyRegular(path.join(repoRoot, sourceRelative), path.join(desktopRoot, targetRelative));
  }

  const catalogPath = path.join(desktopRoot, "components", "local-research-catalog.tsx");
  let catalog = fs.readFileSync(catalogPath, "utf8");
  catalog = replaceExactly(
    catalog,
    'import type { ChangeEvent, FormEvent } from "react";',
    'import type { ChangeEvent, FormEvent } from "react";\nimport WikipediaEngineCandidates from "./wikipedia-engine-candidates";',
    "Wikipedia candidate component import",
  );
  catalog = replaceExactly(
    '    <div className="research-tabs" role="tablist" aria-label="Локальные наборы данных">',
    '    <details className="research-details research-wikipedia-candidates">\n' +
      '      <summary>Открытая таксономия кодов двигателей VAG · Wikipedia · 241 кандидат · CC BY-SA 4.0</summary>\n' +
      '      <WikipediaEngineCandidates />\n' +
      '    </details>\n\n' +
      '    <div className="research-tabs" role="tablist" aria-label="Локальные наборы данных">',
    "Wikipedia candidate research section",
  );
  fs.writeFileSync(catalogPath, catalog, "utf8");

  const packagePath = path.join(desktopRoot, "package.json");
  const packageJson = JSON.parse(fs.readFileSync(packagePath, "utf8"));
  const researchScript = packageJson.scripts?.["test:research"];
  if (typeof researchScript !== "string") fail("Desktop package.json has no test:research script");
  const tests = [
    "tests/wikipedia-engine-candidates-db.test.cjs",
    "tests/wikipedia-engine-candidates-ui.test.cjs",
  ];
  let nextScript = researchScript;
  for (const testFile of tests) {
    if (!nextScript.includes(testFile)) nextScript += " " + testFile;
  }
  packageJson.scripts["test:research"] = nextScript;
  fs.writeFileSync(packagePath, JSON.stringify(packageJson, null, 2) + "\n", "utf8");

  const researchRoot = path.join(desktopRoot, "data", "research");
  const reader = require(path.join(desktopRoot, "lib", "wikipedia-engine-candidates-db.cjs"));
  const summary = reader.getSummary(researchRoot);
  if (summary.counts.candidateRows !== 241 || summary.counts.uniqueCandidateCodes !== 241 ||
      summary.marketScope !== "UNKNOWN" || summary.productImportAllowed !== false ||
      summary.repairUseAllowed !== false || summary.diagnosticExecutionAllowed !== false) {
    fail("Wikipedia candidate pack failed the desktop integration boundary");
  }
  const evidence = {
    pack_id: summary.packId,
    database_sha256: summary.databaseSha256,
    source_manifest_sha256: summary.sourceManifestSha256,
    source_snapshot_sha256: summary.sourceSnapshotSha256,
    source_artifact_sha256: summary.sourceArtifactSha256,
    candidate_rows: summary.counts.candidateRows,
    unique_candidate_codes: summary.counts.uniqueCandidateCodes,
    source_documents: summary.counts.sourceDocuments,
    source_rows_with_codes: summary.counts.sourceRowsWithCodes,
    market_scope: summary.marketScope,
    applicability_precision: summary.applicabilityPrecision,
    product_import_allowed: summary.productImportAllowed,
    repair_use_allowed: summary.repairUseAllowed,
    diagnostic_execution_allowed: summary.diagnosticExecutionAllowed,
  };
  fs.writeFileSync(path.join(desktopRoot, "wikipedia-engine-candidates-run91-verification.json"), JSON.stringify(evidence, null, 2) + "\n", "utf8");

  const patchTarget = path.join(desktopRoot, "scripts", "patches", "apply-wikipedia-engine-candidate-ui-run91.cjs");
  copyRegular(__filename, patchTarget);
  process.stdout.write(JSON.stringify({ status: "integrated_candidate_only", ...evidence }) + "\n");
}

if (require.main === module) {
  try { main(); }
  catch (error) {
    process.stderr.write(String(error?.stack || error) + "\n");
    process.exitCode = 1;
  }
}

module.exports = { main, replaceExactly };

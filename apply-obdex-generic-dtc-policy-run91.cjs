#!/usr/bin/env node
"use strict";

const fs = require("node:fs");
const path = require("node:path");
const crypto = require("node:crypto");

const MARKER = "// run91: enforce canonical generic SAE/ISO DTC namespace policy";
const EXPECTED_POLICY_ID = "vag-tech-pro-dtc-namespace-ranges";
const EXPECTED_POLICY_REVISION = "run87-2026-11-08";
const EXPECTED_ALLOWED_PATTERN = "^(?:P0[0-9A-F]{3}|P2[0-9A-F]{3}|B0[0-9A-F]{3}|C0[0-9A-F]{3}|U0[0-9A-F]{3})$";
const EXPECTED_UNRESOLVED_PATTERN = "^(?:P3[4-9][0-9A-F]{2}|U3[0-9A-F]{3}|B3[0-9A-F]{3}|C3[0-9A-F]{3})$";

function fail(message) { throw new Error(message); }
function sha256(bytes) { return crypto.createHash("sha256").update(bytes).digest("hex"); }
function read(file) { return fs.readFileSync(file, "utf8"); }
function write(file, value) { fs.writeFileSync(file, value, "utf8"); }
function replaceOnce(source, oldValue, newValue, label) {
  const first = source.indexOf(oldValue);
  if (first < 0 || source.indexOf(oldValue, first + oldValue.length) >= 0) {
    fail(label + ": expected one exact source anchor");
  }
  return source.slice(0, first) + newValue + source.slice(first + oldValue.length);
}
function parseArgs() {
  const args = process.argv.slice(2);
  const index = args.indexOf("--desktop-root");
  if (index < 0 || !args[index + 1]) fail("Usage: node apply-obdex-generic-dtc-policy-run91.cjs --desktop-root <path>");
  return path.resolve(args[index + 1]);
}
function loadCanonicalPolicy() {
  const source = path.join(__dirname, "data", "policies", "dtc-namespace-ranges.json");
  const stat = fs.lstatSync(source);
  if (!stat.isFile() || stat.isSymbolicLink()) fail("Canonical DTC namespace policy must be a regular file");
  const bytes = fs.readFileSync(source);
  const policy = JSON.parse(bytes.toString("utf8"));
  if (policy.schema_version !== 1 || policy.policy_id !== EXPECTED_POLICY_ID || policy.policy_revision !== EXPECTED_POLICY_REVISION) {
    fail("Canonical DTC namespace policy identity/revision mismatch");
  }
  if (policy.namespaces?.generic_sae_iso?.pattern !== EXPECTED_ALLOWED_PATTERN ||
      policy.namespaces?.unresolved_reserved?.pattern !== EXPECTED_UNRESOLVED_PATTERN) {
    fail("Canonical DTC namespace patterns changed without a reviewed patch");
  }
  return { source, bytes, policy, sha256: sha256(bytes) };
}
function installPolicy(desktopRoot, canonical) {
  const dataRoot = path.join(desktopRoot, "data");
  const targetDir = path.join(dataRoot, "policies");
  const target = path.join(targetDir, "dtc-namespace-ranges.json");
  fs.mkdirSync(targetDir, { recursive: true });
  if (fs.existsSync(target)) {
    const stat = fs.lstatSync(target);
    if (!stat.isFile() || stat.isSymbolicLink()) fail("Desktop DTC namespace policy target is not a regular file");
  }
  write(target, canonical.bytes);
  if (sha256(fs.readFileSync(target)) !== canonical.sha256) fail("Desktop DTC namespace policy copy hash mismatch");
  return target;
}
function patchResearchDb(file) {
  let source = read(file);
  if (source.includes(MARKER)) {
    for (const token of ["function loadDtcNamespacePolicy", "function genericDtcCountsFromDb", "dtcsQuarantined", "namespacePolicyRevision", "dtcPredicates.allowedSql"]) {
      if (!source.includes(token)) fail("Run91 marker exists but required database policy code is incomplete: " + token);
    }
    return { changed: false, source };
  }
  const helper = [
    MARKER,
    "const RUN91_GENERIC_DTC_ALLOWED_SQL = [",
    "  \"code GLOB 'P0[0-9A-F][0-9A-F][0-9A-F]'\",",
    "  \"code GLOB 'P2[0-9A-F][0-9A-F][0-9A-F]'\",",
    "  \"code GLOB 'B0[0-9A-F][0-9A-F][0-9A-F]'\",",
    "  \"code GLOB 'C0[0-9A-F][0-9A-F][0-9A-F]'\",",
    "  \"code GLOB 'U0[0-9A-F][0-9A-F][0-9A-F]'\",",
    "].join(\" OR \");",
    "const RUN91_UNRESOLVED_DTC_SQL = [",
    "  \"code GLOB 'P3[4-9][0-9A-F][0-9A-F]'\",",
    "  \"code GLOB 'U3[0-9A-F][0-9A-F][0-9A-F]'\",",
    "  \"code GLOB 'B3[0-9A-F][0-9A-F][0-9A-F]'\",",
    "  \"code GLOB 'C3[0-9A-F][0-9A-F][0-9A-F]'\",",
    "].join(\" OR \");",
    "function loadDtcNamespacePolicy(root) {",
    "  const researchRoot = getResearchRoot(root);",
    "  const dataRoot = path.resolve(researchRoot, \"..\");",
    "  const dataRootReal = fs.realpathSync(dataRoot);",
    "  const policyPath = path.join(dataRootReal, \"policies\", \"dtc-namespace-ranges.json\");",
    "  const stat = fs.lstatSync(policyPath);",
    "  if (!stat.isFile() || stat.isSymbolicLink()) throw new Error(\"DTC namespace policy must be a regular file\");",
    "  const realPath = fs.realpathSync(policyPath);",
    "  const relative = path.relative(dataRootReal, realPath);",
    "  if (!relative || relative.startsWith(\"..\") || path.isAbsolute(relative)) throw new Error(\"DTC namespace policy path escaped the local data root\");",
    "  const policy = JSON.parse(fs.readFileSync(realPath, \"utf8\"));",
    "  if (policy.schema_version !== 1 || policy.policy_id !== \"vag-tech-pro-dtc-namespace-ranges\" || policy.policy_revision !== \"run87-2026-11-08\") {",
    "    throw new Error(\"DTC namespace policy identity/revision mismatch\");",
    "  }",
    "  if (policy.namespaces?.generic_sae_iso?.pattern !== \"^(?:P0[0-9A-F]{3}|P2[0-9A-F]{3}|B0[0-9A-F]{3}|C0[0-9A-F]{3}|U0[0-9A-F]{3})$\" ||",
    "      policy.namespaces?.unresolved_reserved?.pattern !== \"^(?:P3[4-9][0-9A-F]{2}|U3[0-9A-F]{3}|B3[0-9A-F]{3}|C3[0-9A-F]{3})$\") {",
    "    throw new Error(\"DTC namespace policy patterns changed without a reviewed desktop patch\");",
    "  }",
    "  return policy;",
    "}",
    "function getDtcNamespaceSqlPredicates(policy) {",
    "  if (policy?.policy_id !== \"vag-tech-pro-dtc-namespace-ranges\" || policy?.policy_revision !== \"run87-2026-11-08\") {",
    "    throw new Error(\"DTC namespace policy is not approved for generic search\");",
    "  }",
    "  return {",
    "    allowedSql: RUN91_GENERIC_DTC_ALLOWED_SQL,",
    "    unresolvedSql: RUN91_UNRESOLVED_DTC_SQL,",
    "    allowedRanges: [\"P0xxx\", \"P2xxx\", \"B0xxx\", \"C0xxx\", \"U0xxx\"],",
    "    unresolvedRanges: [\"P34xx-P39xx\", \"U3xxx\", \"B3xxx\", \"C3xxx\"],",
    "  };",
    "}",
    "function genericDtcCountsFromDb(db, policy) {",
    "  const predicates = getDtcNamespaceSqlPredicates(policy);",
    "  const base = \"verification_status='source_imported_unreviewed' AND vehicle_fitment_claim=0 AND namespace='generic_sae_iso_obd2'\";",
    "  const count = (extra) => db.prepare(\"SELECT count(*) AS n FROM generic_dtc_research WHERE \" + base + (extra ? \" AND (\" + extra + \")\" : \"\")).get().n;",
    "  const sourceRows = count(\"\");",
    "  const searchable = count(predicates.allowedSql);",
    "  const quarantined = count(predicates.unresolvedSql);",
    "  const unclassified = sourceRows - searchable - quarantined;",
    "  if (unclassified !== 0) throw new Error(\"OBDex contains generic-labelled DTC rows outside both searchable and quarantined namespace policy ranges\");",
    "  return { sourceRows, searchable, quarantined, unclassified, policyId: policy.policy_id, policyRevision: policy.policy_revision, predicates };",
    "}",
    ""
  ].join("\n");
  const loadAnchor = [
    "function loadPackManifest(root) {",
    "  const file = path.join(getResearchRoot(root), \"manifest.json\");",
    "  const manifest = JSON.parse(fs.readFileSync(file, \"utf8\"));",
    "  if (manifest.schema_version !== 1 || !Array.isArray(manifest.packs)) throw new Error(\"Invalid local research pack manifest\");",
    "  return manifest;",
    "}",
    "",
    "function getResearchSummary(root) {"
  ].join("\n");
  const loadReplacement = loadAnchor.replace("\n\nfunction getResearchSummary(root) {", "\n\n" + helper + "function getResearchSummary(root) {");
  source = replaceOnce(source, loadAnchor, loadReplacement, "insert canonical DTC namespace policy helpers");
  source = replaceOnce(
    source,
    "    const dtcs = obdex.prepare(\"SELECT count(*) AS n FROM generic_dtc_research WHERE verification_status='source_imported_unreviewed' AND vehicle_fitment_claim=0 AND namespace='generic_sae_iso_obd2'\").get().n;",
    [
      "    const dtcPolicy = loadDtcNamespacePolicy(root);",
      "    const dtcCounts = genericDtcCountsFromDb(obdex, dtcPolicy);",
      "    const dtcs = dtcCounts.searchable;",
      "    if (obManifest.counts?.generic_dtcs !== dtcCounts.sourceRows ||",
      "        obManifest.counts?.searchable_generic_dtcs !== dtcCounts.searchable ||",
      "        obManifest.counts?.quarantined_unresolved_namespace_rows !== dtcCounts.quarantined ||",
      "        obManifest.namespace_policy?.policy_id !== dtcPolicy.policy_id ||",
      "        obManifest.namespace_policy?.policy_revision !== dtcPolicy.policy_revision) {",
      "      throw new Error(\"OBDex desktop manifest/searchable DTC namespace counts mismatch\");",
      "    }"
    ].join("\n"),
    "replace generic DTC summary count"
  );
  source = replaceOnce(
    source,
    "          counts: { dtcs, pids },",
    [
      "          counts: { dtcs, dtcsSourceRows: dtcCounts.sourceRows, dtcsQuarantined: dtcCounts.quarantined, pids },",
      "          namespacePolicy: {",
      "            policyId: dtcPolicy.policy_id,",
      "            policyRevision: dtcPolicy.policy_revision,",
      "            allowedGenericRanges: dtcCounts.predicates.allowedRanges,",
      "            quarantinedUnresolvedRanges: dtcCounts.predicates.unresolvedRanges,",
      "          },"
    ].join("\n"),
    "replace OBDex summary counts"
  );
  source = replaceOnce(
    source,
    "    const pattern = likePattern(q);",
    [
      "    const dtcPolicy = loadDtcNamespacePolicy(root);",
      "    const dtcPredicates = getDtcNamespaceSqlPredicates(dtcPolicy);",
      "    if (obManifest.namespace_policy?.policy_id !== dtcPolicy.policy_id || obManifest.namespace_policy?.policy_revision !== dtcPolicy.policy_revision) {",
      "      throw new Error(\"OBDex search manifest does not match the canonical DTC namespace policy\");",
      "    }",
      "    const pattern = likePattern(q);"
    ].join("\n"),
    "load policy for generic DTC search"
  );
  source = replaceOnce(
    source,
    "        AND vehicle_fitment_claim=0 AND namespace='generic_sae_iso_obd2'\n        AND (code LIKE ? ESCAPE '\\\\'",
    "        AND vehicle_fitment_claim=0 AND namespace='generic_sae_iso_obd2'\n        AND (${dtcPredicates.allowedSql})\n        AND (code LIKE ? ESCAPE '\\\\'",
    "filter unresolved DTC ranges from generic search"
  );
  source = replaceOnce(
    source,
    "        namespace: \"generic_sae_iso_obd2\",",
    "        namespace: \"generic_sae_iso_obd2\",\n        namespacePolicyId: dtcPolicy.policy_id,\n        namespacePolicyRevision: dtcPolicy.policy_revision,",
    "attach namespace policy provenance to generic DTC rows"
  );
  return { changed: true, source };
}
function patchUi(file) {
  let source = read(file);
  if (source.includes("dtcsQuarantined") && source.includes("P34xx–P39xx")) return { changed: false, source };
  source = replaceOnce(
    source,
    'type SummaryPack = { id: string; license: string; contentsLicense?: string; counts: Record<string, number>; source: string; sourceUrl: string; note: string;',
    'type SummaryPack = { id: string; license: string; contentsLicense?: string; counts: Record<string, number>; namespacePolicy?: { policyId: string; policyRevision: string; allowedGenericRanges: string[]; quarantinedUnresolvedRanges: string[] }; source: string; sourceUrl: string; note: string;',
    "extend research summary type with DTC namespace policy"
  );
  source = replaceOnce(
    source,
    '<article className="research-stat"><small>Общие DTC</small><strong>{formatNumber(obdex?.counts?.dtcs)}</strong><span>CC0 · SAE/ISO</span></article>',
    '<article className="research-stat"><small>Общие DTC</small><strong>{formatNumber(obdex?.counts?.dtcs)}</strong><span>CC0 · SAE/ISO · {formatNumber(obdex?.counts?.dtcsQuarantined)} в карантине</span></article>',
    "show only searchable generic DTC count and quarantine count"
  );
  source = replaceOnce(
    source,
    '<b>Важно: справочные кандидаты не являются подтверждённой применимостью.</b>',
    '<b>Важно: справочные кандидаты не являются подтверждённой применимостью.</b>\n      <p>OBDex: {formatNumber(obdex?.counts?.dtcsSourceRows)} исходных строк; {formatNumber(obdex?.counts?.dtcs)} доступны в общем SAE/ISO поиске, {formatNumber(obdex?.counts?.dtcsQuarantined)} остаются в карантине по политике {obdex?.namespacePolicy?.policyRevision || "run87-2026-11-08"}. P34xx–P39xx, U3xxx, B3xxx и C3xxx не выдаются как подтверждённые generic DTC. Эти записи не являются VAG-specific и не доказывают применимость к автомобилю.</p>',
    "explain unresolved generic DTC quarantine in research UI"
  );
  return { changed: true, source };
}
function patchTests(root) {
  const dbTest = path.join(root, "tests", "local-research-db.test.cjs");
  let source = read(dbTest);
  const updatedCountsAssertion = "  assert.deepEqual(obdex.counts, { dtcs: 9204, dtcsSourceRows: 9533, dtcsQuarantined: 329, pids: 132 });";
  if (!source.includes(updatedCountsAssertion)) {
    source = replaceOnce(
      source,
      "  assert.deepEqual(obdex.counts, { dtcs: 9533, pids: 132 });",
      updatedCountsAssertion,
      "update OBDex summary count assertion"
    );
  }
  const insertion = [
    'test("MechanicDB manufacturer-labelled candidates are visible only in their separate research namespace", () => {'
  ].join("\n");
  const newTest = [
    'test("P34xx-P39xx, U3xxx, B3xxx and C3xxx remain quarantined from searchable generic DTCs", () => {',
    '  for (const code of ["P3400", "P3497", "P3500", "P39AB", "U3000", "B3000", "C3000"]) {',
    '    assert.deepEqual(local.searchGenericDtcs(code, 5, root), []);',
    '  }',
    '  const generic = local.searchGenericDtcs("P0300", 1, root)[0];',
    '  assert.equal(generic.code, "P0300");',
    '  assert.equal(generic.namespace, "generic_sae_iso_obd2");',
    '  assert.equal(generic.namespacePolicyId, "vag-tech-pro-dtc-namespace-ranges");',
    '  assert.equal(generic.namespacePolicyRevision, "run87-2026-11-08");',
    '  const summary = local.getResearchSummary(root);',
    '  const obdex = summary.packs.find((pack) => pack.id === "obdex-generic-cc0");',
    '  assert.deepEqual(obdex.counts, { dtcs: 9204, dtcsSourceRows: 9533, dtcsQuarantined: 329, pids: 132 });',
    '});',
    ''
  ].join("\n");
  if (source.includes('P34xx-P39xx, U3xxx, B3xxx and C3xxx remain quarantined from searchable generic DTCs')) {
    // The test may already have been inserted by an earlier interrupted patch.
  } else {
    source = replaceOnce(source, insertion, newTest + insertion, "insert generic DTC quarantine regression test");
  }
  write(dbTest, source);

  const uiTest = path.join(root, "tests", "local-research-ui-contract.test.cjs");
  let ui = read(uiTest);
  if (!ui.includes("dtcsQuarantined")) {
    ui = replaceOnce(
      ui,
      '  assert.match(component, /CC0-1\\.0/);',
      '  assert.match(component, /CC0-1\\.0/);\n  assert.match(component, /dtcsSourceRows/);\n  assert.match(component, /dtcsQuarantined/);\n  assert.match(component, /P34xx–P39xx/);\n  assert.match(component, /namespacePolicy/);',
      "assert generic DTC quarantine is visible in research UI"
    );
    write(uiTest, ui);
  }
}
function main() {
  const desktopRoot = parseArgs();
  const canonical = loadCanonicalPolicy();
  const rootReal = fs.realpathSync(desktopRoot);
  const policyTarget = installPolicy(rootReal, canonical);
  const dbPath = path.join(rootReal, "lib", "local-research-db.cjs");
  const uiPath = path.join(rootReal, "components", "local-research-catalog.tsx");
  if (!fs.existsSync(dbPath) || !fs.existsSync(uiPath)) fail("Desktop local research DB or catalog component is missing");
  const dbResult = patchResearchDb(dbPath);
  if (dbResult.changed) write(dbPath, dbResult.source);
  const uiResult = patchUi(uiPath);
  if (uiResult.changed) write(uiPath, uiResult.source);
  patchTests(rootReal);
  const contractSource = path.join(__dirname, "tests", "local-research-dtc-namespace-policy-run91.test.cjs");
  const contractTarget = path.join(rootReal, "tests", "local-research-dtc-namespace-policy-run91.test.cjs");
  fs.copyFileSync(contractSource, contractTarget);
  const patchDir = path.join(rootReal, "scripts", "patches");
  fs.mkdirSync(patchDir, { recursive: true });
  fs.copyFileSync(__filename, path.join(patchDir, path.basename(__filename)));
  const report = {
    status: "applied",
    desktopRoot: rootReal,
    policyId: canonical.policy.policy_id,
    policyRevision: canonical.policy.policy_revision,
    policySha256: canonical.sha256,
    policyTarget,
    databaseChanged: dbResult.changed,
    uiChanged: uiResult.changed,
    searchableGenericRanges: ["P0xxx", "P2xxx", "B0xxx", "C0xxx", "U0xxx"],
    quarantinedUnresolvedRanges: ["P34xx-P39xx", "U3xxx", "B3xxx", "C3xxx"],
    expectedSearchableRows: 9204,
    expectedQuarantinedRows: 329,
  };
  process.stdout.write(JSON.stringify(report, null, 2) + "\n");
}
main();

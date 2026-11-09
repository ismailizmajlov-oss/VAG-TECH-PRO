#!/usr/bin/env node
"use strict";
const fs = require("node:fs");
const path = require("node:path");

const MARKER = "// run91: classify OBDex DTC research rows against the canonical namespace-range policy";

function replaceOnce(text, before, after, label) {
  const count = text.split(before).length - 1;
  if (count !== 1) throw new Error(`${label}: expected exactly one anchor, found ${count}`);
  return text.replace(before, after);
}

function read(root, relative) {
  const target = path.join(root, relative);
  if (!fs.existsSync(target)) throw new Error(`run91 required file is missing: ${relative}`);
  const stat = fs.lstatSync(target);
  if (!stat.isFile() || stat.isSymbolicLink()) throw new Error(`run91 expected a regular file: ${relative}`);
  return fs.readFileSync(target, "utf8");
}

function write(root, relative, content) {
  const target = path.join(root, relative);
  fs.mkdirSync(path.dirname(target), { recursive: true });
  fs.writeFileSync(target, content, "utf8");
}

function apply(root) {
  const libPath = "lib/local-research-db.cjs";
  const uiPath = "components/local-research-catalog.tsx";
  const libTestPath = "tests/dtc-research-range-quarantine.test.cjs";
  const packagePath = "package.json";
  const policyPath = "data/policies/dtc-namespace-ranges.json";
  const lib = read(root, libPath);
  const ui = read(root, uiPath);
  const packageJson = JSON.parse(read(root, packagePath));
  const policy = JSON.parse(read(root, policyPath));

  const requiredNamespaces = ["generic_sae_iso", "manufacturer_controlled", "unresolved_reserved"];
  for (const key of requiredNamespaces) {
    if (typeof policy.namespaces?.[key]?.pattern !== "string") {
      throw new Error(`Canonical DTC policy is missing namespaces.${key}.pattern`);
    }
    new RegExp(policy.namespaces[key].pattern);
  }
  if (!/^run\d+-\d{4}-\d{2}-\d{2}$/.test(policy.policy_revision || "")) {
    throw new Error("Canonical DTC policy revision is missing or malformed");
  }

  if (lib.includes(MARKER)) {
    if (!lib.includes("function classifyDtcNamespace(code)")) throw new Error("run91 marker exists without classifier");
    if (!ui.includes("DTC RANGE QUARANTINE") || !ui.includes("row.allocationWarning") || !ui.includes("generic_range_unreviewed")) throw new Error("run91 marker exists without quarantine UI");
    if (!ui.includes("sourceNamespaceLabel") || !ui.includes("sourceRecordSha256?: string;")) throw new Error("run91 marker exists without source-record provenance types");
    if (!packageJson.scripts?.["test:research"]?.includes(libTestPath)) throw new Error("run91 test is not wired into npm test");
    if (!fs.existsSync(path.join(root, libTestPath))) throw new Error("run91 marker exists without regression tests");
    return { status: "already_applied", files: [libPath, uiPath, packagePath, libTestPath] };
  }

  const functionAnchor = "function searchGenericDtcs(query, limit = 25, root) {";
  const classifier = `let dtcNamespacePolicyCache;
function loadDtcNamespacePolicy() {
  if (dtcNamespacePolicyCache) return dtcNamespacePolicyCache;
  const policyPath = path.resolve(__dirname, "../data/policies/dtc-namespace-ranges.json");
  const policy = JSON.parse(fs.readFileSync(policyPath, "utf8"));
  if (!policy || policy.schema_version !== 1 || typeof policy.policy_revision !== "string" || !policy.namespaces) {
    throw new Error("Canonical DTC namespace policy is invalid");
  }
  dtcNamespacePolicyCache = policy;
  return dtcNamespacePolicyCache;
}

${MARKER}
function classifyDtcNamespace(code) {
  const normalized = String(code || "").trim().toUpperCase();
  if (!/^[PBCU][0-9A-F]{4}$/.test(normalized)) {
    return {
      namespace: "unknown",
      allocationStatus: "unknown",
      reviewStatus: "quarantined_unknown_range",
      warning: "Код не распознан как пятисимвольный SAE/ISO OBD-II DTC; namespace не подтверждён.",
      policyRevision: loadDtcNamespacePolicy().policy_revision,
    };
  }
  const policy = loadDtcNamespacePolicy();
  const patterns = policy.namespaces;
  if (new RegExp(patterns.generic_sae_iso.pattern).test(normalized)) {
    return {
      namespace: "generic_sae_iso_obd2",
      allocationStatus: "generic_range_unreviewed",
      reviewStatus: "research_only",
      warning: "Код находится в generic SAE/ISO OBD-II диапазоне по локальной политике, но сама запись OBDex не прошла независимую проверку. Она не VAG-specific и не подтверждает применимость к модели, двигателю, КПП или ECU.",
      policyRevision: policy.policy_revision,
    };
  }
  if (new RegExp(patterns.manufacturer_controlled.pattern).test(normalized)) {
    return {
      namespace: "manufacturer_controlled_candidate",
      allocationStatus: "manufacturer_controlled_unattributed",
      reviewStatus: "quarantined_manufacturer_controlled_range",
      warning: "Диапазон контролируется изготовителями. Это не доказывает авторство Volkswagen Group, принадлежность конкретному ECU или применимость к автомобилю.",
      policyRevision: policy.policy_revision,
    };
  }
  if (new RegExp(patterns.unresolved_reserved.pattern).test(normalized)) {
    return {
      namespace: "unknown_reserved",
      allocationStatus: "unresolved_reserved",
      reviewStatus: "quarantined_unresolved_reserved_range",
      warning: "Источник OBDex помечает код как общий, но точное распределение диапазона по актуальному SAE J2012/J2012DA не подтверждено. Код остаётся в карантине и не считается ни нормализованным generic, ни VAG-specific DTC.",
      policyRevision: policy.policy_revision,
    };
  }
  return {
    namespace: "unknown",
    allocationStatus: "unclassified_range",
    reviewStatus: "quarantined_unknown_range",
    warning: "Для кода отсутствует подтверждённое распределение в текущей локальной политике namespace.",
    policyRevision: policy.policy_revision,
  };
}

`;
  let nextLib = replaceOnce(lib, functionAnchor, classifier + functionAnchor, "classifier insertion");
  nextLib = replaceOnce(nextLib, "SELECT code, category, raw_record_json, source_record_sha256, source_sha256, source_version", "SELECT code, namespace, category, raw_record_json, source_record_sha256, source_sha256, source_version", "OBDex upstream namespace provenance");

  const oldReturn = `      return {
        code: row.code,
        title: payload.title?.en || payload.title?.de || row.code,
        titleDe: payload.title?.de || null,
        description: payload.description?.en || payload.description?.de || "",
        descriptionDe: payload.description?.de || null,
        category: row.category || payload.category || null,
        affectedComponents: Array.isArray(payload.affected_components) ? payload.affected_components.slice(0, 12) : [],
        commonCauses: Array.isArray(payload.common_causes) ? payload.common_causes.slice(0, 8).map((item) => ({
          component: item.id || null,
          label: item.label?.en || item.label?.de || item.id || "",
          likelihood: item.likelihood || null,
        })) : [],
        symptoms: Array.isArray(payload.symptoms) ? payload.symptoms.slice(0, 8).map((item) => item.en || item.de || "") : [],
        references: Array.isArray(payload.references) ? payload.references.slice(0, 8) : [],
        sourceSha256: row.source_sha256,
        sourceRecordSha256: row.source_record_sha256,
        sourceManifestSha256: obManifest.source_manifest_sha256,
        upstreamRevision: row.source_version || obManifest.upstream_revision,
        snapshotGeneratedAt: obManifest.snapshot_generated_at_utc,
        license: PACKS.obdex.license,
        namespace: "generic_sae_iso_obd2",
        reviewStatus: "research_only",
        sourceVerificationStatus: "source_imported_unreviewed",
        fitmentClaim: false,
      };`;
  const newReturn = `      const classification = classifyDtcNamespace(row.code);
      const isNormalizedGeneric = classification.namespace === "generic_sae_iso_obd2";
      return {
        code: row.code,
        title: payload.title?.en || payload.title?.de || row.code,
        titleDe: payload.title?.de || null,
        description: payload.description?.en || payload.description?.de || "",
        descriptionDe: payload.description?.de || null,
        category: row.category || payload.category || null,
        affectedComponents: isNormalizedGeneric && Array.isArray(payload.affected_components) ? payload.affected_components.slice(0, 12) : [],
        commonCauses: isNormalizedGeneric && Array.isArray(payload.common_causes) ? payload.common_causes.slice(0, 8).map((item) => ({
          component: item.id || null,
          label: item.label?.en || item.label?.de || item.id || "",
          likelihood: item.likelihood || null,
        })) : [],
        symptoms: isNormalizedGeneric && Array.isArray(payload.symptoms) ? payload.symptoms.slice(0, 8).map((item) => item.en || item.de || "") : [],
        references: [],
        sourceSha256: row.source_sha256,
        sourceRecordSha256: row.source_record_sha256,
        sourceManifestSha256: obManifest.source_manifest_sha256,
        upstreamRevision: row.source_version || obManifest.upstream_revision,
        snapshotGeneratedAt: obManifest.snapshot_generated_at_utc,
        license: PACKS.obdex.license,
        namespace: classification.namespace,
        sourceNamespaceLabel: row.namespace,
        allocationStatus: classification.allocationStatus,
        allocationWarning: classification.warning,
        namespacePolicyRevision: classification.policyRevision,
        reviewStatus: classification.reviewStatus,
        sourceVerificationStatus: "source_imported_unreviewed",
        marketScope: "UNKNOWN",
        applicabilityPrecision: "generic_code_only",
        fitmentClaim: false,
        diagnosticExecutionAllowed: false,
      };`;
  nextLib = replaceOnce(nextLib, oldReturn, newReturn, "OBDex result classification");
  nextLib = replaceOnce(
    nextLib,
    "  searchGenericDtcs,\n  searchGenericPids,",
    "  searchGenericDtcs,\n  classifyDtcNamespace,\n  searchGenericPids,",
    "classifier export",
  );

  let nextUi = ui;
  nextUi = replaceOnce(
    nextUi,
    "  sourceSha256?: string;\n",
    "  sourceSha256?: string;\n  sourceRecordSha256?: string;\n",
    "OBDex per-record hash type",
  );
  nextUi = replaceOnce(
    nextUi,
    "  namespace?: string;\n  definition?: string;",
    "  namespace?: string;\n  sourceNamespaceLabel?: string;\n  allocationStatus?: string;\n  allocationWarning?: string;\n  namespacePolicyRevision?: string;\n  diagnosticExecutionAllowed?: boolean;\n  definition?: string;",
    "research row type",
  );

  nextUi = replaceOnce(
    nextUi,
    '<small>GENERIC SAE/ISO OBD-II · {row.category || "без категории"}</small>',
    '<small>{row.namespace === "generic_sae_iso_obd2" ? "GENERIC SAE/ISO RANGE" : "DTC RANGE QUARANTINE"} · название/категория OBDex (не проверены): {row.category || "без категории"}</small>',
    "OBDex DTC namespace label",
  );
  nextUi = replaceOnce(
    nextUi,
    '<h3 className="research-code">{row.code} · {row.title}</h3></div><span className="research-candidate">RESEARCH ONLY</span></div>',
    '<h3 className="research-code">{row.code} · {row.title}</h3></div><span className="research-candidate">{row.allocationStatus === "generic_range_unreviewed" ? "RESEARCH ONLY" : "QUARANTINE"}</span></div>',
    "OBDex DTC quarantine badge",
  );
  nextUi = replaceOnce(
    nextUi,
    '<div className="research-warning-line">Не VAG-specific · не привязан к модели, двигателю, КПП или ECU · не является тест-планом или указанием на замену детали</div>',
    '<div className="research-warning-line">{row.allocationWarning || "Не VAG-specific · применимость не подтверждена"} Исходная метка: {row.sourceNamespaceLabel}; namespace: {row.namespace}; статус: {row.reviewStatus}; рынок: {row.marketScope}; точность: {row.applicabilityPrecision}; ревизия политики: {row.namespacePolicyRevision}.</div>',
    "OBDex DTC allocation warning",
  );
  const dtcSectionStart = nextUi.indexOf('{dataset === "dtc" && rows.map(');
  const pidsSectionStart = nextUi.indexOf('{dataset === "pids" && rows.map(', dtcSectionStart + 1);
  if (dtcSectionStart < 0 || pidsSectionStart < 0 || pidsSectionStart <= dtcSectionStart) {
    throw new Error("OBDex DTC UI section boundaries are missing");
  }
  let dtcSection = nextUi.slice(dtcSectionStart, pidsSectionStart);
  dtcSection = replaceOnce(
    dtcSection,
    '<p className="research-description">{row.description}</p>',
    '<p className="research-description">{"Описание OBDex (не проверено): " + row.description}</p>',
    "OBDex quarantined description label",
  );
  dtcSection = replaceOnce(
    dtcSection,
    '<summary>Общие возможные причины из набора</summary>',
    '<summary>Непроверенные возможные причины из OBDex</summary>',
    "OBDex unverified common-cause label",
  );
  dtcSection = replaceOnce(
    dtcSection,
    '{(row.affectedComponents ?? [])?.length > 0 && <div className="research-tags">{(row.affectedComponents ?? []).map((item: string) => <span key={item}>{item.replaceAll("_", " ")}</span>)}</div>}',
    '{(row.affectedComponents ?? [])?.length > 0 && <div><small>Компоненты из OBDex (не проверены)</small><div className="research-tags">{(row.affectedComponents ?? []).map((item: string) => <span key={item}>{item.replaceAll("_", " ")}</span>)}</div></div>}',
    "OBDex unverified component label",
  );
  dtcSection = replaceOnce(
    dtcSection,
    'SHA источника {String(row.sourceSha256).slice(0, 12)}… · SHA манифеста {String(row.sourceManifestSha256).slice(0, 12)}…',
    'SHA источника {String(row.sourceSha256).slice(0, 12)}… · SHA записи {String(row.sourceRecordSha256).slice(0, 12)}… · SHA манифеста {String(row.sourceManifestSha256).slice(0, 12)}…',
    "OBDex per-record provenance hash",
  );
  nextUi = nextUi.slice(0, dtcSectionStart) + dtcSection + nextUi.slice(pidsSectionStart);

  const researchTestCommand = packageJson.scripts?.["test:research"];
  if (typeof researchTestCommand !== "string") throw new Error("package.json test:research script is missing");
  if (!researchTestCommand.includes(libTestPath)) {
    packageJson.scripts["test:research"] = researchTestCommand + " " + libTestPath;
  }

  const regression = `"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const path = require("node:path");
const { DatabaseSync } = require("node:sqlite");
const local = require("../lib/local-research-db.cjs");
const root = path.resolve(__dirname, "../data/research");

test("run91 DTC namespace classifier follows the canonical policy ranges", () => {
  for (const code of ["P0300", "P2ABC", "B0001", "C0001", "U0001"]) {
    const row = local.classifyDtcNamespace(code);
    assert.equal(row.namespace, "generic_sae_iso_obd2", code);
    assert.equal(row.allocationStatus, "generic_range_unreviewed", code);
    assert.equal(row.reviewStatus, "research_only", code);
  }
  for (const code of ["P1000", "P3000", "P33FF", "B1000", "C2000", "U2000"]) {
    const row = local.classifyDtcNamespace(code);
    assert.equal(row.namespace, "manufacturer_controlled_candidate", code);
    assert.equal(row.allocationStatus, "manufacturer_controlled_unattributed", code);
    assert.equal(row.reviewStatus, "quarantined_manufacturer_controlled_range", code);
  }
  for (const code of ["P3400", "P3497", "P3500", "P39AB", "U3000", "U3ABC", "B3000", "C3ABC"]) {
    const row = local.classifyDtcNamespace(code);
    assert.equal(row.namespace, "unknown_reserved", code);
    assert.equal(row.allocationStatus, "unresolved_reserved", code);
    assert.equal(row.reviewStatus, "quarantined_unresolved_reserved_range", code);
    assert.match(row.warning, /не подтверждено|не подтверждён/i, code);
  }
  assert.equal(local.classifyDtcNamespace("not-a-dtc").namespace, "unknown");
});

test("run91 OBDex upstream labels cannot override unresolved DTC namespace quarantine", () => {
  const generic = local.searchGenericDtcs("P0300", 5, root)[0];
  assert.ok(generic);
  assert.equal(generic.namespace, "generic_sae_iso_obd2");
  assert.equal(generic.allocationStatus, "generic_range_unreviewed");
  assert.equal(generic.reviewStatus, "research_only");
  assert.equal(generic.fitmentClaim, false);
  assert.equal(generic.diagnosticExecutionAllowed, false);
  const p34 = local.searchGenericDtcs("P3400", 5, root)[0];
  assert.ok(p34);
  assert.equal(p34.sourceNamespaceLabel, "generic_sae_iso_obd2");
  assert.equal(p34.namespace, "unknown_reserved");
  assert.equal(p34.allocationStatus, "unresolved_reserved");
  assert.equal(p34.reviewStatus, "quarantined_unresolved_reserved_range");
  assert.deepEqual(p34.commonCauses, []);
  assert.deepEqual(p34.affectedComponents, []);
  const u3 = local.searchGenericDtcs("U3000", 5, root)[0];
  assert.ok(u3);
  assert.equal(u3.namespace, "unknown_reserved");
  assert.equal(u3.allocationStatus, "unresolved_reserved");
  for (const row of [generic, p34, u3]) {
    assert.equal(row.marketScope, "UNKNOWN");
    assert.equal(row.applicabilityPrecision, "generic_code_only");
    assert.equal(row.fitmentClaim, false);
    assert.equal(row.diagnosticExecutionAllowed, false);
    assert.match(row.sourceRecordSha256, /^[a-f0-9]{64}$/);
    assert.match(row.sourceManifestSha256, /^[a-f0-9]{64}$/);
  }
});

test("run91 OBDex research snapshot counts remain isolated and hash-verified", () => {
  const manifest = JSON.parse(require("node:fs").readFileSync(path.join(root, "manifest.json"), "utf8"));
  const pack = manifest.packs.find((item) => item.id === "obdex-generic-cc0");
  assert.equal(pack?.counts?.generic_dtcs, 9533);
  assert.equal(pack?.counts?.pids, 132);
  const db = new DatabaseSync(path.join(root, "obdex-generic-cc0/generic-obdex-research.sqlite"), { readOnly: true });
  try {
    assert.equal(db.prepare("PRAGMA integrity_check").get().integrity_check, "ok");
    assert.equal(db.prepare("PRAGMA foreign_key_check").all().length, 0);
    const count = (sql) => db.prepare(sql).get().n;
    const genericRanges = count("SELECT count(*) AS n FROM generic_dtc_research WHERE code GLOB 'P0[0-9A-F][0-9A-F][0-9A-F]' OR code GLOB 'P2[0-9A-F][0-9A-F][0-9A-F]' OR code GLOB 'B0[0-9A-F][0-9A-F][0-9A-F]' OR code GLOB 'C0[0-9A-F][0-9A-F][0-9A-F]' OR code GLOB 'U0[0-9A-F][0-9A-F][0-9A-F]'");
    const p34 = count("SELECT count(*) AS n FROM generic_dtc_research WHERE code GLOB 'P3[4-9][0-9A-F][0-9A-F]'");
    const u3 = count("SELECT count(*) AS n FROM generic_dtc_research WHERE code GLOB 'U3[0-9A-F][0-9A-F][0-9A-F]'");
    const b3 = count("SELECT count(*) AS n FROM generic_dtc_research WHERE code GLOB 'B3[0-9A-F][0-9A-F][0-9A-F]'");
    const c3 = count("SELECT count(*) AS n FROM generic_dtc_research WHERE code GLOB 'C3[0-9A-F][0-9A-F][0-9A-F]'");
    assert.equal(count("SELECT count(*) AS n FROM generic_dtc_research"), 9533);
    assert.equal(count("SELECT count(*) AS n FROM generic_pid_research"), 132);
    assert.equal(genericRanges, 9204);
    assert.equal(p34, 155);
    assert.equal(u3, 174);
    assert.equal(b3, 0);
    assert.equal(c3, 0);
  } finally {
    db.close();
  }
});

test("run91 DTC research UI distinguishes generic rows from unresolved namespace quarantine", () => {
  const source = require("node:fs").readFileSync(path.resolve(__dirname, "../components/local-research-catalog.tsx"), "utf8");
  assert.ok(source.includes('row.namespace === "generic_sae_iso_obd2" ? "GENERIC SAE/ISO RANGE" : "DTC RANGE QUARANTINE"'));
  assert.ok(source.includes('row.allocationStatus === "generic_range_unreviewed" ? "RESEARCH ONLY" : "QUARANTINE"'));
  assert.match(source, /row\.allocationWarning/);
  assert.ok(source.includes("sourceRecordSha256?: string;"));
  assert.match(source, /row\.sourceNamespaceLabel/);
  assert.ok(source.includes("Описание OBDex (не проверено)"));
  assert.ok(source.includes("Непроверенные возможные причины из OBDex"));
  assert.ok(source.includes("название/категория OBDex (не проверены)"));
  assert.ok(source.includes("Компоненты из OBDex (не проверены)"));
  assert.ok(source.includes("SHA записи {String(row.sourceRecordSha256)"));
});
`;
  write(root, libTestPath, regression);
  write(root, libPath, nextLib);
  write(root, uiPath, nextUi);
  write(root, packagePath, JSON.stringify(packageJson, null, 2) + "\n");

  return {
    status: "applied",
    files: [libPath, uiPath, packagePath, libTestPath],
    policyRevision: policy.policy_revision,
    policySha256: require("node:crypto").createHash("sha256").update(read(root, policyPath)).digest("hex"),
  };
}

const index = process.argv.indexOf("--desktop-root");
const root = path.resolve(index >= 0 && process.argv[index + 1] ? process.argv[index + 1] : "desktop-source");
console.log(JSON.stringify(apply(root)));

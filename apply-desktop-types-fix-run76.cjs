"use strict";

const fs = require("node:fs");
const path = require("node:path");
const crypto = require("node:crypto");

function replaceExactlyOnce(source, before, after, label) {
  const count = source.split(before).length - 1;
  if (count === 1) return { text: source.replace(before, after), changed: true };
  if (count === 0 && source.includes(after)) return { text: source, changed: false };
  throw new Error(label + ": expected one original occurrence or an already-applied replacement; found " + count);
}

function patchFile(root, relativePath, replacements) {
  const filePath = path.join(root, relativePath);
  if (!fs.existsSync(filePath)) throw new Error("Required generated desktop file is missing: " + relativePath);
  let source = fs.readFileSync(filePath, "utf8");
  let changed = false;
  for (const [before, after, label] of replacements) {
    const result = replaceExactlyOnce(source, before, after, relativePath + ": " + label);
    source = result.text;
    changed = changed || result.changed;
  }
  if (changed) fs.writeFileSync(filePath, source, "utf8");
  return { path: relativePath, changed, sha256: crypto.createHash("sha256").update(source).digest("hex") };
}

const contractTest = [
  '"use strict";',
  'const test = require("node:test");',
  'const assert = require("node:assert/strict");',
  'const fs = require("node:fs");',
  'const path = require("node:path");',
  'const root = path.resolve(__dirname, "..");',
  '',
  'test("run76 generated desktop types cover source revision state and ASTRA rows without duplicate fields", () => {',
  '  const admin = fs.readFileSync(path.join(root, "components/local-data-admin.tsx"), "utf8");',
  '  const ui = fs.readFileSync(path.join(root, "components/local-research-catalog.tsx"), "utf8");',
  '  const api = fs.readFileSync(path.join(root, "app/api/local-research/route.ts"), "utf8");',
  '  const start = ui.indexOf("type ResearchRow = {");',
  '  const end = ui.indexOf("\\n};", start);',
  '  assert.ok(start >= 0 && end > start, "ResearchRow type must be present");',
  '  const rowType = ui.slice(start, end);',
  '  const count = (text, token) => text.split(token).length - 1;',
  '  assert.ok(admin.includes("const [revisionDraft, setRevisionDraft] = useState("));',
  '  assert.ok(admin.includes("const [revisionFile, setRevisionFile] = useState<File | null>(null)"));',
  '  assert.ok(rowType.includes("fuelType?: string | null;"));',
  '  assert.ok(rowType.includes("commercialName?: string | null;"));',
  '  assert.equal(count(rowType, "fuelType?:"), 1);',
  '  assert.equal(count(rowType, "sourceRecordSha256?:"), 1);',
  '  assert.ok(api.includes("let rows: unknown[];"));',
  '});',
  ''
].join("\n");

const desktopRootArg = process.argv.find((value) => value.startsWith("--desktop-root="));
const desktopRoot = path.resolve(desktopRootArg ? desktopRootArg.slice("--desktop-root=".length) : "desktop-source");
if (!fs.existsSync(desktopRoot)) throw new Error("Desktop source root not found: " + desktopRoot);

const changes = [];
changes.push(patchFile(desktopRoot, "components/local-data-admin.tsx", [[
  '  const [approvalFiles, setApprovalFiles] = useState<{ license: File | null; rightsEvidence: File | null; snapshot: File | null }>({ license: null, rightsEvidence: null, snapshot: null });',
  '  const [approvalFiles, setApprovalFiles] = useState<{ license: File | null; rightsEvidence: File | null; snapshot: File | null }>({ license: null, rightsEvidence: null, snapshot: null });\n  const [revisionDraft, setRevisionDraft] = useState({ source_id: "", new_revision: "", snapshot_reference: "", owner_confirmation: "" });\n  const [revisionFile, setRevisionFile] = useState<File | null>(null);',
  "restore source-revision form state"
]]));

changes.push(patchFile(desktopRoot, "components/local-research-catalog.tsx", [
  [
    "  displacementCc?: number;\n  fuelType?: string;\n  drivetrain?: string;",
    "  displacementCc?: number;\n  fuelType?: string | null;\n  drivetrain?: string;",
    "merge nullable fuel type into ResearchRow"
  ],
  [
    "  approvalNumber?: string; typeDesignation?: string | null; variant?: string | null; version?: string | null;",
    "  approvalNumber?: string; commercialName?: string | null; typeDesignation?: string | null; variant?: string | null; version?: string | null;",
    "declare ASTRA commercial name"
  ],
  [
    "  engineTypeDesignation?: string | null; stampedEngineMarking?: string | null; fuelType?: string | null;",
    "  engineTypeDesignation?: string | null; stampedEngineMarking?: string | null;",
    "remove duplicate nullable fuel type"
  ],
  [
    "  gearboxClassificationKind?: string; sourceRecordSha256?: string; gearboxRecordSha256?: string | null;",
    "  gearboxClassificationKind?: string; gearboxRecordSha256?: string | null;",
    "remove duplicate source record digest"
  ]
]));

changes.push(patchFile(desktopRoot, "app/api/local-research/route.ts", [[
  "    let rows: Array<Record<string, unknown>>;",
  "    let rows: unknown[];",
  "accept typed dataset-specific research rows"
]]));

const testPath = path.join(desktopRoot, "tests", "run76-types-fix.test.cjs");
fs.mkdirSync(path.dirname(testPath), { recursive: true });
if (fs.existsSync(testPath) && fs.readFileSync(testPath, "utf8") !== contractTest) {
  throw new Error("Existing run76 contract test differs from the pinned generated test; refusing overwrite.");
}
fs.writeFileSync(testPath, contractTest, "utf8");
changes.push({
  path: "tests/run76-types-fix.test.cjs",
  changed: true,
  sha256: crypto.createHash("sha256").update(contractTest).digest("hex")
});

const ui = fs.readFileSync(path.join(desktopRoot, "components/local-research-catalog.tsx"), "utf8");
const rowStart = ui.indexOf("type ResearchRow = {");
const rowEnd = ui.indexOf("\n};", rowStart);
if (rowStart < 0 || rowEnd <= rowStart) throw new Error("ResearchRow type block could not be validated.");
const rowType = ui.slice(rowStart, rowEnd);
if ((rowType.match(/fuelType\?:/g) || []).length !== 1) throw new Error("ResearchRow must contain exactly one fuelType property.");
if ((rowType.match(/sourceRecordSha256\?:/g) || []).length !== 1) throw new Error("ResearchRow must contain exactly one sourceRecordSha256 property.");
if (!rowType.includes("commercialName?: string | null")) throw new Error("ResearchRow is missing the ASTRA commercialName field.");

console.log(JSON.stringify({
  status: "generated_desktop_types_repaired",
  changes,
  research_row_properties: {
    fuelType: "string | null | undefined",
    commercialName: "string | null | undefined",
    sourceRecordSha256_occurrences: 1
  }
}, null, 2));

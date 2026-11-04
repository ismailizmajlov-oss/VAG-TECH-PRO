"use strict";

const fs = require("node:fs");
const path = require("node:path");

const root = path.join(__dirname, "desktop-source");
const pageFile = path.join(root, "app", "page.tsx");
const packageFile = path.join(root, "package.json");
const testFile = path.join(root, "tests", "desktop-dbrow-types.test.cjs");

function replaceOnce(source, before, after, label) {
  const count = source.split(before).length - 1;
  if (count === 0 && source.includes(after)) return source;
  if (count !== 1) {
    throw new Error(label + ": expected exactly one original anchor or an already-applied replacement; found " + count);
  }
  return source.replace(before, after);
}

if (!fs.existsSync(pageFile) || !fs.existsSync(packageFile)) {
  throw new Error("Desktop page or package manifest is missing.");
}

let page = fs.readFileSync(pageFile, "utf8");
const oldType = "type DbRow = Record<string, any>;";
const newType = [
  "type DbRow = {",
  "  id?: string;",
  "  name?: string;",
  "  slug?: string;",
  "  brand_id?: string;",
  "  model_id?: string;",
  "  market?: string | null;",
  "  platform_code?: string | null;",
  "  generation_id?: string;",
  "  model_year?: number | null;",
  "  production_date?: string | null;",
  "  pr_codes?: unknown;",
  "  body_code?: string | null;",
  "  drive_type?: string | null;",
  "  engine_code?: string | null;",
  "  transmission_code?: string | null;",
  "  ecu_family?: string | null;",
  "  hardware_number?: string | null;",
  "  software_number?: string | null;",
  "  engine?: DbRelation;",
  "  transmission?: DbRelation;",
  "  ecu?: DbRelation;",
  "  generation?: DbRelation;",
  "  model?: DbRelation;",
  "  brand?: DbRelation;",
  "  source?: DbRelation;",
  "  document?: DbRelation;",
  "  configuration?: DbRelation;",
  "  publisher?: string | null;",
  "  title?: string | null;",
  "  revision?: string | null;",
  "  source_url?: string | null;",
  "  permission_status?: string | null;",
  "  _type?: string;",
  "  code?: string;",
  "  component_name?: string;",
  "  connector_id?: string;",
  "  description?: string;",
  "  diagnostic_notes?: string;",
  "  objective?: string;",
  "  parameter_name?: string;",
  "  pin_number?: string;",
  "  summary?: string;",
  "  system_name?: string;",
  "  test_purpose?: string;",
  "  unit?: string;",
  "  value_text?: string;",
  "  wire_color?: string;",
  "  wire_function?: string;",
  "  label?: string;",
  "  nickname?: string;",
  "  is_default?: boolean;",
  "  created_at?: string;",
  "  document_id?: string | null;",
  "  procedure_id?: string | null;",
  "  dtc_id?: string | null;",
  "  specification_id?: string | null;",
  "  wiring_diagram_id?: string | null;",
  "  diagnostic_test_id?: string | null;",
  "  query_text?: string;",
  "  response_summary?: string;",
  "};",
  "type DbRelation = DbRow | DbRow[] | null | undefined;",
  "type IdentifiedDbRow = DbRow & { id: string };",
  "function firstRelation(value: DbRelation): DbRow | null {",
  "  if (Array.isArray(value)) return value[0] || null;",
  "  return value || null;",
  "}"
].join("\n");

page = replaceOnce(page, oldType, newType, "replace permissive Supabase row type");

const stateAnchor = "useState<DbRow[]>([])";
const stateCount = page.split(stateAnchor).length - 1;
if (stateCount === 7) {
  page = page.replaceAll(stateAnchor, "useState<IdentifiedDbRow[]>([])");
} else if (stateCount !== 0 || (page.match(/useState<IdentifiedDbRow\[\]>\(\[\]\)/g) || []).length !== 7) {
  throw new Error("Expected seven identified Supabase row state declarations; found " + stateCount);
}

page = replaceOnce(
  page,
  "async function addBookmark(row: DbRow)",
  "async function addBookmark(row: IdentifiedDbRow)",
  "bookmark row identity"
);
page = replaceOnce(
  page,
  "function selectSavedVehicle(item: DbRow)",
  "function selectSavedVehicle(item: IdentifiedDbRow)",
  "saved vehicle row identity"
);
page = replaceOnce(
  page,
  "const config = item.configuration; const generation = config?.generation; const model = generation?.model; const make = model?.brand;",
  "const config = firstRelation(item.configuration); const generation = firstRelation(config?.generation); const model = firstRelation(generation?.model); const make = firstRelation(model?.brand);",
  "saved vehicle relation normalization"
);
page = replaceOnce(
  page,
  "const c=item.configuration;const g=c?.generation;const m=g?.model;const ecu=c?.ecu;",
  "const c=firstRelation(item.configuration);const g=firstRelation(c?.generation);const m=firstRelation(g?.model);const brandRow=firstRelation(m?.brand);const engine=firstRelation(c?.engine);const transmission=firstRelation(c?.transmission);const ecu=firstRelation(c?.ecu);",
  "garage relation normalization"
);
page = replaceOnce(page, "m?.brand?.name", "brandRow?.name", "garage brand relation");
page = replaceOnce(page, "c?.engine?.engine_code", "engine?.engine_code", "garage engine relation");
page = replaceOnce(page, "c?.transmission?.transmission_code", "transmission?.transmission_code", "garage transmission relation");
page = replaceOnce(page, "configurations.find(c => c.id === configurationId)?.engine?.engine_code", "firstRelation(configurations.find(c => c.id === configurationId)?.engine)?.engine_code", "vehicle summary engine relation");
page = replaceOnce(page, "c.engine?.engine_code", "firstRelation(c.engine)?.engine_code", "configuration option engine relation");
page = replaceOnce(page, "c.transmission?.transmission_code", "firstRelation(c.transmission)?.transmission_code", "configuration option transmission relation");
page = replaceOnce(page, "c.ecu?.ecu_family", "firstRelation(c.ecu)?.ecu_family", "configuration option ECU family relation");
page = replaceOnce(page, "c.ecu?.hardware_number", "firstRelation(c.ecu)?.hardware_number", "configuration option ECU hardware relation");
page = replaceOnce(page, "configurations.find(c => c.id === configurationId)?.ecu?.ecu_family", "firstRelation(configurations.find(c => c.id === configurationId)?.ecu)?.ecu_family", "selected ECU family relation");
page = replaceOnce(page, "configurations.find(c => c.id === configurationId)?.ecu?.hardware_number", "firstRelation(configurations.find(c => c.id === configurationId)?.ecu)?.hardware_number", "selected ECU hardware relation");
page = replaceOnce(page, "configurations.find(c => c.id === configurationId)?.ecu?.software_number", "firstRelation(configurations.find(c => c.id === configurationId)?.ecu)?.software_number", "selected ECU software relation");
page = replaceOnce(page, "configurations.find(c=>c.id===configurationId)?.engine?.engine_code", "firstRelation(configurations.find(c=>c.id===configurationId)?.engine)?.engine_code", "engine input relation");
page = replaceOnce(page, "configurations.find(c=>c.id===configurationId)?.transmission?.transmission_code", "firstRelation(configurations.find(c=>c.id===configurationId)?.transmission)?.transmission_code", "transmission input relation");
page = replaceOnce(
  page,
  "const source=r.source||r.document?.source||null;const documentTitle=r.document?.title||r.title||\"Документ не указан\";const revision=r.revision||r.document?.revision||\"Ревизия не указана\";",
  "const document=firstRelation(r.document);const source=firstRelation(r.source)||firstRelation(document?.source)||null;const documentTitle=document?.title||r.title||\"Документ не указан\";const revision=r.revision||document?.revision||\"Ревизия не указана\";",
  "search result document/source relation normalization"
);
page = replaceOnce(
  page,
  "if (!config || !generation || !model || !make?.name)",
  "if (!config?.id || !generation?.id || !model?.id || !make?.name)",
  "saved vehicle nested identity guard"
);
page = replaceOnce(
  page,
  "new Date(item.created_at).toLocaleDateString()",
  "item.created_at ? new Date(item.created_at).toLocaleDateString() : \"—\"",
  "optional garage timestamp"
);
page = replaceOnce(
  page,
  "new Date(x.created_at).toLocaleString()",
  "(x.created_at ? new Date(x.created_at).toLocaleString() : \"\")",
  "optional history timestamp"
);
page = replaceOnce(
  page,
  "renameSavedVehicle(item.id,item.nickname)",
  "renameSavedVehicle(item.id,item.nickname || \"\")",
  "optional saved vehicle nickname"
);

if (/\bRecord<string,\s*any>/.test(page)) {
  throw new Error("Permissive Record<string, any> declaration remains in app/page.tsx.");
}
if ((page.match(/useState<IdentifiedDbRow\[\]>\(\[\]\)/g) || []).length !== 7) {
  throw new Error("Identified row state count is not seven after patch.");
}
fs.writeFileSync(pageFile, page, "utf8");

const pkg = JSON.parse(fs.readFileSync(packageFile, "utf8"));
if (!pkg.scripts || typeof pkg.scripts["test:desktop"] !== "string") {
  throw new Error("Desktop test script is missing from package.json.");
}
if (!pkg.scripts["test:desktop"].includes("tests/desktop-dbrow-types.test.cjs")) {
  pkg.scripts["test:desktop"] += " tests/desktop-dbrow-types.test.cjs";
}
fs.writeFileSync(packageFile, JSON.stringify(pkg, null, 2) + "\n", "utf8");

const testContent = [
  '"use strict";',
  'const test = require("node:test");',
  'const assert = require("node:assert/strict");',
  'const fs = require("node:fs");',
  'const path = require("node:path");',
  '',
  'const page = fs.readFileSync(path.join(__dirname, "../app/page.tsx"), "utf8");',
  '',
  'test("Supabase page rows use explicit fields and no permissive any index", () => {',
  '  const start = page.indexOf("type DbRow = {");',
  '  const end = page.indexOf("type IdentifiedDbRow", start);',
  '  assert.ok(start >= 0 && end > start, "explicit DbRow declaration must exist");',
  '  const declaration = page.slice(start, end);',
  '  assert.doesNotMatch(declaration, /\\bany\\b/);',
  '  assert.doesNotMatch(declaration, /\\[key: string\\]/);',
  '  assert.match(page, /type IdentifiedDbRow = DbRow & \\{ id: string \\};/);',
  '  assert.doesNotMatch(page, /Record<string,\\s*any>/);',
  '  assert.doesNotMatch(page, /Date\\.now\\(\\)/);',
  '  assert.match(page, /type DbRelation = DbRow \\| DbRow\\[\\] \\| null \\| undefined;/);',
  '  assert.match(page, /function firstRelation\\(value: DbRelation\\): DbRow \\| null/);',
  '  assert.equal((page.match(/useState<IdentifiedDbRow\\[\\]>\\(\\[\\]\\)/g) || []).length, 7);',
  '});',
  '',
  'test("one-to-many PostgREST relations are normalized before dereferencing", () => {',
  '  assert.match(page, /firstRelation\\(item\\.configuration\\)/);',
  '  assert.match(page, /firstRelation\\(r\\.document\\)/);',
  '  assert.match(page, /firstRelation\\(c\\.engine\\)\\?\\.engine_code/);',
  '  assert.doesNotMatch(page, /c\\?\\.engine\\?\\.engine_code/);',
  '  assert.doesNotMatch(page, /r\\.document\\?\\.title/);',
  '});',
  '',
  'test("saved vehicle navigation guards every required identity before using it", () => {',
  '  assert.match(page, /if \\(!config\\?\\.id \\|\\| !generation\\?\\.id \\|\\| !model\\?\\.id \\|\\| !make\\?\\.name\\)/);',
  '  assert.match(page, /renameSavedVehicle\\(item\\.id,item\\.nickname \\|\\| ""\\)/);',
  '});',
  ''
].join("\n");

if (fs.existsSync(testFile)) {
  const existing = fs.readFileSync(testFile, "utf8");
  if (existing !== testContent) throw new Error("Desktop DbRow regression test already exists with different contents.");
} else {
  fs.writeFileSync(testFile, testContent, "utf8");
}

console.log(JSON.stringify({
  status: "typed_supabase_row_model_applied",
  identifiedStateCollections: 7,
  explicitProperties: 58,
  permissiveAnyRemoved: true,
  regressionTest: "tests/desktop-dbrow-types.test.cjs"
}, null, 2));

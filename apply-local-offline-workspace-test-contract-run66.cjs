"use strict";
const fs = require("node:fs");
const path = require("node:path");
const ROOT = path.resolve(process.cwd(), "desktop-source");
const FILE = path.join(ROOT, "tests", "local-offline-workspace.test.cjs");
function fail(message) { throw new Error(`[run66] ${message}`); }
if (!fs.existsSync(FILE)) fail("local-offline-workspace test file is missing");
let source = fs.readFileSync(FILE, "utf8").replace(/\r\n/g, "\n");
const replacements = [
  [
    '  assert.match(ui, /Ручной выбор · не подтверждено/);',
    '  assert.match(ui, /Ручные значения двигателя и КПП сохраняются без подтверждения применимости/);\n  assert.match(ui, /VIN не обязателен и не сохраняется/);'
  ],
  [
    '  assert.match(ui, /exact_configuration_verified/);',
    '  assert.match(ui, /configuration_match_status !== "declared_codes_match"/);\n  assert.match(ui, /!selectedVehicle\\?\\.configuration_id/);\n  assert.match(ui, /совпадающей конфигурацией из разрешённого источника/);\n  assert.match(ui, /Сам выбор каталожной записи не подтверждает фактическую комплектацию/);'
  ]
];
for (const [before, after] of replacements) {
  if (source.includes(after)) continue;
  const count = source.split(before).length - 1;
  if (count !== 1) fail(`expected one stale assertion anchor, found ${count}: ${before}`);
  source = source.replace(before, after);
}
if (!source.includes('assert.match(ui, /configuration_match_status !== "declared_codes_match"/);')) fail("fail-closed configuration status assertion was not installed");
fs.writeFileSync(FILE, source, "utf8");
console.log(JSON.stringify({status:"patched",file:path.relative(ROOT,FILE),assertions:["manual selection remains unverified without source match","technical lookup requires declared engine and gearbox to match a rights-cleared exact configuration"]},null,2));

"use strict";
const fs = require("node:fs");
const path = require("node:path");
const args = process.argv.slice(2);
const rootIndex = args.indexOf("--desktop-root");
const desktopRoot = path.resolve(rootIndex >= 0 && args[rootIndex + 1] ? args[rootIndex + 1] : "desktop-source");
const componentPath = path.join(desktopRoot, "components", "local-offline-workspace.tsx");
const testPath = path.join(desktopRoot, "tests", "local-offline-workspace.test.cjs");
const read = (file) => fs.readFileSync(file, "utf8").replace(/\r\n/g, "\n");
const write = (file, value) => fs.writeFileSync(file, value.replace(/\n/g, "\r\n"), "utf8");
function replaceRegion(source, startMarker, endMarker, replacement, label, alreadyMarker) {
  if (alreadyMarker && source.includes(alreadyMarker)) return source;
  const start = source.indexOf(startMarker);
  if (start < 0) throw new Error(label + ": start marker not found");
  const end = source.indexOf(endMarker, start);
  if (end < 0) throw new Error(label + ": end marker not found");
  return source.slice(0, start) + replacement + source.slice(end + endMarker.length);
}

let ui = read(componentPath);
const exactMatchBlock = [
  "  const hasRequiredVehicleIdentity = Boolean(",
  "    selectedVehicle &&",
  "    selectedVehicle.generation_name?.trim() &&",
  "    selectedVehicle.market_scope &&",
  '    selectedVehicle.market_scope !== "UNKNOWN" &&',
  "    Number.isInteger(selectedVehicle.model_year) &&",
  "    selectedVehicle.engine_code_declared?.trim() &&",
  "    selectedVehicle.transmission_code_declared?.trim()",
  "  );",
  "  const matchingConfigurations = useMemo(() => selectedVehicle && hasRequiredVehicleIdentity ? verifiedConfigurations.filter((item) => {",
  "    if (normalizeVehicleCode(item.brand_name) !== normalizeVehicleCode(selectedVehicle.brand_name) || normalizeVehicleCode(item.model_name) !== normalizeVehicleCode(selectedVehicle.model_name)) return false;",
  "    if (normalizeVehicleCode(item.generation_name) !== normalizeVehicleCode(selectedVehicle.generation_name)) return false;",
  "    if (!marketScopeIncludes(item.market_scope, selectedVehicle.market_scope)) return false;",
  "    if (item.model_year !== selectedVehicle.model_year) return false;",
  "    if (normalizeVehicleCode(item.engine_code) !== normalizeVehicleCode(selectedVehicle.engine_code_declared)) return false;",
  "    if (normalizeVehicleCode(item.transmission_code) !== normalizeVehicleCode(selectedVehicle.transmission_code_declared)) return false;",
  "    if (selectedVehicle.ecu_declared) {",
  "      const declared = selectedVehicle.ecu_declared.split(/[\\/,;]+/).map(normalizeVehicleCode).filter(Boolean);",
  "      const available = [item.ecu_family, item.hardware_number, item.software_number].map(normalizeVehicleCode).filter(Boolean);",
  "      if (declared.some((token) => !available.includes(token))) return false;",
  "    }",
  "    if (selectedVehicle.pr_codes.some((code) => !item.pr_codes.some((candidate) => normalizeVehicleCode(candidate) === normalizeVehicleCode(code)))) return false;",
  "    return true;",
  "  }) : [], [verifiedConfigurations, selectedVehicle, hasRequiredVehicleIdentity]);",
  "  const canLinkExactConfiguration = Boolean(",
  "    hasRequiredVehicleIdentity &&",
  '    selectedVehicle?.identity_status !== "configuration_no_longer_eligible" &&',
  "    matchingConfigurations.length === 1",
  "  );"
].join("\n");
ui = replaceRegion(
  ui,
  "  const matchingConfigurations = useMemo(() => selectedVehicle ? verifiedConfigurations.filter((item) => {",
  "  }) : [], [verifiedConfigurations, selectedVehicle]);",
  exactMatchBlock,
  "exact configuration UI gate",
  "const canLinkExactConfiguration = Boolean("
);

const oldLinkGuard = '    if (!selectedVehicle.engine_code_declared || !selectedVehicle.transmission_code_declared) { onMessage("Для привязки конфигурации введите фактические коды двигателя и КПП с маркировки автомобиля. Выбор каталожной записи сам по себе не подтверждает комплектацию."); return; }\n';
const newLinkGuard = '    if (!canLinkExactConfiguration || matchingConfigurations[0]?.id !== configurationId) { onMessage("Связь заблокирована: нужны поколение, рынок, год, фактические коды двигателя и КПП и ровно одна совпадающая разрешённая конфигурация. При неоднозначности уточните ECU или PR-коды."); return; }\n';
if (ui.includes(oldLinkGuard)) ui = ui.replace(oldLinkGuard, newLinkGuard);
else if (!ui.includes("if (!canLinkExactConfiguration || matchingConfigurations[0]?.id !== configurationId)")) throw new Error("linkConfiguration guard: expected original guard not found");

const selectorStart = '      {selectedVehicle && matchingConfigurations.length > 0 ? <label className="local-config-select">';
const selectorEnd = " : null}";
const newSelector = [
  '      {selectedVehicle && matchingConfigurations.length === 1 ? <label className="local-config-select">Конфигурация каталога<select disabled={!canLinkExactConfiguration} value={selectedVehicle.configuration_id === matchingConfigurations[0].id ? String(selectedVehicle.configuration_id) : ""} onChange={(e) => { if (e.target.value) void linkConfiguration(Number(e.target.value)); }}><option value="">Выберите единственную точную конфигурацию</option><option value={matchingConfigurations[0].id}>{[matchingConfigurations[0].generation_name,matchingConfigurations[0].market_scope,matchingConfigurations[0].model_year ? "MY " + matchingConfigurations[0].model_year : null,matchingConfigurations[0].engine_code,matchingConfigurations[0].transmission_code,matchingConfigurations[0].ecu_family,matchingConfigurations[0].hardware_number,matchingConfigurations[0].pr_codes.length ? "PR " + matchingConfigurations[0].pr_codes.join("/") : null].filter(Boolean).join(" · ")}</option></select><small>Совпали поколение, рынок, год и заявленные коды двигателя/КПП. Это не независимая проверка фактической комплектации.</small></label>',
  '        : selectedVehicle && matchingConfigurations.length > 1 ? <p className="local-note">Найдено несколько конфигураций. Связь и VAG-specific поиск заблокированы; уточните ECU или PR-коды, чтобы получить единственное совпадение.</p>',
  '        : selectedVehicle && !hasRequiredVehicleIdentity ? <p className="local-note">Для точного выбора укажите поколение, рынок, год модели, фактический код двигателя и фактический код КПП. VIN не обязателен. Без этих полей связь и VAG-specific поиск заблокированы.</p>',
  '        : selectedVehicle ? <p className="local-note">Нет единственной совпадающей конфигурации из разрешённого источника. Проверьте введённые данные и источники каталога.</p> : null}'
].join("\n");
if (ui.includes(selectorStart)) ui = replaceRegion(ui, selectorStart, selectorEnd, newSelector, "configuration selector UI");
else if (!ui.includes('matchingConfigurations.length === 1 ? <label className="local-config-select">')) throw new Error("configuration selector UI: expected original block not found");

const oldSearchDisabled = 'disabled={searching || selectedVehicle?.configuration_match_status !== "declared_codes_match"}';
const newSearchDisabled = 'disabled={searching || !canLinkExactConfiguration || selectedVehicle?.configuration_match_status !== "declared_codes_match"}';
if (ui.includes(oldSearchDisabled)) ui = ui.replace(oldSearchDisabled, newSearchDisabled);
else if (!ui.includes(newSearchDisabled)) throw new Error("technical search gate: original disabled expression not found");
ui = ui.replace(
  'onMessage("Выбрана конфигурация каталога: заявленные коды двигателя и КПП совпали. Это не заменяет проверку ECU и PR-кодов на автомобиле.");',
  'onMessage("Выбрана единственная конфигурация: поколение, рынок, год и заявленные коды совпали. Это не является независимой проверкой фактического автомобиля.");'
);
ui = ui.replace('"Коды ДВС/КПП заявлены пользователем и совпадают с конфигурацией каталога"', '"Заявленные параметры совпадают с одной разрешённой конфигурацией; автомобиль независимо не проверен"');
ui = ui.replace('"Коды двигателя и КПП совпадают с выбранной конфигурацией каталога"', '"Заявленные параметры совпадают с одной точной конфигурацией каталога"');
write(componentPath, ui);

let contract = read(testPath);
const legacyAssertions = [
  '  assert.match(ui, /!selectedVehicle\\.generation_name/);\n',
  '  assert.match(ui, /!selectedVehicle\\.model_year/);\n',
  '  assert.match(ui, /selectedVehicle\\.market_scope === "UNKNOWN"/);\n',
  '  assert.match(ui, /!selectedVehicle\\?\\.configuration_id/);\n',
  '  assert.match(ui, /совпадающей конфигурацией из разрешённого источника/);\n',
  '  assert.match(ui, /Сам выбор каталожной записи не подтверждает фактическую комплектацию/);\n',
  '  assert.match(ui, /Кандидаты.*не подставляются/);\n'
];
for (const legacy of legacyAssertions) contract = contract.replace(legacy, "");
const anchor = '  assert.match(ui, /const canLinkExactConfiguration = Boolean/);\n';
const additions = [
  anchor.trimEnd(),
  '  assert.match(ui, /selectedVehicle\\.generation_name\\?\\.trim\\(\\)/);',
  '  assert.match(ui, /selectedVehicle\\.market_scope !== "UNKNOWN"/);',
  '  assert.match(ui, /Number\\.isInteger\\(selectedVehicle\\.model_year\\)/);',
  '  assert.match(ui, /selectedVehicle\\.engine_code_declared\\?\\.trim\\(\\)/);',
  '  assert.match(ui, /selectedVehicle\\.transmission_code_declared\\?\\.trim\\(\\)/);',
  '  assert.match(ui, /matchingConfigurations\\.length === 1/);',
  '  assert.match(ui, /matchingConfigurations\\.length > 1/);',
  '  assert.match(ui, /disabled={!canLinkExactConfiguration}/);',
  '  assert.match(ui, /if \\(!canLinkExactConfiguration \\|\\| matchingConfigurations\\[0\\]\\?\\.id !== configurationId\\)/);',
  '  assert.match(ui, /разрешённого источника/);',
  '  assert.match(ui, /не является независимой проверкой/);',
  '  assert.match(ui, /Кандидаты не используются для ремонта/);'
].join("\n") + "\n";
if (!contract.includes("matchingConfigurations\\.length === 1")) {
  if (!contract.includes(anchor)) throw new Error("UI contract test anchor not found");
  contract = contract.replace(anchor, additions);
}
write(testPath, contract);

console.log(JSON.stringify({ status: "patched", complete_identity_required: true, unique_match_required: true, ambiguous_match_blocked: true, technical_lookup_requires_unique_match: true }, null, 2));

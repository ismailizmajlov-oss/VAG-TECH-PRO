const fs = require("node:fs");
const path = require("node:path");

const args = process.argv.slice(2);
const desktopIndex = args.indexOf("--desktop-root");
const desktopRoot = path.resolve(desktopIndex >= 0 ? args[desktopIndex + 1] : "desktop-source");
const lifecyclePath = path.join(desktopRoot, "scripts", "windows-installer-lifecycle.ps1");
const contractTestPath = path.join(desktopRoot, "tests", "windows-lifecycle-script-contract.test.cjs");
if (!fs.existsSync(lifecyclePath)) throw new Error("Windows lifecycle script is missing.");
if (!fs.existsSync(contractTestPath)) throw new Error("Windows lifecycle contract test is missing.");

let lifecycle = fs.readFileSync(lifecyclePath, "utf8");
const functionStart = lifecycle.search(/function\s+Start-DesktopAndWait\b/i);
if (functionStart < 0) throw new Error("Start-DesktopAndWait function was not found.");
const functionOpen = lifecycle.indexOf("{", functionStart);
if (functionOpen < 0) throw new Error("Start-DesktopAndWait function body was not found.");
const functionHeader = lifecycle.slice(functionStart, functionOpen + 1);
const inlineParams = functionHeader.match(/function\s+Start-DesktopAndWait\s*\(([^)]*)\)/i);
if (inlineParams) {
  if (!/\$ExpectRdwPack\b/i.test(inlineParams[1])) {
    const params = inlineParams[1].trim();
    const next = params ? params + ", [bool]$ExpectRdwPack = $false" : "[bool]$ExpectRdwPack = $false";
    lifecycle = lifecycle.slice(0, functionStart) +
      functionHeader.replace(inlineParams[0], "function Start-DesktopAndWait(" + next + ")") +
      lifecycle.slice(functionOpen + 1);
  }
} else {
  const bodyPrefix = lifecycle.slice(functionOpen + 1, functionOpen + 1800);
  const paramMatch = /^(\s*)param\s*\(([\s\S]*?)\)/im.exec(bodyPrefix);
  if (paramMatch) {
    if (!/\$ExpectRdwPack\b/i.test(paramMatch[2])) {
      const params = paramMatch[2].trim();
      const next = params ? params + ",\n    [bool]$ExpectRdwPack = $false" : "[bool]$ExpectRdwPack = $false";
      const replacement = paramMatch[1] + "param(" + next + ")";
      const absoluteStart = functionOpen + 1 + paramMatch.index;
      lifecycle = lifecycle.slice(0, absoluteStart) + replacement +
        lifecycle.slice(absoluteStart + paramMatch[0].length);
    }
  } else {
    lifecycle = lifecycle.slice(0, functionOpen + 1) +
      "\n  param([bool]$ExpectRdwPack = $false)\n" +
      lifecycle.slice(functionOpen + 1);
  }
}

const rdwMarker = "# RDW CC0 data is an independent EU/NL candidate pack;";
const genericMarker = "# generic_repair_guidance is a separate local SQLite pack";
const rdwStart = lifecycle.indexOf(rdwMarker);
const genericStart = rdwStart >= 0 ? lifecycle.indexOf(genericMarker, rdwStart) : -1;
if (rdwStart < 0 || genericStart < 0 || genericStart <= rdwStart) {
  throw new Error("RDW lifecycle verification block boundaries are missing.");
}
const rdwBlock = lifecycle.slice(rdwStart, genericStart);
if (!rdwBlock.includes("if ($ExpectRdwPack) {")) {
  const indented = rdwBlock.split(/\r?\n/).map((line) => line ? "  " + line : line).join("\n");
  const wrapped = "  if ($ExpectRdwPack) {\n" + indented + "\n  }\n";
  lifecycle = lifecycle.slice(0, rdwStart) + wrapped + lifecycle.slice(genericStart);
}

const upgradeMarker = "# 4. Upgrade over the previous version and verify the SQLite user data survives.";
const upgradeStart = lifecycle.indexOf(upgradeMarker);
if (upgradeStart < 0) throw new Error("Upgrade lifecycle section is missing.");
const upgradeTail = lifecycle.slice(upgradeStart);
if (!upgradeTail.includes("$session = Start-DesktopAndWait -ExpectRdwPack $true")) {
  const call = /\$session\s*=\s*Start-DesktopAndWait(?!\s+-ExpectRdwPack)/i.exec(upgradeTail);
  if (!call) throw new Error("Upgrade lifecycle Start-DesktopAndWait call is missing.");
  const updatedTail = upgradeTail.slice(0, call.index) +
    upgradeTail.slice(call.index).replace(
      /\$session\s*=\s*Start-DesktopAndWait/i,
      "$session = Start-DesktopAndWait -ExpectRdwPack $true"
    );
  lifecycle = lifecycle.slice(0, upgradeStart) + updatedTail;
}
fs.writeFileSync(lifecyclePath, lifecycle, "utf8");

let contractTests = fs.readFileSync(contractTestPath, "utf8");
const testMarker = 'require("node:test").test("RDW candidate pack is checked after upgrade, not during the older clean install"';
if (!contractTests.includes(testMarker)) {
  const testBlock = [
    "",
    'require("node:test").test("RDW candidate pack is checked after upgrade, not during the older clean install", () => {',
    '  const assert = require("node:assert/strict");',
    '  const fs = require("node:fs");',
    '  const path = require("node:path");',
    '  const lifecycle = fs.readFileSync(path.join(__dirname, "..", "scripts", "windows-installer-lifecycle.ps1"), "utf8");',
    '  assert.match(lifecycle, /function\\s+Start-DesktopAndWait\\b/i);',
    '  assert.match(lifecycle, /\\$ExpectRdwPack\\s*=\\s*\\$false/i);',
    '  const firstInstallStart = lifecycle.indexOf("# 1. Clean install and first offline launch.");',
    '  const userDataStart = lifecycle.indexOf("# 2. Create real user data and a validated backup.");',
    '  const firstInstall = lifecycle.slice(firstInstallStart, userDataStart);',
    '  assert.ok(firstInstall.includes("$session = Start-DesktopAndWait"));',
    '  assert.ok(!firstInstall.includes("ExpectRdwPack"));',
    '  const gate = lifecycle.indexOf("if ($ExpectRdwPack) {");',
    '  const rdwStart = lifecycle.indexOf("# RDW CC0 data is an independent EU/NL candidate pack;");',
    '  const genericStart = lifecycle.indexOf("# generic_repair_guidance is a separate local SQLite pack");',
    '  assert.ok(gate >= 0 && rdwStart > gate && genericStart > rdwStart);',
    '  const upgradeStart = lifecycle.indexOf("# 4. Upgrade over the previous version and verify the SQLite user data survives.");',
    '  assert.ok(lifecycle.slice(upgradeStart).includes("$session = Start-DesktopAndWait -ExpectRdwPack $true"));',
    '});',
    ""
  ].join("\n");
  contractTests += testBlock;
  fs.writeFileSync(contractTestPath, contractTests, "utf8");
}
console.log("RDW lifecycle version gate applied and verified.");

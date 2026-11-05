const fs = require("node:fs");
const path = require("node:path");

const args = process.argv.slice(2);
const desktopIndex = args.indexOf("--desktop-root");
const desktopRoot = path.resolve(desktopIndex >= 0 ? args[desktopIndex + 1] : "desktop-source");
const lifecyclePath = path.join(desktopRoot, "scripts", "windows-installer-lifecycle.ps1");
const contractTestPath = path.join(desktopRoot, "tests", "windows-lifecycle-script-contract.test.cjs");
if (!fs.existsSync(contractTestPath)) throw new Error("Windows lifecycle contract test is missing.");
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
    '  assert.ok(lifecycle.includes("function Start-DesktopAndWait([bool]$ExpectRdwPack = $false) {"));',
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
console.log("RDW lifecycle version gate applied.");

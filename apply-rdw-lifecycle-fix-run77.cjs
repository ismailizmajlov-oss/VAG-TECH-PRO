"use strict";

const fs = require("node:fs");
const path = require("node:path");

const args = process.argv.slice(2);
const desktopIndex = args.indexOf("--desktop-root");
const desktopRoot = path.resolve(desktopIndex >= 0 ? args[desktopIndex + 1] : "desktop-source");
const lifecyclePath = path.join(desktopRoot, "scripts", "windows-installer-lifecycle.ps1");
const contractTestPath = path.join(desktopRoot, "tests", "windows-lifecycle-script-contract.test.cjs");

function replaceExactlyOnce(source, before, after, label) {
  if (source.includes(after)) return source;
  const count = source.split(before).length - 1;
  if (count !== 1) throw new Error(label + ": expected exactly one anchor, found " + count);
  return source.replace(before, after);
}

if (!fs.existsSync(lifecyclePath)) throw new Error("Windows installer lifecycle script is missing.");
if (!fs.existsSync(contractTestPath)) throw new Error("Windows lifecycle contract test is missing.");

let lifecycle = fs.readFileSync(lifecyclePath, "utf8").replace(/\r\n/g, "\n");
lifecycle = replaceExactlyOnce(
  lifecycle,
  "function Start-DesktopAndWait {",
  "function Start-DesktopAndWait([bool]$ExpectRdwPack = $false) {",
  "RDW lifecycle function parameter"
);

const rdwStartMarker = "  # RDW CC0 data is an independent EU/NL candidate pack;";
const genericStartMarker = "  # generic_repair_guidance is a separate local SQLite pack";
const rdwStart = lifecycle.indexOf(rdwStartMarker);
const genericStart = lifecycle.indexOf(genericStartMarker, rdwStart + 1);
if (rdwStart < 0 || genericStart < 0 || genericStart <= rdwStart) {
  throw new Error("RDW lifecycle block boundaries are missing or out of order.");
}
const rdwBlock = lifecycle.slice(rdwStart, genericStart);
if (!rdwBlock.includes("if ($ExpectRdwPack) {")) {
  const wrapped = "  if ($ExpectRdwPack) {\n" + rdwBlock + "  }\n";
  lifecycle = lifecycle.slice(0, rdwStart) + wrapped + lifecycle.slice(genericStart);
}

const upgradeMarker = "# 4. Upgrade over the previous version and verify the SQLite user data survives.";
const upgradeStart = lifecycle.indexOf(upgradeMarker);
if (upgradeStart < 0) throw new Error("Windows lifecycle upgrade section is missing.");
const beforeUpgrade = lifecycle.slice(0, upgradeStart);
let afterUpgrade = lifecycle.slice(upgradeStart);
afterUpgrade = replaceExactlyOnce(
  afterUpgrade,
  "$session = Start-DesktopAndWait\n",
  "$session = Start-DesktopAndWait -ExpectRdwPack $true\n",
  "RDW post-upgrade lifecycle call"
);
lifecycle = beforeUpgrade + afterUpgrade;
fs.writeFileSync(lifecyclePath, lifecycle, "utf8");

let contractTests = fs.readFileSync(contractTestPath, "utf8").replace(/\r\n/g, "\n");
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

console.log("RDW lifecycle gate applied: the 0.2.4 clean install is not required to contain the 0.2.5 RDW pack; the upgraded install is.");

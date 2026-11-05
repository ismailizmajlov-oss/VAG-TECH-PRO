const fs = require("node:fs");
const path = require("node:path");

const args = process.argv.slice(2);
const desktopIndex = args.indexOf("--desktop-root");
const desktopRoot = path.resolve(desktopIndex >= 0 ? args[desktopIndex + 1] : "desktop-source");
const lifecyclePath = path.join(desktopRoot, "scripts", "windows-installer-lifecycle.ps1");
const testPath = path.join(desktopRoot, "tests", "rdw-lifecycle-version-gate.test.cjs");
if (!fs.existsSync(lifecyclePath)) throw new Error("Windows lifecycle script is missing from the assembled desktop source.");

let source = fs.readFileSync(lifecyclePath, "utf8");
const oldSignature = "function Start-DesktopAndWait {";
const newSignature = "function Start-DesktopAndWait([bool]$ExpectRdwPack = $false) {";
if (source.includes(oldSignature)) source = source.replace(oldSignature, newSignature);
if (!source.includes(newSignature)) throw new Error("Could not pin the lifecycle RDW expectation parameter.");

const rdwStartMarker = "  # RDW CC0 data is an independent EU/NL candidate pack;";
const genericMarker = "  # generic_repair_guidance is a separate local SQLite pack";
const rdwStart = source.indexOf(rdwStartMarker);
const genericStart = source.indexOf(genericMarker, rdwStart + 1);
if (rdwStart < 0 || genericStart < 0 || genericStart <= rdwStart) {
  throw new Error("Could not isolate the RDW-only lifecycle assertions.");
}
const preceding = source.slice(Math.max(0, rdwStart - 120), rdwStart);
if (!preceding.includes("if ($ExpectRdwPack)")) {
  const block = source.slice(rdwStart, genericStart).trimEnd();
  const indented = block.split(/\r?\n/).map((line) => "  " + line).join("\n");
  source = source.slice(0, rdwStart) + "  if ($ExpectRdwPack) {\n" + indented + "\n  }\n" + source.slice(genericStart);
}

const upgradeMarker = "# 4. Upgrade over the previous version and verify the SQLite user data survives.";
const upgradeStart = source.indexOf(upgradeMarker);
if (upgradeStart < 0) throw new Error("Could not find the upgrade lifecycle phase.");
const upgradeTail = source.slice(upgradeStart);
const oldUpgradeCall = "$session = Start-DesktopAndWait";
if (!upgradeTail.includes(oldUpgradeCall)) throw new Error("Could not find the post-upgrade desktop launch.");
source = source.slice(0, upgradeStart) + upgradeTail.replace(oldUpgradeCall, "$session = Start-DesktopAndWait -ExpectRdwPack $true");

const firstInstallStart = source.indexOf("# 1. Clean install and first offline launch.");
const userDataStart = source.indexOf("# 2. Create real user data and a validated backup.");
const firstInstallBlock = source.slice(firstInstallStart, userDataStart);
if (!firstInstallBlock.includes("$session = Start-DesktopAndWait") || firstInstallBlock.includes("-ExpectRdwPack")) {
  throw new Error("The clean-install phase must not require the later RDW pack.");
}
if (!source.slice(upgradeStart).includes("$session = Start-DesktopAndWait -ExpectRdwPack $true")) {
  throw new Error("The upgraded 0.2.5 phase must verify the RDW pack.");
}

fs.writeFileSync(lifecyclePath, source, "utf8");
fs.mkdirSync(path.dirname(testPath), { recursive: true });
const testSource = [
  'const test = require("node:test");',
  'const assert = require("node:assert/strict");',
  'const fs = require("node:fs");',
  'const path = require("node:path");',
  '',
  'const lifecycle = fs.readFileSync(path.join(__dirname, "..", "scripts", "windows-installer-lifecycle.ps1"), "utf8");',
  '',
  'test("RDW candidate pack is checked after upgrade, not during the older clean install", () => {',
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
  ''
].join("\n");
fs.writeFileSync(testPath, testSource, "utf8");
console.log("RDW lifecycle version gate applied.");

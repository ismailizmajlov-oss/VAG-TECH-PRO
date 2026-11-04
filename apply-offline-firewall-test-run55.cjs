"use strict";
const fs = require("node:fs");
const path = require("node:path");

const root = path.resolve(process.cwd(), "desktop-source");
const lifecyclePath = path.join(root, "scripts", "windows-installer-lifecycle.ps1");
const packagePath = path.join(root, "package.json");
const testPath = path.join(root, "tests", "windows-offline-firewall-contract.test.cjs");

function replaceOnce(source, before, after, label) {
  const count = source.split(before).length - 1;
  if (count !== 1) throw new Error(label + ": expected one anchor, found " + count);
  return source.replace(before, after);
}

if (!fs.existsSync(lifecyclePath) || !fs.existsSync(packagePath)) {
  throw new Error("Desktop lifecycle script or package.json is missing");
}

let lifecycle = fs.readFileSync(lifecyclePath, "utf8");
if (!lifecycle.includes("VAG TECH PRO Offline IPv4")) {
  const start = "# 1. Clean install and first offline launch.\nInstall-NSIS $InstallerPath\n";
  const insert = start + [
    "$offlineFirewallRuleNames = @()",
    "try {",
    "  $ruleV4 = New-NetFirewallRule -DisplayName \"VAG TECH PRO Offline IPv4 $PID\" -Direction Outbound -Program $appExe -Action Block -Profile Any -RemoteAddress @(\"0.0.0.0-126.255.255.255\", \"128.0.0.0-255.255.255.255\")",
    "  $offlineFirewallRuleNames += $ruleV4.Name",
    "  $ruleV6 = New-NetFirewallRule -DisplayName \"VAG TECH PRO Offline IPv6 $PID\" -Direction Outbound -Program $appExe -Action Block -Profile Any -RemoteAddress @(\"::/1\", \"8000::/1\")",
    "  $offlineFirewallRuleNames += $ruleV6.Name",
    "  foreach ($ruleName in $offlineFirewallRuleNames) {",
    "    if (-not (Get-NetFirewallRule -Name $ruleName -ErrorAction SilentlyContinue)) { throw \"Offline firewall rule was not activated: $ruleName\" }",
    "  }"
  ].join("\n") + "\n";
  lifecycle = replaceOnce(lifecycle, start, insert, "offline firewall insertion");
}
const oldEnd = 'Write-Output "Windows x64 clean install, offline launch, SQLite backup/restore, in-place upgrade, integrity and uninstall-preservation checks passed."';
const newEnd = [
  '  Write-Output "Windows x64 clean install, external-network-blocked offline launch, SQLite backup/restore, in-place upgrade, integrity and uninstall-preservation checks passed."',
  "} finally {",
  "  foreach ($ruleName in $offlineFirewallRuleNames) {",
  "    Remove-NetFirewallRule -Name $ruleName -ErrorAction SilentlyContinue",
  "  }",
  "}"
].join("\n");
if (!lifecycle.includes("external-network-blocked offline launch")) {
  lifecycle = replaceOnce(lifecycle, oldEnd, newEnd, "offline firewall cleanup");
}
if (!lifecycle.includes("New-NetFirewallRule") || !lifecycle.includes('RemoteAddress @("::/1", "8000::/1")') || !lifecycle.includes("Remove-NetFirewallRule -Name $ruleName")) {
  throw new Error("Offline network-isolation contract is incomplete");
}
fs.writeFileSync(lifecyclePath, lifecycle, "utf8");

const pkg = JSON.parse(fs.readFileSync(packagePath, "utf8"));
const testName = "tests/windows-offline-firewall-contract.test.cjs";
if (typeof pkg.scripts?.["test:desktop"] !== "string") throw new Error("Desktop test script is missing");
if (!pkg.scripts["test:desktop"].includes(testName)) pkg.scripts["test:desktop"] += " " + testName;
fs.writeFileSync(packagePath, JSON.stringify(pkg, null, 2) + "\n", "utf8");

const test = [
  '"use strict";',
  'const fs = require("node:fs");',
  'const path = require("node:path");',
  'const test = require("node:test");',
  'const assert = require("node:assert/strict");',
  'const script = fs.readFileSync(path.resolve(__dirname, "../scripts/windows-installer-lifecycle.ps1"), "utf8");',
  'test("Windows lifecycle blocks external IPv4 while preserving the 127/8 loopback range", () => {',
  '  assert.match(script, /New-NetFirewallRule[^\\n]*Offline IPv4/);',
  '  assert.match(script, /RemoteAddress\\s+@\\("0\\.0\\.0\\.0-126\\.255\\.255\\.255",\\s*"128\\.0\\.0\\.0-255\\.255\\.255\\.255"\\)/);',
  '  assert.doesNotMatch(script, /RemoteAddress\\s+"0\\.0\\.0\\.0\\/0"/);',
  '});',
  'test("Windows lifecycle blocks IPv6 and always removes temporary firewall rules", () => {',
  '  assert.ok(script.includes(\'RemoteAddress @("::/1", "8000::/1")\'));',
  '  assert.match(script, /finally\\s*\\{[\\s\\S]*Remove-NetFirewallRule -Name \\$ruleName/);',
  '});'
].join("\n") + "\n";
fs.writeFileSync(testPath, test, "utf8");

process.stdout.write(JSON.stringify({
  lifecycle: "external IPv4 and IPv6 blocked for app executable during install/backup/restore/upgrade/uninstall lifecycle",
  loopback: "127.0.0.0/8 excluded from IPv4 block; desktop server binds to IPv4 loopback, while two valid IPv6 /1 prefixes block all IPv6 egress",
  cleanup: "firewall rules removed in finally",
  test: testName,
  desktopTestScript: pkg.scripts["test:desktop"]
}, null, 2));

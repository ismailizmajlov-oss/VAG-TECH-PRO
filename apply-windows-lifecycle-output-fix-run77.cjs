'use strict';
const fs = require('node:fs');
const path = require('node:path');

const rootArg = process.argv.indexOf('--desktop-root');
const root = rootArg >= 0 ? path.resolve(process.argv[rootArg + 1]) : path.resolve('desktop-source');
const scriptPath = path.join(root, 'scripts', 'windows-installer-lifecycle.ps1');
const testPath = path.join(root, 'tests', 'windows-lifecycle-script-contract.test.cjs');
if (!fs.existsSync(scriptPath) || !fs.existsSync(testPath)) {
  throw new Error('Expected Windows lifecycle script and contract test are missing.');
}

let lifecycle = fs.readFileSync(scriptPath, 'utf8');
const oldStatus = '  Write-Output "ASTRA offline CH approval search passed; no VAG factory fitment or repair claims."';
const newStatus = '  Write-Host "ASTRA offline CH approval search passed; no VAG factory fitment or repair claims."';
let statusOutputChanged = false;
if (lifecycle.includes(oldStatus)) {
  lifecycle = lifecycle.replace(oldStatus, newStatus);
  statusOutputChanged = true;
}
const helper = lifecycle.split("function Start-DesktopAndWait {")[1]?.split("function Stop-Desktop($session) {")[0];
if (!helper || helper.includes("Write-Output") || !helper.includes("return @{ Process = $process; BaseUrl = $baseUrl }")) {
  throw new Error("Start-DesktopAndWait must return one session object and emit no incidental success-pipeline output.");
}
if (!lifecycle.includes("$session -isnot [System.Collections.IDictionary]") || lifecycle.includes("$origin = $session.BaseUrl")) {
  throw new Error("Windows lifecycle session-object validation was not applied.");
}
if (statusOutputChanged) fs.writeFileSync(scriptPath, lifecycle, 'utf8');

let tests = fs.readFileSync(testPath, 'utf8');
const testName = 'Start-DesktopAndWait returns one session object without incidental pipeline output';
if (!tests.includes(testName)) {
  tests += `\n\ntest(${JSON.stringify(testName)}, () => {\n  const helper = script.split("function Start-DesktopAndWait {")[1]?.split("function Stop-Desktop($session) {")[0];\n  assert.ok(helper, "Start-DesktopAndWait helper must exist");\n  assert.doesNotMatch(helper, /\\bWrite-Output\\b/);\n  assert.match(helper, /return \\@\\{ Process = \\$process; BaseUrl = \\$baseUrl \\}/);\n  assert.match(script, /\\$session -isnot \\[System\\.Collections\\.IDictionary\\]/);\n  assert.match(script, /\\$session\\[.BaseUrl.\\]/);\n});\n`;
  fs.writeFileSync(testPath, tests, 'utf8');
}
const updatedLifecycle = fs.readFileSync(scriptPath, 'utf8');
const updatedHelper = updatedLifecycle.split("function Start-DesktopAndWait {")[1]?.split("function Stop-Desktop($session) {")[0];
const updatedTests = fs.readFileSync(testPath, 'utf8');
if (!updatedHelper || updatedHelper.includes("Write-Output") || !updatedHelper.includes("return @{ Process = $process; BaseUrl = $baseUrl }") || !updatedTests.includes(testName)) {
  throw new Error('Run77 lifecycle output contract postcondition failed.');
}
process.stdout.write(JSON.stringify({
  status: 'verified',
  fix: 'Start-DesktopAndWait success pipeline contains only the session object',
  astraStatusOutputChanged: statusOutputChanged,
  files: ['scripts/windows-installer-lifecycle.ps1', 'tests/windows-lifecycle-script-contract.test.cjs']
}, null, 2) + '\n');

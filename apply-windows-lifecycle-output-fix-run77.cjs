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
if (lifecycle.includes(oldStatus)) {
  lifecycle = lifecycle.replace(oldStatus, newStatus);
} else if (!lifecycle.includes(newStatus)) {
  throw new Error('Lifecycle status-output statement did not match the reviewed source revision.');
}
fs.writeFileSync(scriptPath, lifecycle, 'utf8');

let tests = fs.readFileSync(testPath, 'utf8');
const testName = 'Windows lifecycle readiness helper emits one session object without pipeline noise';
if (!tests.includes(testName)) {
  tests += `\n\ntest(${JSON.stringify(testName)}, () => {\n  const match = script.match(/function Start-DesktopAndWait\\s*\\{([\\s\\S]*?)\\n\\}/);\n  assert.ok(match, "Start-DesktopAndWait function must exist");\n  assert.doesNotMatch(match[1], /\\bWrite-Output\\b/, "status messages must not enter the function success pipeline");\n  assert.match(match[1], /Write-Host "ASTRA offline CH approval search passed; no VAG factory fitment or repair claims\\."/);\n  assert.match(match[1], /return \\@\\{ Process = \\$process; BaseUrl = \\$baseUrl \\}/);\n});\n`;
}
fs.writeFileSync(testPath, tests, 'utf8');

const updatedLifecycle = fs.readFileSync(scriptPath, 'utf8');
const updatedTests = fs.readFileSync(testPath, 'utf8');
if (updatedLifecycle.includes(oldStatus) || !updatedLifecycle.includes(newStatus) || !updatedTests.includes(testName)) {
  throw new Error('Run77 lifecycle output patch postcondition failed.');
}
process.stdout.write(JSON.stringify({
  status: 'patched',
  fix: 'Start-DesktopAndWait status message moved from success pipeline to host stream',
  files: ['scripts/windows-installer-lifecycle.ps1', 'tests/windows-lifecycle-script-contract.test.cjs']
}, null, 2) + '\n');

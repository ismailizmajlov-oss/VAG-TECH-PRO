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
const statusFixes = [
  {
    marker: 'ASTRA offline CH approval search passed',
    oldLine: '  Write-Output "ASTRA offline CH approval search passed; no VAG factory fitment or repair claims."',
    newLine: '  Write-Host "ASTRA offline CH approval search passed; no VAG factory fitment or repair claims."'
  },
  {
    marker: 'ASTRA TARGA offline CH source-row search passed',
    oldLine: '  Write-Output "ASTRA TARGA offline CH source-row search passed; no OEM pair, RU/EAEU fitment or repair claims."',
    newLine: '  Write-Host "ASTRA TARGA offline CH source-row search passed; no OEM pair, RU/EAEU fitment or repair claims."'
  }
];

for (const fix of statusFixes) {
  const oldCount = lifecycle.split(fix.oldLine).length - 1;
  const newCount = lifecycle.split(fix.newLine).length - 1;
  if (oldCount === 1 && newCount === 0) {
    lifecycle = lifecycle.replace(fix.oldLine, fix.newLine);
  } else if (oldCount !== 0 || newCount !== 1) {
    throw new Error('Lifecycle status-output statement is missing, duplicated or has an unexpected form: ' + fix.marker);
  }
}

const helperStartToken = 'function Start-DesktopAndWait {';
const helperEndToken = '\nfunction Stop-Desktop($session) {';
const helperStart = lifecycle.indexOf(helperStartToken);
const helperEnd = lifecycle.indexOf(helperEndToken, helperStart);
if (helperStart < 0 || helperEnd < 0) {
  throw new Error('Start-DesktopAndWait helper boundaries could not be located.');
}
const helper = lifecycle.slice(helperStart, helperEnd);
if (helper.includes('Write-Output')) {
  throw new Error('Start-DesktopAndWait still emits incidental PowerShell success-pipeline output.');
}
fs.writeFileSync(scriptPath, lifecycle, 'utf8');

const updatedLifecycle = fs.readFileSync(scriptPath, 'utf8');
const updatedHelperStart = updatedLifecycle.indexOf(helperStartToken);
const updatedHelperEnd = updatedLifecycle.indexOf(helperEndToken, updatedHelperStart);
const updatedHelper = updatedLifecycle.slice(updatedHelperStart, updatedHelperEnd);
for (const fix of statusFixes) {
  const lines = updatedLifecycle.split(/\r?\n/).filter((line) => line.includes(fix.marker));
  if (lines.length !== 1 || !/\bWrite-(Host|Verbose)\b/.test(lines[0])) {
    throw new Error('Run77 lifecycle output postcondition failed: ' + fix.marker);
  }
}
if (!updatedHelper || updatedHelper.includes('Write-Output')) {
  throw new Error('Run77 lifecycle output patch postcondition failed.');
}

process.stdout.write(JSON.stringify({
  status: 'patched',
  fix: 'Start-DesktopAndWait emits one session object; ASTRA and ASTRA TARGA status messages use the host stream, not the success pipeline',
  files: ['scripts/windows-installer-lifecycle.ps1', 'tests/windows-lifecycle-script-contract.test.cjs']
}, null, 2) + '\n');

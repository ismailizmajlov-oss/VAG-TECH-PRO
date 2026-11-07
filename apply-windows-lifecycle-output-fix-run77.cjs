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
  } else if (oldCount !== 0 || newCount > 1) {
    throw new Error(`Lifecycle status-output statement is duplicated or has an unexpected form: ${fix.marker}`);
  }
}
const helperMatch = lifecycle.match(/function Start-DesktopAndWait\\s*\\{([\\s\\S]*?)\\n\\}/);
if (!helperMatch || /\\bWrite-Output\\b/.test(helperMatch[1])) {
  throw new Error('Start-DesktopAndWait still emits incidental PowerShell success-pipeline output.');
}
fs.writeFileSync(scriptPath, lifecycle, 'utf8');

let tests = fs.readFileSync(testPath, 'utf8');
const testName = 'Windows lifecycle readiness helper emits one session object without pipeline noise';
if (!tests.includes(testName)) {
  tests += `\\n\\ntest(${JSON.stringify(testName)}, () => {\\n  const match = script.match(/function Start-DesktopAndWait\\\\s*\\\\{([\\\\s\\\\S]*?)\\\\n\\\\}/);\\n  assert.ok(match, "Start-DesktopAndWait function must exist");\\n  assert.doesNotMatch(match[1], /\\\\bWrite-Output\\\\b/, "status messages must not enter the function success pipeline");\\n  const statusMarkers = ["ASTRA offline CH approval search passed", "ASTRA TARGA offline CH source-row search passed"];\\n  for (const marker of statusMarkers) {\\n    const lines = script.split(/\\\\r?\\\\n/).filter((line) => line.includes(marker));\\n    assert.ok(lines.length <= 1, `${marker} status line must not be duplicated`);\\n    for (const line of lines) assert.match(line, /\\\\bWrite-(Host|Verbose)\\\\b/, `${marker} status must not enter the success pipeline`);\\n  }\\n  assert.match(match[1], /return \\\\@\\\\{ Process = \\\\$process; BaseUrl = \\\\$baseUrl \\\\}/);\\n});\\n`;
} else if (!tests.includes('ASTRA TARGA offline CH source-row search passed')) {
  const oldAssertion = '  const astraStatusLines = script.split(/\\r?\\n/).filter((line) => line.includes("ASTRA offline CH approval search passed"));';
  const newAssertion = '  const statusMarkers = ["ASTRA offline CH approval search passed", "ASTRA TARGA offline CH source-row search passed"];\\n  for (const marker of statusMarkers) {\\n    const lines = script.split(/\\r?\\n/).filter((line) => line.includes(marker));\\n    assert.ok(lines.length <= 1, `${marker} status line must not be duplicated`);\\n    for (const line of lines) assert.match(line, /\\bWrite-(Host|Verbose)\\b/, `${marker} status must not enter the success pipeline`);\\n  }';
  if (!tests.includes(oldAssertion)) throw new Error('Lifecycle contract test no longer matches the reviewed run77 patch point.');
  tests = tests.replace(oldAssertion, newAssertion);
  const oldLoop = '  for (const line of astraStatusLines) assert.match(line, /\\bWrite-(Host|Verbose)\\b/, "ASTRA status must not enter the success pipeline");\\n';
  tests = tests.replace(oldLoop, '');
}
fs.writeFileSync(testPath, tests, 'utf8');

const updatedLifecycle = fs.readFileSync(scriptPath, 'utf8');
const updatedTests = fs.readFileSync(testPath, 'utf8');
const updatedHelper = updatedLifecycle.match(/function Start-DesktopAndWait\\s*\\{([\\s\\S]*?)\\n\\}/);
for (const fix of statusFixes) {
  const lines = updatedLifecycle.split(/\\r?\\n/).filter((line) => line.includes(fix.marker));
  if (lines.length > 1 || lines.some((line) => !/\\bWrite-(Host|Verbose)\\b/.test(line))) {
    throw new Error(`Run77 lifecycle output postcondition failed: ${fix.marker}`);
  }
}
if (!updatedHelper || /\\bWrite-Output\\b/.test(updatedHelper[1]) || !updatedTests.includes(testName)) {
  throw new Error('Run77 lifecycle output patch postcondition failed.');
}
process.stdout.write(JSON.stringify({
  status: 'patched',
  fix: 'Start-DesktopAndWait emits one session object; ASTRA and ASTRA TARGA status messages use the host stream, not the success pipeline',
  files: ['scripts/windows-installer-lifecycle.ps1', 'tests/windows-lifecycle-script-contract.test.cjs']
}, null, 2) + '\\n');

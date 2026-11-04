"use strict";
const fs = require("node:fs");
const path = require("node:path");
const root = path.resolve(process.cwd(), "desktop-source");
function read(file) { return fs.readFileSync(path.join(root, file), "utf8").replace(/\r\n/g, "\n"); }
function write(file, value) { fs.writeFileSync(path.join(root, file), value, "utf8"); }
function replaceOnce(source, before, after, label) {
  if (source.includes(after)) return source;
  const count = source.split(before).length - 1;
  if (count !== 1) throw new Error(label + ": expected one anchor, found " + count);
  return source.replace(before, after);
}

function patchRoute() {
  let source = read("app/api/local-core/route.ts");
  const old = '  if (!dbPath || !isLocalRequest(request)) return Response.json({ error: "Local desktop database is unavailable" }, { status: 404, headers });';
  const next = '  if (!dbPath) return Response.json({ error: "Local desktop database path is not configured" }, { status: 503, headers });\n  if (!isLocalRequest(request)) return Response.json({ error: "Local loopback request rejected" }, { status: 403, headers });';
  const count = source.split(old).length - 1;
  if (count === 2) source = source.replaceAll(old, next);
  else if (count !== 0 && count !== 2) throw new Error("Expected GET and POST local database gates");
  else if (count === 0 && !(source.includes(next))) throw new Error("Local database gate anchor missing");
  write("app/api/local-core/route.ts", source);
}

function patchLifecycleScript() {
  let source = read("scripts/windows-installer-lifecycle.ps1");
  const before = `function Invoke-LocalJsonPost([string]$BaseUrl, [hashtable]$Body) {
  return Invoke-RestMethod -Uri "$BaseUrl/api/local-core" -Method Post -Headers @{ Origin = $BaseUrl } -ContentType "application/json" -Body ($Body | ConvertTo-Json -Depth 10) -TimeoutSec 30
}`;
  const after = `function Invoke-LocalJsonPost([string]$BaseUrl, [hashtable]$Body) {
  $client = [System.Net.Http.HttpClient]::new()
  $request = [System.Net.Http.HttpRequestMessage]::new([System.Net.Http.HttpMethod]::Post, "$BaseUrl/api/local-core")
  try {
    $request.Headers.TryAddWithoutValidation("Origin", $BaseUrl) | Out-Null
    $request.Headers.TryAddWithoutValidation("Sec-Fetch-Site", "same-origin") | Out-Null
    $json = $Body | ConvertTo-Json -Depth 10 -Compress
    $request.Content = [System.Net.Http.StringContent]::new($json, [System.Text.Encoding]::UTF8, "application/json")
    $response = $client.SendAsync($request).GetAwaiter().GetResult()
    try {
      $responseText = $response.Content.ReadAsStringAsync().GetAwaiter().GetResult()
      if (-not $response.IsSuccessStatusCode) { throw "Local JSON request failed: HTTP $([int]$response.StatusCode) $responseText" }
      if ([string]::IsNullOrWhiteSpace($responseText)) { return $null }
      return $responseText | ConvertFrom-Json
    } finally { $response.Dispose() }
  } finally {
    $request.Dispose()
    $client.Dispose()
  }
}`;
  source = replaceOnce(source, before, after, "replace PowerShell JSON POST with explicit same-origin HttpClient");
  write("scripts/windows-installer-lifecycle.ps1", source);
}

function patchContractTest() {
  let source = read("tests/windows-lifecycle-script-contract.test.cjs");
  const block = [
    'test("Windows lifecycle JSON mutations use explicit same-origin HttpClient headers", () => {',
    '  assert.match(script, /System\\.Net\\.Http\\.HttpClient/);',
    '  assert.match(script, /TryAddWithoutValidation/);',
    '  assert.match(script, /Origin/);',
    '  assert.match(script, /Sec-Fetch-Site/);',
    '  assert.match(script, /Local JSON request failed/);',
    '});',
  ].join("\n");
  if (!source.includes(block)) source = source.trimEnd() + "\n\n" + block + "\n";
  write("tests/windows-lifecycle-script-contract.test.cjs", source);
}
function patchApiTests() {
  let source = read("tests/local-core-api.test.cjs");
  source = replaceOnce(source,
    '  const headers = { host: "127.0.0.1:43123", origin: "http://127.0.0.1:43123" };\\n\\n  const admin = await GET(new Request(`${baseUrl}?action=admin-summary`, { headers: { host: headers.host } }));',
    '  const headers = { host: "127.0.0.1:43123", origin: "http://127.0.0.1:43123" };\\n\\n  delete process.env.VAG_TECH_PRO_DB_PATH;\\n  const missingDatabase = await GET(new Request(`${baseUrl}?action=admin-summary`, { headers: { host: headers.host } }));\\n  assert.equal(missingDatabase.status, 503);\\n  assert.equal((await missingDatabase.json()).error, "Local desktop database path is not configured");\\n  process.env.VAG_TECH_PRO_DB_PATH = dbPath;\\n  const nonLoopback = await GET(new Request(`${baseUrl}?action=admin-summary`, { headers: { host: "evil.example" } }));\\n  assert.equal(nonLoopback.status, 403);\\n  assert.equal((await nonLoopback.json()).error, "Local loopback request rejected");\\n\\n  const admin = await GET(new Request(`${baseUrl}?action=admin-summary`, { headers: { host: headers.host } }));',
    "test distinct database and loopback gate failures");
  source = replaceOnce(source, '  assert.equal(crossOrigin.status, 404);', '  assert.equal(crossOrigin.status, 403);', "expect forbidden cross-origin mutation");
  source = replaceOnce(source, '  assert.equal(crossSiteWithoutOrigin.status, 404);', '  assert.equal(crossSiteWithoutOrigin.status, 403);', "expect forbidden cross-site request without origin");
  write("tests/local-core-api.test.cjs", source);
}

patchRoute();
patchLifecycleScript();
patchContractTest();
patchApiTests();
console.log(JSON.stringify({ status: "run40_lifecycle_httpclient_and_diagnostic_gate_applied" }, null, 2));

"use strict";
const fs = require("node:fs");
const path = require("node:path");
const root = path.resolve(process.cwd(), "desktop-source");
const scriptFile = path.join(root, "scripts", "windows-installer-lifecycle.ps1");
const testFile = path.join(root, "tests", "windows-lifecycle-script-contract.test.cjs");

function read(file) {
  return fs.readFileSync(file, "utf8").replace(/\r\n/g, "\n");
}
function write(file, value) {
  fs.writeFileSync(file, value, "utf8");
}
function replaceExact(source, before, after, label, expected = 1) {
  const count = source.split(before).length - 1;
  if (count === 0 && source.includes(after)) return { source, changed: false };
  if (count !== expected) throw new Error(label + ": expected " + expected + " original anchor(s), found " + count);
  return { source: source.replace(before, after), changed: true };
}
function replaceAllExact(source, before, after, label, minimum = 1) {
  const count = source.split(before).length - 1;
  if (count === 0 && source.includes(after)) return { source, changed: false };
  if (count < minimum) throw new Error(label + ": expected at least " + minimum + " original anchor(s), found " + count);
  return { source: source.split(before).join(after), changed: true };
}

let script = read(scriptFile);
const helperLines = [
  "function New-LoopbackHttpClient {",
  "  $handler = [System.Net.Http.HttpClientHandler]::new()",
  "  $handler.UseProxy = $false",
  "  $handler.AllowAutoRedirect = $false",
  "  return [System.Net.Http.HttpClient]::new($handler)",
  "}",
  "",
  "function Set-LoopbackRequestHeaders([System.Net.Http.HttpRequestMessage]$Request, [string]$BaseUrl) {",
  "  $uri = [System.Uri]::new(\"$BaseUrl/api/local-core\")",
  "  if ($uri.Scheme -ne \"http\" -or @(\"127.0.0.1\", \"localhost\", \"::1\", \"[::1]\") -notcontains $uri.Host) {",
  "    throw \"Refusing non-loopback lifecycle request: $($uri.AbsoluteUri)\"",
  "  }",
  "  $origin = $uri.GetLeftPart([System.UriPartial]::Authority)",
  "  $Request.Headers.Host = $uri.Authority",
  "  $Request.Headers.Remove(\"Origin\") | Out-Null",
  "  $Request.Headers.Remove(\"Sec-Fetch-Site\") | Out-Null",
  "  if (-not $Request.Headers.TryAddWithoutValidation(\"Origin\", $origin)) { throw \"Could not set the same-origin Origin header.\" }",
  "  if (-not $Request.Headers.TryAddWithoutValidation(\"Sec-Fetch-Site\", \"same-origin\")) { throw \"Could not set the same-origin Fetch Metadata header.\" }",
  "  return $origin",
  "}",
  ""
].join("\n");
if (!script.includes("function New-LoopbackHttpClient")) {
  const anchor = "function Invoke-LocalJsonPost(";
  const count = script.split(anchor).length - 1;
  if (count !== 1) throw new Error("Could not locate the lifecycle JSON request helper.");
  script = script.replace(anchor, helperLines + anchor);
}

let result;
result = replaceAllExact(
  script,
  "$client = [System.Net.Http.HttpClient]::new()",
  "$client = New-LoopbackHttpClient",
  "replace direct local HttpClient construction",
  2
);
script = result.source;
result = replaceExact(
  script,
  "$backupClient = [System.Net.Http.HttpClient]::new()",
  "$backupClient = New-LoopbackHttpClient",
  "replace backup HttpClient construction"
);
script = result.source;

result = replaceExact(
  script,
  '    $request.Headers.TryAddWithoutValidation("Origin", $BaseUrl) | Out-Null\n    $request.Headers.TryAddWithoutValidation("Sec-Fetch-Site", "same-origin") | Out-Null',
  "    $origin = Set-LoopbackRequestHeaders $request $BaseUrl",
  "pin JSON mutation request to explicit loopback authority"
);
script = result.source;

result = replaceExact(
  script,
  '    $request.Headers.Add("Origin", $BaseUrl)',
  "    Set-LoopbackRequestHeaders $request $BaseUrl | Out-Null",
  "pin SQLite restore request to explicit loopback authority"
);
script = result.source;

result = replaceExact(
  script,
  '  $request.Headers.Add("Origin", $origin)',
  "  Set-LoopbackRequestHeaders $request $origin | Out-Null",
  "pin backup export request to explicit loopback authority"
);
script = result.source;

const localJsonError = [
  "      if (-not $response.IsSuccessStatusCode) {",
  "        $finalUri = if ($response.RequestMessage -and $response.RequestMessage.RequestUri) { $response.RequestMessage.RequestUri.AbsoluteUri } else { \"<unknown>\" }",
  "        $location = if ($response.Headers.Location) { $response.Headers.Location.ToString() } else { \"<none>\" }",
  "        throw \"Local JSON request failed: HTTP $([int]$response.StatusCode) request=$($request.RequestUri.AbsoluteUri) final=$finalUri host=$($request.Headers.Host) origin=$origin fetchSite=same-origin proxy=disabled redirect=disabled location=$location $responseText\"",
  "      }"
].join("\n");
result = replaceExact(
  script,
  '      if (-not $response.IsSuccessStatusCode) { throw "Local JSON request failed: HTTP $([int]$response.StatusCode) $responseText" }',
  localJsonError,
  "add loopback JSON transport diagnostics"
);
script = result.source;

const restoreError = [
  "    if (-not $response.IsSuccessStatusCode) {",
  "      $finalUri = if ($response.RequestMessage -and $response.RequestMessage.RequestUri) { $response.RequestMessage.RequestUri.AbsoluteUri } else { \"<unknown>\" }",
  "      $location = if ($response.Headers.Location) { $response.Headers.Location.ToString() } else { \"<none>\" }",
  "      throw \"SQLite restore failed: HTTP $([int]$response.StatusCode) request=$($request.RequestUri.AbsoluteUri) final=$finalUri host=$($request.Headers.Host) proxy=disabled redirect=disabled location=$location $responseText\"",
  "    }"
].join("\n");
result = replaceExact(
  script,
  '    if (-not $response.IsSuccessStatusCode) { throw "SQLite restore failed: HTTP $([int]$response.StatusCode) $responseText" }',
  restoreError,
  "add SQLite restore transport diagnostics"
);
script = result.source;

const backupError = [
  "  if (-not $response.IsSuccessStatusCode) {",
  "    $finalUri = if ($response.RequestMessage -and $response.RequestMessage.RequestUri) { $response.RequestMessage.RequestUri.AbsoluteUri } else { \"<unknown>\" }",
  "    $location = if ($response.Headers.Location) { $response.Headers.Location.ToString() } else { \"<none>\" }",
  "    throw \"Backup export failed: HTTP $([int]$response.StatusCode) request=$($request.RequestUri.AbsoluteUri) final=$finalUri host=$($request.Headers.Host) proxy=disabled redirect=disabled location=$location\"",
  "  }"
].join("\n");
result = replaceExact(
  script,
  '  if (-not $response.IsSuccessStatusCode) { throw "Backup export failed: HTTP $([int]$response.StatusCode)" }',
  backupError,
  "add backup export transport diagnostics"
);
script = result.source;

if (script.includes("$client = [System.Net.Http.HttpClient]::new()") ||
    script.includes("$backupClient = [System.Net.Http.HttpClient]::new()") ||
    !script.includes("$handler.UseProxy = $false") ||
    !script.includes("$handler.AllowAutoRedirect = $false") ||
    !script.includes("$Request.Headers.Host = $uri.Authority") ||
    !script.includes('TryAddWithoutValidation("Sec-Fetch-Site", "same-origin")')) {
  throw new Error("Loopback transport hardening is incomplete.");
}
write(scriptFile, script);

let tests = read(testFile);
const contractTest = [
  'test("native lifecycle HTTP clients pin loopback authority and bypass system proxies", () => {',
  '  assert.match(script, /UseProxy = \\$false/);',
  '  assert.match(script, /AllowAutoRedirect = \\$false/);',
  '  assert.match(script, /Headers\\.Host = \\$uri\\.Authority/);',
  '  assert.match(script, /Set-LoopbackRequestHeaders/);',
  '  assert.match(script, /Sec-Fetch-Site/);',
  '  assert.match(script, /proxy=disabled/);',
  '});'
].join("\n");
if (!tests.includes("native lifecycle HTTP clients pin loopback authority")) {
  tests = tests.trimEnd() + "\n\n" + contractTest + "\n";
  write(testFile, tests);
}
console.log(JSON.stringify({
  status: "run42_loopback_transport_hardening_applied",
  proxy: "disabled",
  redirects: "disabled",
  host: "explicit loopback authority",
  fetchMetadata: "same-origin",
  diagnostics: "request/final URI, host and redirect location"
}));

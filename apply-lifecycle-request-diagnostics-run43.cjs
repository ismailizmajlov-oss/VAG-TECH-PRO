"use strict";
const fs = require("node:fs");
const path = require("node:path");
const root = path.resolve(process.cwd(), "desktop-source");
const routeFile = path.join(root, "app", "api", "local-core", "route.ts");
const scriptFile = path.join(root, "scripts", "windows-installer-lifecycle.ps1");
const testFile = path.join(root, "tests", "windows-lifecycle-script-contract.test.cjs");

function read(file) {
  return fs.readFileSync(file, "utf8").replace(/\r\n/g, "\n");
}
function write(file, value) {
  fs.writeFileSync(file, value, "utf8");
}
function replaceOnce(source, before, after, label) {
  if (source.includes(after)) return source;
  const count = source.split(before).length - 1;
  if (count !== 1) throw new Error(label + ": expected exactly one anchor, found " + count);
  return source.replace(before, after);
}

let route = read(routeFile);
if (!route.includes('[local-core] loopback request rejected')) {
  const start = route.indexOf("function isLocalRequest(request: Request) {");
  const marker = "\n}\n\nfunction isSameOriginMutation";
  const end = route.indexOf(marker, start);
  if (start < 0 || end < 0) throw new Error("Could not locate isLocalRequest for diagnostic-only instrumentation.");
  const replacement = [
    "function isLocalRequest(request: Request) {",
    "  const url = new URL(request.url);",
    '  const host = request.headers.get("host") || url.host;',
    '  const origin = request.headers.get("origin");',
    '  const fetchSite = request.headers.get("sec-fetch-site");',
    "  const reject = (reason: string) => {",
    '    console.warn("[local-core] loopback request rejected", JSON.stringify({',
    "      reason,",
    "      urlOrigin: url.origin,",
    "      urlHost: url.host,",
    "      host,",
    "      origin: origin ?? null,",
    "      fetchSite: fetchSite ?? null,",
    "    }));",
    "    return false;",
    "  };",
    "  if (origin) {",
    "    try { if (new URL(origin).origin !== url.origin) return reject(\"origin-mismatch\"); }",
    "    catch { return reject(\"invalid-origin\"); }",
    "  }",
    '  if (fetchSite && fetchSite !== "same-origin" && fetchSite !== "none") return reject("fetch-metadata");',
    '  const allowedHost = ["127.0.0.1", "localhost", "[::1]"].some((name) => host === name || host.startsWith(name + ":"));',
    '  if (!allowedHost) return reject("host-not-loopback");',
    "  return true;",
    "}"
  ].join("\n");
  route = route.slice(0, start) + replacement + route.slice(end + 2);
  write(routeFile, route);
}

let script = read(scriptFile);
const oldThrow = '        throw "Local JSON request failed: HTTP $([int]$response.StatusCode) request=$($request.RequestUri.AbsoluteUri) final=$finalUri host=$($request.Headers.Host) origin=$origin fetchSite=same-origin proxy=disabled redirect=disabled location=$location $responseText"';
const newThrow = [
  '        $desktopLogPath = Join-Path $env:APPDATA "VAG TECH PRO\\logs\\desktop.log"
        $desktopLogTail = if (Test-Path -LiteralPath $desktopLogPath) { (Get-Content -LiteralPath $desktopLogPath -Tail 80 | Out-String).Trim() } else { "<missing:$desktopLogPath>" }',
  '        throw "Local JSON request failed: HTTP $([int]$response.StatusCode) request=$($request.RequestUri.AbsoluteUri) final=$finalUri host=$($request.Headers.Host) origin=$origin fetchSite=same-origin proxy=disabled redirect=disabled location=$location desktopLogTail=$desktopLogTail $responseText"'
].join("\n");
script = replaceOnce(script, oldThrow, newThrow, "include desktop server log tail in native request failure");
write(scriptFile, script);

let tests = read(testFile);
if (!tests.includes("local loopback rejection diagnostics preserve the security decision")) {
  const anchor = 'const script = fs.readFileSync(path.join(__dirname, "..", "scripts", "windows-installer-lifecycle.ps1"), "utf8");';
  if (!tests.includes(anchor)) throw new Error("Lifecycle contract test script anchor missing.");
  tests = tests.replace(anchor, anchor + '\nconst route = fs.readFileSync(path.join(__dirname, "..", "app", "api", "local-core", "route.ts"), "utf8");');
  tests += [
    "",
    'test("local loopback rejection diagnostics preserve the security decision", () => {',
    '  assert.match(route, /\\[local-core\\] loopback request rejected/);',
    '  assert.match(route, /urlOrigin/);',
    '  assert.match(route, /fetchSite/);',
    '  assert.match(script, /desktopLogTail/);',
    '});',
    ""
  ].join("\n");
  write(testFile, tests);
}
console.log(JSON.stringify({
  status: "run43_loopback_rejection_diagnostics_applied",
  securityPolicy: "unchanged",
  diagnostics: ["reason", "request URL origin", "Host", "Origin", "Sec-Fetch-Site"],
  lifecycleLogTailLines: 80
}));

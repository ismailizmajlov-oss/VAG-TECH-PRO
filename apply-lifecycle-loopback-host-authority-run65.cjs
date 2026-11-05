"use strict";
const fs = require("node:fs");
const path = require("node:path");
const root = path.resolve(process.cwd(), "desktop-source");
function read(file) { return fs.readFileSync(path.join(root, file), "utf8").replace(/\r\n/g, "\n"); }
function write(file, source) { fs.writeFileSync(path.join(root, file), source, "utf8"); }
function replaceOnce(source, before, after, label) {
  if (source.includes(after)) return source;
  const count = source.split(before).length - 1;
  if (count !== 1) throw new Error(label + ": expected one anchor, found " + count);
  return source.replace(before, after);
}
function patchRoute() {
  const file = "app/api/local-core/route.ts";
  let source = read(file);
  const start = source.indexOf("function isLocalRequest(request: Request) {");
  const end = source.indexOf("\n\n\nasync function readLimitedBytes", start);
  if (start < 0 || end < 0) throw new Error("Loopback request gate block not found");
  if (source.slice(start, end).includes("function normalizedLoopbackOrigin(request: Request)")) return;
  const replacement = [
    "function normalizedLoopbackOrigin(request: Request) {",
    "  const requestUrl = new URL(request.url);",
    '  if (requestUrl.protocol !== "http:") return null;',
    "",
    "  // Next may normalize request.url to localhost while preserving the actual loopback Host header.",
    "  // Treat Host as the incoming authority and require Origin to match that exact authority.",
    '  const hostHeader = request.headers.get("host") || requestUrl.host;',
    "  let hostUrl: URL;",
    '  try { hostUrl = new URL("http://" + hostHeader); } catch { return null; }',
    '  if (hostUrl.username || hostUrl.password || hostUrl.pathname !== "/" || hostUrl.search || hostUrl.hash) return null;',
    "  const hostname = hostUrl.hostname.toLowerCase();",
    "  const requestHostname = requestUrl.hostname.toLowerCase();",
    '  const loopbackNames = ["127.0.0.1", "localhost", "[::1]", "::1"];',
    "  if (!loopbackNames.includes(hostname) || !loopbackNames.includes(requestHostname) || requestUrl.port !== hostUrl.port) return null;",
    "",
    '  const origin = request.headers.get("origin");',
    "  let originUrl: URL | null = null;",
    "  if (origin) {",
    "    try { originUrl = new URL(origin); } catch { return null; }",
    '    if (originUrl.protocol !== "http:" || originUrl.username || originUrl.password || originUrl.host.toLowerCase() !== hostUrl.host.toLowerCase()) return null;',
    "  }",
    "",
    '  const fetchSite = request.headers.get("sec-fetch-site");',
    '  if (fetchSite && fetchSite !== "same-origin" && fetchSite !== "none") return null;',
    "  return { host: hostUrl.host, origin: originUrl?.origin ?? null };",
    "}",
    "",
    "function isLocalRequest(request: Request) {",
    "  return normalizedLoopbackOrigin(request) !== null;",
    "}",
    "",
    "function isSameOriginMutation(request: Request) {",
    "  const local = normalizedLoopbackOrigin(request);",
    "  return Boolean(local && local.origin);",
    "}",
  ].join("\n");
  source = source.slice(0, start) + replacement + source.slice(end);
  write(file, source);
}
function patchApiTest() {
  const file = "tests/local-core-api.test.cjs";
  let source = read(file);
  const before = [
    '  const crossSiteWithoutOrigin = await GET(new Request("http://127.0.0.1:43123/api/local-core?action=admin-summary", {',
    '    headers: { host: headers.host, "sec-fetch-site": "cross-site" },',
    "  }));",
    "  assert.equal(crossSiteWithoutOrigin.status, 403);",
  ].join("\n");
  const after = before + [
    "",
    "  // Next may normalize Request.url to localhost while the incoming Host and Origin remain loopback.",
    '  const nativeClientWithNormalizedUrl = await POST(new Request("http://localhost:43123/api/local-core", {',
    '    method: "POST",',
    '    headers: { host: headers.host, origin: headers.origin, "sec-fetch-site": "same-origin", "content-type": "application/json" },',
    '    body: JSON.stringify({ action: "source.register-candidate", source: {',
    '      source_id: "native-client-normalized-url", publisher: "Test", title: "Native client normalized URL", source_type: "test",',
    '      revision: "r1", market_scope: "ALL", license_id: "not_confirmed",',
    "    } }),",
    "  }));",
    "  assert.equal(nativeClientWithNormalizedUrl.status, 201);",
    "  assert.equal(core.listSources(dbPath).length, 3);",
    "",
    '  const nonLoopbackRequestUrl = await POST(new Request("http://evil.example:43123/api/local-core", {',
    '    method: "POST",',
    '    headers: { host: headers.host, origin: headers.origin, "sec-fetch-site": "same-origin", "content-type": "application/json" },',
    '    body: JSON.stringify({ action: "source.register-candidate", source: {',
    '      source_id: "non-loopback-request-url", publisher: "Test", title: "Non-loopback request URL", source_type: "test",',
    '      revision: "r1", market_scope: "ALL", license_id: "not_confirmed",',
    "    } }),",
    "  }));",
    "  assert.equal(nonLoopbackRequestUrl.status, 403);",
    "  assert.equal(core.listSources(dbPath).length, 3);",
  ].join("\n");
  source = replaceOnce(source, before, after, "normalized URL and non-loopback rejection tests");
  source = replaceOnce(source, "  assert.equal(finalSummary.sources.length, 3);", "  assert.equal(finalSummary.sources.length, 4);", "updated source count");
  write(file, source);
}
function patchLifecycleScript() {
  const file = "scripts/windows-installer-lifecycle.ps1";
  let source = read(file);
  source = replaceOnce(source,
    '    $request.Headers.TryAddWithoutValidation("Origin", $BaseUrl) | Out-Null\n    $request.Headers.TryAddWithoutValidation("Sec-Fetch-Site", "same-origin") | Out-Null',
    '    $request.Headers.Host = ([System.Uri]::new($BaseUrl)).Authority\n    $request.Headers.TryAddWithoutValidation("Origin", $BaseUrl) | Out-Null\n    $request.Headers.TryAddWithoutValidation("Sec-Fetch-Site", "same-origin") | Out-Null',
    "explicit Host for JSON POST");
  source = replaceOnce(source,
    '    $request.Headers.Add("Origin", $BaseUrl)\n    $request.Content = $multipart',
    '    $request.Headers.Host = ([System.Uri]::new($BaseUrl)).Authority\n    $request.Headers.Add("Origin", $BaseUrl)\n    $request.Headers.TryAddWithoutValidation("Sec-Fetch-Site", "same-origin") | Out-Null\n    $request.Content = $multipart',
    "explicit Host for multipart restore");
  source = replaceOnce(source,
    '  $request.Headers.Add("Origin", $origin)\n  $request.Content = [System.Net.Http.StringContent]::new',
    '  $request.Headers.Host = ([System.Uri]::new($origin)).Authority\n  $request.Headers.Add("Origin", $origin)\n  $request.Headers.TryAddWithoutValidation("Sec-Fetch-Site", "same-origin") | Out-Null\n  $request.Content = [System.Net.Http.StringContent]::new',
    "explicit Host for backup export");
  write(file, source);
}
function patchContractTest() {
  const file = "tests/windows-lifecycle-script-contract.test.cjs";
  let source = read(file);
  const block = [
    'test("local API loopback origin validation uses the incoming Host authority, not Next normalized request URL", () => {',
    '  const route = fs.readFileSync(path.join(__dirname, "../app/api/local-core/route.ts"), "utf8");',
    "  assert.match(route, /function normalizedLoopbackOrigin/);",
    "  assert.match(route, /hostHeader/);",
    "  assert.match(route, /originUrl\\.host/);",
    "  assert.match(route, /sec-fetch-site/);",
    "  assert.doesNotMatch(route, /new URL\\(origin\\)\\.origin !== requestUrl\\.origin/);",
    "});",
    "",
  ].join("\n");
  if (!source.includes(block.trim())) {
    const anchor = 'test("Windows lifecycle test verifies in-place upgrade and user database preservation on uninstall", () => {\n';
    source = replaceOnce(source, anchor, block + anchor, "loopback Host authority contract test");
  }
  write(file, source);
}
patchRoute();
patchApiTest();
patchLifecycleScript();
patchContractTest();
console.log(JSON.stringify({ status: "run65_loopback_host_authority_fix_applied" }));

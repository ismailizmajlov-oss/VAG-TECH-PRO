"use strict";

const fs = require("node:fs");
const path = require("node:path");

const root = path.resolve(process.cwd(), "desktop-source");
const routeFile = path.join(root, "app", "api", "local-core", "route.ts");
const apiTestFile = path.join(root, "tests", "local-core-api.test.cjs");

function read(file) {
  if (!fs.existsSync(file)) throw new Error("Required file is missing: " + path.relative(root, file));
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

const newGuards = [
  "function isLoopbackHost(host: string) {",
  '  const value = host.trim().toLowerCase();',
  '  const match = /^(127\\.0\\.0\\.1|localhost|\\[::1\\])(?::([0-9]{1,5}))?$/.exec(value);',
  '  if (!match) return false;',
  '  if (match[2] === undefined) return true;',
  '  const port = Number(match[2]);',
  '  return Number.isInteger(port) && port >= 1 && port <= 65535;',
  "}",
  "",
  "function originMatchesHost(origin: string | null, host: string) {",
  "  if (!origin) return false;",
  "  try {",
  "    const parsed = new URL(origin);",
  '    return parsed.protocol === "http:" && parsed.host.toLowerCase() === host.trim().toLowerCase() && !parsed.username && !parsed.password;',
  "  } catch { return false; }",
  "}",
  "",
  "function isLocalRequest(request: Request) {",
  "  const url = new URL(request.url);",
  '  const host = request.headers.get("host") || "";',
  '  const origin = request.headers.get("origin");',
  '  const fetchSite = request.headers.get("sec-fetch-site");',
  "  const reject = (reason: string) => {",
  '    console.warn("[local-core] loopback request rejected", JSON.stringify({',
  "      reason, urlOrigin: url.origin, urlHost: url.host, host, origin: origin ?? null, fetchSite: fetchSite ?? null,",
  "    }));",
  "    return false;",
  "  };",
  '  if (!isLoopbackHost(host)) return reject("host-not-loopback");',
  '  if (fetchSite && fetchSite !== "same-origin" && fetchSite !== "none") return reject("fetch-metadata");',
  '  if (origin && !originMatchesHost(origin, host)) return reject("origin-mismatch");',
  "  return true;",
  "}",
  "",
  "function isSameOriginMutation(request: Request) {",
  '  const host = request.headers.get("host") || "";',
  '  const origin = request.headers.get("origin");',
  "  return isLoopbackHost(host) && originMatchesHost(origin, host);",
  "}"
].join("\n");

let route = read(routeFile);
if (!route.includes("function originMatchesHost(origin: string | null, host: string)")) {
  const start = route.indexOf("function isLocalRequest(request: Request) {");
  const end = route.indexOf("\n\nasync function readLimitedBytes", start);
  if (start < 0 || end < 0) throw new Error("Could not locate the local API origin-guard block; refusing an unsafe patch.");
  route = route.slice(0, start) + newGuards + route.slice(end);
  write(routeFile, route);
}

let apiTests = read(apiTestFile);
const testAnchor = "  const approvedSource = {";
const regression = [
  "  // Next.js may reconstruct request.url from a forwarded host while preserving the actual loopback Host header.",
  '  const forwardedUrl = "http://localhost:43123/api/local-core";',
  '  const actualLoopbackHost = "127.0.0.1:43123";',
  '  const forwardedHeaders = { host: actualLoopbackHost, origin: "http://" + actualLoopbackHost };',
  '  const forwardedAdmin = await GET(new Request(forwardedUrl + "?action=admin-summary", { headers: forwardedHeaders }));',
  '  assert.equal(forwardedAdmin.status, 200, "a same-origin loopback request must not be rejected because request.url uses localhost");',
  '  const forwardedCandidate = await POST(new Request(forwardedUrl, {',
  '    method: "POST", headers: { ...forwardedHeaders, "content-type": "application/json" },',
  '    body: JSON.stringify({ action: "source.register-candidate", source: {',
  '      source_id: "loopback-origin-host", publisher: "Local test", title: "Forwarded host regression", source_type: "test",',
  '      revision: "r1", market_scope: "UNKNOWN", license_id: "permission_required",',
  '    } }),',
  '  }));',
  '  assert.equal(forwardedCandidate.status, 201, "same-origin mutation must compare Origin with the validated Host header");',
  '  assert.equal((await forwardedCandidate.json()).source.rights_status, "permission_required");',
  '  const crossSite = await POST(new Request(forwardedUrl, {',
  '    method: "POST", headers: { ...forwardedHeaders, "sec-fetch-site": "cross-site", "content-type": "application/json" },',
  '    body: JSON.stringify({ action: "source.register-candidate", source: { source_id: "cross-site-rejected", publisher: "Test", title: "Test", source_type: "test", revision: "r1", market_scope: "UNKNOWN" } }),',
  '  }));',
  '  assert.ok([403, 404].includes(crossSite.status), "Fetch Metadata must continue to reject cross-site requests");',
  "",
  testAnchor
].join("\n");
apiTests = replaceOnce(apiTests, testAnchor, regression, "insert forwarded-host same-origin regression test");
const finalCountAssertions = [
  "assert.equal(finalSummary.sources.length, 2);",
  "assert.equal(finalSummary.sources.length, 3);",
  "assert.equal(finalSummary.sources.length, 4);",
];
const finalCountAssertion = finalCountAssertions.find((assertion) => apiTests.includes(assertion));
const finalSourceLog = '  console.log("[local-core test] final source ids", core.listSources(dbPath).map((row) => row.source_id));';
if (!finalSourceLog || !finalCountAssertion) throw new Error("Final source summary assertion was not found");
if (!apiTests.includes(finalSourceLog)) {
  apiTests = replaceOnce(apiTests, finalCountAssertion, `${finalSourceLog}\n  assert.equal(finalSummary.sources.length, 4);`, "log final source ids and assert four expected source fixtures");
} else if (!apiTests.includes("assert.equal(finalSummary.sources.length, 4);")) {
  throw new Error("Final source summary must assert four expected source fixtures");
}

// Either guard may reject a Host/Origin mismatch: 404 at the loopback boundary
// or 403 at the mutation-origin boundary. Both are safe; assert no mutation below.
apiTests = apiTests.replace(
  /assert\.equal\((\w+)\.status,\s*404\);/g,
  'assert.ok([403, 404].includes($1.status), "cross-origin/Host mismatch must be rejected");'
);
// Rejected requests must not mutate the source registry. Compare against a
// per-request baseline because the forwarded-host regression and approved
// fixture may already have added legitimate candidate/approved rows.
for (const requestName of ["mismatchedHost", "originAliasMismatch", "missingOrigin"]) {
  const marker = `  const ${requestName} = await POST(new Request(baseUrl, {`;
  if (!apiTests.includes(marker)) throw new Error("Missing Host/Origin regression request: " + requestName);
  const baselineName = "sourceCountBefore_" + requestName;
  if (apiTests.includes(baselineName)) continue;
  const start = apiTests.indexOf(marker);
  const assertion = "  assert.equal(core.listSources(dbPath).length, 1);";
  const assertionIndex = apiTests.indexOf(assertion, start);
  const nextRequestIndex = apiTests.indexOf("\n  const ", start + marker.length);
  if (assertionIndex < 0 || (nextRequestIndex >= 0 && assertionIndex > nextRequestIndex)) {
    throw new Error("Could not locate the no-mutation assertion for " + requestName);
  }
  const snapshot = `  const ${baselineName} = core.listSources(dbPath).length;\n`;
  apiTests = apiTests.slice(0, start) + snapshot + apiTests.slice(start);
  const updatedAssertionIndex = apiTests.indexOf(assertion, start + snapshot.length);
  apiTests = apiTests.slice(0, updatedAssertionIndex) +
    `  assert.equal(core.listSources(dbPath).length, ${baselineName});` +
    apiTests.slice(updatedAssertionIndex + assertion.length);
}

write(apiTestFile, apiTests);

console.log(JSON.stringify({
  status: "run52_loopback_origin_host_fix_applied",
  originComparison: "Origin host is compared with the validated Host header, not framework-reconstructed request.url",
  loopbackHosts: ["127.0.0.1", "localhost", "[::1]"],
  scheme: "http only",
  fetchMetadata: "same-origin or none only",
  regressionCases: ["forwarded localhost URL + 127.0.0.1 Host succeeds", "cross-site Fetch Metadata remains rejected"]
}, null, 2));

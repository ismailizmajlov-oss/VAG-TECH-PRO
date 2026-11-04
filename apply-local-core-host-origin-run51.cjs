"use strict";
const fs = require("node:fs");
const path = require("node:path");

const root = path.resolve(process.cwd(), "desktop-source");
const routePath = path.join(root, "app", "api", "local-core", "route.ts");
const apiTestPath = path.join(root, "tests", "local-core-api.test.cjs");

function replaceOnce(source, before, after, label) {
  const count = source.split(before).length - 1;
  if (count === 0 && source.includes(after)) return source;
  if (count !== 1) throw new Error(label + ": expected one original block or an already-applied replacement; found " + count);
  return source.replace(before, after);
}

let route = fs.readFileSync(routePath, "utf8").replace(/\r\n/g, "\n");
if (!route.includes("function originMatchesHostHeader(request: Request)")) {
  const blockPattern = new RegExp("function isLocalRequest\\(request: Request\\)\\s*\\{[\\s\\S]*?\\n\\}\\s*\\n\\s*function isSameOriginMutation\\(request: Request\\)\\s*\\{[\\s\\S]*?\\n\\}", "m");
  const replacement = [
    "function parseHostAuthority(hostHeader: string | null) {",
    "  if (!hostHeader || /[\\r\\n\\s/@\\\\]/.test(hostHeader)) return null;",
    "  try {",
    "    const parsed = new URL(\"http://\" + hostHeader);",
    "    if (parsed.username || parsed.password || parsed.pathname !== \"/\" || parsed.search || parsed.hash) return null;",
    "    const hostname = parsed.hostname.toLowerCase();",
    "    if (![\"127.0.0.1\", \"localhost\", \"[::1]\"].includes(hostname)) return null;",
    "    return parsed.host.toLowerCase();",
    "  } catch { return null; }",
    "}",
    "",
    "function originMatchesHostHeader(request: Request) {",
    "  const originHeader = request.headers.get(\"origin\");",
    "  const hostAuthority = parseHostAuthority(request.headers.get(\"host\"));",
    "  if (!originHeader || !hostAuthority) return false;",
    "  try {",
    "    const origin = new URL(originHeader);",
    "    const requestProtocol = new URL(request.url).protocol;",
    "    return !origin.username && !origin.password && origin.pathname === \"/\" && !origin.search && !origin.hash &&",
    "      origin.protocol === requestProtocol && origin.host.toLowerCase() === hostAuthority;",
    "  } catch { return false; }",
    "}",
    "",
    "function isLocalRequest(request: Request) {",
    "  if (!parseHostAuthority(request.headers.get(\"host\"))) return false;",
    "  const origin = request.headers.get(\"origin\");",
    "  if (origin && !originMatchesHostHeader(request)) return false;",
    "  const fetchSite = request.headers.get(\"sec-fetch-site\");",
    "  if (fetchSite && fetchSite !== \"same-origin\" && fetchSite !== \"none\") return false;",
    "  return true;",
    "}",
    "",
    "function isSameOriginMutation(request: Request) {",
    "  return originMatchesHostHeader(request);",
    "}"
  ].join("\n");
  if (!blockPattern.test(route)) throw new Error("Could not locate the local-core Host/Origin validation block.");
  route = route.replace(blockPattern, replacement);
  fs.writeFileSync(routePath, route, "utf8");
}
if (!route.includes("origin.host.toLowerCase() === hostAuthority")) {
  throw new Error("Local-core Host/Origin binding verification failed.");
}

let apiTests = fs.readFileSync(apiTestPath, "utf8").replace(/\r\n/g, "\n");
if (!apiTests.includes("const mismatchedHost = await POST")) {
  const anchor = [
    "  assert.equal(crossOrigin.status, 404);",
    "  assert.equal(core.listSources(dbPath).length, 1);",
    ""
  ].join("\n");
  const additions = [
    "  // Next.js may reconstruct request.url; the actual Host header must match Origin.",
    "  const mismatchedHost = await POST(new Request(baseUrl, {",
    "    method: \"POST\", headers: { host: \"localhost:43123\", origin: \"http://127.0.0.1:43123\", \"content-type\": \"application/json\" },",
    "    body: JSON.stringify({ action: \"source.register-candidate\", source: { source_id: \"host-mismatch\", publisher: \"Test\", title: \"Test\", source_type: \"test\", revision: \"r1\", market_scope: \"ALL\" } }),",
    "  }));",
    "  assert.equal(mismatchedHost.status, 404);",
    "  assert.equal(core.listSources(dbPath).length, 1);",
    "",
    "  const originAliasMismatch = await POST(new Request(baseUrl, {",
    "    method: \"POST\", headers: { host: headers.host, origin: \"http://localhost:43123\", \"content-type\": \"application/json\" },",
    "    body: JSON.stringify({ action: \"source.register-candidate\", source: { source_id: \"origin-alias-mismatch\", publisher: \"Test\", title: \"Test\", source_type: \"test\", revision: \"r1\", market_scope: \"ALL\" } }),",
    "  }));",
    "  assert.equal(originAliasMismatch.status, 404);",
    "  assert.equal(core.listSources(dbPath).length, 1);",
    "",
    "  const missingOrigin = await POST(new Request(baseUrl, {",
    "    method: \"POST\", headers: { host: headers.host, \"content-type\": \"application/json\" },",
    "    body: JSON.stringify({ action: \"source.register-candidate\", source: { source_id: \"missing-origin\", publisher: \"Test\", title: \"Test\", source_type: \"test\", revision: \"r1\", market_scope: \"ALL\" } }),",
    "  }));",
    "  assert.equal(missingOrigin.status, 403);",
    "  assert.equal(core.listSources(dbPath).length, 1);",
    ""
  ].join("\n");
  if (apiTests.split(anchor).length - 1 !== 1) throw new Error("Could not locate the local-core cross-origin regression-test insertion point.");
  apiTests = apiTests.replace(anchor, anchor + additions);
  fs.writeFileSync(apiTestPath, apiTests, "utf8");
}
if (!apiTests.includes("const mismatchedHost = await POST")) {
  throw new Error("Host/Origin regression tests were not installed.");
}
console.log("PASS: local-core mutation Origin is bound to the actual loopback Host header; spoofed Host/Origin mismatch and missing-Origin regressions added.");

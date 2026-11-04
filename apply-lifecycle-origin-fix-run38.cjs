"use strict";
const fs = require("node:fs");
const path = require("node:path");
const root = path.resolve(process.cwd(), "desktop-source");

function patch(file, before, after, label) {
  const target = path.join(root, file);
  let source = fs.readFileSync(target, "utf8").replace(/\r\n/g, "\n");
  if (source.includes(after)) return { file, status: "already_applied" };
  const count = source.split(before).length - 1;
  if (count !== 1) throw new Error(label + ": expected exactly one original block, found " + count);
  source = source.replace(before, after);
  fs.writeFileSync(target, source, "utf8");
  return { file, status: "patched" };
}

const route = patch(
  "app/api/local-core/route.ts",
  '  if (fetchSite && fetchSite !== "same-origin" && fetchSite !== "none") return false;\n',
  '  // Fetch Metadata is browser-oriented. Native PowerShell/HttpClient callers may send a non-browser value;\n  // when Origin is present it is validated above and remains authoritative for this loopback-only API.\n  if (!origin && fetchSite && fetchSite !== "same-origin" && fetchSite !== "none") return false;\n',
  "same-origin Origin precedence for native clients"
);

const testInsertion = [
  '  const crossOrigin = await POST(new Request(baseUrl, {',
  '    method: "POST", headers: { host: headers.host, origin: "http://evil.example", "content-type": "application/json" },',
  '    body: JSON.stringify({ action: "source.register-candidate", source: { source_id: "cross-origin", publisher: "Test", title: "Test", source_type: "test", revision: "r1", market_scope: "ALL" } }),',
  '  }));',
  '  assert.equal(crossOrigin.status, 404);',
  '  assert.equal(core.listSources(dbPath).length, 1);',
  ''
].join("\n");
const testReplacement = testInsertion + [
  '  const nativeClientWithFetchMetadata = await POST(new Request(baseUrl, {',
  '    method: "POST",',
  '    headers: { ...headers, "sec-fetch-site": "cross-site", "content-type": "application/json" },',
  '    body: JSON.stringify({ action: "source.register-candidate", source: {',
  '      source_id: "native-client-same-origin", publisher: "Test", title: "Native client same-origin", source_type: "test",',
  '      revision: "r1", market_scope: "ALL", license_id: "not_confirmed",',
  '    } }),',
  '  }));',
  '  assert.equal(nativeClientWithFetchMetadata.status, 201);',
  '  assert.equal(core.listSources(dbPath).length, 2);',
  '',
  '  const crossSiteWithoutOrigin = await GET(new Request("http://127.0.0.1:43123/api/local-core?action=admin-summary", {',
  '    headers: { host: headers.host, "sec-fetch-site": "cross-site" },',
  '  }));',
  '  assert.equal(crossSiteWithoutOrigin.status, 404);',
  ''
].join("\n");
const test = patch(
  "tests/local-core-api.test.cjs",
  testInsertion,
  testReplacement,
  "native-client fetch metadata regression test"
);
const count = patch(
  "tests/local-core-api.test.cjs",
  '  assert.equal(finalSummary.sources.length, 2);',
  '  assert.equal(finalSummary.sources.length, 3);',
  "updated local source count"
);

console.log(JSON.stringify({ status: "run38_loopback_origin_fix_applied", changes: [route, test, count] }, null, 2));

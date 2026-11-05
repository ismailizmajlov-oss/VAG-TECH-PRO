"use strict";
const fs = require("node:fs");
const path = require("node:path");
const root = path.resolve(process.cwd(), "desktop-source");

function read(file) {
  return fs.readFileSync(path.join(root, file), "utf8").replace(/\r\n/g, "\n");
}
function write(file, value) {
  fs.writeFileSync(path.join(root, file), value, "utf8");
}
function replaceOnce(source, before, after, label) {
  const count = source.split(before).length - 1;
  if (count === 0) {
    if (source.includes(after)) return source;
    throw new Error(label + ": neither the original nor the patched anchor is present");
  }
  if (count !== 1) throw new Error(label + ": expected exactly one original anchor, found " + count);
  return source.replace(before, after);
}

function patchRoute() {
  const file = "app/api/local-core/route.ts";
  let source = read(file);
  const oldComment = [
    '  // Fetch Metadata is browser-oriented. Native PowerShell/HttpClient callers may send a non-browser value;',
    '  // when Origin is present it is validated above and remains authoritative for this loopback-only API.'
  ].join("\n") + "\n";
  const newComment = '  // Native HttpClient callers explicitly identify their request as same-origin; reject contradictory Fetch Metadata.\n';
  source = replaceOnce(source, oldComment, newComment, "update obsolete native-client Fetch Metadata comment");
  const permissive = '  if (!origin && fetchSite && fetchSite !== "same-origin" && fetchSite !== "none") return false;\n';
  const strict = '  if (fetchSite && fetchSite !== "same-origin" && fetchSite !== "none") return false;\n';
  source = replaceOnce(source, permissive, strict, "reject contradictory cross-site Fetch Metadata even with a matching Origin");
  write(file, source);
}

function patchApiTest() {
  const file = "tests/local-core-api.test.cjs";
  let source = read(file);
  const oldNativeHeader = [
    '  const nativeClientWithFetchMetadata = await POST(new Request(baseUrl, {',
    '    method: "POST",',
    '    headers: { ...headers, "sec-fetch-site": "cross-site", "content-type": "application/json" },'
  ].join("\n");
  const newNativeHeader = [
    '  const nativeClientWithFetchMetadata = await POST(new Request(baseUrl, {',
    '    method: "POST",',
    '    headers: { ...headers, "sec-fetch-site": "same-origin", "content-type": "application/json" },'
  ].join("\n");
  source = replaceOnce(source, oldNativeHeader, newNativeHeader, "native HttpClient must identify its request as same-origin");
  const before = [
    '  assert.equal(nativeClientWithFetchMetadata.status, 201);',
    '  assert.equal(core.listSources(dbPath).length, 2);'
  ].join("\n");
  const after = [
    '  assert.equal(nativeClientWithFetchMetadata.status, 201);',
    '',
    '  const crossSiteWithMatchingOrigin = await POST(new Request(baseUrl, {',
    '    method: "POST",',
    '    headers: { ...headers, "sec-fetch-site": "cross-site", "content-type": "application/json" },',
    '    body: JSON.stringify({ action: "source.register-candidate", source: {',
    '      source_id: "cross-site-with-matching-origin", publisher: "Test", title: "Cross-site with matching Origin",',
    '      source_type: "test", revision: "r1", market_scope: "ALL", license_id: "not_confirmed",',
    '    } }),',
    '  }));',
    '  assert.equal(crossSiteWithMatchingOrigin.status, 403);',
    '  assert.equal(core.listSources(dbPath).length, 2);'
  ].join("\n");
  source = replaceOnce(source, before, after, "cross-site Fetch Metadata must be rejected despite matching Origin");
  write(file, source);
}

patchRoute();
patchApiTest();
console.log(JSON.stringify({status:"run41_strict_fetch_metadata_gate_applied",route:"strict",nativeClient:"same-origin",crossSiteWithMatchingOrigin:"403"}));

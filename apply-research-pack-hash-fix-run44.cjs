"use strict";

const fs = require("node:fs");
const path = require("node:path");

const root = path.join(__dirname, "desktop-source");
const dbFile = path.join(root, "lib", "local-research-db.cjs");
const testFile = path.join(root, "tests", "local-research-db.test.cjs");
for (const file of [dbFile, testFile]) if (!fs.existsSync(file)) throw new Error(`Required desktop source file is missing: ${file}`);

function replaceOnce(source, before, after, label) {
  const first = source.indexOf(before);
  if (first < 0 || first !== source.lastIndexOf(before)) throw new Error(`Expected ${label} block was not found exactly once; refusing an unsafe patch.`);
  return source.slice(0, first) + after + source.slice(first + before.length);
}

let source = fs.readFileSync(dbFile, "utf8");
const oldDatabaseBlock = [
  "  const cacheKey = `${realFile}|${stat.size}|${stat.mtimeMs}|${pack.database_sha256}`;",
  "  if (VERIFIED_PACKS.has(cacheKey)) return pack;",
  '  const actual = crypto.createHash("sha256").update(fs.readFileSync(realFile)).digest("hex");',
  "  if (actual !== pack.database_sha256) throw new Error(`Research database SHA-256 mismatch for ${packId}`);",
  "  VERIFIED_PACKS.add(cacheKey);",
  "  return pack;"
].join("\n");
const newDatabaseBlock = [
  "  // Re-hash every access. File size and mtime are not integrity proofs:",
  "  // Windows timestamp granularity can let same-size tampering reuse a cache key.",
  '  const actual = crypto.createHash("sha256").update(fs.readFileSync(realFile)).digest("hex");',
  "  if (actual !== pack.database_sha256) throw new Error(`Research database SHA-256 mismatch for ${packId}`);",
  "  return pack;"
].join("\n");
source = replaceOnce(source, oldDatabaseBlock, newDatabaseBlock, "database hash-cache");
const oldProvenanceBlock = [
  "  const cacheKey = `${realFile}|${stat.size}|${stat.mtimeMs}|${expected}`;",
  "  if (VERIFIED_PACKS.has(cacheKey)) return pack;",
  '  const actual = crypto.createHash("sha256").update(fs.readFileSync(realFile)).digest("hex");',
  "  if (actual !== expected) throw new Error(`Research provenance SHA-256 mismatch for ${packId}/${fileField}`);",
  "  VERIFIED_PACKS.add(cacheKey);",
  "  return pack;"
].join("\n");
const newProvenanceBlock = [
  "  // Always re-hash provenance artifacts; size/mtime memoization can hide same-size tampering.",
  '  const actual = crypto.createHash("sha256").update(fs.readFileSync(realFile)).digest("hex");',
  "  if (actual !== expected) throw new Error(`Research provenance SHA-256 mismatch for ${packId}/${fileField}`);",
  "  return pack;"
].join("\n");
source = replaceOnce(source, oldProvenanceBlock, newProvenanceBlock, "provenance hash-cache");
source = source.replace('const VERIFIED_PACKS = new Set();\n\n', "");
if (source.includes("VERIFIED_PACKS") || source.includes("const cacheKey = `${realFile}|${stat.size}|${stat.mtimeMs}")) throw new Error("Research hash memoization remains after patch.");
fs.writeFileSync(dbFile, source, "utf8");

let tests = fs.readFileSync(testFile, "utf8");
tests = replaceOnce(
  tests,
  '    const expected = crypto.createHash("sha256").update(fs.readFileSync(dataFile)).digest("hex");\n    fs.writeFileSync(path.join(temp, "manifest.json"), JSON.stringify({ schema_version: 1, packs: [{ id: "test-pack", database_sha256: expected }] }));\n    assert.equal(local.verifyPackDatabaseHash(temp, "test-pack", "pack.bin").database_sha256, expected);\n    fs.writeFileSync(dataFile, "tampered pack bytes");\n    assert.throws(() => local.verifyPackDatabaseHash(temp, "test-pack", "pack.bin"), /SHA-256 mismatch/);',
  '    const expected = crypto.createHash("sha256").update(fs.readFileSync(dataFile)).digest("hex");\n    const originalStat = fs.statSync(dataFile);\n    fs.writeFileSync(path.join(temp, "manifest.json"), JSON.stringify({ schema_version: 1, packs: [{ id: "test-pack", database_sha256: expected }] }));\n    assert.equal(local.verifyPackDatabaseHash(temp, "test-pack", "pack.bin").database_sha256, expected);\n    fs.writeFileSync(dataFile, "tampered pack bytes");\n    fs.utimesSync(dataFile, originalStat.atime, originalStat.mtime);\n    assert.throws(() => local.verifyPackDatabaseHash(temp, "test-pack", "pack.bin"), /SHA-256 mismatch/);',
  "database hash regression test"
);
tests = replaceOnce(
  tests,
  '    const expected = crypto.createHash("sha256").update(fs.readFileSync(license)).digest("hex");\n    fs.writeFileSync(path.join(temp, "manifest.json"), JSON.stringify({\n      schema_version: 1,\n      packs: [{ id: "test-pack", license_file: "LICENSE.txt", license_file_sha256: expected }],\n    }));\n    assert.equal(local.verifyPackFileHash(temp, "test-pack", "license_file", "license_file_sha256").id, "test-pack");\n    fs.writeFileSync(license, "changed license notice");\n    assert.throws(() => local.verifyPackFileHash(temp, "test-pack", "license_file", "license_file_sha256"), /SHA-256 mismatch/);',
  '    const expected = crypto.createHash("sha256").update(fs.readFileSync(license)).digest("hex");\n    const originalStat = fs.statSync(license);\n    fs.writeFileSync(path.join(temp, "manifest.json"), JSON.stringify({\n      schema_version: 1,\n      packs: [{ id: "test-pack", license_file: "LICENSE.txt", license_file_sha256: expected }],\n    }));\n    assert.equal(local.verifyPackFileHash(temp, "test-pack", "license_file", "license_file_sha256").id, "test-pack");\n    fs.writeFileSync(license, "XX BY 4.0 license notice");\n    fs.utimesSync(license, originalStat.atime, originalStat.mtime);\n    assert.throws(() => local.verifyPackFileHash(temp, "test-pack", "license_file", "license_file_sha256"), /SHA-256 mismatch/);',
  "provenance hash regression test"
);
fs.writeFileSync(testFile, tests, "utf8");
console.log("Applied uncached SHA-256 verification to research databases and provenance artifacts; regression tests now restore original timestamps after same-length tampering.");

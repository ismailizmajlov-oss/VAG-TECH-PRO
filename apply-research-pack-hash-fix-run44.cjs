"use strict";

const fs = require("node:fs");
const path = require("node:path");

const root = path.join(__dirname, "desktop-source");
const file = path.join(root, "lib", "local-research-db.cjs");
if (!fs.existsSync(file)) throw new Error(`Desktop source file is missing: ${file}`);

let source = fs.readFileSync(file, "utf8");
const oldBlock = [
  "  const cacheKey = `${realFile}|${stat.size}|${stat.mtimeMs}|${pack.database_sha256}`;",
  "  if (VERIFIED_PACKS.has(cacheKey)) return pack;",
  '  const actual = crypto.createHash("sha256").update(fs.readFileSync(realFile)).digest("hex");',
  "  if (actual !== pack.database_sha256) throw new Error(`Research database SHA-256 mismatch for ${packId}`);",
  "  VERIFIED_PACKS.add(cacheKey);",
  "  return pack;"
].join("\n");
const newBlock = [
  "  // Re-hash every access. File size and mtime are not integrity proofs:",
  "  // Windows timestamp granularity can let same-size tampering reuse a cache key.",
  '  const actual = crypto.createHash("sha256").update(fs.readFileSync(realFile)).digest("hex");',
  "  if (actual !== pack.database_sha256) throw new Error(`Research database SHA-256 mismatch for ${packId}`);",
  "  return pack;"
].join("\n");
if (!source.includes(oldBlock)) throw new Error("Expected vulnerable hash-cache block was not found exactly; refusing an unsafe patch.");
if (source.indexOf(oldBlock) !== source.lastIndexOf(oldBlock)) throw new Error("Hash-cache block occurs more than once; refusing ambiguous patch.");
source = source.replace(oldBlock, newBlock);
source = source.replace('const VERIFIED_PACKS = new Set();\n\n', "");
fs.writeFileSync(file, source, "utf8");

const written = fs.readFileSync(file, "utf8");
if (written.includes("VERIFIED_PACKS") || written.includes("const cacheKey = `${realFile}|${stat.size}|${stat.mtimeMs}|${pack.database_sha256}`")) {
  throw new Error("Research pack hash memoization remains after patch.");
}
console.log("Applied fail-closed research pack integrity fix: SHA-256 is recomputed on every database access.");

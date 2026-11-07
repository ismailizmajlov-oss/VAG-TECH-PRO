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
if (compressedSha !== "3b17b9f8ced47f8441c29b47a84f65b22fe85ee000c09e3a0a90dbe94ede62e7") throw new Error("Run80 compressed patch SHA-256 mismatch");
const inner = zlib.gunzipSync(compressed);
const innerSha = crypto.createHash("sha256").update(inner).digest("hex");
if (innerSha !== "739b374073bf8f87f81abeefee45442d3d4a56e8cbaae324451b2405ed60fe07") throw new Error("Run80 patch SHA-256 mismatch");
const temp = path.join(os.tmpdir(), "vag-tech-pro-run80-" + process.pid + ".cjs");
fs.writeFileSync(temp, inner, { flag: "wx" });
try {
  const result = spawnSync(process.execPath, [temp, ...process.argv.slice(2)], { stdio: "inherit" });
  if (result.error) throw result.error;
  process.exitCode = result.status == null ? 1 : result.status;
} finally {
  fs.rmSync(temp, { force: true });
}

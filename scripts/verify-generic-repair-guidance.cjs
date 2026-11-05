"use strict";

const guidance = require("../lib/generic-repair-guidance-db.cjs");

try {
  const result = guidance.getSummary();
  process.stdout.write(JSON.stringify({ status: "verified_generic_guidance_research_only", ...result }, null, 2) + "\n");
} catch (error) {
  process.stderr.write("Generic MechanicDB guidance verification failed: " + (error.stack || error.message) + "\n");
  process.exitCode = 1;
}

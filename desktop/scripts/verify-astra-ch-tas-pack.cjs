"use strict";
const { getAstraSummary } = require("../lib/astra-ch-tas-db.cjs");
const summary = getAstraSummary();
process.stdout.write(JSON.stringify({ status: "verified_research_only", ...summary }, null, 2) + "\n");

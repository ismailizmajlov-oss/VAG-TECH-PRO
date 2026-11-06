"use strict";
const { getRdwSummary } = require("../lib/rdw-vag-research-db.cjs");
const summary = getRdwSummary();
process.stdout.write(JSON.stringify({ status: "verified_research_only", ...summary }, null, 2) + "\n");

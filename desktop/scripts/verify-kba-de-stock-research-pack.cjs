"use strict";
const path = require("node:path");
const { getKbaSummary } = require("../lib/kba-de-stock-research-db.cjs");
const root = process.argv[2] ? path.resolve(process.argv[2]) : path.resolve(process.cwd(), "data", "research");
const summary = getKbaSummary(root);
process.stdout.write(JSON.stringify(summary, null, 2) + "\n");

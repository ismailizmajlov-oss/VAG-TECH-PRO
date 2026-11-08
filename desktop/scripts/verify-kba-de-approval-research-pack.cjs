"use strict";

const path = require("node:path");
const { getKbaApprovalSummary } = require("../lib/kba-de-approval-research-db.cjs");

const root = process.argv[2] ? path.resolve(process.argv[2]) : path.resolve(process.cwd(), "data", "research");
const summary = getKbaApprovalSummary(root);
process.stdout.write(JSON.stringify(summary, null, 2) + "\n");

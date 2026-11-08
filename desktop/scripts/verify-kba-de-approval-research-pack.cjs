"use strict";
const path=require("node:path");
const {getKbaApprovalSummary}=require("../lib/kba-de-approval-research-db.cjs");
const root=process.argv[2]?path.resolve(process.argv[2]):path.resolve(process.cwd(),"data","research");
process.stdout.write(JSON.stringify(getKbaApprovalSummary(root),null,2)+"\n");

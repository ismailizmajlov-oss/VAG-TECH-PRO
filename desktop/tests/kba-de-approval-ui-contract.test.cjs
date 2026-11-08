"use strict";
const test=require("node:test"),assert=require("node:assert/strict"),fs=require("node:fs"),path=require("node:path");
const ROOT=path.join(__dirname,"..");
test("KBA approval research panel is separate, offline and explicit about DE-only non-fitment",()=>{
 const ui=fs.readFileSync(path.join(ROOT,"components/local-research-catalog.tsx"),"utf8");
 const panel=fs.readFileSync(path.join(ROOT,"components/kba-de-approval-research.tsx"),"utf8");
 const api=fs.readFileSync(path.join(ROOT,"app/api/local-research/route.ts"),"utf8");
 assert.match(ui,/kba-de-approvals/);assert.match(ui,/KbaDeApprovalResearch/);
 assert.match(panel,/type_approval_document_metadata_only/);assert.match(panel,/RU\/ЕАЭС/);assert.match(panel,/DL-DE BY 2\.0/);
 assert.match(panel,/sourceSnapshotSha256/);assert.match(panel,/sourceRecordSha256/);assert.match(panel,/exact engine\/gearbox pair false/);
 assert.match(api,/kba-de-approval-research-db\.cjs/);assert.match(api,/kba-de-approval-summary/);assert.match(api,/dataset === "kba-de-approvals"/);
});

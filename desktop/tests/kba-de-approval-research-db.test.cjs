"use strict";
const test=require("node:test"),assert=require("node:assert/strict"),path=require("node:path");
const {getKbaApprovalSummary,searchKbaApprovals}=require("../lib/kba-de-approval-research-db.cjs");
const ROOT=process.env.VAG_TECH_PRO_KBA_APPROVAL_TEST_ROOT||path.join(__dirname,"..","data","research");
test("KBA DE approval pack verifies rights, provenance, counts and non-fitment boundaries",()=>{
 const s=getKbaApprovalSummary(ROOT);
 assert.equal(s.marketScope,"DE");assert.equal(s.license,"DL-DE-BY-2.0");assert.equal(s.rightsStatus,"approved_by_published_DL_DE_BY_2_0");
 assert.equal(s.applicabilityPrecision,"type_approval_document_metadata_only");assert.equal(s.reviewStatus,"verified_research_only");
 assert.equal(s.researchPackIngested,true);assert.equal(s.productDatabaseIngested,false);assert.equal(s.productionImport,false);assert.equal(s.productImportAllowed,false);
 assert.equal(s.ruEaeuApplicability,false);assert.equal(s.exactVehicleFitment,false);assert.equal(s.exactEngineGearboxPair,false);assert.equal(s.repairApplicability,false);assert.equal(s.diagnosticExecutionAllowed,false);
 assert.equal(s.rowHashesVerified,true);assert.deepEqual(s.counts,{sourceRows:3782,approvalRecords:918,manufacturerLabels:8,distinctApprovalNumbers:918});
 for(const h of [s.sourceSnapshotSha256,s.sourceManifestSha256,s.databaseSha256])assert.match(h,/^[a-f0-9]{64}$/);
 assert.match(s.attributionText,/Kraftfahrt-Bundesamt \(KBA\)/);assert.match(s.attributionText,/Modified data/);
});
test("KBA DE approval search keeps raw metadata and never invents fitment",()=>{
 const rows=searchKbaApprovals("Volkswagen",10,ROOT);assert.ok(rows.length>0);assert.ok(rows.every(r=>r.marketScope==="DE"&&r.applicabilityPrecision==="type_approval_document_metadata_only"&&r.reviewStatus==="research_only"));
 assert.ok(rows.every(r=>r.exactVehicleFitment===false&&r.modelYear===null&&r.generation===null&&r.engineCode===null&&r.gearboxCode===null&&r.exactEngineGearboxPair===false&&r.ruEaeuApplicability===false));
 assert.ok(rows.every(r=>r.ecuFitment===false&&r.dtcFitment===false&&r.repairApplicability===false&&/^[a-f0-9]{64}$/.test(r.sourceRecordSha256)));
 assert.ok(rows.some(r=>r.manufacturerLabel==="Volkswagen AG"));
});
test("KBA DE approval search rejects short query and unsafe limits",()=>{
 assert.throws(()=>searchKbaApprovals("V",10,ROOT),/минимум два символа/);
 assert.throws(()=>searchKbaApprovals("VW",0,ROOT),/Лимит должен быть/);
 assert.throws(()=>searchKbaApprovals("VW",51,ROOT),/Лимит должен быть/);
});

"use strict";
const fs=require("node:fs");
const path=require("node:path");
const crypto=require("node:crypto");
const {spawnSync}=require("node:child_process");
function fail(m){throw new Error(m);}
function sha(b){return crypto.createHash("sha256").update(b).digest("hex");}
function shaFile(f){return sha(fs.readFileSync(f));}
function json(f){try{return JSON.parse(fs.readFileSync(f,"utf8"));}catch(e){fail("Cannot read "+f+": "+e.message);}}
function writeJson(f,v){fs.mkdirSync(path.dirname(f),{recursive:true});const t=f+".run69.tmp";fs.writeFileSync(t,JSON.stringify(v,null,2)+"\n","utf8");if(fs.existsSync(f))fs.rmSync(f,{force:true});fs.renameSync(t,f);}
function exact(s,a,b,label){const n=s.split(a).length-1;if(n!==1)fail(label+" anchor count "+n);return s.replace(a,b);}
function arg(n,d){const i=process.argv.indexOf(n);return i>=0&&process.argv[i+1]?process.argv[i+1]:d;}
function verify(f,h,label){if(!/^[a-f0-9]{64}$/.test(String(h||"")))fail("Invalid hash for "+label);const a=shaFile(f);if(a!==h)fail("SHA-256 mismatch for "+label+": "+a);return a;}
function copy(repo,desktop,src,dst){const a=path.join(repo,src),b=path.join(desktop,dst);if(!fs.existsSync(a))fail("Missing repo file "+src);fs.mkdirSync(path.dirname(b),{recursive:true});fs.copyFileSync(a,b);}
function run(cmd,args,cwd,env){const r=spawnSync(cmd,args,{cwd,env,encoding:"utf8",stdio:"inherit"});if(r.error||r.status!==0)fail(cmd+" "+args.join(" ")+" failed: "+(r.error?r.error.message:r.status));}
function main(){
 const repo=process.cwd(),desktop=path.resolve(arg("--desktop-root","desktop-source")),pack=path.resolve(arg("--pack-dir",path.join(repo,"build","generic-repair-guidance")));
 const id="mechanicdb-generic-repair-guidance-odbl",sourceId="mechanicdb-public-generic-repair-guidance",revision="c788dfe9ed1517d4cd0be27f5aacb4776abf4864";
 const files=["ATTRIBUTION.md","LICENSE-MIT.txt","LICENSE-ODbL.txt","generic-repair-guidance.sqlite","manifest.json"];
 if(!fs.existsSync(desktop)||!fs.existsSync(pack))fail("Desktop root or generic pack missing");
 const found=fs.readdirSync(pack).filter(n=>fs.statSync(path.join(pack,n)).isFile()).sort();
 if(JSON.stringify(found)!==JSON.stringify(files.slice().sort()))fail("Unexpected pack output: "+found.join(","));
 const m=json(path.join(pack,"manifest.json")),scope=m.scope||{};
 if(m.pack_id!==id||m.source_revision!==revision||m.data_license!=="ODbL-1.0"||m.rights_status!=="approved_by_published_license"||
    m.commercial_use_allowed!==true||m.display_allowed!==true||m.offline_cache_allowed!==true||m.redistribution_allowed!==true||
    m.share_alike_required!==true||m.attribution_required!==true)fail("Published ODbL rights gate failed");
 if(m.counts?.generic_sae_dtc_references!==75||m.counts?.generic_authored_guidance!==275||
    m.counts?.manufacturer_labelled_dtc_rows_excluded!==15||m.counts?.manufacturer_labelled_guidance_rows_excluded!==51||
    m.counts?.orphan_guidance_rows!==0||m.counts?.generic_dtc_descriptions_copied!==0||
    m.counts?.detailed_code_explanations_copied!==0||m.counts?.replacement_parts_rows_copied!==0||m.counts?.cost_or_labor_estimates_copied!==0)fail("Generic pack counts/exclusion policy changed");
 if(scope.namespace!=="generic_sae_iso"||scope.manufacturer!=="UNKNOWN"||scope.market_scope!=="UNKNOWN"||
    scope.applicability_level!=="generic_only"||scope.vag_specific!==false||scope.exact_vehicle_fitment!==false||
    scope.model_generation_year_fitment!==false||scope.engine_gearbox_fitment!==false||scope.ecu_fitment!==false||
    scope.pr_code_fitment!==false||scope.vin_fitment!==false||scope.diagnostic_execution_allowed!==false||
    scope.oem_repair_procedure!==false||scope.technical_review_status!=="not_independently_reviewed"||scope.safety_review_status!=="not_assessed")fail("Generic-only applicability boundary changed");
 files.forEach(n=>{const rec=m.pack_files&&m.pack_files[n];if(!rec)fail("Missing pack hash "+n);verify(path.join(pack,n),rec.sha256,n);});
 if(m.database_sha256!==m.pack_files["generic-repair-guidance.sqlite"].sha256)fail("SQLite hash mismatch in pack manifest");
 for(const n of ["dtc_codes.csv","diagnostic_fixes.csv"])if(!m.source_files?.[n]||!/^[a-f0-9]{64}$/.test(m.source_files[n].sha256||""))fail("Missing pinned source hash "+n);
 const register=json(path.join(repo,"data/source-manifests/vag-factory-source-register.json"));
 const source=(register.sources||[]).find(x=>x.source_id===sourceId);
 if(!source||source.rights?.data_license_status!=="ODbL-1.0"||!Array.isArray(source.market_scope)||!source.market_scope.includes("UNKNOWN")||!String(source.project_decision||"").includes("allow_separate_generic_educational_reference_pack_only_under_ODbL"))fail("Generic source missing from rights register");
 const sourceManifest=json(path.join(repo,"data/source-manifests/mechanicdb-generic-repair-guidance.json"));
 if(sourceManifest.source_id!==sourceId||sourceManifest.data_license!=="ODbL-1.0")fail("Source-specific manifest mismatch");

 const research=path.join(desktop,"data/research"),target=path.join(research,id);
 if(fs.existsSync(target)&&fs.readdirSync(target).length)fail("Target generic pack already exists; refusing overwrite");
 fs.mkdirSync(target,{recursive:true});files.forEach(n=>fs.copyFileSync(path.join(pack,n),path.join(target,n)));
 const rootPath=path.join(research,"manifest.json"),root=json(rootPath);
 if(root.schema_version!==1||!Array.isArray(root.packs))fail("Desktop root research manifest invalid");
 const dbRel=id+"/generic-repair-guidance.sqlite",licRel=id+"/LICENSE-ODbL.txt",mitRel=id+"/LICENSE-MIT.txt",attrRel=id+"/ATTRIBUTION.md",manRel=id+"/manifest.json";
 const manSha=shaFile(path.join(target,"manifest.json")),licSha=shaFile(path.join(target,"LICENSE-ODbL.txt")),mitSha=shaFile(path.join(target,"LICENSE-MIT.txt")),attrSha=shaFile(path.join(target,"ATTRIBUTION.md"));
 const entry={
  id,kind:"generic_repair_guidance",database:dbRel,database_sha256:m.database_sha256,
  license_file:licRel,license_file_sha256:licSha,upstream_license_file:mitRel,upstream_license_file_sha256:mitSha,
  attribution_file:attrRel,attribution_sha256:attrSha,license:"ODbL-1.0",license_status:"approved_by_published_license_for_free_sample_only",
  source_manifest_file:manRel,source_manifest_sha256:manSha,publisher:m.publisher,dataset:"MechanicDB generic SAE/ISO repair guidance",
  source_url:m.source_repository,upstream_revision:m.source_revision,snapshot_generated_at_utc:m.built_at_utc,
  source_snapshot_sha256:m.source_snapshot_sha256,logical_content_sha256:m.logical_content_sha256,
  source_file_sha256:Object.fromEntries(Object.entries(m.source_files).map(x=>[x[0],x[1].sha256])),counts:m.counts,
  market_scope:"UNKNOWN",applicability_precision:"generic_only_no_vehicle_fitment",namespace:"generic_sae_iso",manufacturer:"UNKNOWN",
  vag_specific:false,exact_vehicle_fitment:false,model_generation_year_fitment:false,engine_gearbox_fitment:false,ecu_fitment:false,
  diagnostic_execution_allowed:false,oem_repair_procedure:false,technical_review_status:"not_independently_reviewed",safety_review_status:"not_assessed",
  review_status:"research_only",fitment_claim:false,execution_allowed:false,commercial_use_allowed:true,display_allowed:true,
  cache_allowed:true,redistribution_allowed:true,share_alike_required:true,attribution_required:true,attribution_text:m.attribution_text,limitations:m.limitations
 };
 const idx=root.packs.findIndex(x=>x.id===id);if(idx>=0)root.packs[idx]=entry;else root.packs.push(entry);
 root.packs.sort((a,b)=>a.id.localeCompare(b.id));root.integration_revision="run69";root.integration_updated_at_utc=new Date().toISOString();
 root.research_only_boundaries=Array.isArray(root.research_only_boundaries)?root.research_only_boundaries:[];
 const boundary="MechanicDB generic SAE/ISO guidance is a separate ODbL pack; not VAG-specific, market UNKNOWN, no vehicle/engine/gearbox/ECU fitment, not an OEM procedure or executable test plan.";
 if(!root.research_only_boundaries.includes(boundary))root.research_only_boundaries.push(boundary);
 root.integrated_artifacts=Array.isArray(root.integrated_artifacts)?root.integrated_artifacts:[];
 root.integrated_artifacts=root.integrated_artifacts.filter(x=>x.id!==id);
 root.integrated_artifacts.push({id,source_revision:m.source_revision,source_snapshot_sha256:m.source_snapshot_sha256,logical_content_sha256:m.logical_content_sha256,database_sha256:m.database_sha256,source_manifest_sha256:manSha,license:"ODbL-1.0",applicability:"generic_only",vag_specific:false});
 writeJson(rootPath,root);const packCount=root.packs.length;const expectedPackCount=Number(arg("--expected-pack-count","8"));if(packCount!==expectedPackCount)fail("Expected "+expectedPackCount+" desktop research packs after run69, found "+packCount);

 const copies=[
  ["lib/generic-repair-guidance-db.cjs","lib/generic-repair-guidance-db.cjs"],
  ["lib/generic-repair-guidance-db.d.cts","lib/generic-repair-guidance-db.d.cts"],
  ["scripts/verify-generic-repair-guidance.cjs","scripts/verify-generic-repair-guidance.cjs"],
  ["tests/generic-repair-guidance-db.test.cjs","tests/generic-repair-guidance-db.test.cjs"],
  ["tests/generic-repair-guidance-ui-contract.test.cjs","tests/generic-repair-guidance-ui-contract.test.cjs"],
  ["data/source-manifests/vag-factory-source-register.json","data/source-manifests/vag-factory-source-register.json"],
  ["data/source-manifests/mechanicdb-generic-repair-guidance.json","data/source-manifests/mechanicdb-generic-repair-guidance.json"],
  ["docs/research/MECHANICDB_GENERIC_REPAIR_GUIDANCE_REVIEW_2026-11-04.md","docs/research/MECHANICDB_GENERIC_REPAIR_GUIDANCE_REVIEW_2026-11-04.md"]
 ];
 copies.forEach(x=>copy(repo,desktop,x[0],x[1]));

 const verifierPath=path.join(desktop,"scripts/verify-local-research-packs.cjs");let verifier=fs.readFileSync(verifierPath,"utf8");
 const count=verifier.match(/manifest\.packs\.length\s*===\s*(\d+)/);if(!count)fail("Research pack count gate not found");
 if(Number(count[1])!==packCount-1&&Number(count[1])!==packCount)fail("Unexpected previous research pack count "+count[1]);
 verifier=verifier.replace(/manifest\.packs\.length\s*===\s*\d+/,"manifest.packs.length === "+packCount);
 const words={6:"six",7:"seven",8:"eight",9:"nine"};verifier=verifier.replace(/Expected (?:five|six|seven|eight|nine) separately licensed research packs/g,"Expected "+(words[packCount]||String(packCount))+" separately licensed research packs");
 fs.writeFileSync(verifierPath,verifier,"utf8");

 const pkgPath=path.join(desktop,"package.json"),pkg=json(pkgPath);
 if(!pkg.scripts||!pkg.scripts["test:research"]||!pkg.scripts["verify:local-research"])fail("Desktop research scripts missing");
 if(!pkg.scripts["test:research"].includes("generic-repair-guidance-db.test.cjs"))pkg.scripts["test:research"]+=" tests/generic-repair-guidance-db.test.cjs tests/generic-repair-guidance-ui-contract.test.cjs";
 if(!pkg.scripts["verify:local-research"].includes("verify-generic-repair-guidance.cjs"))pkg.scripts["verify:local-research"]+=" && node scripts/verify-generic-repair-guidance.cjs";
 writeJson(pkgPath,pkg);

 const routePath=path.join(desktop,"app/api/local-research/route.ts");let route=fs.readFileSync(routePath,"utf8");
 const localImport='import * as localResearch from "../../../lib/local-research-db.cjs";';
 if(!route.includes("generic-repair-guidance-db.cjs"))route=exact(route,localImport,localImport+'\nimport * as genericGuidance from "../../../lib/generic-repair-guidance-db.cjs";',"API import");
 if(!route.includes('dataset === "generic-guidance-summary"'))route=exact(route,'    if (dataset === "summary") {','    if (dataset === "generic-guidance-summary") {\n      return Response.json(genericGuidance.getSummary(), { headers });\n    }\n    if (dataset === "summary") {',"API summary endpoint");
 if(!route.includes('dataset === "generic-guidance"'))route=exact(route,'    else return Response.json({ error: "Неизвестный локальный справочник." }, { status: 404, headers });','    else if (dataset === "generic-guidance") rows = genericGuidance.search(query, limit);\n    else return Response.json({ error: "Неизвестный локальный справочник." }, { status: 404, headers });',"API search endpoint");
 fs.writeFileSync(routePath,route,"utf8");

 const uiPath=path.join(desktop,"components/local-research-catalog.tsx");let ui=fs.readFileSync(uiPath,"utf8");
 const type=ui.match(/^type Dataset = ([^;]+);$/m);if(!type)fail("Dataset type missing");
 if(!type[1].includes('"generic-guidance"'))ui=ui.replace(type[0],'type Dataset = '+type[1]+' | "generic-guidance";');
 const state='const [summary, setSummary] = useState<SummaryPack[]>([]);';
 if(!ui.includes("genericGuidanceSummary"))ui=exact(ui,state,state+'\n  const [genericGuidanceSummary, setGenericGuidanceSummary] = useState<ResearchRow | null>(null);',"UI state");
 const tabsStart=ui.indexOf("const tabs:"),tabsEnd=ui.indexOf("\n];",tabsStart);if(tabsStart<0||tabsEnd<0)fail("Tabs array missing");
 if(!ui.includes('id: "generic-guidance"'))ui=ui.slice(0,tabsEnd)+'\n  { id: "generic-guidance", label: "Общие рекомендации", hint: "ODbL · SAE/ISO · не VAG-specific" },'+ui.slice(tabsEnd);
 if(!ui.includes("dataset=generic-guidance-summary")){
  const effect=ui.indexOf("useEffect(() => {"),cleanup=ui.indexOf("    return () => {",effect);if(effect<0||cleanup<0)fail("Summary effect cleanup missing");
  const fetchBlock=[
   '    fetch("/api/local-research?dataset=generic-guidance-summary", { signal: current.signal, cache: "no-store" })',
   '      .then(async (response) => {',
   '        const payload = await response.json();',
   '        if (!response.ok) throw new Error(payload.error || "Общий справочник недоступен.");',
   '        setGenericGuidanceSummary(payload);',
   '      })',
   '      .catch((reason) => {',
   '        if (reason?.name !== "AbortError") setError(reason?.message || "Не удалось проверить общий справочник.");',
   '      });',''
  ].join("\n");
  ui=ui.slice(0,cleanup)+fetchBlock+ui.slice(cleanup);
 }
 const statsMarker='\n    </div>\n\n    <div className="research-boundary">';
 if(!ui.includes("genericGuidanceSummary?.counts?.genericRepairGuidance"))ui=exact(ui,statsMarker,'\n      <article className="research-stat"><small>Общие рекомендации</small><strong>{formatNumber(genericGuidanceSummary?.counts?.genericRepairGuidance)}</strong><span>{formatNumber(genericGuidanceSummary?.counts?.genericDtcReferences)} общих DTC · ODbL-1.0</span></article>'+statsMarker,"statistics card");
 const boundaryMarker='\n    </div>\n\n    <div className="research-tabs"';
 if(!ui.includes("Общие заметки остаются отдельным generic SAE/ISO набором"))ui=exact(ui,boundaryMarker,'\n      {genericGuidanceSummary && <p>Общие заметки остаются отдельным generic SAE/ISO набором MechanicDB под ODbL-1.0: они не VAG-specific, рынок UNKNOWN, применимость к модели/поколению/году/двигателю/КПП/ECU не установлена; это не OEM-процедуры и не выполняемые тест-планы.</p>'+boundaryMarker,"scope boundary");
 const placeholder='placeholder={dataset ===';
 if(!ui.includes('dataset === "generic-guidance" ? "DTC, узел или фраза из общей заметки'))ui=exact(ui,placeholder,'placeholder={dataset === "generic-guidance" ? "DTC, узел или фраза из общей заметки…" : dataset ===',"search placeholder");
 const card=[
  '      {dataset === "generic-guidance" && rows.map((row) => <article className="research-result" key={row.guidanceId}>',
  '        <div className="research-result-top"><div><small>GENERIC SAE/ISO · {row.dtcCode} · {row.systemCategory || "категория не указана"}</small><h3>{row.title}</h3></div><span className="research-candidate">GENERIC ONLY</span></div>',
  '        <div className="research-warning-line">Не использовать как тест-план или OEM-процедуру. {row.warning}</div>',
  '        <div className="research-data-grid">',
  '          <div><small>Порядок в источнике</small><b>{row.considerationOrder} · не вероятность</b></div>',
  '          <div><small>Уровень из источника</small><b>{row.skillLevel || "—"} · не оценка безопасности</b></div>',
  '          <div><small>Тип действия из источника</small><b>{row.actionType || "—"} · не команда</b></div>',
  '          <div><small>VAG-specific / рынок</small><b>{row.vagSpecific ? "да" : "нет"} · {row.marketScope}</b></div>',
  '          <div><small>Точная применимость</small><b>{row.exactVehicleFitment ? "да" : "нет"}</b></div>',
  '          <div><small>Выполнение диагностики / OEM-процедура</small><b>{row.diagnosticExecutionAllowed ? "да" : "нет"} · {row.oemRepairProcedure ? "да" : "нет"}</b></div>',
  '        </div>',
  '        <p className="research-description">{row.instructions}</p>',
  '        {row.rationale && <p className="research-description">Пояснение из источника: {row.rationale}</p>}',
  '        <div className="research-source"><span>MechanicDB · ODbL-1.0 · ревизия {row.sourceRevision} · файл {row.sourceFile} · строка {row.sourceLineNo} · SHA строки {String(row.sourceLineSha256).slice(0, 12)}… · SHA файла {String(row.sourceFileSha256).slice(0, 12)}… · SHA snapshot {String(row.sourceSnapshotSha256).slice(0, 12)}… · SHA БД {String(row.databaseSha256).slice(0, 12)}… · SHA манифеста {String(row.sourceManifestSha256).slice(0, 12)}…</span>{row.sourceFileUrl && <a href={row.sourceFileUrl} target="_blank" rel="noopener noreferrer">Открыть исходный CSV</a>}</div>',
  '      </article>)}'
 ].join("\n");
 const resultsMarker='\n    </div>}\n\n    {!rows.length';
 if(!ui.includes('dataset === "generic-guidance" && rows.map'))ui=exact(ui,resultsMarker,"\n"+card+resultsMarker,"generic guidance result card");
 const creditsEnd='\n    </div>\n  </section>;';
 if(!ui.includes("genericGuidanceSummary.attributionText")){
  const credits=[
   '      {genericGuidanceSummary && <><p><a href={genericGuidanceSummary.sourceUrl} target="_blank" rel="noopener noreferrer">MechanicDB / MechanicDB-public</a> — отдельный бесплатный sample под ODbL-1.0. В локальном pack 75 общих SAE/ISO DTC-ссылок и 275 общих заметок; 15 make-labelled DTC и 51 связанная заметка исключены. Это не VAG-specific, не OEM repair data и не применимость для РФ/ЕАЭС.</p>',
   '        <details className="research-details"><summary>Атрибуция, лицензия и provenance MechanicDB</summary><pre className="research-attribution">{genericGuidanceSummary.attributionText}</pre>',
   '          <p>ODbL-1.0 · share-alike и атрибуция обязательны · ревизия {genericGuidanceSummary.sourceRevision} · SHA snapshot {genericGuidanceSummary.sourceSnapshotSha256} · SHA logical content {genericGuidanceSummary.logicalContentSha256} · SHA SQLite {genericGuidanceSummary.databaseSha256} · SHA source manifest {genericGuidanceSummary.sourceManifestSha256} · SHA ODbL notice {genericGuidanceSummary.licenseSha256} · SHA attribution {genericGuidanceSummary.attributionSha256}</p>',
   '          <p>{genericGuidanceSummary.rowEvidenceMode}</p><p>{genericGuidanceSummary.warning}</p></details></>}'
  ].join("\n");
  ui=exact(ui,creditsEnd,"\n"+credits+creditsEnd,"generic guidance attribution");
 }
 fs.writeFileSync(uiPath,ui,"utf8");

 const lifePath=path.join(desktop,"scripts/windows-installer-lifecycle.ps1");let life=fs.readFileSync(lifePath,"utf8");
 const lifeAnchor='  if ($summary.mode -ne "offline_local_sqlite_admin") { throw "The local SQLite API did not initialize in offline mode." }\n';
 if(!life.includes("api/local-research?dataset=generic-guidance-summary")){
  const checks=[
   '  # generic_repair_guidance is a separate local SQLite pack and must remain readable with external network blocked.',
   '  $genericSummary = Invoke-RestMethod -Uri "$baseUrl/api/local-research?dataset=generic-guidance-summary" -TimeoutSec 20',
   '  if ($genericSummary.counts.genericRepairGuidance -ne 275 -or $genericSummary.counts.genericDtcReferences -ne 75 -or $genericSummary.vagSpecific -ne $false -or $genericSummary.marketScope -ne "UNKNOWN") { throw "Generic guidance summary or scope boundary failed in offline desktop." }',
   '  $genericRows = Invoke-RestMethod -Uri "$baseUrl/api/local-research?dataset=generic-guidance&q=P0011" -TimeoutSec 20',
   '  if (@($genericRows.rows).Count -lt 1 -or $genericRows.rows[0].vagSpecific -ne $false -or $genericRows.rows[0].diagnosticExecutionAllowed -ne $false -or $genericRows.rows[0].exactVehicleFitment -ne $false) { throw "Generic guidance is missing or was promoted to VAG fitment/executable diagnostics." }',''
  ].join("\n");
  life=exact(life,lifeAnchor,lifeAnchor+checks,"offline lifecycle generic guidance");
 }
 fs.writeFileSync(lifePath,life,"utf8");

 const researchReadme=path.join(research,"README.md");
 const researchText="\n## MechanicDB generic repair guidance (ODbL-1.0)\n\n- Separate SQLite: "+id+"/generic-repair-guidance.sqlite.\n- Pinned upstream revision: "+revision+"; 75 generic SAE/ISO DTC references and 275 generic authored guidance rows.\n- 15 manufacturer-labelled DTC rows and 51 associated guidance rows are excluded. No DTC descriptions, parts mapping, costs, labor estimates or OEM procedures are copied.\n- Namespace generic_sae_iso; manufacturer and market UNKNOWN; no model/generation/year/engine/gearbox/ECU/PR/VIN fitment; no diagnostic execution.\n- Technical review is not independent; safety review is not assessed. Display only as generic research notes, never as VAG-specific repair instructions.\n- ODbL-1.0 requires attribution and share-alike. See bundled ATTRIBUTION.md, LICENSE-ODbL.txt and LICENSE-MIT.txt.\n";
 if(!fs.existsSync(researchReadme))fs.writeFileSync(researchReadme,"# Local research data\n","utf8");
 let rr=fs.readFileSync(researchReadme,"utf8");if(!rr.includes(id))fs.writeFileSync(researchReadme,rr+researchText,"utf8");
 const docs=path.join(desktop,"docs/RESEARCH_DATA_PACKS.md");fs.mkdirSync(path.dirname(docs),{recursive:true});
 if(!fs.existsSync(docs))fs.writeFileSync(docs,"# Research data packs\n","utf8");
 let dt=fs.readFileSync(docs,"utf8");if(!dt.includes(id))fs.writeFileSync(docs,dt+"\n## MechanicDB generic guidance — research only\n\nThe separate ODbL-1.0 pack contains 75 generic SAE/ISO DTC references and 275 generic authored guidance rows from a pinned MechanicDB sample. It is not VAG-specific, has UNKNOWN market scope and no exact vehicle, model-year, engine, gearbox, ECU, PR-code or VIN applicability. It is not an OEM repair procedure or executable test plan. Manufacturer-labelled rows are excluded. Attribution and share-alike are mandatory; see bundled license and attribution notices.\n","utf8");

 const env=Object.assign({},process.env,{VAG_TECH_PRO_RESEARCH_DIR:research});
 run("node",["--check",path.join(desktop,"lib/generic-repair-guidance-db.cjs")],desktop,env);
 run("node",["--check",path.join(desktop,"scripts/verify-generic-repair-guidance.cjs")],desktop,env);
 run("node",["scripts/verify-generic-repair-guidance.cjs"],desktop,env);
 if(!process.argv.includes("--skip-existing-research-verifier"))run("node",["scripts/verify-local-research-packs.cjs"],desktop,env);
 if(!process.argv.includes("--skip-tests"))run("node",["--test","tests/generic-repair-guidance-db.test.cjs","tests/generic-repair-guidance-ui-contract.test.cjs"],desktop,env);
 const report={schema_version:1,status:"verified_generic_research_only",integration_revision:"run69",pack_id:id,source_id:sourceId,source_revision:m.source_revision,source_snapshot_sha256:m.source_snapshot_sha256,logical_content_sha256:m.logical_content_sha256,database_sha256:m.database_sha256,source_manifest_sha256:manSha,root_manifest_sha256:shaFile(rootPath),license:"ODbL-1.0",attribution_required:true,share_alike_required:true,market_scope:"UNKNOWN",applicability_level:"generic_only",vag_specific:false,exact_vehicle_fitment:false,engine_gearbox_fitment:false,ecu_fitment:false,diagnostic_execution_allowed:false,oem_repair_procedure:false,counts:m.counts};
 writeJson(path.join(research,"run69-integration-verification.json"),report);
 process.stdout.write(JSON.stringify(report,null,2)+"\n");
}
try{main();}catch(e){process.stderr.write("Generic MechanicDB desktop integration failed: "+(e.stack||e.message)+"\n");process.exitCode=1;}

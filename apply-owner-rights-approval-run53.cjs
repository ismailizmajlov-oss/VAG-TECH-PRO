"use strict";
const fs = require("node:fs");
const path = require("node:path");
const root = path.resolve(process.cwd(), "desktop-source");

function read(file) {
  const target = path.join(root, file);
  if (!fs.existsSync(target)) throw new Error(`Required file is missing: ${file}`);
  return fs.readFileSync(target, "utf8").replace(/\r\n/g, "\n");
}
function write(file, value) {
  fs.writeFileSync(path.join(root, file), value, "utf8");
}
function replaceExactly(source, before, after, label) {
  if (source.includes(after)) return source;
  const count = source.split(before).length - 1;
  if (count !== 1) throw new Error(`${label}: expected exactly one original anchor, found ${count}`);
  return source.replace(before, after);
}

function patchCore() {
  let source = read("lib/local-core-db.cjs");
  const fn = `const OWNER_RIGHTS_CONFIRMATION = "ПОДТВЕРЖДАЮ, ЧТО ИМЕЮ ПРАВО ИСПОЛЬЗОВАТЬ ЭТОТ ИСТОЧНИК В VAG TECH PRO НА УКАЗАННЫХ УСЛОВИЯХ: КОММЕРЧЕСКОЕ ИСПОЛЬЗОВАНИЕ, ПОКАЗ, ОФЛАЙН-КЭШ, МАССОВОЕ ИСПОЛЬЗОВАНИЕ И РАСПРОСТРАНЕНИЕ";
function approveSourceByOwner(dbPath, input, options = {}) {
  if (!input || typeof input !== "object" || Array.isArray(input)) throw new TypeError("Source rights approval metadata is required");
  const sourceId = String(input.source_id || "").trim().toLowerCase();
  if (!/^[a-z0-9][a-z0-9._-]{1,63}$/.test(sourceId)) throw new TypeError("Source rights approval requires a valid source ID");
  for (const field of ["expected_revision", "expected_market_scope", "license_id", "license_url", "rights_status"]) {
    if (typeof input[field] !== "string" || !input[field].trim() || input[field].trim().length > 180) throw new TypeError("Source rights approval " + field + " is required");
  }
  if (!["approved_by_published_license", "approved_by_written_permission"].includes(input.rights_status)) {
    throw new Error("Source rights approval must be based on a published license or written permission");
  }
  if (input.owner_confirmation !== OWNER_RIGHTS_CONFIRMATION) {
    throw new Error("Source rights approval requires the exact owner confirmation phrase");
  }
  const grants = ["commercial_use_allowed", "display_allowed", "offline_cache_allowed", "bulk_reuse_allowed", "redistribution_allowed"];
  if (grants.some((field) => input[field] !== true)) {
    throw new Error("Source rights approval requires explicit grants for commercial use, display, offline cache, bulk reuse and redistribution");
  }
  if (typeof input.share_alike_required !== "boolean" || typeof input.attribution_required !== "boolean") {
    throw new TypeError("Source rights approval requires explicit Share-Alike and attribution terms");
  }
  if (input.attribution_required && (typeof input.attribution_text !== "string" || !input.attribution_text.trim())) {
    throw new Error("Source rights approval requires the exact attribution text when attribution is required");
  }
  if (typeof input.attribution_text === "string" && input.attribution_text.length > 1000) throw new TypeError("Source rights attribution text is too long");
  if (!["license_sha256", "rights_evidence_sha256", "source_snapshot_sha256"].every((field) => HASH_RE.test(input[field] || ""))) {
    throw new Error("Source rights approval requires valid license, rights-evidence and source-snapshot SHA-256 hashes");
  }
  let licenseUrl;
  try { licenseUrl = new URL(input.license_url); } catch { throw new TypeError("Source rights license URL must be a valid HTTPS URL"); }
  if (licenseUrl.protocol !== "https:") throw new TypeError("Source rights license URL must be a valid HTTPS URL");

  const db = openDatabase(dbPath);
  try {
    const now = (options.clock || (() => new Date()))().toISOString();
    db.exec("BEGIN IMMEDIATE");
    try {
      const current = db.prepare("SELECT source_id,revision,market_scope,rights_status,status,source_url FROM sources WHERE source_id=?").get(sourceId);
      if (!current) throw new Error("Source rights approval candidate was not found");
      if (typeof current.source_url !== "string" || !current.source_url.startsWith("https://")) throw new Error("Source rights approval requires a registered HTTPS source URL");
      if (current.status !== "candidate" || current.rights_status !== "permission_required") {
        throw new Error("Source rights approval requires a permission_required candidate; approved or blocked sources cannot be overwritten");
      }
      if (current.revision !== input.expected_revision || current.market_scope !== input.expected_market_scope) {
        throw new Error("Source rights approval revision or market scope changed; refresh the candidate before approval");
      }
      const updated = db.prepare(\`UPDATE sources SET
        license_id=?,license_url=?,license_sha256=?,rights_status=?,
        commercial_use_allowed=1,display_allowed=1,offline_cache_allowed=1,bulk_reuse_allowed=1,redistribution_allowed=1,
        share_alike_required=?,attribution_required=?,attribution_text=?,source_snapshot_sha256=?,rights_evidence_sha256=?,
        status='approved',updated_at=?
        WHERE source_id=? AND status='candidate' AND rights_status='permission_required'\`).run(
        input.license_id.trim(), licenseUrl.toString(), input.license_sha256, input.rights_status,
        input.share_alike_required ? 1 : 0, input.attribution_required ? 1 : 0,
        input.attribution_required ? input.attribution_text.trim() : null,
        input.source_snapshot_sha256, input.rights_evidence_sha256, now, sourceId
      );
      if (updated.changes !== 1) throw new Error("Source rights approval lost its candidate-state precondition; no changes were committed");
      const audit = {
        approval_method: input.rights_status,
        expected_revision: current.revision,
        market_scope: current.market_scope,
        license_id: input.license_id.trim(),
        license_sha256: input.license_sha256,
        rights_evidence_sha256: input.rights_evidence_sha256,
        source_snapshot_sha256: input.source_snapshot_sha256,
        grants: Object.fromEntries(grants.map((field) => [field, true])),
        share_alike_required: input.share_alike_required,
        attribution_required: input.attribution_required,
        attribution_text: input.attribution_required ? input.attribution_text.trim() : null,
        approval_note: typeof input.approval_note === "string" ? input.approval_note.trim().slice(0, 500) : null,
        evidence_files_remain_with_owner: true,
        technical_records_approved: false,
      };
      db.prepare("INSERT INTO audit_events(event_type,entity_type,entity_key,details_json,created_at) VALUES('source_rights_approved_by_owner','source',?,?,?)")
        .run(sourceId, JSON.stringify(audit), now);
      db.exec("COMMIT");
      return db.prepare(\`SELECT source_id,rights_status,status,revision,market_scope,license_id,license_sha256,source_snapshot_sha256,rights_evidence_sha256,updated_at
        FROM sources WHERE source_id=?\`).get(sourceId);
    } catch (error) { db.exec("ROLLBACK"); throw error; }
  } finally { db.close(); }
}

`;
  source = replaceExactly(source, "function registerSourceCandidate(dbPath, input, options = {}) {", fn + "function registerSourceCandidate(dbPath, input, options = {}) {", "insert owner-controlled source-rights approval function");
  source = replaceExactly(source,
    "module.exports={APP_ID,SCHEMA_VERSION,RECORD_TYPES,CRITICAL_TYPES,APPLICABILITY_PRECISIONS,MIGRATION_1,canonical,sha256,initializeDatabase,openDatabase,validateDatabase,registerSource,registerSourceCandidate,importPackage,",
    "module.exports={APP_ID,SCHEMA_VERSION,RECORD_TYPES,CRITICAL_TYPES,APPLICABILITY_PRECISIONS,MIGRATION_1,canonical,sha256,initializeDatabase,openDatabase,validateDatabase,registerSource,registerSourceCandidate,approveSourceByOwner,importPackage,",
    "export owner-controlled source-rights approval function");
  write("lib/local-core-db.cjs", source);
}

function patchRoute() {
  let source = read("app/api/local-core/route.ts");
  source = replaceExactly(source,
    '    if (body.action === "source.register-candidate") return Response.json({ source: localCore.registerSourceCandidate(dbPath, body.source) }, { status: 201, headers });',
    '    if (body.action === "source.register-candidate") return Response.json({ source: localCore.registerSourceCandidate(dbPath, body.source) }, { status: 201, headers });\n    if (body.action === "source.approve-by-owner") return Response.json({ source: localCore.approveSourceByOwner(dbPath, body.approval) }, { status: 200, headers });',
    "add owner-only source rights approval API action");
  source = replaceExactly(source,
    'const safe = /required|valid|unknown|unsupported|too long|rights|SHA-256|configuration|bookmark|vehicle|query|market|revision|collision|self-approve|exact|backup|SQLite|database/i.test(message);',
    'const safe = /required|valid|unknown|unsupported|too long|rights|approval|evidence|SHA-256|configuration|bookmark|vehicle|query|market|revision|collision|self-approve|exact|backup|SQLite|database/i.test(message);',
    "return safe owner-rights approval validation messages");
  const deadHelperStart = source.indexOf("function parseHostAuthority(");
  const loopbackHelperStart = deadHelperStart >= 0 ? source.indexOf("function isLoopbackHost(", deadHelperStart) : -1;
  if (deadHelperStart >= 0 && loopbackHelperStart > deadHelperStart) source = source.slice(0, deadHelperStart) + source.slice(loopbackHelperStart);
  write("app/api/local-core/route.ts", source);
}

function patchUi() {
  let source = read("components/local-data-admin.tsx");
  source = replaceExactly(source,
    '  status: string; snapshot_count: number; record_count: number; verified_record_count: number; updated_at: string;',
    '  status: string; snapshot_count: number; record_count: number; verified_record_count: number; updated_at: string;\n  license_sha256: string | null; source_snapshot_sha256: string | null; rights_evidence_sha256: string | null;',
    "include rights evidence hashes in source admin type");
  source = replaceExactly(source,
    '  const [busy, setBusy] = useState<"import" | "backup" | "restore" | "source" | null>(null);',
    '  const [busy, setBusy] = useState<"import" | "backup" | "restore" | "source" | "approve" | null>(null);',
    "add owner approval busy state");
  source = replaceExactly(source,
    '  const [candidateSource, setCandidateSource] = useState({ source_id: "", publisher: "", title: "", source_type: "public_registry", source_url: "", revision: "", market_scope: "RU/EAEU", license_id: "", license_url: "", attribution_text: "" });',
    '  const [candidateSource, setCandidateSource] = useState({ source_id: "", publisher: "", title: "", source_type: "public_registry", source_url: "", revision: "", market_scope: "RU/EAEU", license_id: "", license_url: "", attribution_text: "" });\n  const [approval, setApproval] = useState({ source_id: "", rights_status: "approved_by_published_license" as "approved_by_published_license" | "approved_by_written_permission", license_id: "", license_url: "", commercial_use_allowed: false, display_allowed: false, offline_cache_allowed: false, bulk_reuse_allowed: false, redistribution_allowed: false, share_alike_required: "" as "" | "yes" | "no", attribution_required: "" as "" | "yes" | "no", attribution_text: "", owner_confirmation: "", approval_note: "" });\n  const [approvalFiles, setApprovalFiles] = useState<{ license: File | null; rightsEvidence: File | null; snapshot: File | null }>({ license: null, rightsEvidence: null, snapshot: null });',
    "add owner rights approval form state");
  source = replaceExactly(source,
    'function safeHttpsUrl(value: string | null) {',
    'const OWNER_CONFIRMATION = "ПОДТВЕРЖДАЮ, ЧТО ИМЕЮ ПРАВО ИСПОЛЬЗОВАТЬ ЭТОТ ИСТОЧНИК В VAG TECH PRO НА УКАЗАННЫХ УСЛОВИЯХ: КОММЕРЧЕСКОЕ ИСПОЛЬЗОВАНИЕ, ПОКАЗ, ОФЛАЙН-КЭШ, МАССОВОЕ ИСПОЛЬЗОВАНИЕ И РАСПРОСТРАНЕНИЕ";\nasync function sha256File(file: File) {\n  const digest = await window.crypto.subtle.digest("SHA-256", await file.arrayBuffer());\n  return Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, "0")).join("");\n}\nfunction safeHttpsUrl(value: string | null) {',
    "add local-only evidence hashing helper");
  source = replaceExactly(source,
    '  async function importPackage() {',
    `  function updateApproval<K extends keyof typeof approval>(key: K, value: (typeof approval)[K]) {
    setApproval((current) => ({ ...current, [key]: value }));
  }
  function updateApprovalFile(key: "license" | "rightsEvidence" | "snapshot", event: ChangeEvent<HTMLInputElement>) {
    setApprovalFiles((current) => ({ ...current, [key]: event.target.files?.[0] || null }));
  }
  async function approveSource(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const candidate = sources.find((item) => item.source_id === approval.source_id && item.status === "candidate" && item.rights_status === "permission_required");
    if (!candidate) { onMessage("Выберите действующий источник-кандидат со статусом permission_required."); return; }
    if (!approvalFiles.license || !approvalFiles.rightsEvidence || !approvalFiles.snapshot) { onMessage("Нужны файл лицензии, документ с подтверждением прав и точный снимок исходных данных."); return; }
    if (approvalFiles.license.size > 20 * 1024 * 1024 || approvalFiles.rightsEvidence.size > 20 * 1024 * 1024 || approvalFiles.snapshot.size > 128 * 1024 * 1024) {
      onMessage("Лицензия и подтверждение прав должны быть до 20 MiB каждое, снимок источника — до 128 MiB."); return;
    }
    if (![approval.commercial_use_allowed, approval.display_allowed, approval.offline_cache_allowed, approval.bulk_reuse_allowed, approval.redistribution_allowed].every(Boolean)) {
      onMessage("Нельзя подтвердить источник без прямого разрешения на все пять видов использования."); return;
    }
    if (!approval.license_id.trim() || !safeHttpsUrl(approval.license_url) || !approval.rights_status || approval.share_alike_required === "" || approval.attribution_required === "") {
      onMessage("Заполните лицензию, HTTPS URL, Share-Alike и условие атрибуции."); return;
    }
    if (approval.attribution_required === "yes" && !approval.attribution_text.trim()) { onMessage("Укажите обязательный текст атрибуции."); return; }
    if (approval.owner_confirmation !== OWNER_CONFIRMATION) { onMessage("Введите точную фразу подтверждения владельца."); return; }
    if (!window.confirm("Вы подтверждаете, что лично проверили документы и имеете право использовать этот источник в VAG TECH PRO, а документы прямо разрешают коммерческое использование, отображение, офлайн-кэширование, массовое использование и распространение? Технические записи всё равно останутся непроверенными.")) return;
    setBusy("approve");
    try {
      const [licenseSha, rightsEvidenceSha, snapshotSha] = await Promise.all([
        sha256File(approvalFiles.license), sha256File(approvalFiles.rightsEvidence), sha256File(approvalFiles.snapshot),
      ]);
      const response = await fetch("/api/local-core", {
        method: "POST", headers: { "Content-Type": "application/json" }, cache: "no-store",
        body: JSON.stringify({ action: "source.approve-by-owner", approval: {
          source_id: candidate.source_id, expected_revision: candidate.revision, expected_market_scope: candidate.market_scope,
          rights_status: approval.rights_status, license_id: approval.license_id.trim(), license_url: approval.license_url.trim(),
          license_sha256: licenseSha, rights_evidence_sha256: rightsEvidenceSha, source_snapshot_sha256: snapshotSha,
          commercial_use_allowed: true, display_allowed: true, offline_cache_allowed: true, bulk_reuse_allowed: true, redistribution_allowed: true,
          share_alike_required: approval.share_alike_required === "yes", attribution_required: approval.attribution_required === "yes",
          attribution_text: approval.attribution_text.trim(), owner_confirmation: approval.owner_confirmation, approval_note: approval.approval_note.trim(),
        } }),
      });
      const body = await readJson(response);
      setApproval({ source_id: "", rights_status: "approved_by_published_license", license_id: "", license_url: "", commercial_use_allowed: false, display_allowed: false, offline_cache_allowed: false, bulk_reuse_allowed: false, redistribution_allowed: false, share_alike_required: "", attribution_required: "", attribution_text: "", owner_confirmation: "", approval_note: "" });
      setApprovalFiles({ license: null, rightsEvidence: null, snapshot: null });
      for (const id of ["source-license-evidence-file", "source-rights-evidence-file", "source-snapshot-evidence-file"]) {
        const input = document.getElementById(id) as HTMLInputElement | null;
        if (input) input.value = "";
      }
      await refresh(true);
      onMessage(\`Права источника ${'${'}body.source?.source_id || candidate.source_id} зафиксированы по подтверждению владельца. Хэши сохранены; технические записи и применимость не подтверждены.\`);
    } catch (cause) {
      onMessage(cause instanceof Error ? cause.message : "Не удалось зафиксировать подтверждение прав источника.");
    } finally { setBusy(null); }
  }

  async function importPackage() {`,
    "add owner rights approval action");
  source = replaceExactly(source,
    '<div><h3>Добавить источник-кандидат</h3><p>Новая запись всегда получает статус permission_required и нулевые права на коммерческое использование, показ, офлайн-кэш, массовое использование и распространение. Утвердить права из этого экрана нельзя.</p></div>',
    '<div><h3>Добавить источник-кандидат</h3><p>Новая запись всегда получает статус permission_required и нулевые права. Подтверждение прав доступно отдельно только владельцу при наличии проверенной лицензии или письменного разрешения и файлов-доказательств.</p></div>',
    "clarify candidate registration and owner approval separation");
  source = replaceExactly(source,
    '      <p>Пакет импортируется только при совпадении SHA-256, ревизии, прав источника и применимости. Импортированные технические записи остаются кандидатами до отдельной модерации. Этот экран не позволяет самостоятельно объявить источник лицензированным или запись проверенной.</p>',
    '      <p>Пакет импортируется только при совпадении SHA-256, ревизии, прав источника и применимости. Владелец может отдельно зафиксировать права источника только после проверки документов и локального хэширования доказательств. Импортированные технические записи остаются кандидатами до отдельной технической модерации; подтверждение прав не подтверждает применимость.</p>',
    "clarify owner approval and technical review separation");
  source = replaceExactly(source,
    '      <div className="admin-source-grid"><span>Лицензия <b>{source.license_id || "Не указана"}</b></span><span>Коммерция <b>{rightsLabel(source.commercial_use_allowed)}</b></span><span>Показ <b>{rightsLabel(source.display_allowed)}</b></span><span>Офлайн-кэш <b>{rightsLabel(source.offline_cache_allowed)}</b></span><span>Массовое использование <b>{rightsLabel(source.bulk_reuse_allowed)}</b></span><span>Перераспространение <b>{rightsLabel(source.redistribution_allowed)}</b></span><span>Снимки <b>{source.snapshot_count}</b></span><span>Записи <b>{source.record_count} · проверено {source.verified_record_count}</b></span></div>',
    '      <div className="admin-source-grid"><span>Лицензия <b>{source.license_id || "Не указана"}</b></span><span>Коммерция <b>{rightsLabel(source.commercial_use_allowed)}</b></span><span>Показ <b>{rightsLabel(source.display_allowed)}</b></span><span>Офлайн-кэш <b>{rightsLabel(source.offline_cache_allowed)}</b></span><span>Массовое использование <b>{rightsLabel(source.bulk_reuse_allowed)}</b></span><span>Перераспространение <b>{rightsLabel(source.redistribution_allowed)}</b></span><span>SHA-256 лицензии <b>{source.license_sha256 || "—"}</b></span><span>SHA-256 снимка <b>{source.source_snapshot_sha256 || "—"}</b></span><span>SHA-256 прав <b>{source.rights_evidence_sha256 || "—"}</b></span><span>Снимки <b>{source.snapshot_count}</b></span><span>Записи <b>{source.record_count} · проверено {source.verified_record_count}</b></span></div>',
    "display license, rights-evidence and source-snapshot hashes in the source registry");
  const approvalForm = String.raw`
    <div className="admin-section-head"><h2>Подтверждение прав владельцем</h2><span>Не подтверждает точность данных или применимость</span></div>
    <form className="admin-tool-card admin-source-form admin-source-approval" onSubmit={approveSource}>
      <div><h3>Зафиксировать лицензию или письменное разрешение</h3><p>Только владелец может выполнить это действие после самостоятельной проверки документов. Приложение не толкует договор и не проверяет подлинность подписи. Файлы не отправляются на сервер: в SQLite сохраняются только SHA-256. Исходные файлы необходимо хранить отдельно.</p></div>
      <div className="admin-source-form-grid">
        <label>Источник-кандидат<select required value={approval.source_id} onChange={(event) => updateApproval("source_id", event.target.value)} disabled={busy !== null || loading}><option value="">Выберите permission_required источник</option>{sources.filter((item) => item.status === "candidate" && item.rights_status === "permission_required").map((item) => <option key={item.source_id} value={item.source_id}>{item.publisher} · {item.title} · {item.market_scope}</option>)}</select></label>
        <label>Основание<select required value={approval.rights_status} onChange={(event) => updateApproval("rights_status", event.target.value as typeof approval.rights_status)}><option value="approved_by_published_license">Опубликованная лицензия</option><option value="approved_by_written_permission">Письменное разрешение</option></select></label>
        <label>ID лицензии<input required maxLength={100} value={approval.license_id} onChange={(event) => updateApproval("license_id", event.target.value)} placeholder="CC-BY-4.0 / номер разрешения" /></label>
        <label>HTTPS URL лицензии / разрешения<input required type="url" value={approval.license_url} onChange={(event) => updateApproval("license_url", event.target.value)} placeholder="https://…" /></label>
        <label>Файл лицензии<input id="source-license-evidence-file" type="file" required accept=".txt,.md,.pdf,text/plain,application/pdf" onChange={(event) => updateApprovalFile("license", event)} disabled={busy !== null} /></label>
        <label>Файл подтверждения прав<input id="source-rights-evidence-file" type="file" required accept=".txt,.md,.pdf,text/plain,application/pdf" onChange={(event) => updateApprovalFile("rightsEvidence", event)} disabled={busy !== null} /></label>
        <label className="admin-source-form-wide">Точный снимок исходных данных<input id="source-snapshot-evidence-file" type="file" required onChange={(event) => updateApprovalFile("snapshot", event)} disabled={busy !== null} /></label>
        <label>Share-Alike<select required value={approval.share_alike_required} onChange={(event) => updateApproval("share_alike_required", event.target.value as typeof approval.share_alike_required)}><option value="">Укажите по документу</option><option value="yes">Обязателен</option><option value="no">Не обязателен</option></select></label>
        <label>Атрибуция<select required value={approval.attribution_required} onChange={(event) => updateApproval("attribution_required", event.target.value as typeof approval.attribution_required)}><option value="">Укажите по документу</option><option value="yes">Обязательна</option><option value="no">Не обязательна</option></select></label>
        <label className="admin-source-form-wide">Точный текст атрибуции<textarea rows={2} maxLength={1000} value={approval.attribution_text} onChange={(event) => updateApproval("attribution_text", event.target.value)} required={approval.attribution_required === "yes"} placeholder="Текст, который должен отображаться в приложении" /></label>
        <label className="admin-source-form-wide">Примечание владельца<textarea rows={2} maxLength={500} value={approval.approval_note} onChange={(event) => updateApproval("approval_note", event.target.value)} placeholder="Например: номер письма, пункт лицензии, дата проверки" /></label>
      </div>
      <fieldset className="admin-rights-confirmations"><legend>Документ прямо разрешает все перечисленные действия</legend>
        <label><input type="checkbox" required checked={approval.commercial_use_allowed} onChange={(event) => updateApproval("commercial_use_allowed", event.target.checked)} /> Коммерческое использование</label>
        <label><input type="checkbox" required checked={approval.display_allowed} onChange={(event) => updateApproval("display_allowed", event.target.checked)} /> Отображение в приложении</label>
        <label><input type="checkbox" required checked={approval.offline_cache_allowed} onChange={(event) => updateApproval("offline_cache_allowed", event.target.checked)} /> Офлайн-кэширование</label>
        <label><input type="checkbox" required checked={approval.bulk_reuse_allowed} onChange={(event) => updateApproval("bulk_reuse_allowed", event.target.checked)} /> Массовое использование</label>
        <label><input type="checkbox" required checked={approval.redistribution_allowed} onChange={(event) => updateApproval("redistribution_allowed", event.target.checked)} /> Распространение вместе с VAG TECH PRO</label>
      </fieldset>
      <label className="admin-owner-confirmation">Подтверждение владельца — введите дословно: <b>{OWNER_CONFIRMATION}</b><input required value={approval.owner_confirmation} onChange={(event) => updateApproval("owner_confirmation", event.target.value)} autoComplete="off" /></label>
      <div className="admin-import-actions"><span>Хэшируются локально: лицензия, разрешение и снимок. Содержимое файлов не передаётся API.</span><button type="submit" disabled={busy !== null || loading || !sources.some((item) => item.source_id === approval.source_id && item.status === "candidate" && item.rights_status === "permission_required")}>{busy === "approve" ? "Проверка хэшей и фиксация…" : "Подтвердить только права источника"}</button></div>
    </form>
`;
  source = replaceExactly(source,
    '    {loading ? <div className="empty">Загрузка локального реестра…</div> : error ? <div className="empty">{error}</div> : sources.length ? <div className="admin-source-list">{sources.map((source) => <article className="result admin-source" key={source.source_id}>',
    approvalForm + '    {loading ? <div className="empty">Загрузка локального реестра…</div> : error ? <div className="empty">{error}</div> : sources.length ? <div className="admin-source-list">{sources.map((source) => <article className="result admin-source" key={source.source_id}>',
    "insert owner approval form before source register list");
  write("components/local-data-admin.tsx", source);
}

function patchStyles() {
  let source = read("app/globals.css");
  const css = String.raw`
.admin-rights-confirmations{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px;margin:0;padding:11px;border:1px solid var(--line);border-radius:8px;background:var(--bg)}
.admin-rights-confirmations legend{padding:0 5px;color:var(--text);font-size:10px;font-weight:800}
.admin-rights-confirmations label{display:flex;align-items:center;gap:7px;color:var(--muted);font-size:10px}
.admin-rights-confirmations input{accent-color:#b83a45}
.admin-owner-confirmation{display:grid;gap:6px;color:var(--muted);font-size:10px}
.admin-owner-confirmation b{color:var(--text);font-size:10px;line-height:1.5;overflow-wrap:anywhere}
.admin-owner-confirmation input{width:100%;min-height:36px;padding:8px;border:1px solid var(--line);border-radius:7px;background:var(--bg);color:var(--text);font:inherit;font-size:10px}
.admin-source-approval .admin-source-form-grid select{width:100%;min-height:36px;padding:8px;border:1px solid var(--line);border-radius:7px;background:var(--bg);color:var(--text);font:inherit;font-size:10px}
@media(max-width:700px){.admin-rights-confirmations{grid-template-columns:1fr}}
`;
  source = replaceExactly(source, ".admin-source-form{margin:10px 0 12px}", ".admin-source-form{margin:10px 0 12px}\n" + css, "style owner rights approval controls");
  write("app/globals.css", source);
}

function patchCoreTests() {
  let source = read("tests/local-core-db.test.cjs");
  source = source.replace("local source administration can register permission-required candidates but cannot approve or overwrite sources", "candidate registration cannot approve or overwrite sources; owner approval is separate");
  const block = String.raw`

test("owner approval records source rights only and never verifies technical records", (t) => {
  const { dbPath } = fixture(t);
  core.registerSourceCandidate(dbPath, {
    source_id: "owner-approved-source", publisher: "Rights holder", title: "Authorized dataset", source_type: "written_permission",
    source_url: "https://rights.example/source", revision: "rev-2026-11", market_scope: "RU/EAEU",
  });
  const approval = {
    source_id: "owner-approved-source", expected_revision: "rev-2026-11", expected_market_scope: "RU/EAEU",
    rights_status: "approved_by_written_permission", license_id: "PERMISSION-2026-11", license_url: "https://rights.example/permission",
    license_sha256: "a".repeat(64), rights_evidence_sha256: "b".repeat(64), source_snapshot_sha256: "c".repeat(64),
    commercial_use_allowed: true, display_allowed: true, offline_cache_allowed: true, bulk_reuse_allowed: true, redistribution_allowed: true,
    share_alike_required: false, attribution_required: true, attribution_text: "Source: Rights holder, permission 2026-11",
    owner_confirmation: "ПОДТВЕРЖДАЮ, ЧТО ИМЕЮ ПРАВО ИСПОЛЬЗОВАТЬ ЭТОТ ИСТОЧНИК В VAG TECH PRO НА УКАЗАННЫХ УСЛОВИЯХ: КОММЕРЧЕСКОЕ ИСПОЛЬЗОВАНИЕ, ПОКАЗ, ОФЛАЙН-КЭШ, МАССОВОЕ ИСПОЛЬЗОВАНИЕ И РАСПРОСТРАНЕНИЕ",
    approval_note: "Signed permission checked by owner",
  };
  core.registerSourceCandidate(dbPath, { source_id: "source-without-url", publisher: "Rights holder", title: "No origin URL", source_type: "written_permission", revision: "rev-no-url", market_scope: "RU/EAEU" });
  assert.throws(() => core.approveSourceByOwner(dbPath, { ...approval, source_id: "source-without-url", expected_revision: "rev-no-url" }), /registered HTTPS source URL/);
  assert.throws(() => core.approveSourceByOwner(dbPath, { ...approval, owner_confirmation: "" }), /exact owner confirmation/);
  assert.throws(() => core.approveSourceByOwner(dbPath, { ...approval, redistribution_allowed: false }), /explicit grants/);
  assert.throws(() => core.approveSourceByOwner(dbPath, { ...approval, license_sha256: "bad" }), /valid license, rights-evidence and source-snapshot/);
  assert.throws(() => core.approveSourceByOwner(dbPath, { ...approval, expected_revision: "stale" }), /revision or market scope changed/);
  assert.throws(() => core.approveSourceByOwner(dbPath, { ...approval, license_url: "http://rights.example/permission" }), /HTTPS URL/);
  const approved = core.approveSourceByOwner(dbPath, approval);
  assert.equal(approved.status, "approved");
  assert.equal(approved.rights_status, "approved_by_written_permission");
  assert.equal(approved.revision, "rev-2026-11");
  assert.equal(approved.market_scope, "RU/EAEU");
  assert.equal(approved.license_sha256, "a".repeat(64));
  assert.equal(approved.rights_evidence_sha256, "b".repeat(64));
  const db = new DatabaseSync(dbPath);
  const audit = db.prepare("SELECT event_type,details_json FROM audit_events WHERE entity_key='owner-approved-source' ORDER BY id DESC LIMIT 1").get();
  assert.equal(audit.event_type, "source_rights_approved_by_owner");
  const details = JSON.parse(audit.details_json);
  assert.equal(details.technical_records_approved, false);
  assert.equal(details.evidence_files_remain_with_owner, true);
  assert.equal(db.prepare("SELECT count(*) AS n FROM technical_records").get().n, 0);
  db.close();
  assert.throws(() => core.approveSourceByOwner(dbPath, approval), /permission_required candidate/);
  const pkg = packageOf([genericDtc()], {
    package_id: "owner-approved-source-package", source_id: "owner-approved-source", source_revision: "rev-2026-11", market_scope: "RU/EAEU",
    source_snapshot_sha256: "c".repeat(64), license_sha256: "a".repeat(64), rights_evidence_sha256: "b".repeat(64),
    snapshot_manifest: { upstream_revision: "rev-2026-11", source_sha256: "c".repeat(64), record_count: 1 },
  });
  const imported = core.importPackage(dbPath, pkg);
  assert.equal(imported.inserted, 1);
  assert.equal(core.searchVerifiedTechnicalRecords(dbPath, { record_type: "dtc_generic", query: "P0300" }).length, 0);
  const stored = new DatabaseSync(dbPath);
  assert.equal(stored.prepare("SELECT review_status FROM technical_records WHERE source_id='owner-approved-source'").get().review_status, "candidate");
  stored.close();
});
`;
  if (!source.includes('test("owner approval records source rights only')) source += block;
  write("tests/local-core-db.test.cjs", source);
}

function patchApiTests() {
  let source = read("tests/local-core-api.test.cjs");
  source = replaceExactly(source,
    'const { execFileSync } = require("node:child_process");\nconst core = require("../lib/local-core-db.cjs");',
    'const { execFileSync } = require("node:child_process");\nconst { DatabaseSync } = require("node:sqlite");\nconst core = require("../lib/local-core-db.cjs");',
    "import DatabaseSync for the owner approval API audit assertion");
  const anchor = '  const crossOrigin = await POST(new Request(baseUrl, {';
  const block = String.raw`  const ownerApproval = {
    source_id: "fgis-otts-candidate", expected_revision: "2026-11-03", expected_market_scope: "RU/EAEU",
    rights_status: "approved_by_written_permission", license_id: "PERMISSION-2026-11", license_url: "https://example.gov.ru/permission",
    license_sha256: "d".repeat(64), rights_evidence_sha256: "e".repeat(64), source_snapshot_sha256: "f".repeat(64),
    commercial_use_allowed: true, display_allowed: true, offline_cache_allowed: true, bulk_reuse_allowed: true, redistribution_allowed: true,
    share_alike_required: false, attribution_required: true, attribution_text: "Source: Rosstandart permission 2026-11",
    owner_confirmation: "ПОДТВЕРЖДАЮ, ЧТО ИМЕЮ ПРАВО ИСПОЛЬЗОВАТЬ ЭТОТ ИСТОЧНИК В VAG TECH PRO НА УКАЗАННЫХ УСЛОВИЯХ: КОММЕРЧЕСКОЕ ИСПОЛЬЗОВАНИЕ, ПОКАЗ, ОФЛАЙН-КЭШ, МАССОВОЕ ИСПОЛЬЗОВАНИЕ И РАСПРОСТРАНЕНИЕ",
  };
  const deniedApprovalResponse = await POST(new Request(baseUrl, {
    method: "POST", headers: { ...headers, "content-type": "application/json" },
    body: JSON.stringify({ action: "source.approve-by-owner", approval: { ...ownerApproval, owner_confirmation: "wrong" } }),
  }));
  assert.equal(deniedApprovalResponse.status, 400);
  const approvalResponse = await POST(new Request(baseUrl, {
    method: "POST", headers: { ...headers, "content-type": "application/json" },
    body: JSON.stringify({ action: "source.approve-by-owner", approval: ownerApproval }),
  }));
  assert.equal(approvalResponse.status, 200);
  const approvedCandidate = await approvalResponse.json();
  assert.equal(approvedCandidate.source.status, "approved");
  assert.equal(approvedCandidate.source.rights_status, "approved_by_written_permission");
  assert.equal(core.listSources(dbPath).find((row) => row.source_id === "fgis-otts-candidate").offline_cache_allowed, 1);
  const approvalDb = new DatabaseSync(dbPath);
  assert.equal(approvalDb.prepare("SELECT count(*) AS n FROM technical_records").get().n, 0);
  approvalDb.close();

`;
  if (!source.includes("const ownerApproval = {")) source = replaceExactly(source, anchor, block + anchor, "insert local API owner rights approval regression");
  write("tests/local-core-api.test.cjs", source);
}

function patchUiTests() {
  let source = read("tests/local-data-admin-ui-contract.test.cjs");
  source = source.replace('assert.match(component, /не позволяет самостоятельно объявить источник лицензированным/);', 'assert.match(component, /Владелец может отдельно зафиксировать права источника/);');
  const block = String.raw`

test("owner rights approval hashes local evidence and keeps technical applicability unverified", () => {
  const component = read("components/local-data-admin.tsx");
  const core = read("lib/local-core-db.cjs");
  const route = read("app/api/local-core/route.ts");
  assert.match(component, /crypto\.subtle\.digest\("SHA-256"/);
  assert.match(component, /source-rights-evidence-file/);
  assert.match(component, /source-snapshot-evidence-file/);
  assert.match(component, /owner_confirmation/);
  assert.match(component, /технические записи и применимость не подтверждены/);
  assert.match(component, /Файлы не отправляются на сервер/);
  assert.match(component, /SHA-256 снимка/);
  assert.match(component, /SHA-256 прав/);
  assert.match(route, /source\.approve-by-owner/);
  assert.match(route, /approveSourceByOwner/);
  assert.doesNotMatch(route, /originMatchesHostHeader/);
  assert.match(core, /technical_records_approved: false/);
  assert.match(core, /evidence_files_remain_with_owner: true/);
});
`;
  if (!source.includes('test("owner rights approval hashes local evidence')) source += block;
  write("tests/local-data-admin-ui-contract.test.cjs", source);
}

patchCore();
patchRoute();
patchUi();
patchStyles();
patchCoreTests();
patchApiTests();
patchUiTests();
console.log(JSON.stringify({
  status: "owner_source_rights_approval_workflow_applied",
  scope: "manual owner attestation only; source records remain technical candidates",
  evidence: ["license SHA-256", "written permission / terms SHA-256", "source snapshot SHA-256"],
  dataHandling: "evidence files are hashed locally and are not uploaded; owner retains originals",
  safety: "all five reuse rights required; source candidate and revision/market scope preconditions; audit event",
  tests: ["core approval and rights gate", "API action", "UI local hashing contract"]
}, null, 2));
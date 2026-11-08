"use client";
import { useEffect, useState, type FormEvent } from "react";

type Summary = {
  counts: { sourceRows: number; approvalRecords: number; manufacturerLabels: number; distinctApprovalNumbers: number };
  marketScope: string; license: string; licenseUrl: string; sourceUrl: string; catalogUrl: string;
  sourceRevision: string; sourceSnapshotSha256: string; sourceManifestSha256: string; databaseSha256: string;
  attributionText: string; warning: string;
};
type Row = {
  id: string; sourceRowNumber: number; manufacturerLabel: string; manufacturerLabelMappingStatus: string;
  tradeName: string | null; typeDesignation: string | null; approvalObject: string | null; typeApprovalNumber: string | null;
  technicalService: string | null; procedureType: string | null; approvalDate: string | null; emissionsMemberState: string | null;
  sourceRecordSha256: string; sourceRevision: string; sourceSnapshotSha256: string; sourceManifestSha256: string;
  marketScope: string; applicabilityPrecision: string; reviewStatus: string; databaseSha256: string;
  warning: string; catalogUrl: string;
};
export function KbaDeApprovalResearch({ onBack }: { onBack: () => void }) {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [query, setQuery] = useState("Volkswagen");
  const [rows, setRows] = useState<Row[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    fetch("/api/local-research?dataset=kba-de-approval-summary", { cache: "no-store" })
      .then(async (r) => { const p = await r.json(); if (!r.ok) throw new Error(p.error || "KBA DE approval summary unavailable"); return p; })
      .then((p) => { if (active && p?.ok) setSummary(p.summary as Summary); })
      .catch((e: unknown) => { if (active) setError(e instanceof Error ? e.message : "KBA DE approval summary unavailable"); });
    return () => { active = false; };
  }, []);
  async function search(event?: FormEvent) {
    event?.preventDefault();
    setLoading(true); setError("");
    try {
      const params = new URLSearchParams({ dataset: "kba-de-approvals", q: query, limit: "30" });
      const response = await fetch("/api/local-research?" + params.toString(), { cache: "no-store" });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.error || "KBA DE approval search failed");
      setRows(Array.isArray(payload.rows) ? payload.rows as Row[] : []);
    } catch (reason) {
      setRows([]);
      setError(reason instanceof Error ? reason.message : "KBA DE approval search failed");
    } finally { setLoading(false); }
  }
  useEffect(() => { void search(); }, []);
  return <section className="content list-view local-research-view">
    <div className="head">
      <div><h1>KBA · одобрения типа DE</h1><div className="research-subtitle">Официальные метаданные одобрений целого ТС · отдельный offline research pack</div></div>
      <button type="button" className="link-button" onClick={onBack}>Назад к справочникам</button>
    </div>
    <div className="research-boundary">
      <b>Только Германия · только метаданные документа · не применяемость к автомобилю.</b>
      Дата одобрения не является модельным годом или датой производства. Набор не содержит VIN-комплектацию, поколение, точный код двигателя/КПП и их пару, ECU, DTC, схемы или ремонтные процедуры. Не выводить применимость к России или ЕАЭС.
    </div>
    {summary && <div className="research-stats">
      <article className="research-stat"><small>Строки исходного XLSX</small><strong>{summary.counts.sourceRows.toLocaleString("ru-RU")}</strong></article>
      <article className="research-stat"><small>Строки кандидатов</small><strong>{summary.counts.approvalRecords.toLocaleString("ru-RU")}</strong></article>
      <article className="research-stat"><small>Точные manufacturer labels</small><strong>{summary.counts.manufacturerLabels.toLocaleString("ru-RU")}</strong></article>
      <article className="research-stat"><small>Уникальные номера одобрений</small><strong>{summary.counts.distinctApprovalNumbers.toLocaleString("ru-RU")}</strong></article>
    </div>}
    <form className="research-search" onSubmit={search}>
      <input aria-label="Поиск KBA approvals" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Производитель, Handelsname, Typbezeichnung или номер одобрения…" />
      <button type="submit" disabled={loading || query.trim().length < 2}>{loading ? "Поиск…" : "Найти"}</button>
    </form>
    <div className="research-status">{error || (rows.length ? "Найдено записей: " + rows.length : "Введите запрос для поиска.")}</div>
    <div className="research-results">
      {rows.map((row) => <article className="research-result" key={row.id}>
        <div className="research-result-top"><div><small>KBA · DE · WHOLE-VEHICLE TYPE APPROVAL</small><h3>{row.manufacturerLabel} · {row.tradeName || row.typeDesignation || row.typeApprovalNumber || "без торгового имени"}</h3></div><span className="research-candidate">DOCUMENT METADATA ONLY</span></div>
        <div className="research-data-grid">
          <div><small>Номер одобрения</small><b>{row.typeApprovalNumber || "—"}</b></div>
          <div><small>Typbezeichnung</small><b>{row.typeDesignation || "—"}</b></div>
          <div><small>Genehmigungsobjekt</small><b>{row.approvalObject || "—"}</b></div>
          <div><small>Дата одобрения · не модельный год</small><b>{row.approvalDate || "—"}</b></div>
          <div><small>Техническая служба / процедура</small><b>{[row.technicalService, row.procedureType].filter(Boolean).join(" · ") || "—"}</b></div>
          <div><small>Код двигателя / КПП / точная пара</small><b>Не предоставлены</b></div>
        </div>
        <div className="research-warning-line">{row.warning}</div>
        <details className="research-details"><summary>Provenance и точность</summary>
          <p>Source row {row.sourceRowNumber} · manufacturer label {row.manufacturerLabelMappingStatus} · revision {row.sourceRevision}</p>
          <p>Row SHA-256 {row.sourceRecordSha256}</p>
          <p>Source XLSX SHA-256 {row.sourceSnapshotSha256} · source manifest SHA-256 {row.sourceManifestSha256} · SQLite SHA-256 {row.databaseSha256}</p>
          <p>Market {row.marketScope} · {row.applicabilityPrecision} · {row.reviewStatus} · exact vehicle fitment false · exact engine/gearbox pair false · RU/EAEU false</p>
        </details>
        <div className="research-source"><span>KBA · DL-DE BY 2.0 · DE-only · не производственная применимость</span><a href={row.catalogUrl} target="_blank" rel="noopener noreferrer">Открыть каталог KBA</a></div>
      </article>)}
    </div>
    {summary && <div className="research-credits">
      <p><a href={summary.catalogUrl} target="_blank" rel="noopener noreferrer">Kraftfahrt-Bundesamt (KBA), Liste der erteilten Typgenehmigungen (Gesamtfahrzeug)</a> — DL-DE BY 2.0. {summary.attributionText}</p>
      <p>Source revision {summary.sourceRevision} · XLSX SHA-256 {summary.sourceSnapshotSha256} · source manifest SHA-256 {summary.sourceManifestSha256} · SQLite SHA-256 {summary.databaseSha256}</p>
      <p>Исследовательский слой не пополняет подтверждённый VAG-каталог, OEM-применяемость или российскую/ЕАЭС базу.</p>
    </div>}
  </section>;
}

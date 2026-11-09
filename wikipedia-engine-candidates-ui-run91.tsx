"use client";

import { useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";

type CandidateRow = {
  candidateId: number;
  candidateCode: string;
  sourceRevisionId: number;
  sourceTitle: string;
  sourceUrl: string;
  sectionHeading: string | null;
  sourceRowKind: string;
  sourceRowNumber: number;
  sourceRowText: string;
  candidateValueText: string;
  sourceRowSha256: string;
  sourceSnapshotSha256: string;
  sourceManifestSha256: string;
  marketScope: "UNKNOWN";
  applicabilityPrecision: "community_engine_code_candidate_only";
  reviewStatus: "candidate";
  productImportAllowed: false;
  exactVehicleFitment: false;
  generationYearFitment: false;
  engineGearboxFitment: false;
  ecuFitment: false;
  dtcFitment: false;
  repairUseAllowed: false;
  diagnosticExecutionAllowed: false;
};

type CandidateSummary = {
  packId: string;
  license: "CC-BY-SA-4.0";
  licenseUrl: string;
  rightsStatus: string;
  marketScope: "UNKNOWN";
  applicabilityPrecision: "community_engine_code_candidate_only";
  verificationStatus: string;
  qualityReviewStatus: "not_approved_for_technical_use";
  productImportAllowed: false;
  exactVehicleFitment: false;
  generationYearFitment: false;
  engineGearboxFitment: false;
  ecuFitment: false;
  dtcFitment: false;
  repairUseAllowed: false;
  diagnosticExecutionAllowed: false;
  counts: {
    sourceDocuments: number;
    candidateRows: number;
    uniqueCandidateCodes: number;
    sourceRowsWithCodes: number;
  };
  sourceRevisions: Record<string, string>;
  qualityWarnings: string[];
  databaseSha256: string;
  sourceManifestSha256: string;
  sourceSnapshotSha256: string;
  attributionSha256: string;
  licenseNoticeSha256: string;
  sourceArtifactSha256: string;
  attributionText: string;
  licenseNoticeText: string;
};

function formatNumber(value: number | undefined) {
  return typeof value === "number" ? new Intl.NumberFormat("ru-RU").format(value) : "—";
}

export default function WikipediaEngineCandidates() {
  const [summary, setSummary] = useState<CandidateSummary | null>(null);
  const [query, setQuery] = useState("");
  const [rows, setRows] = useState<CandidateRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("Введите не менее двух символов для поиска кода-кандидата.");
  const controller = useRef<AbortController | null>(null);

  useEffect(() => {
    const current = new AbortController();
    fetch("/api/wikipedia-engine-candidates?summary=1", { signal: current.signal, cache: "no-store" })
      .then(async (response) => {
        const payload = await response.json();
        if (!response.ok || !payload?.ok) throw new Error(payload.error || "Набор кандидатов недоступен.");
        setSummary(payload.summary as CandidateSummary);
      })
      .catch((reason: unknown) => {
        if (reason instanceof Error && reason.name !== "AbortError") {
          setError(reason.message || "Не удалось проверить набор кандидатов.");
        }
      });
    return () => {
      current.abort();
      controller.current?.abort();
    };
  }, []);

  async function search(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const value = query.trim();
    if (value.length < 2) {
      setRows([]);
      setNotice("Введите не менее двух символов.");
      return;
    }
    controller.current?.abort();
    const next = new AbortController();
    controller.current = next;
    setLoading(true);
    setError("");
    setNotice("Поиск выполняется только по локальной SQLite.");
    try {
      const response = await fetch(
        "/api/wikipedia-engine-candidates?q=" + encodeURIComponent(value) + "&limit=30",
        { signal: next.signal, cache: "no-store" },
      );
      const payload = await response.json();
      if (!response.ok || !payload?.ok) throw new Error(payload.error || "Поиск не выполнен.");
      setRows(Array.isArray(payload.rows) ? payload.rows as CandidateRow[] : []);
      setNotice("Найдено кандидатов: " + formatNumber(payload.count) + ". Это не подтверждение применимости.");
    } catch (reason: unknown) {
      if (!(reason instanceof Error && reason.name === "AbortError")) {
        setRows([]);
        setError(reason instanceof Error ? reason.message : "Локальный поиск недоступен.");
      }
    } finally {
      if (controller.current === next) setLoading(false);
    }
  }

  return <section className="research-wikipedia-candidates" aria-label="Кандидаты кодов двигателей VAG из Wikipedia">
    <div className="research-boundary">
      <b>Только поисковые кандидаты. Не использовать для подбора деталей или ремонта.</b>
      <p>Из четырёх закреплённых редакций статей Wikipedia извлечено {formatNumber(summary?.counts.candidateRows)} строк с {formatNumber(summary?.counts.uniqueCandidateCodes)} уникальными токенами. Это community-список с предупреждениями о неполных ссылках, оригинальном исследовании и спорной точности. Ни один код не подтверждён заводским источником.</p>
      <p>Рынок UNKNOWN; поколение, модельный год, точная модификация, связь двигателя с КПП и ECU не установлены. Импорт в производственный каталог, ремонтное применение и диагностическое выполнение запрещены.</p>
    </div>

    {summary && <div className="research-credits">
      <b>Wikipedia contributors · CC BY-SA 4.0 · отдельный исследовательский набор</b>
      <p><a href={summary.licenseUrl} target="_blank" rel="noopener noreferrer">Условия CC BY-SA 4.0</a>. Коммерческое использование, offline-кэширование и распространение разрешены опубликованной лицензией при обязательной атрибуции и ShareAlike. Набор не объединяется с OEM-материалами и сохраняет собственную лицензию.</p>
      <p>{summary.attributionText}</p>
      <p>Редакции: {Object.entries(summary.sourceRevisions).map(([title, revision]) => title + " [" + revision + "]").join(" · ")}</p>
      <p>SQLite SHA-256: {summary.databaseSha256}</p>
      <p>Source manifest SHA-256: {summary.sourceManifestSha256} · snapshot SHA-256: {summary.sourceSnapshotSha256}</p>
      <p>Attribution SHA-256: {summary.attributionSha256} · license notice SHA-256: {summary.licenseNoticeSha256} · source artifact SHA-256: {summary.sourceArtifactSha256}</p>
      <details className="research-details">
        <summary>Предупреждения качества источника</summary>
        <ul>{summary.qualityWarnings.map((warning) => <li key={warning}>{warning}</li>)}</ul>
      </details>
      <details className="research-details">
        <summary>Полный текст уведомления о лицензии</summary>
        <pre className="research-attribution">{summary.licenseNoticeText}</pre>
      </details>
    </div>}

    <form className="research-search" onSubmit={search}>
      <input
        aria-label="Поиск кандидата кода двигателя"
        value={query}
        onChange={(event) => setQuery(event.target.value)}
        placeholder="Код двигателя или фрагмент строки, например CHYA…"
      />
      <button type="submit" disabled={loading || !summary}>{loading ? "Поиск…" : "Найти кандидатов"}</button>
    </form>
    <p className="research-status" role="status">{notice}</p>
    {error && <div className="research-empty" role="alert">{error}</div>}
    <div className="research-results">
      {rows.map((row) => <article className="research-result" key={row.candidateId}>
        <div className="research-result-top">
          <div>
            <small>ENGINE CODE CANDIDATE · NOT VERIFIED</small>
            <h3><code className="research-code">{row.candidateCode}</code></h3>
          </div>
          <span className="research-candidate">КАНДИДАТ · НЕ OEM</span>
        </div>
        <p className="research-description">{row.sourceRowText}</p>
        <div className="research-tags">
          <span>Рынок UNKNOWN</span>
          <span>Применимость не установлена</span>
          <span>Ремонт запрещён</span>
          <span>Диагностика запрещена</span>
        </div>
        <p className="research-description">
          Раздел: {row.sectionHeading || "не указан"} · строка источника: {row.sourceRowNumber} · ревизия: {row.sourceRevisionId}
        </p>
        <p className="research-description">
          <a href={row.sourceUrl} target="_blank" rel="noopener noreferrer">{row.sourceTitle} · закреплённая редакция {row.sourceRevisionId}</a>
        </p>
        <details className="research-details">
          <summary>Provenance и ограничения</summary>
          <ul>
            <li>Кандидат извлечён из строки: {row.candidateValueText}</li>
            <li>SHA-256 строки: {row.sourceRowSha256}</li>
            <li>SHA-256 снимка: {row.sourceSnapshotSha256}</li>
            <li>SHA-256 манифеста: {row.sourceManifestSha256}</li>
            <li>Статус: {row.reviewStatus}; применимость: {row.applicabilityPrecision}</li>
            <li>Product import, exact fitment, engine/gearbox fitment, ECU fitment, repair use и diagnostic execution: false</li>
          </ul>
        </details>
      </article>)}
      {!loading && rows.length === 0 && <div className="research-empty">Введите код или фрагмент текста для поиска в этом отдельном наборе.</div>}
    </div>
  </section>;
}

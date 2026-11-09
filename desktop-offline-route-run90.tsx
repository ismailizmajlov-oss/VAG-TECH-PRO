"use client";

import { useState } from "react";
import LocalOfflineWorkspace from "@/components/local-offline-workspace";
import LocalDataAdmin from "@/components/local-data-admin";
import LocalResearchCatalog from "@/components/local-research-catalog";

type Module = "MECHANIC" | "ELECTRICIAN" | "DIAGNOSTIC";
type DesktopView = "workspace" | "garage" | "bookmarks" | "history" | "local-research" | "local-admin";

const modules: Array<{ id: Module; title: string; icon: string; description: string; initialSection: string }> = [
  { id: "MECHANIC", title: "Механика", icon: "⚒", description: "Ремонт и обслуживание", initialSection: "Привод ГРМ" },
  { id: "ELECTRICIAN", title: "Автоэлектрика", icon: "ϟ", description: "Схемы, распиновки и проверки", initialSection: "Электросхемы" },
  { id: "DIAGNOSTIC", title: "Диагностика", icon: "⌁", description: "DTC, тест-планы и адаптации", initialSection: "Считывание DTC" },
];

const sections: Record<Module, string[]> = {
  MECHANIC: [
    "Общие сведения", "Ремонтные данные", "Привод ГРМ", "ГБЦ", "Поршневая группа", "Система смазки",
    "Система охлаждения", "Турбонаддув", "Впуск и выпуск", "Топливная система", "Сцепление",
    "Коробка передач", "Передняя подвеска", "Задняя подвеска", "Передние тормоза", "Задние тормоза",
    "Кузов", "Сервис и обслуживание",
  ],
  ELECTRICIAN: [
    "Электросхемы", "Распределение питания", "Массы и соединения", "CAN / LIN", "Блоки управления",
    "ECU двигателя", "ABS / ESP", "Комфорт и кузов", "Датчики двигателя", "Исполнительные механизмы",
    "Освещение", "Проверка цепи", "Падение напряжения", "Осциллограммы",
  ],
  DIAGNOSTIC: [
    "Считывание DTC", "DTC", "Параметры в реальном времени", "Тесты исполнительных механизмов",
    "Ошибки КПП", "Адаптации", "ABS / ESP", "SRS / Airbag", "Комфорт", "Сброс интервалов",
    "Базовые установки", "Кодирование",
  ],
};

export default function DesktopHome() {
  const [active, setActive] = useState<Module>("MECHANIC");
  const [selected, setSelected] = useState("Привод ГРМ");
  const [view, setView] = useState<DesktopView>("workspace");
  const [message, setMessage] = useState("Автономный режим. Все рабочие данные читаются из локальной SQLite.");

  function switchModule(next: Module) {
    const target = modules.find((item) => item.id === next);
    setActive(next);
    setSelected(target?.initialSection || "Общие сведения");
    setView("workspace");
  }

  const offlineView = view === "local-research" || view === "local-admin" ? "workspace" : view;

  return <div className="app" data-theme="dark">
    <header className="top">
      <div className="brand">◢ VAG TECH <em>PRO</em></div>
      <span className="muted" style={{ marginLeft: "auto", letterSpacing: ".08em", whiteSpace: "nowrap" }}>АВТОНОМНЫЙ РЕЖИМ · ЛОКАЛЬНАЯ SQLITE</span>
      <span className="muted" style={{ whiteSpace: "nowrap" }}>WINDOWS x64</span>
    </header>
    <aside className="sidebar" aria-label="Навигация VAG TECH PRO">
      <button type="button" className={"nav " + (view === "workspace" ? "active" : "")} aria-pressed={view === "workspace"} onClick={() => setView("workspace")}>⌂　Рабочее место</button>
      <button type="button" className={"nav " + (view === "garage" ? "active" : "")} aria-pressed={view === "garage"} onClick={() => setView("garage")}>▣　Гараж и подбор автомобиля</button>
      <button type="button" className={"nav " + (view === "bookmarks" ? "active" : "")} aria-pressed={view === "bookmarks"} onClick={() => setView("bookmarks")}>♧　Закладки</button>
      <button type="button" className={"nav " + (view === "history" ? "active" : "")} aria-pressed={view === "history"} onClick={() => setView("history")}>◷　История запросов</button>
      <div className="label">Технические модули</div>
      {modules.map((item) => <button key={item.id} type="button" data-module aria-pressed={active === item.id && view === "workspace"} className={"nav " + (active === item.id && view === "workspace" ? "active" : "")} onClick={() => switchModule(item.id)}>
        <span>{item.icon}</span><span><b>{item.title}</b><small>{item.description}</small></span>
      </button>)}
      <div className="label">Локальные данные</div>
      <button type="button" className={"nav " + (view === "local-research" ? "active" : "")} aria-pressed={view === "local-research"} onClick={() => setView("local-research")}>▤　Исследовательские наборы</button>
      <button type="button" className={"nav " + (view === "local-admin" ? "active" : "")} aria-pressed={view === "local-admin"} onClick={() => setView("local-admin")}>⚙　База, источники и импорт</button>
      <div className="toast">●　Работа без облака и учётной записи</div>
    </aside>
    <main className="main">
      {view === "local-research" ? <LocalResearchCatalog /> : view === "local-admin" ? <LocalDataAdmin onMessage={setMessage} /> : <LocalOfflineWorkspace
        view={offlineView}
        active={active}
        selected={selected}
        sections={sections[active]}
        onSelect={setSelected}
        onMessage={setMessage}
        onViewResearch={() => setView("local-research")}
      />}
      <p className="toast" role="status" aria-live="polite">{message}</p>
      <footer className="footer-note">VAG TECH PRO · Автономная рабочая база. Критические значения показываются только с источником, ревизией и подтверждённой применимостью. Не заменяет заводскую документацию.</footer>
    </main>
  </div>;
}

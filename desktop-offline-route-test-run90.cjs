"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const root = path.resolve(__dirname, "..");
const read = (file) => fs.readFileSync(path.join(root, file), "utf8");

test("Electron opens the dedicated local SQLite desktop route", () => {
  const main = read("electron/main.cjs");
  assert.match(main, /const desktopUrl = .*\/desktop/);
  assert.match(main, /waitForServer\(desktopUrl/);
  assert.match(main, /loadURL\(desktopUrl\)/);
  assert.match(main, /VAG_TECH_PRO_DESKTOP_OFFLINE/);
  assert.match(main, /NEXT_PUBLIC_SUPABASE_URL/);
  assert.match(main, /SUPABASE_SERVICE_ROLE_KEY/);
});

test("dedicated desktop route has no cloud authentication or Supabase dependency", () => {
  const route = read("app/desktop/page.tsx");
  assert.match(route, /data-theme="dark"/);
  assert.match(route, /LocalOfflineWorkspace/);
  assert.match(route, /LocalDataAdmin/);
  assert.match(route, /LocalResearchCatalog/);
  assert.match(route, /локальн.*SQLite/i);
  assert.doesNotMatch(route, /createClient|supabase|signIn|signOut|https?:\/\//i);
  for (const component of ["components/local-offline-workspace.tsx", "components/local-data-admin.tsx", "components/local-research-catalog.tsx"]) {
    assert.doesNotMatch(read(component), /createClient|supabase\.from|supabase\.auth/i, component + " must remain local-only");
  }
  assert.match(read("components/local-offline-workspace.tsx"), /\/api\/local-core/);
  assert.match(read("components/local-data-admin.tsx"), /\/api\/local-core/);
  assert.match(read("components/local-research-catalog.tsx"), /\/api\/local-research/);
  assert.match(route, /className="muted"/);
  const css = read("app/globals.css");
  assert.match(css, /\.muted/);
});

test("offline desktop navigation exposes all repair modules and local data workflows", () => {
  const route = read("app/desktop/page.tsx");
  for (const label of ["Механика", "Автоэлектрика", "Диагностика", "Гараж и подбор автомобиля", "Закладки", "История запросов", "Исследовательские наборы", "База, источники и импорт"]) {
    assert.ok(route.includes(label), "missing desktop navigation item: " + label);
  }
  for (const type of ["Привод ГРМ", "Коробка передач", "Электросхемы", "ECU двигателя", "Считывание DTC", "Адаптации", "Сервис и обслуживание"]) {
    assert.ok(route.includes(type), "missing technical section: " + type);
  }
});

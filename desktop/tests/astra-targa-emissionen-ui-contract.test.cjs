"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const source = fs.readFileSync(path.join(__dirname, "../components/local-research-catalog.tsx"), "utf8");

test("ASTRA TARGA is a separate CH-only research tab", () => {
  assert.match(source, /"astra-targa"/);
  assert.match(source, /TARGA · варианты КПП · CH/);
  assert.match(source, /sourceDefinedVariantLink/);
  assert.match(source, /exactVagFactoryCodePair/);
  assert.match(source, /ruEaeuApplicability/);
  assert.match(source, /Swiss Open Government Data/);
  assert.match(source, /не является подтверждённым заводским кодом VAG/);
  assert.match(source, /не является кодом КПП VAG/);
});

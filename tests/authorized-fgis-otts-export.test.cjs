'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const crypto = require('node:crypto');
const { spawnSync } = require('node:child_process');
const { DatabaseSync } = require('node:sqlite');
const { normalizeRecord, validateSourceIdentity, loadSourceContext } = require('../scripts/import-authorized-fgis-otts-export.cjs');

const script = path.resolve(__dirname, '../scripts/import-authorized-fgis-otts-export.cjs');
const sha = (bytes) => crypto.createHash('sha256').update(bytes).digest('hex');

function fixture(dir, overrides = {}) {
  const licenseBytes = Buffer.from('TEST FIXTURE ONLY — synthetic licence text; not a real source licence.\n', 'utf8');
  const permissionBytes = Buffer.from('TEST FIXTURE ONLY — synthetic permission evidence; not a real authorization.\n', 'utf8');
  const licensePath = path.join(dir, 'LICENSE-TEST.txt');
  const permissionPath = path.join(dir, 'PERMISSION-TEST.txt');
  const manifestPath = path.join(dir, 'source-manifest.json');
  const inputPath = path.join(dir, 'export.json');
  const outputPath = path.join(dir, 'authorized-otts.sqlite');
  fs.writeFileSync(licensePath, licenseBytes);
  fs.writeFileSync(permissionPath, permissionBytes);

  const manifest = {
    schema_version: 1,
    source_id: 'rosstandart-fgis-registers-kts',
    publisher: 'TEST ONLY — synthetic Rosstandart source fixture',
    source_url: 'https://www.interstandart.ru/page/fgis_01',
    source_revision: '2038_as_amended_by_2335',
    retrieved_at: '2026-11-03T12:00:00.000Z',
    market_scope: ['RU', 'EAEU_TR_TS_018_2011'],
    rights: {
      basis: 'open_license',
      review_status: 'approved_by_owner',
      reviewed_by: 'TEST ONLY',
      reviewed_at: '2026-11-03',
      approval_reference: 'TEST ONLY — no real rights approval',
      license_identifier: 'CC0-1.0-TEST-FIXTURE',
      license_url: 'https://example.invalid/test-license',
      license_text_sha256: sha(licenseBytes),
      commercial_use_allowed: true,
      display_allowed: true,
      offline_cache_allowed: true,
      bulk_export_allowed: true,
      pdf_redistribution_allowed: false,
      pdf_binary_included: false
    },
    ...overrides.manifest
  };
  const record = {
    source_record_key: 'TEST-OTTS-001',
    approval_registration_number: 'E-RU.TEST.00001',
    make: 'Volkswagen',
    commercial_name: 'Synthetic Test Vehicle',
    vehicle_type: 'TEST-VARIANT',
    valid_from: '2020-01-01',
    valid_to: '2025-12-31',
    base_vehicle_or_chassis: 'TEST-BASE',
    modifications: 'Synthetic fixture only',
    vehicle_category: 'M1',
    environmental_class: 'TEST',
    annex_1_pdf: 'https://example.invalid/approval.pdf',
    electronically_issued_flag: true,
    publication_date: '2020-01-02',
    source_url: 'https://www.rst.gov.ru/TEST_FIXTURE/record/1',
    source_field_namespace: 'annex_2_publication_fields',
    source_field_numbers: {
      approval_registration_number: 4,
      valid_from: 5,
      valid_to: 6,
      make: 12,
      commercial_name: 13,
      vehicle_type: 14,
      base_vehicle_or_chassis: 15,
      modifications: 16,
      vehicle_category: 17,
      environmental_class: 18,
      annex_1_pdf: 19,
      electronically_issued_flag: 20,
      publication_date: 26
    },
    ...overrides.record
  };
  const input = { schema_version: 1, package_type: 'rosstandart_fgis_annex2_export', records: [record] };
  fs.writeFileSync(manifestPath, JSON.stringify(manifest, null, 2));
  fs.writeFileSync(inputPath, JSON.stringify(input, null, 2));
  return { licensePath, permissionPath, manifestPath, inputPath, outputPath, licenseBytes, permissionBytes, manifest, input };
}
test('binds the package to the same canonical FGIS identity in both authoritative manifests', () => {
  const context = loadSourceContext();
  const manifest = { source_revision: '2038_as_amended_by_2335' };
  const sourceUrl = 'https://www.interstandart.ru/page/fgis_01';
  assert.equal(context.sourceRecord.source_id, 'rosstandart-fgis-registers-kts');
  assert.equal(context.russianSource.source_id, 'rosstandart-fgis-registers-kts');
  assert.doesNotThrow(() => validateSourceIdentity(manifest, sourceUrl, context));
  const mismatched = { ...context, russianSource: { ...context.russianSource, source_id: 'rosstandart-fgis-reestr-kts' } };
  assert.throws(() => validateSourceIdentity(manifest, sourceUrl, mismatched), /FGIS source identity differs across authoritative manifests/);
});

test('rejects source URL and host-policy drift between authoritative manifests', () => {
  const context = loadSourceContext();
  const manifest = { source_revision: '2038_as_amended_by_2335' };
  const sourceUrl = 'https://www.interstandart.ru/page/fgis_01';
  const urlMismatch = { ...context, russianSource: { ...context.russianSource, source_url: 'https://www.rst.gov.ru/other-register' } };
  assert.throws(() => validateSourceIdentity(manifest, sourceUrl, urlMismatch), /package source_url does not match both authoritative FGIS source manifests/);
  const policyMismatch = { ...context, sourceRecord: { ...context.sourceRecord, source_url_host_policy: { ...context.sourceRecord.source_url_host_policy, allowed_domains: ['example.invalid'] } } };
  assert.throws(() => validateSourceIdentity(manifest, sourceUrl, policyMismatch), /official FGIS source URL host policy differs/);
});

test('rejects unverified, lookalike, credential-bearing and non-standard-port source URLs', () => {
  const cases = [
    { label: 'manifest host', overrides: { manifest: { source_url: 'https://example.invalid/fgis' } }, expected: /source_url must use a verified Rosstandart\/Interstandart official host/ },
    { label: 'record lookalike host', overrides: { record: { source_url: 'https://rst.gov.ru.evil.example/record/1' } }, expected: /source_url must use a verified Rosstandart\/Interstandart official host/ },
    { label: 'URL credentials', overrides: { manifest: { source_url: 'https://user@www.rst.gov.ru/fgis' } }, expected: /source_url must not contain URL credentials/ },
    { label: 'non-standard port', overrides: { record: { source_url: 'https://www.rst.gov.ru:8443/record/1' } }, expected: /source_url must not use a non-default port/ }
  ];
  for (const item of cases) {
    const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'vag-fgis-source-host-'));
    try {
      const f = fixture(dir, item.overrides);
      const result = run(f);
      assert.notEqual(result.status, 0, item.label);
      assert.match(result.stderr, item.expected, item.label);
      assert.equal(fs.existsSync(f.outputPath), false, item.label);
    } finally { fs.rmSync(dir, { recursive: true, force: true }); }
  }
});

function run(f, mode = 'license') {
  const evidenceArgs = mode === 'permission' ? ['--permission-document', f.permissionPath] : ['--license-text', f.licensePath];
  return spawnSync(process.execPath, [script, '--input', f.inputPath, '--manifest', f.manifestPath,
    ...evidenceArgs, '--output', f.outputPath], { encoding: 'utf8' });
}

test('preserves supported VAG make labels while sanitizing control characters', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'vag-fgis-make-sanitization-'));
  try {
    const f = fixture(dir);
    for (const make of ['Volkswagen', 'Audi', 'Škoda', 'SEAT', 'CUPRA']) {
      const record = { ...f.input.records[0], make: `${make}\u0000` };
      const normalized = normalizeRecord(record, 0, f.manifest).normalized;
      assert.equal(normalized.make, make);
    }
  } finally { fs.rmSync(dir, { recursive: true, force: true }); }
});

test('imports a rights-cleared Annex 2 export into a review-only SQLite staging database', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'vag-fgis-authorized-'));
  try {
    const f = fixture(dir);
    const result = run(f);
    assert.equal(result.status, 0, result.stderr || result.stdout);
    const db = new DatabaseSync(f.outputPath, { readOnly: true });
    try {
      assert.equal(db.prepare('PRAGMA integrity_check').get().integrity_check, 'ok');
      assert.deepEqual(db.prepare('PRAGMA foreign_key_check').all(), []);
      assert.equal(db.prepare('SELECT COUNT(*) AS n FROM type_approval_records').get().n, 1);
      assert.equal(db.prepare('SELECT COUNT(*) AS n FROM raw_source_records').get().n, 1);
      assert.equal(db.prepare('SELECT COUNT(*) AS n FROM record_field_provenance').get().n, 13);
      const row = db.prepare('SELECT * FROM type_approval_records').get();
      assert.equal(row.make, 'Volkswagen');
      assert.equal(row.source_field_namespace, 'annex_2_publication_fields');
      assert.equal(row.applicability_precision, 'type_approval_document_metadata_only');
      assert.equal(row.review_status, 'needs_review');
      assert.equal(row.publication_status, 'blocked_pending_technical_review');
      assert.equal(row.exact_engine_fitment_claim, 0);
      assert.equal(row.exact_transmission_fitment_claim, 0);
      assert.equal(row.exact_ecu_fitment_claim, 0);
      const pdfField = db.prepare("SELECT field_number, field_value FROM record_field_provenance WHERE field_name='annex_1_pdf'").get();
      assert.equal(pdfField.field_number, 19);
      assert.equal(pdfField.field_value, 'https://example.invalid/approval.pdf');
      const snapshot = db.prepare('SELECT * FROM source_snapshot').get();
      assert.equal(snapshot.source_snapshot_sha256, sha(fs.readFileSync(f.inputPath)));
      assert.equal(snapshot.source_manifest_sha256, sha(fs.readFileSync(f.manifestPath)));
      const recordHashes = db.prepare('SELECT t.canonical_source_record_sha256, r.canonical_sha256 FROM type_approval_records t JOIN raw_source_records r USING (source_record_key)').get();
      assert.equal(recordHashes.canonical_source_record_sha256, recordHashes.canonical_sha256);
      assert.equal(snapshot.rights_status, 'verified_for_metadata_offline_distribution');
      assert.equal(snapshot.import_status, 'staging_only_not_published');
      assert.equal(snapshot.commercial_use_allowed, 1);
      assert.equal(snapshot.offline_cache_allowed, 1);
      assert.equal(snapshot.pdf_redistribution_allowed, 0);
    } finally { db.close(); }
    const sidecar = JSON.parse(fs.readFileSync(`${f.outputPath}.manifest.json`, 'utf8'));
    assert.equal(sidecar.record_count, 1);
    assert.equal(sidecar.integrity_check, 'ok');
    assert.equal(sidecar.rights_basis, 'open_license');
    assert.equal(sidecar.license_identifier, 'CC0-1.0-TEST-FIXTURE');
    assert.deepEqual(sidecar.market_scope, ['RU', 'EAEU_TR_TS_018_2011']);
    assert.equal(sidecar.commercial_use_allowed, true);
    assert.equal(sidecar.offline_cache_allowed, true);
    assert.equal(sidecar.pdf_redistribution_allowed, false);
    assert.match(sidecar.database_sha256, /^[a-f0-9]{64}$/);
    assert.equal(sidecar.database_sha256, sha(fs.readFileSync(f.outputPath)));
  } finally { fs.rmSync(dir, { recursive: true, force: true }); }
});

test('blocks import if any required reuse right is not explicitly true', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'vag-fgis-rights-'));
  try {
    const f = fixture(dir, { manifest: { rights: { ...fixtureRights(dir), offline_cache_allowed: false } } });
    const result = run(f);
    assert.notEqual(result.status, 0);
    assert.match(result.stderr, /rights\.offline_cache_allowed must be true/);
    assert.equal(fs.existsSync(f.outputPath), false);
  } finally { fs.rmSync(dir, { recursive: true, force: true }); }
});

function fixtureRights(dir) {
  const bytes = Buffer.from('TEST FIXTURE ONLY — synthetic licence text; not a real source licence.\n', 'utf8');
  return {
    basis: 'open_license', review_status: 'approved_by_owner', reviewed_by: 'TEST ONLY',
    reviewed_at: '2026-11-03', approval_reference: 'TEST ONLY — no real rights approval',
    license_identifier: 'CC0-1.0-TEST-FIXTURE', license_url: 'https://example.invalid/test-license',
    license_text_sha256: sha(bytes), commercial_use_allowed: true, display_allowed: true,
    offline_cache_allowed: true, bulk_export_allowed: true, pdf_redistribution_allowed: false,
    pdf_binary_included: false
  };
}

test('blocks a license-text hash mismatch', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'vag-fgis-license-hash-'));
  try {
    const f = fixture(dir, { manifest: { rights: { ...fixtureRights(dir), license_text_sha256: '0'.repeat(64) } } });
    const result = run(f);
    assert.notEqual(result.status, 0);
    assert.match(result.stderr, /license text SHA-256 does not match/);
    assert.equal(fs.existsSync(f.outputPath), false);
  } finally { fs.rmSync(dir, { recursive: true, force: true }); }
});

test('rejects Annex 1 field numbers in an Annex 2 record', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'vag-fgis-field-namespace-'));
  try {
    const f = fixture(dir, { record: { source_field_numbers: { approval_registration_number: 4, make: 14, commercial_name: 15, vehicle_type: 16 } } });
    const result = run(f);
    assert.notEqual(result.status, 0);
    assert.match(result.stderr, /does not match Annex 2/);
    assert.equal(fs.existsSync(f.outputPath), false);
  } finally { fs.rmSync(dir, { recursive: true, force: true }); }
});

test('rejects engine, gearbox, ECU, VIN and PR-code claims from the public Annex 2 export', () => {
  const forbiddenTechnicalFields = [
    'engine_code', 'engine_type', 'gearbox_code', 'gearbox_type',
    'transmission_code', 'ecu_id', 'dtc_code', 'wiring_diagram', 'torque_value'
  ];
  for (const field of forbiddenTechnicalFields) {
    const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'vag-fgis-no-fitment-'));
    try {
      const f = fixture(dir, { record: { [field]: 'TEST' } });
      const result = run(f);
      assert.notEqual(result.status, 0, field);
      assert.match(result.stderr, new RegExp(field + ' is not part of Annex 2|is not an allowed Annex 2 field'));
      assert.equal(fs.existsSync(f.outputPath), false);
    } finally { fs.rmSync(dir, { recursive: true, force: true }); }
  }
});

test('requires a matching permission document for written-permission imports', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'vag-fgis-permission-'));
  try {
    const f = fixture(dir, { manifest: { rights: {
      basis: 'written_permission', review_status: 'approved_by_owner', reviewed_by: 'TEST ONLY',
      reviewed_at: '2026-11-03', approval_reference: 'TEST ONLY — no real rights approval',
      permission_document_url: 'https://example.invalid/permission.pdf',
      permission_document_sha256: sha(Buffer.from('TEST FIXTURE ONLY — synthetic permission evidence; not a real authorization.\n', 'utf8')),
      commercial_use_allowed: true, display_allowed: true, offline_cache_allowed: true,
      bulk_export_allowed: true, pdf_redistribution_allowed: false, pdf_binary_included: false
    } } });
    const result = run(f);
    assert.notEqual(result.status, 0);
    assert.match(result.stderr, /--permission-document is required/);
    assert.equal(fs.existsSync(f.outputPath), false);
  } finally { fs.rmSync(dir, { recursive: true, force: true }); }
});

test('refuses to overwrite an existing database', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'vag-fgis-no-overwrite-'));
  try {
    const f = fixture(dir);
    fs.writeFileSync(f.outputPath, 'do not overwrite');
    const result = run(f);
    assert.notEqual(result.status, 0);
    assert.match(result.stderr, /refusing to overwrite/);
    assert.equal(fs.readFileSync(f.outputPath, 'utf8'), 'do not overwrite');
  } finally { fs.rmSync(dir, { recursive: true, force: true }); }
});


test('accepts a written-permission package only when the exact permission document is supplied and hashed', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'vag-fgis-written-permission-'));
  try {
    const permissionBytes = Buffer.from('TEST FIXTURE ONLY — synthetic permission evidence; not a real authorization.\n', 'utf8');
    const f = fixture(dir, { manifest: { rights: {
      basis: 'written_permission', review_status: 'approved_by_owner', reviewed_by: 'TEST ONLY',
      reviewed_at: '2026-11-03', approval_reference: 'TEST ONLY — no real rights approval',
      permission_document_url: 'https://example.invalid/permission.pdf',
      permission_document_sha256: sha(permissionBytes),
      commercial_use_allowed: true, display_allowed: true, offline_cache_allowed: true,
      bulk_export_allowed: true, pdf_redistribution_allowed: false, pdf_binary_included: false
    } } });
    const result = run(f, 'permission');
    assert.equal(result.status, 0, result.stderr || result.stdout);
    const db = new DatabaseSync(f.outputPath, { readOnly: true });
    try {
      const snapshot = db.prepare('SELECT rights_basis, permission_document_sha256, license_text_sha256 FROM source_snapshot').get();
      assert.equal(snapshot.rights_basis, 'written_permission');
      assert.equal(snapshot.permission_document_sha256, sha(permissionBytes));
      assert.equal(snapshot.license_text_sha256, null);
    } finally { db.close(); }
  } finally { fs.rmSync(dir, { recursive: true, force: true }); }
});

test('rejects records outside the electronically issued Annex 2 public-search scope', () => {
  for (const flag of [false, null]) {
    const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'vag-fgis-electronic-scope-'));
    try {
      const f = fixture(dir, { record: { electronically_issued_flag: flag } });
      const result = run(f);
      assert.notEqual(result.status, 0);
      assert.match(result.stderr, /electronically_issued_flag must be true for the Annex 2 public-search scope/);
      assert.equal(fs.existsSync(f.outputPath), false);
    } finally { fs.rmSync(dir, { recursive: true, force: true }); }
  }
});

test('rejects any public field value that is not explicitly mapped to its Annex 2 field number', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'vag-fgis-unmapped-field-'));
  try {
    const f = fixture(dir, { record: { source_field_numbers: {
      approval_registration_number: 4, valid_from: 5, valid_to: 6, make: 12,
      commercial_name: 13, vehicle_type: 14, base_vehicle_or_chassis: 15,
      modifications: 16, vehicle_category: 17, annex_1_pdf: 19,
      electronically_issued_flag: 20, publication_date: 26
    } } });
    const result = run(f);
    assert.notEqual(result.status, 0);
    assert.match(result.stderr, /environmental_class is present without its exact Annex 2 field number/);
    assert.equal(fs.existsSync(f.outputPath), false);
  } finally { fs.rmSync(dir, { recursive: true, force: true }); }
});

test('rejects a source revision whose Annex 2 field map has not been validated', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'vag-fgis-revision-'));
  try {
    const f = fixture(dir, { manifest: { source_revision: '2038_as_amended_by_future_revision' } });
    const result = run(f);
    assert.notEqual(result.status, 0);
    assert.match(result.stderr, /source_revision does not match the validated Annex 2 field map/);
    assert.equal(fs.existsSync(f.outputPath), false);
  } finally { fs.rmSync(dir, { recursive: true, force: true }); }
});

test('canonical row SHA-256 is stable when JSON object key order changes', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'vag-fgis-canonical-hash-'));
  try {
    const f = fixture(dir);
    const record = f.input.records[0];
    const reversed = Object.fromEntries(Object.entries(record).reverse());
    const first = normalizeRecord(record, 0, f.manifest).canonicalSourceRecordSha256;
    const second = normalizeRecord(reversed, 0, f.manifest).canonicalSourceRecordSha256;
    assert.equal(first, second);
    assert.match(first, /^[a-f0-9]{64}$/);
  } finally { fs.rmSync(dir, { recursive: true, force: true }); }
});


test('rejects an invalid permission-document hash', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'vag-fgis-permission-hash-'));
  try {
    const f = fixture(dir, { manifest: { rights: {
      basis: 'written_permission', review_status: 'approved_by_owner', reviewed_by: 'TEST ONLY',
      reviewed_at: '2026-11-03', approval_reference: 'TEST ONLY — no real rights approval',
      permission_document_url: 'https://example.invalid/permission.pdf',
      permission_document_sha256: '0'.repeat(64),
      commercial_use_allowed: true, display_allowed: true, offline_cache_allowed: true,
      bulk_export_allowed: true, pdf_redistribution_allowed: false, pdf_binary_included: false
    } } });
    const result = run(f, 'permission');
    assert.notEqual(result.status, 0);
    assert.match(result.stderr, /permission document SHA-256 does not match/);
    assert.equal(fs.existsSync(f.outputPath), false);
  } finally { fs.rmSync(dir, { recursive: true, force: true }); }
});

test('refuses a package that claims to include PDF bytes in the metadata-only importer', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'vag-fgis-pdf-binary-'));
  try {
    const f = fixture(dir, { manifest: { rights: { ...fixtureRights(dir), pdf_binary_included: true } } });
    const result = run(f);
    assert.notEqual(result.status, 0);
    assert.match(result.stderr, /rights.pdf_binary_included must be false/);
    assert.equal(fs.existsSync(f.outputPath), false);
  } finally { fs.rmSync(dir, { recursive: true, force: true }); }
});
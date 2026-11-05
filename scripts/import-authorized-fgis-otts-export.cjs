#!/usr/bin/env node
'use strict';

const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const { DatabaseSync } = require('node:sqlite');

const SOURCE_ID = 'rosstandart-fgis-kts';
const EXPECTED_NAMESPACE = 'annex_2_publication_fields';
const EXPECTED_PRECISION = 'type_approval_document_metadata_only';
const SUPPORTED_DOCUMENT_TYPES = new Set(['OTTS', 'EOTTS']);
const MAX_EXPORT_BYTES = 25 * 1024 * 1024;
const MAX_MANIFEST_BYTES = 512 * 1024;
const MAX_EVIDENCE_BYTES = 10 * 1024 * 1024;
const MAX_RECORDS = 5000;
const MAX_TEXT = 2000;
const VAG_MAKES = new Set(['Volkswagen', 'Audi', 'Škoda', 'SEAT', 'CUPRA']);
const FORBIDDEN_FITMENT_KEYS = new Set([
  'engine_code', 'factory_engine_code', 'transmission_code', 'factory_gearbox_code',
  'ecu_hardware_number', 'ecu_software_number', 'ecu_id', 'pr_codes', 'vin', 'vin_pattern',
  'configuration_id', 'vehicle_configuration', 'vehicle_configuration_id'
]);
const FIELD_NUMBERS = new Map([
  ['approval_form_accounting_number', 1], ['application_form_accounting_numbers', 2],
  ['supplementary_sheet_accounting_numbers', 3], ['approval_registration_number', 4],
  ['valid_from', 5], ['valid_to', 6], ['certification_body_name', 7],
  ['certification_body_address', 8], ['certification_body_phone', 9],
  ['certification_body_email', 10], ['certification_body_accreditation_certificate_number', 11],
  ['make', 12], ['commercial_name', 13], ['vehicle_type', 14],
  ['base_vehicle_or_chassis', 15], ['modifications', 16], ['vehicle_category', 17],
  ['environmental_class', 18], ['annex_1_pdf', 19], ['electronically_issued_flag', 20],
  ['suspension_date', 21], ['suspension_reason', 22], ['resumption_date', 23],
  ['resumption_reason', 24], ['early_termination_date', 25], ['publication_date', 26],
  ['early_termination_date_based_on_cancellation_notice', 27],
  ['early_termination_reason_based_on_cancellation_notice', 28]
]);
const ALLOWED_RECORD_KEYS = new Set([
  'source_record_key', 'document_type', 'source_field_namespace', 'source_field_numbers', 'source_url',
  ...FIELD_NUMBERS.keys()
]);
const DATE_FIELDS = new Set([
  'valid_from', 'valid_to', 'suspension_date', 'resumption_date',
  'early_termination_date', 'publication_date', 'early_termination_date_based_on_cancellation_notice'
]);
const TEXT_FIELDS = [
  'document_type', 'approval_form_accounting_number', 'application_form_accounting_numbers',
  'supplementary_sheet_accounting_numbers', 'approval_registration_number',
  'certification_body_name', 'certification_body_address', 'certification_body_phone',
  'certification_body_email', 'certification_body_accreditation_certificate_number',
  'make', 'commercial_name', 'vehicle_type', 'base_vehicle_or_chassis', 'modifications',
  'vehicle_category', 'environmental_class', 'annex_1_pdf_url', 'suspension_reason',
  'resumption_reason', 'early_termination_reason_based_on_cancellation_notice'
];

function fail(message) { throw new Error(message); }
function sha256(value) { return crypto.createHash('sha256').update(value).digest('hex'); }
function canonicalJson(value) {
  if (Array.isArray(value)) return `[${value.map(canonicalJson).join(',')}]`;
  if (value && typeof value === 'object') return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${canonicalJson(value[key])}`).join(',')}}`;
  return JSON.stringify(value);
}
function cleanText(value, label, max = MAX_TEXT, required = false) {
  if (value === null || value === undefined || value === '') {
    if (required) fail(`${label} is required`);
    return null;
  }
  if (typeof value !== 'string') fail(`${label} must be a string`);
  const text = value.replace(/[\u0000-\u001f\u007f]/g, ' ').replace(/\s+/g, ' ').trim();
  if (required && !text) fail(`${label} is required`);
  if (text.length > max) fail(`${label} exceeds ${max} characters`);
  return text || null;
}
function validUrl(value, label, required = false) {
  if (!value && !required) return null;
  let parsed;
  try { parsed = new URL(value); } catch { fail(`${label} must be an absolute HTTPS URL`); }
  if (parsed.protocol !== 'https:') fail(`${label} must use HTTPS`);
  return parsed.toString();
}
function validDate(value, label) {
  if (value === null || value === undefined || value === '') return null;
  if (!/^\d{4}-\d{2}-\d{2}$/.test(String(value))) fail(`${label} must use YYYY-MM-DD`);
  const parsed = new Date(`${value}T00:00:00.000Z`);
  if (!Number.isFinite(parsed.getTime()) || parsed.toISOString().slice(0, 10) !== value) fail(`${label} is not a valid calendar date`);
  return value;
}
function readJson(file, maxBytes, label) {
  const stat = fs.statSync(file);
  if (!stat.isFile()) fail(`${label} must be a regular file`);
  if (stat.size > maxBytes) fail(`${label} exceeds ${maxBytes} bytes`);
  const bytes = fs.readFileSync(file);
  try { return { value: JSON.parse(bytes.toString('utf8')), bytes }; }
  catch { fail(`${label} is not valid JSON`); }
}
function validateRights(manifest, licenseBytes, permissionBytes) {
  const rights = manifest.rights;
  if (!rights || typeof rights !== 'object' || Array.isArray(rights)) fail('rights object is required');
  if (rights.review_status !== 'approved_by_owner') fail('rights.review_status must be approved_by_owner');
  cleanText(rights.reviewed_by, 'rights.reviewed_by', 160, true);
  cleanText(rights.reviewed_at, 'rights.reviewed_at', 10, true);
  validDate(rights.reviewed_at, 'rights.reviewed_at');
  cleanText(rights.approval_reference, 'rights.approval_reference', 240, true);
  for (const key of ['commercial_use_allowed', 'display_allowed', 'offline_cache_allowed', 'bulk_export_allowed']) {
    if (rights[key] !== true) fail(`rights.${key} must be true before an offline SQLite import`);
  }
  if (rights.pdf_binary_included !== false) fail('rights.pdf_binary_included must be false; PDF binaries use a separately licensed document pipeline');
  if (typeof rights.pdf_redistribution_allowed !== 'boolean') fail('rights.pdf_redistribution_allowed must be an explicit boolean');
  if (rights.basis === 'open_license') {
    cleanText(rights.license_identifier, 'rights.license_identifier', 120, true);
    validUrl(rights.license_url, 'rights.license_url', true);
    if (!licenseBytes) fail('--license-text is required for an open-license source');
    const actual = sha256(licenseBytes);
    if (!/^[a-f0-9]{64}$/.test(rights.license_text_sha256 || '') || actual !== rights.license_text_sha256) {
      fail('license text SHA-256 does not match rights.license_text_sha256');
    }
    return { basis: 'open_license', licenseTextSha256: actual, permissionDocumentSha256: null };
  }
  if (rights.basis === 'written_permission') {
    validUrl(rights.permission_document_url, 'rights.permission_document_url', true);
    if (!permissionBytes) fail('--permission-document is required for written permission');
    const actual = sha256(permissionBytes);
    if (!/^[a-f0-9]{64}$/.test(rights.permission_document_sha256 || '') || actual !== rights.permission_document_sha256) {
      fail('permission document SHA-256 does not match rights.permission_document_sha256');
    }
    return { basis: 'written_permission', licenseTextSha256: null, permissionDocumentSha256: actual };
  }
  fail('rights.basis must be open_license or written_permission');
}
function normalizeRecord(record, index, manifest) {
  const prefix = `records[${index}]`;
  if (!record || typeof record !== 'object' || Array.isArray(record)) fail(`${prefix} must be an object`);
  const documentType = cleanText(record.document_type, `${prefix}.document_type`, 20, true);
  if (!SUPPORTED_DOCUMENT_TYPES.has(documentType)) fail(`${prefix}.document_type must be OTTS or EOTTS; OTSH and SBKTS records are not accepted by this importer`);
  for (const key of Object.keys(record)) {
    if (FORBIDDEN_FITMENT_KEYS.has(key)) fail(`${prefix}.${key} is not part of Annex 2 and cannot be imported as exact fitment`);
    if (!ALLOWED_RECORD_KEYS.has(key)) fail(`${prefix}.${key} is not an allowed Annex 2 field or provenance key`);
  }
  if (record.source_field_namespace !== EXPECTED_NAMESPACE) fail(`${prefix}.source_field_namespace must be ${EXPECTED_NAMESPACE}`);
  const key = cleanText(record.source_record_key, `${prefix}.source_record_key`, 240, true);
  const approvalNumber = cleanText(record.approval_registration_number, `${prefix}.approval_registration_number`, 180, true);
  const make = cleanText(record.make, `${prefix}.make`, 80, true);
  if (!VAG_MAKES.has(make)) fail(`${prefix}.make is not one of the supported VAG brands`);
  const sourceUrl = validUrl(record.source_url, `${prefix}.source_url`, true);
  const fieldNumbers = record.source_field_numbers;
  if (!fieldNumbers || typeof fieldNumbers !== 'object' || Array.isArray(fieldNumbers)) fail(`${prefix}.source_field_numbers is required`);
  for (const [field, number] of Object.entries(fieldNumbers)) {
    if (!FIELD_NUMBERS.has(field) || FIELD_NUMBERS.get(field) !== number) fail(`${prefix}.source_field_numbers.${field} does not match Annex 2`);
    if (!Object.prototype.hasOwnProperty.call(record, field)) fail(`${prefix}.${field} is mapped to Annex 2 but its raw field value is missing`);
  }
  for (const field of FIELD_NUMBERS.keys()) {
    if (Object.prototype.hasOwnProperty.call(record, field) && fieldNumbers[field] !== FIELD_NUMBERS.get(field)) {
      fail(`${prefix}.${field} is present without its exact Annex 2 field number`);
    }
  }
  if (fieldNumbers.approval_registration_number !== 4 || fieldNumbers.make !== 12 || fieldNumbers.commercial_name !== 13 || fieldNumbers.vehicle_type !== 14) {
    fail(`${prefix}.source_field_numbers must identify approval number, make, commercial name and vehicle type using Annex 2 fields 4/12/13/14`);
  }
  const normalized = {
    approval_form_accounting_number: cleanText(record.approval_form_accounting_number, `${prefix}.approval_form_accounting_number`, 180),
    application_form_accounting_numbers: Array.isArray(record.application_form_accounting_numbers) ? record.application_form_accounting_numbers.map((v, i) => cleanText(v, `${prefix}.application_form_accounting_numbers[${i}]`, 180, true)).join('; ') : cleanText(record.application_form_accounting_numbers, `${prefix}.application_form_accounting_numbers`, 1000),
    supplementary_sheet_accounting_numbers: Array.isArray(record.supplementary_sheet_accounting_numbers) ? record.supplementary_sheet_accounting_numbers.map((v, i) => cleanText(v, `${prefix}.supplementary_sheet_accounting_numbers[${i}]`, 180, true)).join('; ') : cleanText(record.supplementary_sheet_accounting_numbers, `${prefix}.supplementary_sheet_accounting_numbers`, 1000),
    source_record_key: key,
    document_type: documentType,
    approval_registration_number: approvalNumber,
    make,
    commercial_name: cleanText(record.commercial_name, `${prefix}.commercial_name`, 180, true),
    vehicle_type: cleanText(record.vehicle_type, `${prefix}.vehicle_type`, 180, true),
    valid_from: validDate(record.valid_from, `${prefix}.valid_from`),
    valid_to: validDate(record.valid_to, `${prefix}.valid_to`),
    base_vehicle_or_chassis: cleanText(record.base_vehicle_or_chassis, `${prefix}.base_vehicle_or_chassis`, 500),
    modifications: cleanText(record.modifications, `${prefix}.modifications`, 1000),
    vehicle_category: cleanText(record.vehicle_category, `${prefix}.vehicle_category`, 40),
    environmental_class: cleanText(record.environmental_class, `${prefix}.environmental_class`, 80),
    certification_body_name: cleanText(record.certification_body_name, `${prefix}.certification_body_name`, 240),
    certification_body_address: cleanText(record.certification_body_address, `${prefix}.certification_body_address`, 500),
    certification_body_phone: cleanText(record.certification_body_phone, `${prefix}.certification_body_phone`, 120),
    certification_body_email: cleanText(record.certification_body_email, `${prefix}.certification_body_email`, 180),
    certification_body_accreditation_certificate_number: cleanText(record.certification_body_accreditation_certificate_number, `${prefix}.certification_body_accreditation_certificate_number`, 180),
    annex_1_pdf_url: validUrl(record.annex_1_pdf, `${prefix}.annex_1_pdf`),
    electronically_issued_flag: record.electronically_issued_flag == null ? null : (typeof record.electronically_issued_flag === 'boolean' ? record.electronically_issued_flag : fail(`${prefix}.electronically_issued_flag must be boolean`)),
    suspension_date: validDate(record.suspension_date, `${prefix}.suspension_date`),
    suspension_reason: cleanText(record.suspension_reason, `${prefix}.suspension_reason`, 500),
    resumption_date: validDate(record.resumption_date, `${prefix}.resumption_date`),
    resumption_reason: cleanText(record.resumption_reason, `${prefix}.resumption_reason`, 500),
    early_termination_date: validDate(record.early_termination_date, `${prefix}.early_termination_date`),
    publication_date: validDate(record.publication_date, `${prefix}.publication_date`),
    early_termination_date_based_on_cancellation_notice: validDate(record.early_termination_date_based_on_cancellation_notice, `${prefix}.early_termination_date_based_on_cancellation_notice`),
    early_termination_reason_based_on_cancellation_notice: cleanText(record.early_termination_reason_based_on_cancellation_notice, `${prefix}.early_termination_reason_based_on_cancellation_notice`, 500),
    source_url: sourceUrl,
    source_field_namespace: EXPECTED_NAMESPACE,
    source_field_numbers: fieldNumbers,
    market_scope: manifest.market_scope,
    applicability_precision: EXPECTED_PRECISION,
    review_status: 'needs_review',
    publication_status: 'blocked_pending_technical_review',
    exact_engine_fitment_claim: 0,
    exact_transmission_fitment_claim: 0,
    exact_ecu_fitment_claim: 0
  };
  if (normalized.electronically_issued_flag !== true) {
    fail(`${prefix}.electronically_issued_flag must be true for the Annex 2 public-search scope`);
  }
  for (const field of TEXT_FIELDS) {
    if (normalized[field] !== undefined && normalized[field] !== null && typeof normalized[field] !== 'string') fail(`${prefix}.${field} must be text`);
  }
  const canonicalRecordJson = canonicalJson(record);
  return { normalized, raw: record, canonicalRecordJson, canonicalSourceRecordSha256: sha256(Buffer.from(canonicalRecordJson, 'utf8')) };
}
function validatePackage(input, manifest, licenseBytes, permissionBytes) {
  if (!input || typeof input !== 'object' || Array.isArray(input)) fail('export root must be an object');
  if (input.schema_version !== 2 || input.package_type !== 'rosstandart_fgis_annex2_export') fail('unsupported export package type or schema version');
  if (!Array.isArray(input.document_types) || input.document_types.length < 1 || input.document_types.length > SUPPORTED_DOCUMENT_TYPES.size) {
    fail('document_types must explicitly list one or more supported OTTS/EOTTS document types');
  }
  const declaredDocumentTypes = input.document_types.map((value, index) => cleanText(value, `document_types[${index}]`, 20, true));
  if (new Set(declaredDocumentTypes).size !== declaredDocumentTypes.length || declaredDocumentTypes.some((value) => !SUPPORTED_DOCUMENT_TYPES.has(value))) {
    fail('document_types may contain only unique OTTS/EOTTS values; OTSH and SBKTS are excluded');
  }
  if (!manifest || typeof manifest !== 'object' || Array.isArray(manifest)) fail('source manifest must be an object');
  if (manifest.schema_version !== 1 || manifest.source_id !== SOURCE_ID) fail(`source manifest must identify ${SOURCE_ID}`);
  cleanText(manifest.source_revision, 'source_revision', 120, true);
  if (manifest.source_revision !== '2038_as_amended_by_2335') fail('source_revision does not match the validated Annex 2 field map; update the importer after any later amendment');
  if (!Array.isArray(manifest.market_scope) || !manifest.market_scope.includes('RU') || !manifest.market_scope.includes('EAEU_TR_TS_018_2011')) {
    fail('market_scope must include RU and EAEU_TR_TS_018_2011');
  }
  validUrl(manifest.source_url, 'source_url', true);
  if (!/^\d{4}-\d{2}-\d{2}T/.test(String(manifest.retrieved_at || '')) || !Number.isFinite(Date.parse(manifest.retrieved_at))) fail('retrieved_at must be a valid ISO timestamp');
  if (!Array.isArray(input.records) || input.records.length < 1 || input.records.length > MAX_RECORDS) fail(`records must contain 1..${MAX_RECORDS} rows`);
  const seenKeys = new Set();
  const seenNumbers = new Set();
  const records = input.records.map((record, index) => {
    const row = normalizeRecord(record, index, manifest);
    const key = row.normalized.source_record_key.toLowerCase();
    const approval = `${row.normalized.document_type}|${row.normalized.approval_registration_number.toUpperCase()}`;
    if (seenKeys.has(key)) fail(`duplicate source_record_key: ${row.normalized.source_record_key}`);
    if (seenNumbers.has(approval)) fail(`duplicate approval_registration_number for ${row.normalized.document_type}: ${row.normalized.approval_registration_number}`);
    seenKeys.add(key); seenNumbers.add(approval);
    return row;
  });
  const actualDocumentTypes = [...new Set(records.map((row) => row.normalized.document_type))].sort();
  if (canonicalJson(actualDocumentTypes) !== canonicalJson([...declaredDocumentTypes].sort())) {
    fail('input.document_types must exactly match the document_type values present in records');
  }
  const rightsResult = validateRights(manifest, licenseBytes, permissionBytes);
  return { records, rightsResult, documentTypes: actualDocumentTypes };
}
function parseArgs(argv) {
  const values = {};
  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i];
    if (!['--input', '--manifest', '--license-text', '--permission-document', '--output'].includes(arg)) fail(`unknown argument: ${arg}`);
    if (!argv[i + 1] || argv[i + 1].startsWith('--')) fail(`${arg} requires a value`);
    values[arg] = argv[++i];
  }
  for (const arg of ['--input', '--manifest', '--output']) if (!values[arg]) fail(`missing ${arg}`);
  if (values['--license-text'] && values['--permission-document']) fail('provide either --license-text or --permission-document, not both');
  return values;
}
function createSchema(db) {
  db.exec(`
    PRAGMA foreign_keys = ON;
    PRAGMA journal_mode = DELETE;
    PRAGMA user_version = 2;
    PRAGMA application_id = 1447117908;
    CREATE TABLE source_snapshot (
      id INTEGER PRIMARY KEY CHECK (id = 1),
      source_id TEXT NOT NULL,
      publisher TEXT NOT NULL,
      source_url TEXT NOT NULL,
      source_revision TEXT NOT NULL,
      retrieved_at TEXT NOT NULL,
      source_snapshot_sha256 TEXT NOT NULL CHECK (length(source_snapshot_sha256) = 64),
      source_manifest_sha256 TEXT NOT NULL CHECK (length(source_manifest_sha256) = 64),
      market_scope_json TEXT NOT NULL,
      document_types_json TEXT NOT NULL,
      applicability_precision TEXT NOT NULL,
      rights_basis TEXT NOT NULL,
      license_identifier TEXT,
      license_url TEXT,
      license_text_sha256 TEXT,
      permission_document_url TEXT,
      permission_document_sha256 TEXT,
      commercial_use_allowed INTEGER NOT NULL CHECK (commercial_use_allowed = 1),
      display_allowed INTEGER NOT NULL CHECK (display_allowed = 1),
      offline_cache_allowed INTEGER NOT NULL CHECK (offline_cache_allowed = 1),
      bulk_export_allowed INTEGER NOT NULL CHECK (bulk_export_allowed = 1),
      pdf_redistribution_allowed INTEGER NOT NULL CHECK (pdf_redistribution_allowed IN (0,1)),
      rights_reviewed_by TEXT NOT NULL,
      rights_reviewed_at TEXT NOT NULL,
      rights_approval_reference TEXT NOT NULL,
      rights_status TEXT NOT NULL CHECK (rights_status = 'verified_for_metadata_offline_distribution'),
      import_status TEXT NOT NULL CHECK (import_status = 'staging_only_not_published'),
      record_count INTEGER NOT NULL CHECK (record_count > 0),
      created_at TEXT NOT NULL
    );
    CREATE TABLE type_approval_records (
      id INTEGER PRIMARY KEY,
      document_type TEXT NOT NULL CHECK (document_type IN ('OTTS','EOTTS')),
      approval_form_accounting_number TEXT,
      application_form_accounting_numbers TEXT,
      supplementary_sheet_accounting_numbers TEXT,
      source_record_key TEXT NOT NULL UNIQUE,
      approval_registration_number TEXT NOT NULL,
      make TEXT NOT NULL CHECK (make IN ('Volkswagen','Audi','Škoda','SEAT','CUPRA')),
      commercial_name TEXT NOT NULL,
      vehicle_type TEXT NOT NULL,
      valid_from TEXT,
      valid_to TEXT,
      base_vehicle_or_chassis TEXT,
      modifications TEXT,
      vehicle_category TEXT,
      environmental_class TEXT,
      certification_body_name TEXT,
      certification_body_address TEXT,
      certification_body_phone TEXT,
      certification_body_email TEXT,
      certification_body_accreditation_certificate_number TEXT,
      annex_1_pdf_url TEXT,
      electronically_issued_flag INTEGER CHECK (electronically_issued_flag IN (0,1) OR electronically_issued_flag IS NULL),
      suspension_date TEXT,
      suspension_reason TEXT,
      resumption_date TEXT,
      resumption_reason TEXT,
      early_termination_date TEXT,
      publication_date TEXT,
      early_termination_date_based_on_cancellation_notice TEXT,
      early_termination_reason_based_on_cancellation_notice TEXT,
      source_url TEXT NOT NULL,
      source_revision TEXT NOT NULL,
      canonical_source_record_sha256 TEXT NOT NULL CHECK (length(canonical_source_record_sha256) = 64),
      market_scope_json TEXT NOT NULL,
      applicability_precision TEXT NOT NULL CHECK (applicability_precision = 'type_approval_document_metadata_only'),
      source_field_namespace TEXT NOT NULL CHECK (source_field_namespace = 'annex_2_publication_fields'),
      source_field_numbers_json TEXT NOT NULL,
      review_status TEXT NOT NULL CHECK (review_status = 'needs_review'),
      publication_status TEXT NOT NULL CHECK (publication_status = 'blocked_pending_technical_review'),
      exact_engine_fitment_claim INTEGER NOT NULL CHECK (exact_engine_fitment_claim = 0),
      exact_transmission_fitment_claim INTEGER NOT NULL CHECK (exact_transmission_fitment_claim = 0),
      exact_ecu_fitment_claim INTEGER NOT NULL CHECK (exact_ecu_fitment_claim = 0),
      UNIQUE(document_type, approval_registration_number)
    );
    CREATE TABLE raw_source_records (
      source_record_key TEXT PRIMARY KEY REFERENCES type_approval_records(source_record_key) ON DELETE CASCADE,
      canonical_json TEXT NOT NULL,
      canonical_sha256 TEXT NOT NULL CHECK (length(canonical_sha256) = 64)
    );
    CREATE TABLE record_field_provenance (
      id INTEGER PRIMARY KEY,
      source_record_key TEXT NOT NULL REFERENCES type_approval_records(source_record_key) ON DELETE CASCADE,
      field_name TEXT NOT NULL,
      field_number INTEGER NOT NULL CHECK (field_number BETWEEN 1 AND 28),
      field_namespace TEXT NOT NULL CHECK (field_namespace = 'annex_2_publication_fields'),
      field_value TEXT,
      source_url TEXT NOT NULL,
      source_revision TEXT NOT NULL,
      canonical_source_record_sha256 TEXT NOT NULL CHECK (length(canonical_source_record_sha256) = 64),
      UNIQUE(source_record_key, field_name)
    );
    CREATE INDEX type_approval_make_name_idx ON type_approval_records(make, commercial_name);
    CREATE INDEX type_approval_number_idx ON type_approval_records(approval_registration_number);
    CREATE INDEX record_field_source_idx ON record_field_provenance(source_record_key, field_number);
  `);
}
function buildDatabase({ inputBytes, manifestBytes, input, manifest, records, rightsResult, outputPath, manifestPath, licenseBytes, permissionBytes }) {
  const tempDb = `${outputPath}.${process.pid}.tmp`;
  const tempManifest = `${manifestPath}.${process.pid}.tmp`;
  if (fs.existsSync(outputPath) || fs.existsSync(manifestPath)) fail('refusing to overwrite an existing SQLite database or manifest');
  if (fs.existsSync(tempDb) || fs.existsSync(tempManifest)) fail('stale temporary output exists; inspect it before retrying');
  fs.mkdirSync(path.dirname(outputPath), { recursive: true });
  let db;
  try {
    db = new DatabaseSync(tempDb);
    createSchema(db);
    const rights = manifest.rights;
    db.exec('BEGIN IMMEDIATE');
    try {
      db.prepare(`INSERT INTO source_snapshot VALUES (1,${Array(28).fill('?').join(',')})`).run(
        SOURCE_ID, cleanText(manifest.publisher, 'publisher', 240, true), validUrl(manifest.source_url, 'source_url', true),
        cleanText(manifest.source_revision, 'source_revision', 120, true), manifest.retrieved_at,
        sha256(inputBytes), sha256(manifestBytes), JSON.stringify(manifest.market_scope), JSON.stringify(input.document_types), EXPECTED_PRECISION,
        rightsResult.basis, rights.license_identifier || null, rights.license_url || null,
        rightsResult.licenseTextSha256, rights.permission_document_url || null, rightsResult.permissionDocumentSha256,
        1, 1, 1, 1, rights.pdf_redistribution_allowed === true ? 1 : 0,
        rights.reviewed_by, rights.reviewed_at, rights.approval_reference,
        'verified_for_metadata_offline_distribution', 'staging_only_not_published', records.length, new Date().toISOString()
      );
      const insertRecord = db.prepare(`INSERT INTO type_approval_records (
        approval_form_accounting_number, application_form_accounting_numbers, supplementary_sheet_accounting_numbers,
        source_record_key, document_type, approval_registration_number, make, commercial_name, vehicle_type,
        valid_from, valid_to, base_vehicle_or_chassis, modifications, vehicle_category,
        environmental_class, certification_body_name, certification_body_address, certification_body_phone,
        certification_body_email, certification_body_accreditation_certificate_number, annex_1_pdf_url, electronically_issued_flag, suspension_date,
        suspension_reason, resumption_date, resumption_reason, early_termination_date,
        publication_date, early_termination_date_based_on_cancellation_notice,
        early_termination_reason_based_on_cancellation_notice, source_url, source_revision,
        canonical_source_record_sha256, market_scope_json, applicability_precision, source_field_namespace,
        source_field_numbers_json, review_status, publication_status, exact_engine_fitment_claim,
        exact_transmission_fitment_claim, exact_ecu_fitment_claim
      ) VALUES (${Array(42).fill('?').join(',')})`);
      const insertRaw = db.prepare('INSERT INTO raw_source_records VALUES (?,?,?)');
      const insertField = db.prepare('INSERT INTO record_field_provenance (source_record_key,field_name,field_number,field_namespace,field_value,source_url,source_revision,canonical_source_record_sha256) VALUES (?,?,?,?,?,?,?,?)');
      for (const item of records) {
        const row = item.normalized;
        insertRecord.run(
          row.approval_form_accounting_number, row.application_form_accounting_numbers, row.supplementary_sheet_accounting_numbers,
          row.source_record_key, row.document_type, row.approval_registration_number, row.make, row.commercial_name, row.vehicle_type,
          row.valid_from, row.valid_to, row.base_vehicle_or_chassis, row.modifications, row.vehicle_category,
          row.environmental_class, row.certification_body_name, row.certification_body_address, row.certification_body_phone,
          row.certification_body_email, row.certification_body_accreditation_certificate_number, row.annex_1_pdf_url, row.electronically_issued_flag == null ? null : (row.electronically_issued_flag ? 1 : 0),
          row.suspension_date, row.suspension_reason, row.resumption_date, row.resumption_reason,
          row.early_termination_date, row.publication_date, row.early_termination_date_based_on_cancellation_notice,
          row.early_termination_reason_based_on_cancellation_notice, row.source_url, manifest.source_revision,
          item.canonicalSourceRecordSha256, JSON.stringify(manifest.market_scope), EXPECTED_PRECISION, EXPECTED_NAMESPACE,
          JSON.stringify(row.source_field_numbers), 'needs_review', 'blocked_pending_technical_review', 0, 0, 0
        );
        insertRaw.run(row.source_record_key, item.canonicalRecordJson, item.canonicalSourceRecordSha256);
        for (const [fieldName, fieldNumber] of Object.entries(row.source_field_numbers)) {
          const value = fieldName === 'annex_1_pdf' ? row.annex_1_pdf_url : row[fieldName];
          insertField.run(row.source_record_key, fieldName, fieldNumber, EXPECTED_NAMESPACE,
            value == null ? null : String(value), row.source_url, manifest.source_revision, item.canonicalSourceRecordSha256);
        }
      }
      db.exec('COMMIT');
    } catch (error) {
      db.exec('ROLLBACK');
      throw error;
    }
    db.exec('PRAGMA optimize');
    db.close(); db = null;
    const check = new DatabaseSync(tempDb, { readOnly: true });
    let result;
    try {
      const integrity = check.prepare('PRAGMA integrity_check').get().integrity_check;
      const foreignKeys = check.prepare('PRAGMA foreign_key_check').all();
      const rowCount = check.prepare('SELECT COUNT(*) AS n FROM type_approval_records').get().n;
      const unsafe = check.prepare(`SELECT COUNT(*) AS n FROM type_approval_records WHERE exact_engine_fitment_claim <> 0 OR exact_transmission_fitment_claim <> 0 OR exact_ecu_fitment_claim <> 0 OR review_status <> 'needs_review' OR publication_status <> 'blocked_pending_technical_review'`).get().n;
      if (integrity !== 'ok') fail(`SQLite integrity_check failed: ${integrity}`);
      if (foreignKeys.length) fail(`SQLite foreign_key_check failed: ${JSON.stringify(foreignKeys)}`);
      if (rowCount !== records.length) fail('SQLite row count differs from validated input');
      if (unsafe) fail('staging database contains an exact-fitment claim or an opened publication status');
      const snapshot = check.prepare('SELECT * FROM source_snapshot WHERE id=1').get();
      result = {
        schema_version: 2,
        database_user_version: 2,
        package_type: 'authorized_fgis_otts_metadata_staging',
        output: path.basename(outputPath),
        source_id: SOURCE_ID,
        publisher: snapshot.publisher,
        source_url: snapshot.source_url,
        retrieved_at: snapshot.retrieved_at,
        source_revision: manifest.source_revision,
        market_scope: JSON.parse(snapshot.market_scope_json),
        document_types: JSON.parse(snapshot.document_types_json),
        source_snapshot_sha256: snapshot.source_snapshot_sha256,
        source_manifest_sha256: snapshot.source_manifest_sha256,
        license_text_sha256: snapshot.license_text_sha256,
        permission_document_sha256: snapshot.permission_document_sha256,
        rights_basis: snapshot.rights_basis,
        license_identifier: snapshot.license_identifier,
        license_url: snapshot.license_url,
        permission_document_url: snapshot.permission_document_url,
        commercial_use_allowed: snapshot.commercial_use_allowed === 1,
        display_allowed: snapshot.display_allowed === 1,
        offline_cache_allowed: snapshot.offline_cache_allowed === 1,
        bulk_export_allowed: snapshot.bulk_export_allowed === 1,
        pdf_redistribution_allowed: snapshot.pdf_redistribution_allowed === 1,
        rights_reviewed_by: snapshot.rights_reviewed_by,
        rights_reviewed_at: snapshot.rights_reviewed_at,
        rights_approval_reference: snapshot.rights_approval_reference,
        database_sha256: sha256(fs.readFileSync(tempDb)),
        record_count: rowCount,
        field_provenance_count: check.prepare('SELECT COUNT(*) AS n FROM record_field_provenance').get().n,
        rights_status: snapshot.rights_status,
        import_status: snapshot.import_status,
        applicability_precision: EXPECTED_PRECISION,
        review_status: 'needs_review',
        publication_status: 'blocked_pending_technical_review',
        integrity_check: integrity,
        foreign_key_violations: foreignKeys.length,
        built_at: snapshot.created_at
      };
    } finally { check.close(); }
    fs.writeFileSync(tempManifest, `${JSON.stringify(result, null, 2)}\n`, { flag: 'wx' });
    fs.renameSync(tempDb, outputPath);
    try { fs.renameSync(tempManifest, manifestPath); }
    catch (error) { fs.rmSync(outputPath, { force: true }); throw error; }
    console.log(JSON.stringify(result, null, 2));
    return result;
  } catch (error) {
    if (db) { try { db.close(); } catch {} }
    fs.rmSync(tempDb, { force: true });
    fs.rmSync(tempManifest, { force: true });
    throw error;
  }
}
function run(args) {
  const inputPath = path.resolve(args['--input']);
  const manifestPath = path.resolve(args['--manifest']);
  const outputPath = path.resolve(args['--output']);
  const outputManifestPath = `${outputPath}.manifest.json`;
  const input = readJson(inputPath, MAX_EXPORT_BYTES, 'export');
  const manifest = readJson(manifestPath, MAX_MANIFEST_BYTES, 'source manifest');
  let licenseBytes = null;
  let permissionBytes = null;
  if (args['--license-text']) {
    const file = path.resolve(args['--license-text']);
    const stat = fs.statSync(file);
    if (!stat.isFile() || stat.size > MAX_EVIDENCE_BYTES) fail('license text must be a regular file within the size limit');
    licenseBytes = fs.readFileSync(file);
  }
  if (args['--permission-document']) {
    const file = path.resolve(args['--permission-document']);
    const stat = fs.statSync(file);
    if (!stat.isFile() || stat.size > MAX_EVIDENCE_BYTES) fail('permission document must be a regular file within the size limit');
    permissionBytes = fs.readFileSync(file);
  }
  const validated = validatePackage(input.value, manifest.value, licenseBytes, permissionBytes);
  return buildDatabase({
    inputBytes: input.bytes, manifestBytes: manifest.bytes, input: input.value,
    manifest: manifest.value, records: validated.records, rightsResult: validated.rightsResult,
    outputPath, manifestPath: outputManifestPath, licenseBytes, permissionBytes
  });
}
if (require.main === module) {
  try { run(parseArgs(process.argv.slice(2))); }
  catch (error) { console.error(`Authorized FGIS OTTS import blocked: ${error.message}`); process.exitCode = 1; }
}
module.exports = { run, parseArgs, validateRights, validatePackage, normalizeRecord, FIELD_NUMBERS, EXPECTED_NAMESPACE, EXPECTED_PRECISION };
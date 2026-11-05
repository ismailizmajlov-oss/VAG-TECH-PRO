'use strict';

const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const { DatabaseSync } = require('node:sqlite');

const PACK_ID = 'rdw-vag-type-approval-cc0';
const SOURCE_ID = 'rdw-vag-type-approval-cc0';
const LICENSE = 'CC0-1.0';
const DATASET_IDS = ['m9d7-ebf2', '4by9-ammk', '7rjk-eycs', 'byxc-wwua', 'x5v3-sewk'];
const FORBIDDEN_REGISTRY_FIELDS = new Set([
  'kenteken', 'houder', 'houdergegevens', 'tenaamstelling',
  'datum_tenaamstelling', 'datum_tenaamstelling_dt', 'wam_verzekerd'
]);

function sha256Buffer(buffer) {
  return crypto.createHash('sha256').update(buffer).digest('hex');
}

function sha256File(filePath) {
  const hash = crypto.createHash('sha256');
  const fd = fs.openSync(filePath, 'r');
  try {
    const buffer = Buffer.allocUnsafe(1024 * 1024);
    let bytes;
    while ((bytes = fs.readSync(fd, buffer, 0, buffer.length, null)) > 0) {
      hash.update(buffer.subarray(0, bytes));
    }
  } finally {
    fs.closeSync(fd);
  }
  return hash.digest('hex');
}

function readJson(filePath) {
  return JSON.parse(fs.readFileSync(filePath, 'utf8'));
}

function safeResolve(root, relativePath) {
  const resolvedRoot = path.resolve(root);
  const resolved = path.resolve(resolvedRoot, relativePath);
  if (resolved !== resolvedRoot && !resolved.startsWith(resolvedRoot + path.sep)) {
    throw new Error('RDW pack path escapes the pack directory');
  }
  return resolved;
}

function hashBundle(items) {
  return sha256Buffer(Buffer.from(items.join(''), 'ascii'));
}

function verifyRdwTypeApprovalPack(options = {}) {
  const cwd = options.cwd || process.cwd();
  const researchRoot = options.researchRoot || process.env.VAG_TECH_PRO_RESEARCH_DIR || path.join(cwd, 'data', 'research');
  const packDir = path.resolve(options.packDir || path.join(researchRoot, PACK_ID));
  const lockPath = path.resolve(options.lockPath || path.join(packDir, 'source-lock.json'));
  const registerPath = path.resolve(options.registerPath || path.join(packDir, 'source-register.json'));

  if (!fs.existsSync(packDir)) return { ok: false, status: 'not_installed', error: 'RDW candidate pack is not installed' };

  const manifestPath = path.join(packDir, 'manifest.json');
  const dbPath = path.join(packDir, 'rdw-vag-type-approval.sqlite');
  const licensePath = path.join(packDir, 'LICENSE-CC0-1.0.txt');
  const attributionPath = path.join(packDir, 'ATTRIBUTION.md');
  for (const requiredPath of [manifestPath, dbPath, licensePath, attributionPath, lockPath, registerPath]) {
    if (!fs.existsSync(requiredPath)) throw new Error('RDW pack is missing required provenance file: ' + requiredPath);
  }

  const manifest = readJson(manifestPath);
  const lock = readJson(lockPath);
  const register = readJson(registerPath);
  if (manifest.source_register_sha256 && sha256File(registerPath) !== manifest.source_register_sha256) throw new Error('RDW source-register SHA-256 mismatch');
  const source = Array.isArray(register.sources) ? register.sources.find((item) => item.source_id === SOURCE_ID) : null;
  if (!source) throw new Error('RDW source is missing from the factory source register');

  if (manifest.pack_id !== PACK_ID || manifest.source_id !== SOURCE_ID) throw new Error('RDW pack identity mismatch');
  if (manifest.data_license !== LICENSE || manifest.rights_status !== 'approved_by_published_license') throw new Error('RDW pack licence or rights status mismatch');
  if (lock.pack_id !== PACK_ID || lock.data_license !== LICENSE || lock.rights_status !== 'approved_by_published_license') throw new Error('RDW source lock identity or rights mismatch');
  if (lock.rights?.commercial_use_allowed !== true || lock.rights?.display_allowed !== true ||
      lock.rights?.offline_cache_allowed !== true || lock.rights?.bulk_reuse_allowed !== true ||
      lock.rights?.redistribution_allowed !== true || lock.rights?.share_alike_required !== false) {
    throw new Error('RDW CC0 reuse permissions are incomplete');
  }
  if (source.rights?.data_license_status !== LICENSE || source.rights?.commercial_use_allowed !== true ||
      source.rights?.display_allowed !== true || source.rights?.offline_cache_allowed !== true ||
      source.rights?.bulk_reuse_allowed !== true || source.rights?.redistribution_allowed !== true ||
      source.rights?.share_alike_required !== false || source.rights?.attribution_required !== false) {
    throw new Error('RDW source-register rights gate failed');
  }
  if (source.verification_status !== 'verified_source_candidate_pack_only' ||
      source.display_status !== 'candidate_only_read_only') {
    throw new Error('RDW source register has not approved this verified candidate-only pack for display');
  }
  if (manifest.verification_status !== 'verified_source_candidate_pack_only' ||
      manifest.exact_vehicle_fitment !== false || manifest.ru_eaeu_applicability !== false ||
      manifest.vag_factory_engine_code_verified !== false || manifest.vag_factory_gearbox_code_verified !== false ||
      manifest.diagnostic_execution_allowed !== false ||
      manifest.no_license_plate_retained !== true || manifest.no_personal_or_holder_data_retained !== true) {
    throw new Error('RDW candidate-only applicability/privacy boundary failed');
  }
  if (!Array.isArray(manifest.market_scope) ||
      !manifest.market_scope.includes('EU_TYPE_APPROVAL') ||
      !manifest.market_scope.includes('NL_REGISTRATION_OBSERVATION') ||
      manifest.market_scope.some((value) => /RU|EAEU/i.test(value))) {
    throw new Error('RDW market scope is invalid or overbroad');
  }
  if (source.applicability?.precision !== 'type_approval_variant_execution_candidate' ||
      source.applicability?.review_status !== 'candidate' ||
      source.applicability?.exact_vehicle_fitment !== false ||
      source.applicability?.generation_verified !== false ||
      source.applicability?.engine_code_fitment !== false ||
      source.applicability?.transmission_code_fitment !== false ||
      source.technical_scope?.ru_eaeu_applicability !== false ||
      source.vehicle_scope?.vag_factory_engine_codes !== false ||
      source.vehicle_scope?.vag_factory_gearbox_codes !== false ||
      source.provenance?.no_license_plate_retention !== true) {
    throw new Error('RDW source-register applicability boundary failed');
  }

  if (sha256File(lockPath) !== manifest.source_manifest_sha256) throw new Error('RDW source lock SHA-256 mismatch');
  if (sha256File(dbPath) !== manifest.database_sha256) throw new Error('RDW SQLite SHA-256 mismatch');
  if (sha256File(licensePath) !== manifest.license_sha256) throw new Error('RDW CC0 notice SHA-256 mismatch');
  if (sha256File(attributionPath) !== manifest.attribution_sha256) throw new Error('RDW attribution SHA-256 mismatch');

  const metadataFiles = Array.isArray(manifest.metadata_files) ? manifest.metadata_files : [];
  if (metadataFiles.length !== DATASET_IDS.length) throw new Error('RDW raw metadata snapshots are incomplete');
  const metadataById = new Map();
  for (const item of metadataFiles) {
    const filePath = safeResolve(packDir, item.path);
    if (!fs.existsSync(filePath) || sha256File(filePath) !== item.sha256) throw new Error('RDW metadata snapshot SHA-256 mismatch');
    if (fs.statSync(filePath).size !== item.byte_size) throw new Error('RDW metadata snapshot byte-size mismatch');
    const metadata = readJson(filePath);
    if (String(metadata.id) !== item.dataset_id) throw new Error('RDW metadata dataset identity mismatch');
    metadataById.set(item.dataset_id, item.sha256);
  }
  if (DATASET_IDS.some((id) => !metadataById.has(id))) throw new Error('RDW metadata set does not match required RDW resources');
  const metadataBundle = hashBundle(metadataFiles.slice().sort((a, b) => a.dataset_id.localeCompare(b.dataset_id)).map((item) => item.sha256));
  if (metadataBundle !== manifest.metadata_bundle_sha256) throw new Error('RDW metadata bundle SHA-256 mismatch');

  const snapshotDir = path.join(packDir, 'snapshots');
  if (!fs.existsSync(snapshotDir)) throw new Error('RDW raw snapshots directory is missing');
  const snapshotFiles = fs.readdirSync(snapshotDir).filter((name) => name.endsWith('.json')).sort();
  const snapshotBundle = hashBundle(snapshotFiles.map((name) => sha256File(path.join(snapshotDir, name))));
  if (snapshotBundle !== manifest.source_snapshot_sha256) throw new Error('RDW raw snapshot bundle SHA-256 mismatch');

  const db = new DatabaseSync(dbPath, { readOnly: true });
  try {
    const integrity = db.prepare('PRAGMA integrity_check').get();
    if (!integrity || Object.values(integrity)[0] !== 'ok') throw new Error('RDW SQLite integrity_check failed');
    if (db.prepare('PRAGMA foreign_key_check').all().length) throw new Error('RDW SQLite foreign_key_check failed');

    const tableNames = new Set(db.prepare("SELECT name FROM sqlite_master WHERE type='table'").all().map((row) => row.name));
    for (const forbidden of ['dtc_definitions', 'generic_dtc', 'repair_procedures', 'wiring_diagrams']) {
      if (tableNames.has(forbidden)) throw new Error('RDW pack must not contain unrelated technical tables: ' + forbidden);
    }

    const provenanceRows = db.prepare('SELECT dataset_id,metadata_sha256,query_sha256,snapshot_sha256,row_count FROM dataset_provenance ORDER BY dataset_id').all();
    if (provenanceRows.length !== metadataFiles.length) throw new Error('RDW dataset provenance count mismatch');
    const snapshotRows = db.prepare('SELECT dataset_id,page_number,request_url,response_sha256,byte_size,row_count,snapshot_path FROM source_snapshots ORDER BY dataset_id,page_number').all();
    if (snapshotRows.length !== manifest.snapshot_count) throw new Error('RDW raw snapshot count mismatch');

    const snapshotsByDataset = new Map();
    for (const row of snapshotRows) {
      const entries = snapshotsByDataset.get(row.dataset_id) || [];
      entries.push(row);
      snapshotsByDataset.set(row.dataset_id, entries);
      const filePath = safeResolve(packDir, row.snapshot_path);
      if (!fs.existsSync(filePath) || sha256File(filePath) !== row.response_sha256) throw new Error('RDW raw response SHA-256 mismatch');
      if (fs.statSync(filePath).size !== row.byte_size) throw new Error('RDW raw response byte-size mismatch');
      const rows = readJson(filePath);
      if (!Array.isArray(rows) || rows.length !== row.row_count) throw new Error('RDW raw response row-count mismatch');
      if (row.dataset_id === 'm9d7-ebf2' && rows.some((item) => Object.keys(item).some((key) => FORBIDDEN_REGISTRY_FIELDS.has(key.toLowerCase())))) {
        throw new Error('RDW vehicle registry snapshot contains an excluded registration field');
      }
    }

    for (const row of provenanceRows) {
      if (!metadataById.has(row.dataset_id) || metadataById.get(row.dataset_id) !== row.metadata_sha256) throw new Error('RDW metadata hash differs between SQLite and manifest');
      const entries = snapshotsByDataset.get(row.dataset_id) || [];
      const queryHash = sha256Buffer(Buffer.from(entries.map((item) => item.request_url).join('\n'), 'utf8'));
      const snapshotHash = sha256Buffer(Buffer.from(entries.map((item) => item.response_sha256).join(''), 'ascii'));
      if (queryHash !== row.query_sha256 || snapshotHash !== row.snapshot_sha256) throw new Error('RDW query or per-dataset snapshot provenance hash mismatch');
      if (entries.reduce((sum, item) => sum + item.row_count, 0) !== row.row_count) throw new Error('RDW dataset row-count provenance mismatch');
      if (row.dataset_id && !DATASET_IDS.includes(row.dataset_id)) throw new Error('Unexpected RDW dataset in provenance');
    }

    const counts = {
      vehicle_variants: db.prepare('SELECT count(*) AS n FROM vehicle_type_approval_candidates').get().n,
      engine_candidates: db.prepare('SELECT count(*) AS n FROM engine_approval_candidates').get().n,
      transmission_candidates: db.prepare('SELECT count(*) AS n FROM transmission_approval_candidates').get().n,
      approval_revision_candidates: db.prepare('SELECT count(*) AS n FROM approval_execution_revisions').get().n,
      manufacturer_designation_candidates: db.prepare('SELECT count(*) AS n FROM manufacturer_designation_candidates').get().n,
      unique_source_row_pair_candidates: db.prepare("SELECT count(*) AS n FROM engine_transmission_pair_candidates WHERE pairing_status='unique_source_rows_candidate'").get().n,
      ambiguous_or_incomplete_pair_keys: db.prepare("SELECT count(*) AS n FROM engine_transmission_pair_candidates WHERE pairing_status<>'unique_source_rows_candidate'").get().n
    };
    if (JSON.stringify(counts) !== JSON.stringify(manifest.counts)) throw new Error('RDW database counts differ from pack manifest');

    const invalidVehicles = db.prepare("SELECT count(*) AS n FROM vehicle_type_approval_candidates WHERE source_id<>? OR source_revision<>? OR market_scope<>'NL_REGISTRATION_OBSERVATION' OR exact_vehicle_fitment<>0 OR ru_eaeu_applicability<>0 OR model_year_verified<>0 OR generation_verified<>0").get(SOURCE_ID, manifest.source_revision).n;
    if (invalidVehicles) throw new Error('RDW vehicle candidate source/applicability check failed');
    const invalidEngines = db.prepare("SELECT count(*) AS n FROM engine_approval_candidates WHERE source_id<>? OR source_revision<>? OR code_namespace<>'RDW.motorcode' OR vag_factory_engine_code_verified<>0").get(SOURCE_ID, manifest.source_revision).n;
    if (invalidEngines) throw new Error('RDW engine namespace or source revision check failed');
    const invalidTransmissions = db.prepare("SELECT count(*) AS n FROM transmission_approval_candidates WHERE source_id<>? OR source_revision<>? OR code_namespace<>'RDW.codetypeversnellingsbak' OR vag_factory_gearbox_code_verified<>0").get(SOURCE_ID, manifest.source_revision).n;
    if (invalidTransmissions) throw new Error('RDW transmission namespace or source revision check failed');
    const invalidPairs = db.prepare("SELECT count(*) AS n FROM engine_transmission_pair_candidates WHERE source_id<>? OR source_revision<>? OR pairing_confirmed<>0 OR exact_vehicle_fitment<>0 OR ru_eaeu_applicability<>0").get(SOURCE_ID, manifest.source_revision).n;
    if (invalidPairs) throw new Error('RDW pair candidate was promoted or lost provenance');
    const invalidUniquePairs = db.prepare("SELECT count(*) AS n FROM engine_transmission_pair_candidates WHERE pairing_status='unique_source_rows_candidate' AND (engine_row_count<>1 OR transmission_row_count<>1 OR engine_candidate_id IS NULL OR transmission_candidate_id IS NULL)").get().n;
    if (invalidUniquePairs) throw new Error('RDW unique candidate pair has inconsistent row counts');
    const invalidAmbiguousPairs = db.prepare("SELECT count(*) AS n FROM engine_transmission_pair_candidates WHERE pairing_status<>'unique_source_rows_candidate' AND (engine_candidate_id IS NOT NULL OR transmission_candidate_id IS NOT NULL)").get().n;
    if (invalidAmbiguousPairs) throw new Error('RDW ambiguous pair was linked');

    const registerCounts = source.counts || {};
    for (const [key, value] of Object.entries(counts)) {
      if (registerCounts[key] !== value) throw new Error('RDW source-register count mismatch for ' + key);
    }

    return {
      ok: true,
      status: 'ready_candidate_only',
      packDir,
      dbPath,
      manifest,
      source
    };
  } finally {
    db.close();
  }
}

function createRdwTypeApprovalDb(options = {}) {
  let cached = null;
  function getVerifiedPack() {
    if (!cached || options.refresh === true) cached = verifyRdwTypeApprovalPack(options);
    return cached;
  }

  function getSummary() {
    try {
      const verified = getVerifiedPack();
      if (!verified.ok) return { status: verified.status, sourceId: SOURCE_ID, counts: null, error: verified.error };
      const manifest = verified.manifest;
      return {
        status: verified.status,
        sourceId: SOURCE_ID,
        sourceRevision: manifest.source_revision,
        dataLicense: LICENSE,
        sourceUrl: 'https://opendata.rdw.nl/',
        licenseUrl: 'https://creativecommons.org/publicdomain/zero/1.0/',
        marketScope: manifest.market_scope,
        applicabilityPrecision: manifest.applicability_precision,
        verificationStatus: manifest.verification_status,
        counts: manifest.counts,
        databaseSha256: manifest.database_sha256,
        sourceSnapshotSha256: manifest.source_snapshot_sha256,
        metadataBundleSha256: manifest.metadata_bundle_sha256,
        sourceManifestSha256: manifest.source_manifest_sha256,
        sourceRegisterSha256: manifest.source_register_sha256 || null,
        exactVehicleFitment: false,
        ruEaeuApplicability: false,
        vagFactoryEngineCodeVerified: false,
        vagFactoryGearboxCodeVerified: false,
        diagnosticExecutionAllowed: false,
        limitations: manifest.limitations
      };
    } catch (error) {
      return { status: 'blocked_integrity_failure', sourceId: SOURCE_ID, counts: null, error: error.message };
    }
  }

  function search(query = '', limit = 20) {
    const summary = getSummary();
    if (summary.status !== 'ready_candidate_only') return { status: summary.status, results: [], summary };
    const verified = getVerifiedPack();
    const safeLimit = Math.max(1, Math.min(Number.isFinite(Number(limit)) ? Math.floor(Number(limit)) : 20, 50));
    const q = String(query || '').trim().toLowerCase();
    const like = q ? '%' + q + '%' : '%';
    const db = new DatabaseSync(verified.dbPath, { readOnly: true });
    try {
      const rows = db.prepare(`
        SELECT
          v.make_name, v.model_name, v.manufacturer_type_code,
          v.type_approval_number, v.variant_code, v.execution_code,
          v.first_registration_seen, v.last_registration_seen,
          v.market_scope, v.applicability_precision, v.verification_status,
          v.source_id, v.source_revision,
          p.revision_number, p.pairing_status, p.engine_row_count, p.transmission_row_count,
          e.rdw_motorcode, t.rdw_transmission_type_code, t.gear_count_min, t.gear_count_max,
          r.revision_start_date, r.revision_end_date,
          d.manufacturer_trade_name, d.manufacturer_type_designation
        FROM vehicle_type_approval_candidates v
        LEFT JOIN engine_transmission_pair_candidates p
          ON p.type_approval_number=v.type_approval_number
          AND p.variant_code=v.variant_code
          AND p.execution_code=v.execution_code
        LEFT JOIN engine_approval_candidates e ON e.engine_candidate_id=p.engine_candidate_id
        LEFT JOIN transmission_approval_candidates t ON t.transmission_candidate_id=p.transmission_candidate_id
        LEFT JOIN approval_execution_revisions r
          ON r.type_approval_number=p.type_approval_number
          AND r.variant_code=p.variant_code
          AND r.execution_code=p.execution_code
          AND r.revision_number=p.revision_number
        LEFT JOIN manufacturer_designation_candidates d
          ON d.type_approval_number=p.type_approval_number
          AND d.variant_code=p.variant_code
          AND d.execution_code=p.execution_code
          AND d.revision_number=p.revision_number
        WHERE lower(v.make_name) LIKE ?
           OR lower(v.model_name) LIKE ?
           OR lower(v.type_approval_number) LIKE ?
           OR lower(v.variant_code) LIKE ?
           OR lower(v.execution_code) LIKE ?
           OR lower(coalesce(e.rdw_motorcode,'')) LIKE ?
           OR lower(coalesce(t.rdw_transmission_type_code,'')) LIKE ?
        ORDER BY v.make_name, v.model_name, v.type_approval_number, p.revision_number
        LIMIT ?
      `).all(like, like, like, like, like, like, like, safeLimit);
      return {
        status: summary.status,
        summary,
        results: rows.map((row) => ({
          make: row.make_name,
          model: row.model_name,
          manufacturerTypeCode: row.manufacturer_type_code,
          typeApprovalNumber: row.type_approval_number,
          variantCode: row.variant_code,
          executionCode: row.execution_code,
          firstRegistrationSeen: row.first_registration_seen,
          lastRegistrationSeen: row.last_registration_seen,
          revisionNumber: row.revision_number,
          revisionStartDate: row.revision_start_date,
          revisionEndDate: row.revision_end_date,
          rdwMotorcode: row.rdw_motorcode,
          engineCodeNamespace: 'RDW.motorcode',
          rdwTransmissionTypeCode: row.rdw_transmission_type_code,
          transmissionCodeNamespace: 'RDW.codetypeversnellingsbak',
          gearCountMin: row.gear_count_min,
          gearCountMax: row.gear_count_max,
          pairingStatus: row.pairing_status || 'no_pair_candidate',
          engineRowCount: row.engine_row_count || 0,
          transmissionRowCount: row.transmission_row_count || 0,
          manufacturerTradeName: row.manufacturer_trade_name,
          manufacturerTypeDesignation: row.manufacturer_type_designation,
          marketScope: row.market_scope,
          applicabilityPrecision: row.applicability_precision,
          verificationStatus: row.verification_status,
          sourceId: row.source_id,
          sourceRevision: row.source_revision,
          pairingConfirmed: false,
          exactVehicleFitment: false,
          ruEaeuApplicability: false,
          vagFactoryEngineCodeVerified: false,
          vagFactoryGearboxCodeVerified: false
        }))
      };
    } finally {
      db.close();
    }
  }

  return { getSummary, search, verify: getVerifiedPack };
}

const defaultDb = createRdwTypeApprovalDb();

module.exports = {
  createRdwTypeApprovalDb,
  verifyRdwTypeApprovalPack,
  getRdwTypeApprovalSummary: () => defaultDb.getSummary(),
  searchRdwTypeApprovalCandidates: (query, limit) => defaultDb.search(query, limit)
};

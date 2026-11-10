"use strict";
const fs = require("node:fs");
const path = require("node:path");
const { DatabaseSync } = require("node:sqlite");
const core = require("./local-core-db.cjs");
const HASH_RE = /^[a-f0-9]{64}$/;

function seedWikidataCandidateCatalog(dbPath, researchRoot, options = {}) {
  const root = path.resolve(researchRoot);
  const packRoot = path.join(root, "wikidata-vag-model-taxonomy-cc0");
  const manifestPath = path.join(packRoot, "manifest.json");
  const licensePath = path.join(packRoot, "LICENSE-NOTICE.txt");
  const snapshotPath = path.join(packRoot, "snapshot.json");
  const researchDbPath = path.join(packRoot, "wikidata-vag-taxonomy.sqlite");
  const missing = [manifestPath, licensePath, snapshotPath, researchDbPath].filter((file) => !fs.existsSync(file));
  if (missing.length) return { status: "skipped", reason: "wikidata_pack_missing", missing: missing.map((file) => path.basename(file)) };

  const manifestBytes = fs.readFileSync(manifestPath);
  const licenseBytes = fs.readFileSync(licensePath);
  const manifest = JSON.parse(manifestBytes.toString("utf8"));
  const licenseSha256 = core.sha256(licenseBytes);
  const rightsEvidenceSha256 = core.sha256(manifestBytes);
  const snapshotSha256 = core.sha256(fs.readFileSync(snapshotPath));
  const databaseSha256 = core.sha256(fs.readFileSync(researchDbPath));
  const expectedLicenseFileSha256 = manifest.pack_files?.["LICENSE-NOTICE.txt"]?.sha256;
  if (manifest.source_id !== "wikidata-vag-model-taxonomy" || manifest.data_license !== "CC0-1.0" ||
      manifest.license_url !== "https://creativecommons.org/publicdomain/zero/1.0/" ||
      manifest.rights_status !== "approved_by_published_license" || manifest.commercial_use_allowed !== true ||
      manifest.display_allowed !== true || manifest.offline_cache_allowed !== true || manifest.bulk_reuse_allowed !== true ||
      manifest.redistribution_allowed !== true || manifest.attribution_required !== false || manifest.attribution_recommended !== true ||
      manifest.share_alike_required !== false || manifest.scope?.market_scope !== "UNKNOWN" ||
      manifest.scope?.applicability_precision !== "candidate_identity_only" || manifest.scope?.review_status !== "candidate" ||
      manifest.scope?.exact_vehicle_fitment !== false || manifest.scope?.generation_verified !== false ||
      manifest.scope?.engine_code_fitment !== false || manifest.scope?.transmission_code_fitment !== false ||
      manifest.scope?.ecu_fitment !== false || manifest.scope?.dtc_fitment !== false ||
      manifest.scope?.repair_procedure_fitment !== false || manifest.scope?.diagnostic_execution_allowed !== false ||
      manifest.scope?.production_years_inferred !== false || !HASH_RE.test(manifest.source_snapshot_sha256 || "") ||
      snapshotSha256 !== manifest.source_snapshot_sha256 || databaseSha256 !== manifest.database_sha256 ||
      licenseSha256 !== expectedLicenseFileSha256 || !HASH_RE.test(rightsEvidenceSha256)) {
    throw new Error("Wikidata candidate seed blocked: manifest, CC0 rights or immutable pack hashes do not match");
  }

  const researchDb = new DatabaseSync(researchDbPath, { readOnly: true });
  let records;
  let sourceRevision;
  let sourceSnapshotSha256;
  let sourceQuerySha256;
  let manufacturerCount;
  let modelCount;
  try {
    researchDb.exec("PRAGMA query_only=ON");
    const integrity = researchDb.prepare("PRAGMA integrity_check").get()?.integrity_check;
    const foreignKeyErrors = researchDb.prepare("PRAGMA foreign_key_check").all();
    if (integrity !== "ok" || foreignKeyErrors.length) throw new Error("Wikidata candidate seed blocked: research SQLite integrity check failed");
    const source = researchDb.prepare("SELECT * FROM source_registry WHERE source_id=?").get(manifest.source_id);
    if (!source || source.license_id !== "CC0-1.0" || source.license_url !== manifest.license_url ||
        source.rights_status !== "approved_by_published_license" || source.commercial_use_allowed !== 1 ||
        source.display_allowed !== 1 || source.offline_cache_allowed !== 1 || source.bulk_reuse_allowed !== 1 ||
        source.redistribution_allowed !== 1 || source.attribution_required !== 0 || source.attribution_recommended !== 1 ||
        source.share_alike_required !== 0 || source.market_scope !== "UNKNOWN" ||
        source.applicability_precision !== "candidate_identity_only" || source.review_status !== "candidate" ||
        source.source_revision !== manifest.source_revision || source.source_snapshot_sha256 !== manifest.source_snapshot_sha256 ||
        source.source_query_sha256 !== manifest.source_query_sha256) {
      throw new Error("Wikidata candidate seed blocked: SQLite source registry differs from the pinned CC0 manifest");
    }
    const rows = researchDb.prepare("SELECT * FROM vehicle_model_entities ORDER BY model_qid,manufacturer_qid").all();
    const bindings = researchDb.prepare("SELECT count(*) AS n FROM source_bindings").get().n;
    const manufacturers = new Map();
    for (const row of rows) {
      if (!/^Q[0-9]+$/.test(row.model_qid) || !/^Q[0-9]+$/.test(row.manufacturer_qid) ||
          !/^https?:\/\/www\.wikidata\.org\/entity\/Q[0-9]+$/.test(row.model_uri) ||
          !/^https?:\/\/www\.wikidata\.org\/entity\/Q[0-9]+$/.test(row.manufacturer_uri) ||
          !row.model_label_en || !row.manufacturer_label_en ||
          row.market_scope !== "UNKNOWN" || row.applicability_precision !== "candidate_identity_only" || row.review_status !== "candidate" ||
          row.exact_vehicle_fitment !== 0 || row.generation_verified !== 0 || row.engine_code_fitment !== 0 ||
          row.transmission_code_fitment !== 0 || row.ecu_fitment !== 0 || row.dtc_fitment !== 0 || row.repair_procedure_fitment !== 0 ||
          !HASH_RE.test(row.source_record_sha256 || "") || row.source_revision !== manifest.source_revision ||
          row.source_snapshot_sha256 !== manifest.source_snapshot_sha256 || row.source_query_sha256 !== manifest.source_query_sha256) {
        throw new Error("Wikidata candidate seed blocked: invalid or over-promoted source row " + row.model_qid);
      }
      const types = JSON.parse(row.entity_types_json);
      const bindingIndexes = JSON.parse(row.source_binding_indexes_json);
      const bindingHashes = JSON.parse(row.source_binding_sha256s_json);
      if (!Array.isArray(types) || !types.length || types.some((item) => !["Q3231690", "Q59773381"].includes(item.entity_class_qid)) ||
          !Array.isArray(bindingIndexes) || !Array.isArray(bindingHashes) || bindingIndexes.length !== row.source_binding_count ||
          bindingHashes.length !== row.source_binding_count || bindingHashes.some((hash) => !HASH_RE.test(hash))) {
        throw new Error("Wikidata candidate seed blocked: source binding evidence is incomplete for " + row.model_qid);
      }
      manufacturers.set(row.manufacturer_qid, row.manufacturer_label_en);
    }
    if (rows.length !== manifest.counts?.model_entities || bindings !== manifest.counts?.source_bindings ||
        manufacturers.size !== manifest.counts?.manufacturers ||
        rows.filter((row) => row.model_label_ru && row.model_label_ru.trim()).length !== manifest.counts?.russian_labels) {
      throw new Error("Wikidata candidate seed blocked: source row counts do not match the pinned manifest");
    }
    sourceRevision = source.source_revision;
    sourceSnapshotSha256 = source.source_snapshot_sha256;
    sourceQuerySha256 = source.source_query_sha256;
    manufacturerCount = manufacturers.size;
    modelCount = rows.length;
    records = [];
    for (const [qid, label] of [...manufacturers].sort((a, b) => a[0].localeCompare(b[0]))) {
      const record = {
        record_type: "brand", natural_key: "wikidata-manufacturer:" + qid, source_record_key: "manufacturer:" + qid,
        market_scope: "UNKNOWN", applicability_precision: "manufacturer_make_candidate", review_status: "candidate",
        payload: { brand_key: "wikidata:" + qid, display_name: label, group_name: "VAG identity candidate", manufacturer_qid: qid,
          manufacturer_group_basis: manifest.scope.manufacturer_group_basis, source_namespace: "wikidata_vag_identity_candidate" }
      };
      record.record_sha256 = core.catalogRecordSha256(record);
      records.push(record);
    }
    for (const row of rows) {
      const modelKey = row.model_qid + ":" + row.manufacturer_qid;
      const payload = {
        brand_key: "wikidata:" + row.manufacturer_qid, model_key: row.model_qid,
        display_name: row.model_label_ru && row.model_label_ru.trim() ? row.model_label_ru : row.model_label_en,
        manufacturer_qid: row.manufacturer_qid, manufacturer_label_en: row.manufacturer_label_en,
        model_qid: row.model_qid, model_uri: row.model_uri, manufacturer_uri: row.manufacturer_uri,
        model_label_en: row.model_label_en, model_label_ru: row.model_label_ru || null,
        entity_types: JSON.parse(row.entity_types_json), inception_dates: JSON.parse(row.inception_dates_json),
        dissolution_dates: JSON.parse(row.dissolution_dates_json), modified_dates: JSON.parse(row.modified_dates_json),
        source_binding_indexes: JSON.parse(row.source_binding_indexes_json), source_binding_sha256s: JSON.parse(row.source_binding_sha256s_json),
        source_binding_count: row.source_binding_count, source_record_sha256: row.source_record_sha256,
        source_query_sha256: row.source_query_sha256, market_scope: "UNKNOWN", applicability_precision: "candidate_identity_only",
        review_status: "candidate", exact_vehicle_fitment: false, generation_verified: false,
        engine_code_fitment: false, transmission_code_fitment: false, ecu_fitment: false,
        dtc_fitment: false, repair_procedure_fitment: false, production_years_inferred: false
      };
      const record = {
        record_type: "vehicle_model", natural_key: "wikidata-model:" + modelKey,
        source_record_key: "model:" + modelKey, market_scope: "UNKNOWN",
        applicability_precision: "vehicle_model_candidate", review_status: "candidate", payload
      };
      record.record_sha256 = core.catalogRecordSha256(record);
      records.push(record);
    }
  } finally { researchDb.close(); }

  const sourceMeta = {
    source_id: manifest.source_id, publisher: manifest.publisher,
    title: "Wikidata VAG model identity taxonomy (CC0 1.0)",
    source_type: "public_structured_data_identity_taxonomy", source_url: manifest.source_repository,
    revision: sourceRevision, license_id: manifest.data_license, license_url: manifest.license_url,
    license_sha256: licenseSha256, rights_status: manifest.rights_status,
    commercial_use_allowed: true, display_allowed: true, offline_cache_allowed: true, bulk_reuse_allowed: true,
    redistribution_allowed: true, share_alike_required: false, attribution_required: false,
    attribution_text: manifest.attribution_text, market_scope: "UNKNOWN",
    source_snapshot_sha256: sourceSnapshotSha256, rights_evidence_sha256: rightsEvidenceSha256
  };
  const registration = core.registerSourceIfAbsent(dbPath, sourceMeta, options);
  const existingSource = registration.source;
  const expected = [sourceMeta.publisher, sourceMeta.title, sourceMeta.source_type, sourceMeta.source_url, sourceMeta.revision,
    sourceMeta.license_id, sourceMeta.license_url, sourceMeta.license_sha256, sourceMeta.rights_status,
    1, 1, 1, 1, 1, 0, 0, sourceMeta.attribution_text, "UNKNOWN", sourceSnapshotSha256, rightsEvidenceSha256, "approved"];
  const actual = [existingSource.publisher, existingSource.title, existingSource.source_type, existingSource.source_url, existingSource.revision,
    existingSource.license_id, existingSource.license_url, existingSource.license_sha256, existingSource.rights_status,
    existingSource.commercial_use_allowed, existingSource.display_allowed, existingSource.offline_cache_allowed,
    existingSource.bulk_reuse_allowed, existingSource.redistribution_allowed, existingSource.share_alike_required,
    existingSource.attribution_required, existingSource.attribution_text, existingSource.market_scope,
    existingSource.source_snapshot_sha256, existingSource.rights_evidence_sha256, existingSource.status];
  if (expected.some((value, index) => value !== actual[index])) {
    return { status: "skipped", reason: "existing_source_metadata_conflict_or_rights_revoked", source_id: manifest.source_id };
  }

  const snapshotManifest = {
    upstream_revision: sourceRevision, source_snapshot_sha256: sourceSnapshotSha256,
    source_query_sha256: sourceQuerySha256, license_id: manifest.data_license, license_url: manifest.license_url,
    license_sha256: licenseSha256, rights_evidence_sha256: rightsEvidenceSha256,
    market_scope: "UNKNOWN", applicability_precision: "candidate_identity_only",
    source_model_entities: modelCount, manufacturer_entities: manufacturerCount,
    source_bindings: manifest.counts.source_bindings, russian_labels: manifest.counts.russian_labels,
    manufacturer_group_basis: manifest.scope.manufacturer_group_basis,
    separate_pack_required: false, share_alike_required: false, attribution_recommended: true, documents: []
  };
  const pkg = {
    package_kind: "vehicle_catalog", package_id: manifest.pack_id, source_id: manifest.source_id,
    source_revision: sourceRevision, market_scope: "UNKNOWN", source_snapshot_sha256: sourceSnapshotSha256,
    license_sha256: licenseSha256, rights_evidence_sha256: rightsEvidenceSha256,
    snapshot_manifest: snapshotManifest, records
  };
  pkg.package_sha256 = core.sha256({ package_kind: pkg.package_kind, package_id: pkg.package_id, source_id: pkg.source_id,
    source_revision: pkg.source_revision, market_scope: pkg.market_scope, source_snapshot_sha256: pkg.source_snapshot_sha256,
    license_sha256: pkg.license_sha256, rights_evidence_sha256: pkg.rights_evidence_sha256,
    snapshot_manifest: pkg.snapshot_manifest, records: pkg.records });
  const imported = core.importPackage(dbPath, pkg, options);
  return { ...imported, packageSha256: pkg.package_sha256, package_sha256: pkg.package_sha256,
    source_id: manifest.source_id, source_revision: sourceRevision, market_scope: "UNKNOWN",
    applicability_precision: "candidate_identity_only", manufacturers: manufacturerCount, models: modelCount,
    verified_models: 0, exact_fitments: 0, engine_codes: 0, transmission_codes: 0 };
}

module.exports = { seedWikidataCandidateCatalog };

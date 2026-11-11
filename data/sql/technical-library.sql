-- VAG TECH PRO technical library storage contract, schema v1.
-- Importers MUST validate payload_json against data/schemas/technical-record-payloads.schema.json.
-- record_sha256 is SHA-256 of canonical UTF-8 JSON (sorted keys, compact separators, no NaN).
-- No technical data is publishable until source rights, applicability and review status are approved.
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS vehicle_catalog_source_rights (
 source_id TEXT PRIMARY KEY REFERENCES vehicle_catalog_sources(source_id) ON DELETE RESTRICT,
 rights_status TEXT NOT NULL CHECK(rights_status IN('not_reviewed','permission_required','approved','restricted','expired')),
 commercial_use_allowed INTEGER NOT NULL DEFAULT 0 CHECK(commercial_use_allowed IN(0,1)),
 display_allowed INTEGER NOT NULL DEFAULT 0 CHECK(display_allowed IN(0,1)),
 offline_cache_allowed INTEGER NOT NULL DEFAULT 0 CHECK(offline_cache_allowed IN(0,1)),
 bulk_reuse_allowed INTEGER NOT NULL DEFAULT 0 CHECK(bulk_reuse_allowed IN(0,1)),
 redistribution_allowed INTEGER NOT NULL DEFAULT 0 CHECK(redistribution_allowed IN(0,1)),
 store_text_allowed INTEGER NOT NULL DEFAULT 0 CHECK(store_text_allowed IN(0,1)),
 store_diagrams_allowed INTEGER NOT NULL DEFAULT 0 CHECK(store_diagrams_allowed IN(0,1)),
 store_structured_data_allowed INTEGER NOT NULL DEFAULT 0 CHECK(store_structured_data_allowed IN(0,1)),
 license_text_sha256 TEXT CHECK(license_text_sha256 IS NULL OR(length(license_text_sha256)=64 AND license_text_sha256 NOT GLOB '*[^a-f0-9]*')),
 permission_reference TEXT, rights_revision TEXT NOT NULL, reviewed_at_utc TEXT NOT NULL,
 CHECK(rights_status<>'approved' OR(display_allowed=1 AND offline_cache_allowed=1 AND bulk_reuse_allowed=1 AND redistribution_allowed=1 AND license_text_sha256 IS NOT NULL))
);
CREATE TRIGGER IF NOT EXISTS vehicle_catalog_rights_permission_reference_insert
BEFORE INSERT ON vehicle_catalog_source_rights WHEN NEW.rights_status='approved'
BEGIN
 SELECT CASE WHEN(SELECT license_status FROM vehicle_catalog_sources WHERE source_id=NEW.source_id)='permission_granted'
 AND(NEW.permission_reference IS NULL OR length(trim(NEW.permission_reference))=0)
 THEN RAISE(ABORT,'permission-granted vehicle catalog rights require a permission reference') END;
END;
CREATE TRIGGER IF NOT EXISTS vehicle_catalog_rights_permission_reference_update
BEFORE UPDATE OF rights_status,permission_reference ON vehicle_catalog_source_rights WHEN NEW.rights_status='approved'
BEGIN
 SELECT CASE WHEN(SELECT license_status FROM vehicle_catalog_sources WHERE source_id=NEW.source_id)='permission_granted'
 AND(NEW.permission_reference IS NULL OR length(trim(NEW.permission_reference))=0)
 THEN RAISE(ABORT,'permission-granted vehicle catalog rights require a permission reference') END;
END;

CREATE TABLE IF NOT EXISTS technical_documents (
 technical_document_id INTEGER PRIMARY KEY,
 source_document_id INTEGER NOT NULL REFERENCES source_documents(source_document_id) ON DELETE RESTRICT,
 technical_kind TEXT NOT NULL CHECK(technical_kind IN('dtc_reference','diagnostic_test_plan','repair_procedure','wiring_diagram','ecu_pinout','torque_specification','adaptation','service_interval','ecu_profile','oem_parts_catalog','other')),
 title TEXT NOT NULL, document_revision TEXT NOT NULL, issue_date TEXT, language TEXT,
 market_scope TEXT NOT NULL CHECK(market_scope IN('RU','EAEU','EU','NAR','CN','ROW','MULTI','UNKNOWN')),
 content_storage_mode TEXT NOT NULL CHECK(content_storage_mode IN('reference_only','structured_only','text','diagram','mixed')),
 content_resource_key TEXT,
 content_sha256 TEXT CHECK(content_sha256 IS NULL OR(length(content_sha256)=64 AND content_sha256 NOT GLOB '*[^a-f0-9]*')),
 review_status TEXT NOT NULL DEFAULT 'candidate' CHECK(review_status IN('candidate','source_checked','technically_verified','publication_approved','rejected')),
 created_at_utc TEXT NOT NULL,
 UNIQUE(source_document_id,technical_kind,title,document_revision,market_scope),
 CHECK((content_storage_mode='reference_only' AND content_resource_key IS NULL AND content_sha256 IS NULL) OR
       (content_storage_mode<>'reference_only' AND content_resource_key IS NOT NULL AND content_sha256 IS NOT NULL))
);
CREATE TABLE IF NOT EXISTS technical_applicability (
 applicability_id INTEGER PRIMARY KEY,
 applicability_source_document_id INTEGER REFERENCES source_documents(source_document_id) ON DELETE RESTRICT,
 vehicle_catalog_evidence_id INTEGER REFERENCES vehicle_catalog_evidence(evidence_id) ON DELETE RESTRICT,
 variant_id INTEGER REFERENCES vehicle_variants(variant_id) ON DELETE RESTRICT,
 engine_id INTEGER REFERENCES engine_codes(engine_id) ON DELETE RESTRICT,
 transmission_id INTEGER REFERENCES transmission_codes(transmission_id) ON DELETE RESTRICT,
 pair_evidence_id INTEGER REFERENCES powertrain_pair_evidence(pair_id) ON DELETE RESTRICT,
 ecu_identity_id INTEGER REFERENCES ecu_identities(ecu_identity_id) ON DELETE RESTRICT,
 market_scope TEXT NOT NULL CHECK(market_scope IN('RU','EAEU','EU','NAR','CN','ROW','MULTI','UNKNOWN')),
 model_year_from INTEGER, model_year_to INTEGER, production_date_from TEXT, production_date_to TEXT,
 applicability_precision TEXT NOT NULL CHECK(applicability_precision IN('exact_vin','exact_ecu_hw_sw','engine_transmission_variant','exact_variant','model_year_only','generic_only','unknown')),
 evidence_locator TEXT NOT NULL,
 evidence_sha256 TEXT NOT NULL CHECK(length(evidence_sha256)=64 AND evidence_sha256 NOT GLOB '*[^a-f0-9]*'),
 review_status TEXT NOT NULL DEFAULT 'candidate' CHECK(review_status IN('candidate','source_checked','technically_verified','publication_approved','rejected')),
 reviewer_note TEXT,
 CHECK((applicability_source_document_id IS NOT NULL)<>(vehicle_catalog_evidence_id IS NOT NULL)),
 CHECK(model_year_from IS NULL OR model_year_to IS NULL OR model_year_from<=model_year_to),
 CHECK(applicability_precision<>'exact_vin' OR(variant_id IS NOT NULL AND vehicle_catalog_evidence_id IS NOT NULL)),
 CHECK(applicability_precision<>'engine_transmission_variant' OR(variant_id IS NOT NULL AND engine_id IS NOT NULL AND transmission_id IS NOT NULL AND pair_evidence_id IS NOT NULL AND vehicle_catalog_evidence_id IS NOT NULL)),
 CHECK(applicability_precision<>'exact_ecu_hw_sw' OR ecu_identity_id IS NOT NULL),
 CHECK(applicability_precision<>'exact_variant' OR variant_id IS NOT NULL)
);
CREATE TABLE IF NOT EXISTS technical_document_applicability (
 technical_document_id INTEGER NOT NULL REFERENCES technical_documents(technical_document_id) ON DELETE CASCADE,
 applicability_id INTEGER NOT NULL REFERENCES technical_applicability(applicability_id) ON DELETE RESTRICT,
 is_primary INTEGER NOT NULL DEFAULT 0 CHECK(is_primary IN(0,1)), note TEXT,
 PRIMARY KEY(technical_document_id,applicability_id)
);
CREATE TABLE IF NOT EXISTS technical_records (
 technical_record_id INTEGER PRIMARY KEY,
 technical_document_id INTEGER NOT NULL, applicability_id INTEGER NOT NULL,
 record_kind TEXT NOT NULL CHECK(record_kind IN('diagnostic_test_plan','repair_procedure','wiring_diagram','ecu_pinout','torque_specification','adaptation','service_interval','ecu_profile','oem_part')),
 record_revision TEXT NOT NULL,
 record_sha256 TEXT NOT NULL CHECK(length(record_sha256)=64 AND record_sha256 NOT GLOB '*[^a-f0-9]*'),
 payload_json TEXT NOT NULL CHECK(json_valid(payload_json) AND json_type(payload_json)='object'),
 dtc_namespace TEXT CHECK(dtc_namespace IS NULL OR dtc_namespace IN('generic_sae_iso','manufacturer_specific_vag','manufacturer_specific_other','unknown')),
 oem_dtc_id INTEGER REFERENCES oem_dtc_index(oem_dtc_id) ON DELETE RESTRICT,
 review_status TEXT NOT NULL DEFAULT 'candidate' CHECK(review_status IN('candidate','source_checked','technically_verified','publication_approved','rejected')),
 created_at_utc TEXT NOT NULL,
 UNIQUE(technical_document_id,applicability_id,record_kind,record_revision),
 FOREIGN KEY(technical_document_id,applicability_id) REFERENCES technical_document_applicability(technical_document_id,applicability_id) ON DELETE RESTRICT,
 CHECK(oem_dtc_id IS NULL OR dtc_namespace IS NOT NULL),
 CHECK(record_kind='diagnostic_test_plan' OR(dtc_namespace IS NULL AND oem_dtc_id IS NULL))
);
CREATE INDEX IF NOT EXISTS idx_technical_documents_source ON technical_documents(source_document_id,review_status);
CREATE INDEX IF NOT EXISTS idx_technical_applicability_vehicle ON technical_applicability(variant_id,engine_id,transmission_id,ecu_identity_id);
CREATE INDEX IF NOT EXISTS idx_technical_applicability_market_year ON technical_applicability(market_scope,model_year_from,model_year_to);
CREATE INDEX IF NOT EXISTS idx_technical_records_kind_status ON technical_records(record_kind,review_status);
CREATE INDEX IF NOT EXISTS idx_technical_records_applicability ON technical_records(applicability_id,record_kind);
CREATE INDEX IF NOT EXISTS idx_technical_records_dtc ON technical_records(dtc_namespace,oem_dtc_id);
CREATE INDEX IF NOT EXISTS idx_technical_torque_component ON technical_records(json_extract(payload_json,'$.component')) WHERE record_kind='torque_specification';
CREATE INDEX IF NOT EXISTS idx_technical_pinout_connector ON technical_records(json_extract(payload_json,'$.connector_id'),json_extract(payload_json,'$.pin_number')) WHERE record_kind='ecu_pinout';
CREATE INDEX IF NOT EXISTS idx_technical_service_item ON technical_records(json_extract(payload_json,'$.service_item')) WHERE record_kind='service_interval';
CREATE INDEX IF NOT EXISTS idx_technical_oem_part_number ON technical_records(json_extract(payload_json,'$.part_number')) WHERE record_kind='oem_part';
CREATE TRIGGER IF NOT EXISTS technical_applicability_publication_guard
BEFORE UPDATE OF review_status ON technical_applicability WHEN NEW.review_status='publication_approved'
BEGIN
 SELECT CASE
 WHEN NEW.market_scope='UNKNOWN' OR NEW.applicability_precision IN('model_year_only','generic_only','unknown')
 THEN RAISE(ABORT,'technical applicability is too broad for publication')
 WHEN NEW.applicability_source_document_id IS NOT NULL AND NOT EXISTS(
  SELECT 1 FROM source_documents sd JOIN technical_source_rights r ON r.source_document_id=sd.source_document_id
  WHERE sd.source_document_id=NEW.applicability_source_document_id AND sd.license_status IN('cc0','public_domain','open_license','permission_granted')
  AND sd.redistribution_allowed=1 AND r.rights_status='approved' AND r.display_allowed=1 AND r.offline_cache_allowed=1
  AND r.bulk_reuse_allowed=1 AND r.redistribution_allowed=1 AND r.store_structured_data_allowed=1)
 THEN RAISE(ABORT,'applicability evidence source rights are not approved for offline structured data')
 WHEN NEW.vehicle_catalog_evidence_id IS NOT NULL AND NOT EXISTS(
  SELECT 1 FROM vehicle_catalog_evidence e
  JOIN vehicle_catalog_sources s ON s.source_id=e.source_id
  JOIN vehicle_catalog_source_rights r ON r.source_id=e.source_id
  WHERE e.evidence_id=NEW.vehicle_catalog_evidence_id
  AND e.review_status='publication_approved' AND e.source_sha256 IS NOT NULL AND e.source_sha256 NOT GLOB '*[^a-f0-9]*'
  AND s.license_status IN('cc0','public_domain','open_license','permission_granted') AND s.redistribution_allowed=1
  AND r.rights_status='approved' AND r.display_allowed=1 AND r.offline_cache_allowed=1
  AND r.bulk_reuse_allowed=1 AND r.redistribution_allowed=1 AND r.store_structured_data_allowed=1)
 THEN RAISE(ABORT,'vehicle catalog applicability evidence or its offline reuse rights are not approved')
 WHEN NEW.applicability_precision='engine_transmission_variant' AND NOT EXISTS(
  SELECT 1 FROM powertrain_pair_evidence p
  JOIN vehicle_catalog_evidence e ON e.evidence_id=p.evidence_id
  JOIN vehicle_variants v ON v.variant_id=p.variant_id
  JOIN engine_codes ec ON ec.engine_id=p.engine_id
  JOIN transmission_codes tc ON tc.transmission_id=p.transmission_id
  WHERE p.pair_id=NEW.pair_evidence_id AND p.variant_id=NEW.variant_id AND p.engine_id=NEW.engine_id
  AND p.transmission_id=NEW.transmission_id AND e.evidence_id=NEW.vehicle_catalog_evidence_id
  AND e.claim_type='engine_transmission_pair' AND e.review_status='publication_approved'
  AND e.source_sha256 IS NOT NULL AND v.status='published' AND v.market_scope=NEW.market_scope
  AND ec.status='published' AND tc.status='published')
 THEN RAISE(ABORT,'exact engine/transmission applicability requires a published variant, engine, transmission and approved pair evidence')
 WHEN NEW.applicability_precision='exact_vin' AND NOT EXISTS(
  SELECT 1 FROM vehicle_catalog_evidence e WHERE e.evidence_id=NEW.vehicle_catalog_evidence_id
  AND e.claim_type='vin_range' AND e.review_status='publication_approved')
 THEN RAISE(ABORT,'exact VIN applicability requires a published VIN-range evidence record')
 WHEN NEW.applicability_precision='exact_ecu_hw_sw' AND(
  NOT EXISTS(SELECT 1 FROM ecu_identities e WHERE e.ecu_identity_id=NEW.ecu_identity_id AND e.identity_status='exact')
  OR(NEW.vehicle_catalog_evidence_id IS NOT NULL AND NOT EXISTS(
   SELECT 1 FROM vehicle_catalog_evidence e WHERE e.evidence_id=NEW.vehicle_catalog_evidence_id AND e.claim_type='ecu_fitment')))
 THEN RAISE(ABORT,'exact ECU applicability requires exact hardware/software identity and ECU-fitment evidence')
 WHEN NEW.applicability_precision='exact_variant' AND(
  NOT EXISTS(SELECT 1 FROM vehicle_variants v WHERE v.variant_id=NEW.variant_id AND v.status='published' AND v.market_scope=NEW.market_scope)
  OR(NEW.vehicle_catalog_evidence_id IS NOT NULL AND NOT EXISTS(
   SELECT 1 FROM vehicle_catalog_evidence e WHERE e.evidence_id=NEW.vehicle_catalog_evidence_id AND e.claim_type IN('variant','other'))))
 THEN RAISE(ABORT,'exact variant applicability requires a published variant and matching evidence in the same market scope')
 END;
END;
CREATE TRIGGER IF NOT EXISTS technical_document_publication_guard
BEFORE UPDATE OF review_status ON technical_documents WHEN NEW.review_status='publication_approved'
BEGIN
 SELECT CASE
 WHEN NOT EXISTS(
  SELECT 1 FROM source_documents sd JOIN technical_source_rights r ON r.source_document_id=sd.source_document_id
  WHERE sd.source_document_id=NEW.source_document_id AND sd.license_status IN('cc0','public_domain','open_license','permission_granted')
  AND sd.redistribution_allowed=1 AND r.rights_status='approved' AND r.display_allowed=1
  AND r.offline_cache_allowed=1 AND r.bulk_reuse_allowed=1 AND r.redistribution_allowed=1
  AND((NEW.content_storage_mode='reference_only')
   OR(NEW.content_storage_mode='text' AND r.store_text_allowed=1)
   OR(NEW.content_storage_mode='diagram' AND r.store_diagrams_allowed=1)
   OR(NEW.content_storage_mode='structured_only' AND r.store_structured_data_allowed=1)
   OR(NEW.content_storage_mode='mixed' AND r.store_text_allowed=1 AND r.store_diagrams_allowed=1 AND r.store_structured_data_allowed=1))
  AND(NEW.content_storage_mode='reference_only' OR sd.source_sha256 IS NOT NULL))
 THEN RAISE(ABORT,'technical document source rights are not approved for its storage mode')
 WHEN NOT EXISTS(
  SELECT 1 FROM technical_document_applicability da JOIN technical_applicability a ON a.applicability_id=da.applicability_id
  WHERE da.technical_document_id=NEW.technical_document_id AND a.review_status='publication_approved'
  AND(NEW.market_scope='MULTI' OR NEW.market_scope=a.market_scope))
 THEN RAISE(ABORT,'technical document needs at least one publication-approved applicability record')
 END;
END;
CREATE TRIGGER IF NOT EXISTS technical_record_insert_guard
BEFORE INSERT ON technical_records
BEGIN
 SELECT CASE
 WHEN NOT EXISTS(SELECT 1 FROM technical_documents d WHERE d.technical_document_id=NEW.technical_document_id
  AND(d.technical_kind=NEW.record_kind OR d.technical_kind='other' OR(d.technical_kind='oem_parts_catalog' AND NEW.record_kind='oem_part')))
 THEN RAISE(ABORT,'technical record kind must match its source document kind')
 WHEN NOT EXISTS(
  SELECT 1 FROM technical_documents d JOIN technical_source_rights r ON r.source_document_id=d.source_document_id
  WHERE d.technical_document_id=NEW.technical_document_id AND r.rights_status='approved'
  AND r.display_allowed=1 AND r.offline_cache_allowed=1 AND r.bulk_reuse_allowed=1 AND r.redistribution_allowed=1
  AND((NEW.record_kind IN('diagnostic_test_plan','repair_procedure') AND r.store_text_allowed=1 AND r.store_structured_data_allowed=1)
   OR(NEW.record_kind='wiring_diagram' AND r.store_diagrams_allowed=1 AND r.store_structured_data_allowed=1)
   OR(NEW.record_kind IN('ecu_pinout','torque_specification','service_interval','ecu_profile','oem_part') AND r.store_structured_data_allowed=1)
   OR(NEW.record_kind='adaptation' AND r.store_text_allowed=1 AND r.store_structured_data_allowed=1)))
 THEN RAISE(ABORT,'technical record cannot be stored without the required source rights')
 WHEN NEW.oem_dtc_id IS NOT NULL AND NOT EXISTS(
  SELECT 1 FROM oem_dtc_index d WHERE d.oem_dtc_id=NEW.oem_dtc_id AND d.dtc_namespace=NEW.dtc_namespace)
 THEN RAISE(ABORT,'diagnostic record namespace must match linked DTC namespace')
 END;
END;
CREATE TRIGGER IF NOT EXISTS technical_record_publication_guard
BEFORE UPDATE OF review_status ON technical_records WHEN NEW.review_status='publication_approved'
BEGIN
 SELECT CASE
 WHEN NOT EXISTS(SELECT 1 FROM technical_documents d WHERE d.technical_document_id=NEW.technical_document_id AND d.review_status='publication_approved')
 THEN RAISE(ABORT,'technical record document is not publication approved')
 WHEN NOT EXISTS(
  SELECT 1 FROM technical_applicability a JOIN technical_document_applicability da ON da.applicability_id=a.applicability_id
  WHERE a.applicability_id=NEW.applicability_id AND da.technical_document_id=NEW.technical_document_id
  AND a.review_status='publication_approved')
 THEN RAISE(ABORT,'technical record applicability is not publication approved for this document')
 WHEN NEW.record_kind='diagnostic_test_plan' AND NEW.dtc_namespace='unknown'
 THEN RAISE(ABORT,'unknown DTC namespace cannot be published')
 END;
END;
CREATE TRIGGER IF NOT EXISTS technical_documents_provenance_immutable
BEFORE UPDATE OF source_document_id,technical_kind,title,document_revision,issue_date,language,market_scope,
 content_storage_mode,content_resource_key,content_sha256,created_at_utc ON technical_documents
BEGIN SELECT RAISE(ABORT,'technical document provenance is immutable; create a new document revision'); END;
CREATE TRIGGER IF NOT EXISTS technical_applicability_provenance_immutable
BEFORE UPDATE OF applicability_source_document_id,vehicle_catalog_evidence_id,variant_id,engine_id,transmission_id,
 pair_evidence_id,ecu_identity_id,market_scope,model_year_from,model_year_to,production_date_from,production_date_to,
 applicability_precision,evidence_locator,evidence_sha256 ON technical_applicability
BEGIN SELECT RAISE(ABORT,'technical applicability evidence is immutable; create a new applicability revision'); END;
CREATE TRIGGER IF NOT EXISTS technical_records_provenance_immutable
BEFORE UPDATE OF technical_document_id,applicability_id,record_kind,record_revision,record_sha256,payload_json,
 dtc_namespace,oem_dtc_id,created_at_utc ON technical_records
BEGIN SELECT RAISE(ABORT,'technical record provenance is immutable; create a new record revision'); END;
CREATE VIEW IF NOT EXISTS v_published_technical_records AS
SELECT tr.technical_record_id,tr.record_kind,tr.record_revision,tr.record_sha256,tr.payload_json,tr.dtc_namespace,tr.oem_dtc_id,
 d.technical_document_id,d.technical_kind,d.title,d.document_revision,d.source_document_id,sd.source_id,sd.publisher,sd.source_url,sd.source_sha256,
 a.applicability_id,a.market_scope,a.applicability_precision,a.variant_id,a.engine_id,a.transmission_id,a.ecu_identity_id,
 a.model_year_from,a.model_year_to,a.evidence_locator,a.evidence_sha256
FROM technical_records tr JOIN technical_documents d ON d.technical_document_id=tr.technical_document_id
JOIN source_documents sd ON sd.source_document_id=d.source_document_id
JOIN technical_source_rights dr ON dr.source_document_id=d.source_document_id
JOIN technical_applicability a ON a.applicability_id=tr.applicability_id
LEFT JOIN source_documents asd ON asd.source_document_id=a.applicability_source_document_id
LEFT JOIN technical_source_rights ar ON ar.source_document_id=asd.source_document_id
LEFT JOIN vehicle_catalog_evidence ve ON ve.evidence_id=a.vehicle_catalog_evidence_id
LEFT JOIN vehicle_catalog_sources vcs ON vcs.source_id=ve.source_id
LEFT JOIN vehicle_catalog_source_rights vr ON vr.source_id=ve.source_id
WHERE tr.review_status='publication_approved' AND d.review_status='publication_approved' AND a.review_status='publication_approved'
AND sd.license_status IN('cc0','public_domain','open_license','permission_granted') AND sd.redistribution_allowed=1
AND dr.rights_status='approved' AND dr.display_allowed=1 AND dr.offline_cache_allowed=1
AND dr.bulk_reuse_allowed=1 AND dr.redistribution_allowed=1
AND ((d.content_storage_mode='reference_only')
 OR (d.content_storage_mode='text' AND dr.store_text_allowed=1)
 OR (d.content_storage_mode='diagram' AND dr.store_diagrams_allowed=1)
 OR (d.content_storage_mode='structured_only' AND dr.store_structured_data_allowed=1)
 OR (d.content_storage_mode='mixed' AND dr.store_text_allowed=1 AND dr.store_diagrams_allowed=1 AND dr.store_structured_data_allowed=1))
AND (
 (a.applicability_source_document_id IS NOT NULL
  AND asd.license_status IN('cc0','public_domain','open_license','permission_granted') AND asd.redistribution_allowed=1
  AND ar.rights_status='approved' AND ar.display_allowed=1 AND ar.offline_cache_allowed=1 AND ar.bulk_reuse_allowed=1
  AND ar.redistribution_allowed=1 AND ar.store_structured_data_allowed=1)
 OR
 (a.vehicle_catalog_evidence_id IS NOT NULL
  AND vcs.license_status IN('cc0','public_domain','open_license','permission_granted') AND vcs.redistribution_allowed=1
  AND vr.rights_status='approved' AND vr.display_allowed=1 AND vr.offline_cache_allowed=1 AND vr.bulk_reuse_allowed=1
  AND vr.redistribution_allowed=1 AND vr.store_structured_data_allowed=1)
);
CREATE VIEW IF NOT EXISTS v_generic_dtc_test_plans AS
SELECT * FROM v_published_technical_records WHERE record_kind='diagnostic_test_plan' AND dtc_namespace='generic_sae_iso';
CREATE VIEW IF NOT EXISTS v_vag_specific_dtc_test_plans AS
SELECT * FROM v_published_technical_records WHERE record_kind='diagnostic_test_plan' AND dtc_namespace='manufacturer_specific_vag';


-- Fail closed: publication checks are implemented on UPDATE; direct INSERT must not bypass them.
CREATE TRIGGER IF NOT EXISTS technical_applicability_publication_insert_requires_guarded_transition
BEFORE INSERT ON technical_applicability
WHEN NEW.review_status='publication_approved'
BEGIN
 SELECT RAISE(ABORT,'technical applicability publication must use guarded review-status transition');
END;
CREATE TRIGGER IF NOT EXISTS technical_document_publication_insert_requires_guarded_transition
BEFORE INSERT ON technical_documents
WHEN NEW.review_status='publication_approved'
BEGIN
 SELECT RAISE(ABORT,'technical document publication must use guarded review-status transition');
END;
CREATE TRIGGER IF NOT EXISTS technical_record_publication_insert_requires_guarded_transition
BEFORE INSERT ON technical_records
WHEN NEW.review_status='publication_approved'
BEGIN
 SELECT RAISE(ABORT,'technical record publication must use guarded review-status transition');
END;


-- Current source rights are checked on every publication lookup. A rights change
-- demotes affected vehicle evidence so previously published fitment cannot remain active.
CREATE TRIGGER IF NOT EXISTS demote_vehicle_catalog_after_technical_rights_narrowing
AFTER UPDATE OF rights_status, commercial_use_allowed, display_allowed,
                offline_cache_allowed, bulk_reuse_allowed, redistribution_allowed,
                store_structured_data_allowed
ON vehicle_catalog_source_rights
WHEN NEW.rights_status<>'approved'
  OR NEW.commercial_use_allowed<>1
  OR NEW.display_allowed<>1
  OR NEW.offline_cache_allowed<>1
  OR NEW.bulk_reuse_allowed<>1
  OR NEW.redistribution_allowed<>1
  OR NEW.store_structured_data_allowed<>1
BEGIN
  UPDATE vehicle_catalog_evidence
  SET review_status='candidate', reviewed_at_utc=NULL,
      reviewer_note='Source rights were revoked or narrowed; evidence returned to candidate status.'
  WHERE source_id=NEW.source_id
    AND review_status IN ('source_checked','technically_verified','publication_approved');
END;

CREATE TRIGGER IF NOT EXISTS demote_vehicle_catalog_after_technical_rights_deletion
AFTER DELETE ON vehicle_catalog_source_rights
BEGIN
  UPDATE vehicle_catalog_evidence
  SET review_status='candidate', reviewed_at_utc=NULL,
      reviewer_note='Source rights record was deleted; evidence returned to candidate status.'
  WHERE source_id=OLD.source_id
    AND review_status IN ('source_checked','technically_verified','publication_approved');
END;

CREATE TRIGGER IF NOT EXISTS restrict_vehicle_catalog_rights_after_source_restriction
AFTER UPDATE OF license_status, redistribution_allowed ON vehicle_catalog_sources
WHEN NEW.redistribution_allowed<>1
  OR NEW.license_status NOT IN ('cc0','public_domain','open_license','permission_granted')
BEGIN
  UPDATE vehicle_catalog_source_rights
  SET rights_status='restricted'
  WHERE source_id=NEW.source_id AND rights_status='approved';
END;

PRAGMA foreign_keys = ON;

-- Licensed EAEU type-approval evidence only.
-- OTTS engine/gearbox/ECU markings are descriptors, never factory-code or exact-vehicle fitment.
-- Apply after data/sql/vehicle-catalog.sql.

CREATE TABLE IF NOT EXISTS vehicle_catalog_source_rights (
  source_id TEXT PRIMARY KEY REFERENCES vehicle_catalog_sources(source_id) ON DELETE CASCADE,
  rights_status TEXT NOT NULL DEFAULT 'permission_required'
    CHECK (rights_status IN ('permission_required','approved','restricted','expired')),
  license_name TEXT,
  license_url TEXT,
  license_text_sha256 TEXT CHECK (
    license_text_sha256 IS NULL OR
    (length(license_text_sha256)=64 AND lower(license_text_sha256) NOT GLOB '*[^0-9a-f]*')
  ),
  commercial_use_allowed INTEGER NOT NULL DEFAULT 0 CHECK (commercial_use_allowed IN (0,1)),
  display_allowed INTEGER NOT NULL DEFAULT 0 CHECK (display_allowed IN (0,1)),
  offline_cache_allowed INTEGER NOT NULL DEFAULT 0 CHECK (offline_cache_allowed IN (0,1)),
  bulk_reuse_allowed INTEGER NOT NULL DEFAULT 0 CHECK (bulk_reuse_allowed IN (0,1)),
  pdf_redistribution_allowed INTEGER NOT NULL DEFAULT 0 CHECK (pdf_redistribution_allowed IN (0,1)),
  attribution_required INTEGER NOT NULL DEFAULT 0 CHECK (attribution_required IN (0,1)),
  attribution_text TEXT,
  permission_reference TEXT,
  rights_revision TEXT,
  reviewed_at_utc TEXT,
  CHECK (attribution_required=0 OR length(trim(coalesce(attribution_text,'')))>0)
);

CREATE TRIGGER IF NOT EXISTS validate_source_rights_approval_insert
BEFORE INSERT ON vehicle_catalog_source_rights
WHEN NEW.rights_status='approved'
BEGIN
  SELECT CASE WHEN NEW.license_name IS NULL OR trim(NEW.license_name)=''
    THEN RAISE(ABORT, 'source rights approval requires a license name') END;
  SELECT CASE WHEN NEW.license_url IS NULL AND NEW.permission_reference IS NULL
    THEN RAISE(ABORT, 'source rights approval requires a license URL or permission reference') END;
  SELECT CASE WHEN NEW.license_text_sha256 IS NULL OR length(NEW.license_text_sha256)<>64
    THEN RAISE(ABORT, 'source rights approval requires a license-text SHA-256') END;
  SELECT CASE WHEN NEW.commercial_use_allowed<>1 OR NEW.display_allowed<>1
      OR NEW.offline_cache_allowed<>1 OR NEW.bulk_reuse_allowed<>1
    THEN RAISE(ABORT, 'source rights approval requires commercial, display, offline-cache and bulk-reuse rights') END;
  SELECT CASE WHEN NEW.rights_revision IS NULL OR trim(NEW.rights_revision)=''
      OR NEW.reviewed_at_utc IS NULL OR trim(NEW.reviewed_at_utc)=''
    THEN RAISE(ABORT, 'source rights approval requires a reviewed revision and timestamp') END;
  SELECT CASE WHEN NOT EXISTS (
    SELECT 1 FROM vehicle_catalog_sources s
    WHERE s.source_id=NEW.source_id
      AND s.redistribution_allowed=1
      AND s.license_status IN ('cc0','public_domain','open_license','permission_granted')
  ) THEN RAISE(ABORT, 'source registry does not authorize redistribution') END;
END;

CREATE TRIGGER IF NOT EXISTS validate_source_rights_approval_update
BEFORE UPDATE ON vehicle_catalog_source_rights
WHEN NEW.rights_status='approved'
BEGIN
  SELECT CASE WHEN NEW.license_name IS NULL OR trim(NEW.license_name)=''
    THEN RAISE(ABORT, 'source rights approval requires a license name') END;
  SELECT CASE WHEN NEW.license_url IS NULL AND NEW.permission_reference IS NULL
    THEN RAISE(ABORT, 'source rights approval requires a license URL or permission reference') END;
  SELECT CASE WHEN NEW.license_text_sha256 IS NULL OR length(NEW.license_text_sha256)<>64
    THEN RAISE(ABORT, 'source rights approval requires a license-text SHA-256') END;
  SELECT CASE WHEN NEW.commercial_use_allowed<>1 OR NEW.display_allowed<>1
      OR NEW.offline_cache_allowed<>1 OR NEW.bulk_reuse_allowed<>1
    THEN RAISE(ABORT, 'source rights approval requires commercial, display, offline-cache and bulk-reuse rights') END;
  SELECT CASE WHEN NEW.rights_revision IS NULL OR trim(NEW.rights_revision)=''
      OR NEW.reviewed_at_utc IS NULL OR trim(NEW.reviewed_at_utc)=''
    THEN RAISE(ABORT, 'source rights approval requires a reviewed revision and timestamp') END;
  SELECT CASE WHEN NOT EXISTS (
    SELECT 1 FROM vehicle_catalog_sources s
    WHERE s.source_id=NEW.source_id
      AND s.redistribution_allowed=1
      AND s.license_status IN ('cc0','public_domain','open_license','permission_granted')
  ) THEN RAISE(ABORT, 'source registry does not authorize redistribution') END;
END;

CREATE TABLE IF NOT EXISTS eaeu_otts_evidence (
  approval_evidence_id INTEGER PRIMARY KEY,
  source_id TEXT NOT NULL REFERENCES vehicle_catalog_sources(source_id),
  member_state TEXT NOT NULL CHECK (member_state IN ('RU','BY','KZ','AM','KG','UNKNOWN')),
  approval_document_type TEXT NOT NULL CHECK (approval_document_type IN ('OTTS','EOTTS','OTSH','EOTSH','UNKNOWN')),
  approval_number TEXT NOT NULL CHECK (length(trim(approval_number))>0),
  source_record_key TEXT NOT NULL CHECK (length(trim(source_record_key))>0),
  approval_revision TEXT,
  form_revision TEXT NOT NULL CHECK (length(trim(form_revision))>0),
  issue_date TEXT,
  valid_from TEXT,
  valid_to TEXT,
  manufacturer TEXT,
  make TEXT,
  commercial_name TEXT,
  vehicle_type TEXT,
  base_vehicle_or_chassis TEXT,
  modifications TEXT,
  vehicle_category TEXT,
  environmental_class TEXT,
  assembly_plant TEXT,
  approval_scope_note TEXT,
  engine_make_type_descriptor TEXT,
  engine_displacement_cc INTEGER CHECK (engine_displacement_cc IS NULL OR engine_displacement_cc>=0),
  engine_fuel_type TEXT,
  engine_control_unit_marking TEXT,
  fuel_pump_marking TEXT,
  injector_marking TEXT,
  transmission_type_descriptor TEXT,
  clutch_make_type_descriptor TEXT,
  gearbox_make_type_descriptor TEXT,
  gearbox_gear_count INTEGER CHECK (gearbox_gear_count IS NULL OR gearbox_gear_count>=0),
  gearbox_ratios_json TEXT NOT NULL DEFAULT '[]',
  transfer_case_type_descriptor TEXT,
  transfer_case_ratios_json TEXT NOT NULL DEFAULT '[]',
  final_drive_type_descriptor TEXT,
  final_drive_ratios_json TEXT NOT NULL DEFAULT '[]',
  market_scope TEXT NOT NULL CHECK (market_scope IN ('RU','EAEU','EU','NAR','CN','ROW','MULTI','UNKNOWN')),
  applicability_precision TEXT NOT NULL DEFAULT 'type_approval_descriptor'
    CHECK (applicability_precision='type_approval_descriptor'),
  evidence_locator TEXT NOT NULL CHECK (length(trim(evidence_locator))>0),
  source_url TEXT NOT NULL CHECK (length(trim(source_url))>0),
  document_reference_url TEXT,
  document_cached INTEGER NOT NULL DEFAULT 0 CHECK (document_cached IN (0,1)),
  document_sha256 TEXT CHECK (
    document_sha256 IS NULL OR
    (length(document_sha256)=64 AND lower(document_sha256) NOT GLOB '*[^0-9a-f]*')
  ),
  source_revision TEXT NOT NULL CHECK (length(trim(source_revision))>0),
  source_snapshot_sha256 TEXT NOT NULL CHECK (
    length(source_snapshot_sha256)=64 AND lower(source_snapshot_sha256) NOT GLOB '*[^0-9a-f]*'
  ),
  record_sha256 TEXT NOT NULL CHECK (
    length(record_sha256)=64 AND lower(record_sha256) NOT GLOB '*[^0-9a-f]*'
  ),
  retrieved_at_utc TEXT NOT NULL,
  review_status TEXT NOT NULL DEFAULT 'candidate'
    CHECK (review_status IN ('candidate','source_checked','technically_verified','publication_approved','rejected')),
  reviewed_at_utc TEXT,
  review_note TEXT,
  UNIQUE(source_id, member_state, approval_number, source_record_key, source_revision),
  CHECK (valid_from IS NULL OR valid_to IS NULL OR valid_from<=valid_to),
  CHECK (
    (document_cached=0 AND document_sha256 IS NULL) OR
    (document_cached=1 AND document_sha256 IS NOT NULL AND document_reference_url IS NOT NULL)
  )
);

CREATE INDEX IF NOT EXISTS idx_eaeu_otts_approval_number
  ON eaeu_otts_evidence(member_state, approval_number, approval_revision);
CREATE INDEX IF NOT EXISTS idx_eaeu_otts_make_model
  ON eaeu_otts_evidence(market_scope, make, commercial_name);
CREATE INDEX IF NOT EXISTS idx_eaeu_otts_review
  ON eaeu_otts_evidence(review_status, applicability_precision);

-- New evidence is always quarantined as a candidate; callers cannot insert pre-reviewed rows.
CREATE TRIGGER IF NOT EXISTS prevent_non_candidate_otts_evidence_insert
BEFORE INSERT ON eaeu_otts_evidence
WHEN NEW.review_status <> 'candidate'
BEGIN
  SELECT RAISE(ABORT, 'new OTTS evidence must enter as candidate');
END;

-- Enforce an explicit, auditable review state machine. Rights revocation may always demote to candidate.
CREATE TRIGGER IF NOT EXISTS validate_otts_evidence_review_transition
BEFORE UPDATE OF review_status ON eaeu_otts_evidence
WHEN NEW.review_status <> OLD.review_status
BEGIN
  SELECT CASE WHEN NOT (
    NEW.review_status='candidate'
    OR (OLD.review_status='candidate' AND NEW.review_status IN ('source_checked','rejected'))
    OR (OLD.review_status='source_checked' AND NEW.review_status IN ('technically_verified','rejected'))
    OR (OLD.review_status='technically_verified' AND NEW.review_status IN ('publication_approved','rejected'))
    OR (OLD.review_status='publication_approved' AND NEW.review_status='rejected')
    OR (OLD.review_status='rejected' AND NEW.review_status='candidate')
  ) THEN RAISE(ABORT, 'invalid OTTS review-state transition') END;

  SELECT CASE WHEN NEW.review_status IN
      ('source_checked','technically_verified','publication_approved','rejected')
      AND (NEW.reviewed_at_utc IS NULL OR trim(NEW.reviewed_at_utc)=''
        OR NEW.review_note IS NULL OR trim(NEW.review_note)='')
    THEN RAISE(ABORT, 'OTTS review transition requires a timestamp and review note') END;
END;

-- Published source facts are immutable. Demote to candidate before correcting a record, then re-review it.
CREATE TRIGGER IF NOT EXISTS prevent_published_otts_evidence_mutation
BEFORE UPDATE ON eaeu_otts_evidence
WHEN OLD.review_status='publication_approved'
  AND NEW.review_status='publication_approved'
  AND (
    NEW.source_id IS NOT OLD.source_id
    OR NEW.member_state IS NOT OLD.member_state
    OR NEW.approval_document_type IS NOT OLD.approval_document_type
    OR NEW.approval_number IS NOT OLD.approval_number
    OR NEW.source_record_key IS NOT OLD.source_record_key
    OR NEW.approval_revision IS NOT OLD.approval_revision
    OR NEW.form_revision IS NOT OLD.form_revision
    OR NEW.issue_date IS NOT OLD.issue_date
    OR NEW.valid_from IS NOT OLD.valid_from
    OR NEW.valid_to IS NOT OLD.valid_to
    OR NEW.manufacturer IS NOT OLD.manufacturer
    OR NEW.make IS NOT OLD.make
    OR NEW.commercial_name IS NOT OLD.commercial_name
    OR NEW.vehicle_type IS NOT OLD.vehicle_type
    OR NEW.base_vehicle_or_chassis IS NOT OLD.base_vehicle_or_chassis
    OR NEW.modifications IS NOT OLD.modifications
    OR NEW.vehicle_category IS NOT OLD.vehicle_category
    OR NEW.environmental_class IS NOT OLD.environmental_class
    OR NEW.assembly_plant IS NOT OLD.assembly_plant
    OR NEW.approval_scope_note IS NOT OLD.approval_scope_note
    OR NEW.engine_make_type_descriptor IS NOT OLD.engine_make_type_descriptor
    OR NEW.engine_displacement_cc IS NOT OLD.engine_displacement_cc
    OR NEW.engine_fuel_type IS NOT OLD.engine_fuel_type
    OR NEW.engine_control_unit_marking IS NOT OLD.engine_control_unit_marking
    OR NEW.fuel_pump_marking IS NOT OLD.fuel_pump_marking
    OR NEW.injector_marking IS NOT OLD.injector_marking
    OR NEW.transmission_type_descriptor IS NOT OLD.transmission_type_descriptor
    OR NEW.clutch_make_type_descriptor IS NOT OLD.clutch_make_type_descriptor
    OR NEW.gearbox_make_type_descriptor IS NOT OLD.gearbox_make_type_descriptor
    OR NEW.gearbox_gear_count IS NOT OLD.gearbox_gear_count
    OR NEW.gearbox_ratios_json IS NOT OLD.gearbox_ratios_json
    OR NEW.transfer_case_type_descriptor IS NOT OLD.transfer_case_type_descriptor
    OR NEW.transfer_case_ratios_json IS NOT OLD.transfer_case_ratios_json
    OR NEW.final_drive_type_descriptor IS NOT OLD.final_drive_type_descriptor
    OR NEW.final_drive_ratios_json IS NOT OLD.final_drive_ratios_json
    OR NEW.market_scope IS NOT OLD.market_scope
    OR NEW.applicability_precision IS NOT OLD.applicability_precision
    OR NEW.evidence_locator IS NOT OLD.evidence_locator
    OR NEW.source_url IS NOT OLD.source_url
    OR NEW.document_reference_url IS NOT OLD.document_reference_url
    OR NEW.document_cached IS NOT OLD.document_cached
    OR NEW.document_sha256 IS NOT OLD.document_sha256
    OR NEW.source_revision IS NOT OLD.source_revision
    OR NEW.source_snapshot_sha256 IS NOT OLD.source_snapshot_sha256
    OR NEW.record_sha256 IS NOT OLD.record_sha256
    OR NEW.retrieved_at_utc IS NOT OLD.retrieved_at_utc
  )
BEGIN
  SELECT RAISE(ABORT, 'published OTTS evidence is immutable; demote to candidate before editing');
END;

-- Data may enter this table only when all rights required for offline product use are approved.
CREATE TRIGGER IF NOT EXISTS prevent_unlicensed_otts_evidence_insert
BEFORE INSERT ON eaeu_otts_evidence
WHEN NOT EXISTS (
  SELECT 1
  FROM vehicle_catalog_sources s
  JOIN vehicle_catalog_source_rights r ON r.source_id=s.source_id
  WHERE s.source_id=NEW.source_id
    AND s.redistribution_allowed=1
    AND s.license_status IN ('cc0','public_domain','open_license','permission_granted')
    AND r.rights_status='approved'
    AND r.commercial_use_allowed=1
    AND r.display_allowed=1
    AND r.offline_cache_allowed=1
    AND r.bulk_reuse_allowed=1
    AND (NEW.document_cached=0 OR r.pdf_redistribution_allowed=1)
)
BEGIN
  SELECT RAISE(ABORT, 'OTTS evidence import blocked: commercial display, offline-cache and bulk-reuse rights are not approved');
END;

CREATE TRIGGER IF NOT EXISTS prevent_unlicensed_otts_evidence_update
BEFORE UPDATE OF source_id, document_cached ON eaeu_otts_evidence
WHEN (NEW.source_id IS NOT OLD.source_id OR NEW.document_cached=1)
  AND NOT EXISTS (
    SELECT 1
    FROM vehicle_catalog_sources s
    JOIN vehicle_catalog_source_rights r ON r.source_id=s.source_id
    WHERE s.source_id=NEW.source_id
      AND s.redistribution_allowed=1
      AND s.license_status IN ('cc0','public_domain','open_license','permission_granted')
      AND r.rights_status='approved'
      AND r.commercial_use_allowed=1
      AND r.display_allowed=1
      AND r.offline_cache_allowed=1
      AND r.bulk_reuse_allowed=1
      AND (NEW.document_cached=0 OR r.pdf_redistribution_allowed=1)
  )
BEGIN
  SELECT RAISE(ABORT, 'OTTS evidence update blocked: source rights are not approved');
END;

CREATE TRIGGER IF NOT EXISTS prevent_unapproved_otts_publication
BEFORE UPDATE OF review_status ON eaeu_otts_evidence
WHEN NEW.review_status='publication_approved'
BEGIN
  SELECT CASE WHEN NEW.reviewed_at_utc IS NULL OR trim(NEW.reviewed_at_utc)=''
      OR NEW.review_note IS NULL OR trim(NEW.review_note)=''
    THEN RAISE(ABORT, 'OTTS publication requires a review timestamp and note') END;
  SELECT CASE WHEN OLD.review_status<>'technically_verified'
    THEN RAISE(ABORT, 'OTTS publication requires technical verification first') END;
  SELECT CASE WHEN NEW.market_scope='UNKNOWN' OR NEW.member_state='UNKNOWN'
    THEN RAISE(ABORT, 'OTTS publication requires a known market and issuing member state') END;
  SELECT CASE WHEN NEW.approval_number='' OR NEW.source_record_key=''
      OR NEW.form_revision='' OR NEW.source_revision='' OR NEW.evidence_locator=''
      OR NEW.source_snapshot_sha256 IS NULL OR NEW.record_sha256 IS NULL
    THEN RAISE(ABORT, 'OTTS publication requires exact revision, locator and SHA-256 provenance') END;
  SELECT CASE WHEN NOT EXISTS (
    SELECT 1
    FROM vehicle_catalog_sources s
    JOIN vehicle_catalog_source_rights r ON r.source_id=s.source_id
    WHERE s.source_id=NEW.source_id
      AND s.redistribution_allowed=1
      AND s.license_status IN ('cc0','public_domain','open_license','permission_granted')
      AND r.rights_status='approved'
      AND r.commercial_use_allowed=1
      AND r.display_allowed=1
      AND r.offline_cache_allowed=1
      AND r.bulk_reuse_allowed=1
  ) THEN RAISE(ABORT, 'OTTS publication blocked: source rights are missing or revoked') END;
  SELECT CASE WHEN NEW.document_cached=1 AND NOT EXISTS (
    SELECT 1 FROM vehicle_catalog_source_rights r
    WHERE r.source_id=NEW.source_id AND r.pdf_redistribution_allowed=1
  ) THEN RAISE(ABORT, 'OTTS PDF caching blocked: PDF redistribution rights are not approved') END;
END;

-- Rights narrowing/revocation automatically removes publication eligibility.
CREATE TRIGGER IF NOT EXISTS demote_otts_after_rights_narrowing
AFTER UPDATE OF rights_status, commercial_use_allowed, display_allowed,
                offline_cache_allowed, bulk_reuse_allowed, pdf_redistribution_allowed
ON vehicle_catalog_source_rights
WHEN NEW.rights_status<>'approved'
  OR NEW.commercial_use_allowed<>1
  OR NEW.display_allowed<>1
  OR NEW.offline_cache_allowed<>1
  OR NEW.bulk_reuse_allowed<>1
  OR (NEW.pdf_redistribution_allowed<>1 AND EXISTS (
    SELECT 1 FROM eaeu_otts_evidence e
    WHERE e.source_id=NEW.source_id
      AND e.review_status='publication_approved'
      AND e.document_cached=1
  ))
BEGIN
  UPDATE eaeu_otts_evidence
  SET review_status='candidate',
      reviewed_at_utc=NULL,
      review_note='Source rights were revoked or narrowed; publication eligibility was removed.',
      document_cached=0,
      document_reference_url=NULL,
      document_sha256=NULL
  WHERE source_id=NEW.source_id
    AND (review_status='publication_approved' OR document_cached=1);
END;

CREATE TRIGGER IF NOT EXISTS demote_otts_after_rights_deletion
AFTER DELETE ON vehicle_catalog_source_rights
BEGIN
  UPDATE eaeu_otts_evidence
  SET review_status='candidate',
      reviewed_at_utc=NULL,
      review_note='Source rights record was deleted; publication eligibility was removed.',
      document_cached=0,
      document_reference_url=NULL,
      document_sha256=NULL
  WHERE source_id=OLD.source_id
    AND (review_status='publication_approved' OR document_cached=1);
END;

CREATE TRIGGER IF NOT EXISTS revoke_otts_rights_after_source_restriction
AFTER UPDATE OF license_status, redistribution_allowed ON vehicle_catalog_sources
WHEN NEW.redistribution_allowed<>1
  OR NEW.license_status NOT IN ('cc0','public_domain','open_license','permission_granted')
BEGIN
  UPDATE vehicle_catalog_source_rights
  SET rights_status='restricted', reviewed_at_utc=NULL
  WHERE source_id=NEW.source_id AND rights_status='approved';
END;

-- Rights revocation demotes evidence but retains its immutable links for audit.
-- All workshop queries must join evidence status and current rights before use.
CREATE TRIGGER IF NOT EXISTS demote_vehicle_catalog_after_rights_narrowing
AFTER UPDATE OF rights_status, commercial_use_allowed, display_allowed,
                offline_cache_allowed, bulk_reuse_allowed
ON vehicle_catalog_source_rights
WHEN NEW.rights_status<>'approved'
  OR NEW.commercial_use_allowed<>1
  OR NEW.display_allowed<>1
  OR NEW.offline_cache_allowed<>1
  OR NEW.bulk_reuse_allowed<>1
BEGIN
  UPDATE vehicle_catalog_evidence
  SET review_status='candidate', reviewed_at_utc=NULL,
      reviewer_note='Source rights were revoked or narrowed; evidence returned to candidate status.'
  WHERE source_id=NEW.source_id
    AND review_status IN ('source_checked','technically_verified','publication_approved');
END;

CREATE TRIGGER IF NOT EXISTS demote_vehicle_catalog_after_rights_deletion
AFTER DELETE ON vehicle_catalog_source_rights
BEGIN
  UPDATE vehicle_catalog_evidence
  SET review_status='candidate', reviewed_at_utc=NULL,
      reviewer_note='Source rights record was deleted; evidence returned to candidate status.'
  WHERE source_id=OLD.source_id
    AND review_status IN ('source_checked','technically_verified','publication_approved');
END;

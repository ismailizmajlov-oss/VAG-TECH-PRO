PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS source_documents (
  source_document_id INTEGER PRIMARY KEY,
  source_id TEXT NOT NULL,
  publisher TEXT NOT NULL,
  document_id TEXT NOT NULL,
  document_type TEXT NOT NULL CHECK (
    document_type IN ('dtc_table','diagnostic_test_plan','tpi_tsb','repair_manual',
                      'wiring_diagram','vehicle_data_sheet','other')
  ),
  revision TEXT NOT NULL,
  issue_date TEXT,
  language TEXT,
  market_scope TEXT NOT NULL CHECK (
    market_scope IN ('RU','EAEU','EU','NAR','CN','ROW','MULTI','UNKNOWN')
  ),
  source_url TEXT,
  source_sha256 TEXT CHECK (source_sha256 IS NULL OR length(source_sha256)=64),
  license_status TEXT NOT NULL CHECK (
    license_status IN ('cc0','public_domain','open_license','permission_granted',
                       'proprietary','unknown','permission_required')
  ),
  license_name TEXT,
  reuse_scope TEXT NOT NULL,
  redistribution_allowed INTEGER NOT NULL CHECK (redistribution_allowed IN (0,1)),
  permission_reference TEXT,
  retrieved_at_utc TEXT NOT NULL,
  upstream_revision TEXT,
  UNIQUE(source_id, document_id, revision, market_scope)
);

CREATE TABLE IF NOT EXISTS ecu_identities (
  ecu_identity_id INTEGER PRIMARY KEY,
  supplier TEXT,
  ecu_family TEXT,
  system_name TEXT,
  diagnostic_address TEXT,
  part_number TEXT,
  hardware_number TEXT,
  hardware_version TEXT,
  software_number TEXT,
  software_version TEXT,
  calibration_id TEXT,
  component_string TEXT,
  identity_status TEXT NOT NULL CHECK (
    identity_status IN ('exact','family_only','not_provided','unknown')
  ),
  UNIQUE(supplier, part_number, hardware_number, software_number, calibration_id)
);

CREATE TABLE IF NOT EXISTS oem_dtc_index (
  oem_dtc_id INTEGER PRIMARY KEY,
  dtc_code TEXT NOT NULL CHECK (
    length(dtc_code)=5 AND dtc_code GLOB '[PBCU][0-9A-F][0-9A-F][0-9A-F][0-9A-F]'
  ),
  dtc_namespace TEXT NOT NULL CHECK (
    dtc_namespace IN ('generic_sae_iso','manufacturer_specific_candidate','manufacturer_specific_vag','manufacturer_specific_other','unknown')
  ),
  manufacturer TEXT NOT NULL CHECK (
    manufacturer IN ('VOLKSWAGEN','AUDI','SKODA','SEAT','CUPRA','OTHER','UNKNOWN')
  ),
  market_scope TEXT NOT NULL CHECK (
    market_scope IN ('RU','EAEU','EU','NAR','CN','ROW','UNKNOWN')
  ),
  model TEXT,
  generation_or_type_code TEXT,
  model_year_from INTEGER,
  model_year_to INTEGER,
  production_date_from TEXT,
  production_date_to TEXT,
  engine_code TEXT,
  transmission_code TEXT,
  drive_configuration TEXT,
  pr_codes_json TEXT NOT NULL DEFAULT '[]',
  ecu_identity_id INTEGER REFERENCES ecu_identities(ecu_identity_id),
  source_document_id INTEGER NOT NULL REFERENCES source_documents(source_document_id),
  description TEXT,
  symptoms_json TEXT NOT NULL DEFAULT '[]',
  causes_json TEXT NOT NULL DEFAULT '[]',
  test_plan_reference TEXT,
  evidence_locator TEXT NOT NULL,
  applicability_level TEXT NOT NULL CHECK (
    applicability_level IN ('exact_vin','exact_ecu_hw_sw','engine_transmission_variant',
                            'manufacturer_make_candidate','model_year_only','generic_only','unknown')
  ),
  vin_range_explicit INTEGER NOT NULL DEFAULT 0 CHECK (vin_range_explicit IN (0,1)),
  engine_code_explicit INTEGER NOT NULL DEFAULT 0 CHECK (engine_code_explicit IN (0,1)),
  transmission_code_explicit INTEGER NOT NULL DEFAULT 0 CHECK (transmission_code_explicit IN (0,1)),
  ecu_hw_sw_explicit INTEGER NOT NULL DEFAULT 0 CHECK (ecu_hw_sw_explicit IN (0,1)),
  review_status TEXT NOT NULL DEFAULT 'candidate' CHECK (
    review_status IN ('candidate','source_header_verified','applicability_verified',
                      'engineer_reviewed','publication_approved','rejected')
  ),
  source_claim_hash TEXT NOT NULL CHECK (length(source_claim_hash)=64),
  created_at_utc TEXT NOT NULL,
  UNIQUE(dtc_code, dtc_namespace, manufacturer, market_scope, model,
         generation_or_type_code, engine_code, transmission_code,
         ecu_identity_id, source_document_id, evidence_locator)
);

CREATE TABLE IF NOT EXISTS repair_procedure_references (
  procedure_reference_id INTEGER PRIMARY KEY,
  oem_dtc_id INTEGER NOT NULL REFERENCES oem_dtc_index(oem_dtc_id) ON DELETE CASCADE,
  procedure_id TEXT,
  procedure_revision TEXT,
  steps_reference TEXT,
  wiring_reference TEXT,
  allowed_to_store_steps INTEGER NOT NULL DEFAULT 0 CHECK (allowed_to_store_steps IN (0,1)),
  allowed_to_store_diagrams INTEGER NOT NULL DEFAULT 0 CHECK (allowed_to_store_diagrams IN (0,1)),
  rights_review_note TEXT
);

CREATE INDEX IF NOT EXISTS idx_oem_dtc_code_market
  ON oem_dtc_index(dtc_code, market_scope, manufacturer);
CREATE INDEX IF NOT EXISTS idx_oem_dtc_engine_gearbox
  ON oem_dtc_index(manufacturer, model, engine_code, transmission_code);
CREATE INDEX IF NOT EXISTS idx_oem_dtc_ecu
  ON oem_dtc_index(ecu_identity_id, dtc_code);
CREATE INDEX IF NOT EXISTS idx_oem_dtc_review
  ON oem_dtc_index(review_status, applicability_level);

-- A row cannot be promoted until both technical review and reuse rights are cleared.
CREATE TRIGGER IF NOT EXISTS prevent_unapproved_oem_dtc_publication
BEFORE UPDATE OF review_status ON oem_dtc_index
WHEN NEW.review_status = 'publication_approved'
BEGIN
  SELECT CASE
    WHEN OLD.review_status <> 'engineer_reviewed'
    THEN RAISE(ABORT, 'publication blocked: engineer review must be completed first')
  END;
  SELECT CASE
    WHEN NOT EXISTS (
      SELECT 1 FROM source_documents s
      WHERE s.source_document_id = NEW.source_document_id
        AND s.redistribution_allowed = 1
        AND s.license_status IN ('cc0','public_domain','open_license','permission_granted')
        AND s.source_sha256 IS NOT NULL
        AND s.upstream_revision IS NOT NULL
        AND s.revision <> ''
        AND s.market_scope IN (NEW.market_scope,'MULTI')
    )
    THEN RAISE(ABORT, 'publication blocked: source rights, revision, hash or market scope not cleared')
  END;
  SELECT CASE
    WHEN NEW.evidence_locator = ''
      OR NEW.market_scope = 'UNKNOWN'
      OR NEW.applicability_level NOT IN ('exact_vin','exact_ecu_hw_sw','engine_transmission_variant')
    THEN RAISE(ABORT, 'publication blocked: exact vehicle applicability evidence is required')
  END;
  SELECT CASE
    WHEN NEW.applicability_level = 'exact_vin' AND NEW.vin_range_explicit <> 1
    THEN RAISE(ABORT, 'publication blocked: exact VIN applicability must be explicit')
  END;
  SELECT CASE
    WHEN NEW.applicability_level = 'exact_ecu_hw_sw' AND NEW.ecu_hw_sw_explicit <> 1
    THEN RAISE(ABORT, 'publication blocked: ECU hardware/software applicability must be explicit')
  END;
  SELECT CASE
    WHEN NEW.applicability_level = 'engine_transmission_variant'
      AND (NEW.engine_code_explicit <> 1 OR NEW.transmission_code_explicit <> 1)
    THEN RAISE(ABORT, 'publication blocked: engine and transmission codes must be explicit')
  END;
END;

-- Make-labelled source rows remain candidates until the DTC definition itself is reviewed.
-- Candidate rows cannot carry model, year, engine, gearbox, ECU or PR-code applicability.
CREATE TRIGGER IF NOT EXISTS validate_manufacturer_specific_candidate_insert
BEFORE INSERT ON oem_dtc_index
WHEN NEW.dtc_namespace = 'manufacturer_specific_candidate'
BEGIN
  SELECT CASE
    WHEN NEW.manufacturer NOT IN ('VOLKSWAGEN','AUDI','SKODA','SEAT','CUPRA')
    THEN RAISE(ABORT, 'manufacturer-specific candidate requires a VAG make label')
  END;
  SELECT CASE
    WHEN NEW.market_scope <> 'UNKNOWN'
      OR NEW.applicability_level <> 'manufacturer_make_candidate'
      OR NEW.review_status NOT IN ('candidate','source_header_verified')
    THEN RAISE(ABORT, 'manufacturer-specific candidate must remain make-level and unverified')
  END;
  SELECT CASE
    WHEN NEW.model IS NOT NULL OR NEW.generation_or_type_code IS NOT NULL
      OR NEW.model_year_from IS NOT NULL OR NEW.model_year_to IS NOT NULL
      OR NEW.production_date_from IS NOT NULL OR NEW.production_date_to IS NOT NULL
      OR NEW.engine_code IS NOT NULL OR NEW.transmission_code IS NOT NULL
      OR NEW.drive_configuration IS NOT NULL OR NEW.ecu_identity_id IS NOT NULL
      OR NEW.pr_codes_json <> '[]'
      OR NEW.vin_range_explicit <> 0 OR NEW.engine_code_explicit <> 0
      OR NEW.transmission_code_explicit <> 0 OR NEW.ecu_hw_sw_explicit <> 0
    THEN RAISE(ABORT, 'make-level candidate cannot claim exact vehicle or ECU fitment')
  END;
END;

CREATE TRIGGER IF NOT EXISTS validate_manufacturer_specific_candidate_update
BEFORE UPDATE ON oem_dtc_index
WHEN NEW.dtc_namespace = 'manufacturer_specific_candidate'
BEGIN
  SELECT CASE
    WHEN NEW.manufacturer NOT IN ('VOLKSWAGEN','AUDI','SKODA','SEAT','CUPRA')
    THEN RAISE(ABORT, 'manufacturer-specific candidate requires a VAG make label')
  END;
  SELECT CASE
    WHEN NEW.market_scope <> 'UNKNOWN'
      OR NEW.applicability_level <> 'manufacturer_make_candidate'
      OR NEW.review_status NOT IN ('candidate','source_header_verified')
    THEN RAISE(ABORT, 'manufacturer-specific candidate must remain make-level and unverified')
  END;
  SELECT CASE
    WHEN NEW.model IS NOT NULL OR NEW.generation_or_type_code IS NOT NULL
      OR NEW.model_year_from IS NOT NULL OR NEW.model_year_to IS NOT NULL
      OR NEW.production_date_from IS NOT NULL OR NEW.production_date_to IS NOT NULL
      OR NEW.engine_code IS NOT NULL OR NEW.transmission_code IS NOT NULL
      OR NEW.drive_configuration IS NOT NULL OR NEW.ecu_identity_id IS NOT NULL
      OR NEW.pr_codes_json <> '[]'
      OR NEW.vin_range_explicit <> 0 OR NEW.engine_code_explicit <> 0
      OR NEW.transmission_code_explicit <> 0 OR NEW.ecu_hw_sw_explicit <> 0
    THEN RAISE(ABORT, 'make-level candidate cannot claim exact vehicle or ECU fitment')
  END;
END;

CREATE TRIGGER IF NOT EXISTS validate_manufacturer_specific_vag_make
BEFORE INSERT ON oem_dtc_index
WHEN NEW.dtc_namespace = 'manufacturer_specific_vag'
 AND (
   NEW.manufacturer NOT IN ('VOLKSWAGEN','AUDI','SKODA','SEAT','CUPRA')
   OR NEW.review_status NOT IN ('source_header_verified','applicability_verified','engineer_reviewed')
   OR NEW.applicability_level = 'manufacturer_make_candidate'
 )
BEGIN
  SELECT RAISE(ABORT, 'VAG-specific namespace requires a reviewed VAG source; use candidate namespace otherwise');
END;

CREATE TRIGGER IF NOT EXISTS validate_manufacturer_specific_vag_make_update
BEFORE UPDATE ON oem_dtc_index
WHEN NEW.dtc_namespace = 'manufacturer_specific_vag'
 AND (
   NEW.manufacturer NOT IN ('VOLKSWAGEN','AUDI','SKODA','SEAT','CUPRA')
   OR NEW.review_status = 'candidate'
   OR NEW.applicability_level = 'manufacturer_make_candidate'
 )
BEGIN
  SELECT RAISE(ABORT, 'VAG-specific namespace requires a reviewed VAG source; use candidate namespace otherwise');
END;

CREATE TRIGGER IF NOT EXISTS prevent_unreviewed_candidate_namespace_promotion
BEFORE UPDATE OF dtc_namespace ON oem_dtc_index
WHEN OLD.dtc_namespace = 'manufacturer_specific_candidate'
 AND NEW.dtc_namespace = 'manufacturer_specific_vag'
BEGIN
  SELECT CASE
    WHEN OLD.review_status <> 'source_header_verified'
      OR NEW.review_status NOT IN ('applicability_verified','engineer_reviewed')
    THEN RAISE(ABORT, 'candidate promotion requires source-header and technical applicability review')
  END;
  SELECT CASE
    WHEN NOT EXISTS (
      SELECT 1 FROM source_documents s
      WHERE s.source_document_id = NEW.source_document_id
        AND s.redistribution_allowed = 1
        AND s.license_status IN ('cc0','public_domain','open_license','permission_granted')
        AND s.source_sha256 IS NOT NULL
        AND s.upstream_revision IS NOT NULL
        AND s.revision <> ''
    )
    THEN RAISE(ABORT, 'candidate promotion blocked: source rights and provenance are not cleared')
  END;
END;

-- DTC range ownership is enforced at the namespace boundary.
-- P1xxx, P30xx-P33xx, B1/B2, C1/C2 and U1/U2 are manufacturer-controlled ranges.
CREATE TRIGGER IF NOT EXISTS prevent_generic_code_in_manufacturer_namespace_insert
BEFORE INSERT ON oem_dtc_index
WHEN NEW.dtc_namespace IN ('manufacturer_specific_candidate','manufacturer_specific_vag','manufacturer_specific_other')
 AND NOT (
   substr(NEW.dtc_code,1,2) = 'P1'
   OR (substr(NEW.dtc_code,1,2) = 'P3' AND substr(NEW.dtc_code,3,1) IN ('0','1','2','3'))
   OR substr(NEW.dtc_code,1,2) IN ('B1','B2','C1','C2','U1','U2')
 )
BEGIN
  SELECT RAISE(ABORT, 'generic SAE/ISO code cannot enter a manufacturer-specific namespace');
END;

CREATE TRIGGER IF NOT EXISTS prevent_generic_code_in_manufacturer_namespace_update
BEFORE UPDATE ON oem_dtc_index
WHEN NEW.dtc_namespace IN ('manufacturer_specific_candidate','manufacturer_specific_vag','manufacturer_specific_other')
 AND NOT (
   substr(NEW.dtc_code,1,2) = 'P1'
   OR (substr(NEW.dtc_code,1,2) = 'P3' AND substr(NEW.dtc_code,3,1) IN ('0','1','2','3'))
   OR substr(NEW.dtc_code,1,2) IN ('B1','B2','C1','C2','U1','U2')
 )
BEGIN
  SELECT RAISE(ABORT, 'generic SAE/ISO code cannot enter a manufacturer-specific namespace');
END;

CREATE TRIGGER IF NOT EXISTS prevent_manufacturer_code_in_generic_namespace_insert
BEFORE INSERT ON oem_dtc_index
WHEN NEW.dtc_namespace = 'generic_sae_iso'
 AND (
   substr(NEW.dtc_code,1,2) = 'P1'
   OR (substr(NEW.dtc_code,1,2) = 'P3' AND substr(NEW.dtc_code,3,1) IN ('0','1','2','3'))
   OR substr(NEW.dtc_code,1,2) IN ('B1','B2','C1','C2','U1','U2')
 )
BEGIN
  SELECT RAISE(ABORT, 'manufacturer-controlled code cannot enter the generic SAE/ISO namespace');
END;

CREATE TRIGGER IF NOT EXISTS prevent_manufacturer_code_in_generic_namespace_update
BEFORE UPDATE ON oem_dtc_index
WHEN NEW.dtc_namespace = 'generic_sae_iso'
 AND (
   substr(NEW.dtc_code,1,2) = 'P1'
   OR (substr(NEW.dtc_code,1,2) = 'P3' AND substr(NEW.dtc_code,3,1) IN ('0','1','2','3'))
   OR substr(NEW.dtc_code,1,2) IN ('B1','B2','C1','C2','U1','U2')
 )
BEGIN
  SELECT RAISE(ABORT, 'manufacturer-controlled code cannot enter the generic SAE/ISO namespace');
END;

CREATE TRIGGER IF NOT EXISTS prevent_generic_vag_mislabel_update
BEFORE UPDATE ON oem_dtc_index
WHEN NEW.dtc_namespace = 'generic_sae_iso'
 AND NEW.manufacturer IN ('VOLKSWAGEN','AUDI','SKODA','SEAT','CUPRA')
BEGIN
  SELECT RAISE(ABORT, 'generic SAE/ISO DTC cannot be labelled as manufacturer-specific VAG');
END;

-- Generic SAE/ISO definitions may not be silently labelled as manufacturer-specific VAG.
CREATE TRIGGER IF NOT EXISTS prevent_generic_vag_mislabel
BEFORE INSERT ON oem_dtc_index
WHEN NEW.dtc_namespace = 'generic_sae_iso'
 AND NEW.manufacturer IN ('VOLKSWAGEN','AUDI','SKODA','SEAT','CUPRA')
BEGIN
  SELECT RAISE(ABORT, 'generic SAE/ISO DTC cannot be labelled as manufacturer-specific VAG');
END;

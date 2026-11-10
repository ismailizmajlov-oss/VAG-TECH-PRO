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
    market_scope IN ('RU','EAEU','EU','NAR','CN','ROW','UNKNOWN')
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
    dtc_code=upper(dtc_code)
    AND dtc_code GLOB '[PBCU][0-9A-F][0-9A-F][0-9A-F][0-9A-F]'
  ),
  dtc_namespace TEXT NOT NULL CHECK (
    dtc_namespace IN ('generic_sae_iso','manufacturer_specific_vag','manufacturer_specific_other','unknown')
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
                            'model_year_only','generic_only','unknown')
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


-- OBD-II code ranges are part of the namespace contract, not a manufacturer-name heuristic.
-- Generic SAE/ISO ranges: P0xxx, P2xxx, B0xxx, C0xxx and U0xxx. P34xx-P39xx remain quarantined until exact current-standard assignments are verified.
CREATE TRIGGER IF NOT EXISTS validate_generic_dtc_code_range_insert
BEFORE INSERT ON oem_dtc_index
WHEN NEW.dtc_namespace='generic_sae_iso' AND NOT (
 NEW.dtc_code GLOB 'P0[0-9A-F][0-9A-F][0-9A-F]' OR NEW.dtc_code GLOB 'P2[0-9A-F][0-9A-F][0-9A-F]'
 OR NEW.dtc_code GLOB 'B0[0-9A-F][0-9A-F][0-9A-F]'
 OR NEW.dtc_code GLOB 'C0[0-9A-F][0-9A-F][0-9A-F]' OR NEW.dtc_code GLOB 'U0[0-9A-F][0-9A-F][0-9A-F]'

)
BEGIN SELECT RAISE(ABORT, 'generic SAE/ISO DTC code is outside allowed generic OBD-II ranges'); END;

CREATE TRIGGER IF NOT EXISTS validate_generic_dtc_code_range_update
BEFORE UPDATE OF dtc_code, dtc_namespace ON oem_dtc_index
WHEN NEW.dtc_namespace='generic_sae_iso' AND NOT (
 NEW.dtc_code GLOB 'P0[0-9A-F][0-9A-F][0-9A-F]' OR NEW.dtc_code GLOB 'P2[0-9A-F][0-9A-F][0-9A-F]'
 OR NEW.dtc_code GLOB 'B0[0-9A-F][0-9A-F][0-9A-F]'
 OR NEW.dtc_code GLOB 'C0[0-9A-F][0-9A-F][0-9A-F]' OR NEW.dtc_code GLOB 'U0[0-9A-F][0-9A-F][0-9A-F]'

)
BEGIN SELECT RAISE(ABORT, 'generic SAE/ISO DTC code is outside allowed generic OBD-II ranges'); END;

-- Manufacturer-controlled ranges: P1xxx, P30xx-P33xx, B1xxx-B2xxx,
-- C1xxx-C2xxx and U1xxx-U2xxx. P34xx-P39xx, U3xxx and B3xxx/C3xxx are quarantined.
CREATE TRIGGER IF NOT EXISTS validate_manufacturer_dtc_code_range_insert
BEFORE INSERT ON oem_dtc_index
WHEN NEW.dtc_namespace IN ('manufacturer_specific_vag','manufacturer_specific_other') AND NOT (
 NEW.dtc_code GLOB 'P1[0-9A-F][0-9A-F][0-9A-F]'
 OR NEW.dtc_code GLOB 'P3[0-3][0-9A-F][0-9A-F]'
 OR NEW.dtc_code GLOB 'B[1-2][0-9A-F][0-9A-F][0-9A-F]' OR NEW.dtc_code GLOB 'C[1-2][0-9A-F][0-9A-F][0-9A-F]'
 OR NEW.dtc_code GLOB 'U[1-2][0-9A-F][0-9A-F][0-9A-F]'
)
BEGIN SELECT RAISE(ABORT, 'manufacturer-controlled DTC code is outside allowed OBD-II ranges'); END;

CREATE TRIGGER IF NOT EXISTS validate_manufacturer_dtc_code_range_update
BEFORE UPDATE OF dtc_code, dtc_namespace ON oem_dtc_index
WHEN NEW.dtc_namespace IN ('manufacturer_specific_vag','manufacturer_specific_other') AND NOT (
 NEW.dtc_code GLOB 'P1[0-9A-F][0-9A-F][0-9A-F]'
 OR NEW.dtc_code GLOB 'P3[0-3][0-9A-F][0-9A-F]'
 OR NEW.dtc_code GLOB 'B[1-2][0-9A-F][0-9A-F][0-9A-F]' OR NEW.dtc_code GLOB 'C[1-2][0-9A-F][0-9A-F][0-9A-F]'
 OR NEW.dtc_code GLOB 'U[1-2][0-9A-F][0-9A-F][0-9A-F]'
)
BEGIN SELECT RAISE(ABORT, 'manufacturer-controlled DTC code is outside allowed OBD-II ranges'); END;

-- Direct INSERT must not bypass the guarded review-status transition below.
CREATE TRIGGER IF NOT EXISTS oem_dtc_publication_insert_requires_guarded_transition
BEFORE INSERT ON oem_dtc_index
WHEN NEW.review_status='publication_approved'
BEGIN
  SELECT RAISE(ABORT, 'DTC publication must use guarded review-status transition');
END;

-- A row cannot be promoted until both technical review and reuse rights are cleared.
CREATE TRIGGER IF NOT EXISTS prevent_unapproved_oem_dtc_publication
BEFORE UPDATE OF review_status ON oem_dtc_index
WHEN NEW.review_status = 'publication_approved'
BEGIN
  SELECT CASE
    WHEN NOT EXISTS (
      SELECT 1 FROM source_documents s
      WHERE s.source_document_id = NEW.source_document_id
        AND s.redistribution_allowed = 1
        AND s.license_status IN ('cc0','public_domain','open_license','permission_granted')
    )
    THEN RAISE(ABORT, 'publication blocked: source reuse rights not cleared')
  END;
  SELECT CASE
    WHEN NEW.evidence_locator = ''
      OR NEW.applicability_level IN ('generic_only','unknown','model_year_only')
    THEN RAISE(ABORT, 'publication blocked: insufficient exact applicability evidence')
  END;
END;

-- Generic SAE/ISO definitions may not be silently labelled as manufacturer-specific VAG.
CREATE TRIGGER IF NOT EXISTS prevent_generic_vag_mislabel
BEFORE INSERT ON oem_dtc_index
WHEN NEW.dtc_namespace = 'generic_sae_iso'
 AND NEW.manufacturer IN ('VOLKSWAGEN','AUDI','SKODA','SEAT','CUPRA')
BEGIN
  SELECT RAISE(ABORT, 'generic SAE/ISO DTC cannot be labelled as manufacturer-specific VAG');
END;

-- Keep namespace and manufacturer identity consistent on both insert and update.
CREATE TRIGGER IF NOT EXISTS require_unknown_manufacturer_for_generic_dtc
BEFORE INSERT ON oem_dtc_index
WHEN NEW.dtc_namespace='generic_sae_iso' AND NEW.manufacturer<>'UNKNOWN'
BEGIN
  SELECT RAISE(ABORT, 'generic SAE/ISO DTC must use UNKNOWN manufacturer');
END;

CREATE TRIGGER IF NOT EXISTS require_unknown_manufacturer_for_generic_dtc_update
BEFORE UPDATE OF dtc_namespace, manufacturer ON oem_dtc_index
WHEN NEW.dtc_namespace='generic_sae_iso' AND NEW.manufacturer<>'UNKNOWN'
BEGIN
  SELECT RAISE(ABORT, 'generic SAE/ISO DTC must use UNKNOWN manufacturer');
END;

CREATE TRIGGER IF NOT EXISTS require_vag_manufacturer_for_vag_dtc
BEFORE INSERT ON oem_dtc_index
WHEN NEW.dtc_namespace='manufacturer_specific_vag'
 AND NEW.manufacturer NOT IN ('VOLKSWAGEN','AUDI','SKODA','SEAT','CUPRA')
BEGIN
  SELECT RAISE(ABORT, 'VAG-specific DTC requires a VAG Group manufacturer');
END;

CREATE TRIGGER IF NOT EXISTS require_vag_manufacturer_for_vag_dtc_update
BEFORE UPDATE OF dtc_namespace, manufacturer ON oem_dtc_index
WHEN NEW.dtc_namespace='manufacturer_specific_vag'
 AND NEW.manufacturer NOT IN ('VOLKSWAGEN','AUDI','SKODA','SEAT','CUPRA')
BEGIN
  SELECT RAISE(ABORT, 'VAG-specific DTC requires a VAG Group manufacturer');
END;

CREATE TRIGGER IF NOT EXISTS require_other_manufacturer_for_other_oem_dtc
BEFORE INSERT ON oem_dtc_index
WHEN NEW.dtc_namespace='manufacturer_specific_other' AND NEW.manufacturer<>'OTHER'
BEGIN
  SELECT RAISE(ABORT, 'other manufacturer-specific DTC must use OTHER manufacturer');
END;

CREATE TRIGGER IF NOT EXISTS require_other_manufacturer_for_other_oem_dtc_update
BEFORE UPDATE OF dtc_namespace, manufacturer ON oem_dtc_index
WHEN NEW.dtc_namespace='manufacturer_specific_other' AND NEW.manufacturer<>'OTHER'
BEGIN
  SELECT RAISE(ABORT, 'other manufacturer-specific DTC must use OTHER manufacturer');
END;

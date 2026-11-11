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
  source_sha256 TEXT CHECK (source_sha256 IS NULL OR (length(source_sha256)=64 AND source_sha256 NOT GLOB '*[^a-f0-9]*')),
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

CREATE TABLE IF NOT EXISTS technical_source_rights (
 source_document_id INTEGER PRIMARY KEY REFERENCES source_documents(source_document_id) ON DELETE RESTRICT,
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
CREATE TRIGGER IF NOT EXISTS technical_source_rights_license_text_sha256_insert_guard
BEFORE INSERT ON technical_source_rights
WHEN NEW.license_text_sha256 IS NOT NULL
 AND (length(NEW.license_text_sha256)<>64 OR NEW.license_text_sha256 GLOB '*[^a-f0-9]*')
BEGIN SELECT RAISE(ABORT,'technical source license SHA-256 must be 64 lowercase hexadecimal characters'); END;
CREATE TRIGGER IF NOT EXISTS technical_source_rights_license_text_sha256_update_guard
BEFORE UPDATE OF license_text_sha256 ON technical_source_rights
WHEN NEW.license_text_sha256 IS NOT NULL
 AND (length(NEW.license_text_sha256)<>64 OR NEW.license_text_sha256 GLOB '*[^a-f0-9]*')
BEGIN SELECT RAISE(ABORT,'technical source license SHA-256 must be 64 lowercase hexadecimal characters'); END;

CREATE TRIGGER IF NOT EXISTS technical_source_permission_reference_guard
BEFORE INSERT ON technical_source_rights WHEN NEW.rights_status='approved'
BEGIN
 SELECT CASE WHEN(SELECT license_status FROM source_documents WHERE source_document_id=NEW.source_document_id)='permission_granted'
 AND(NEW.permission_reference IS NULL OR length(trim(NEW.permission_reference))=0)
 THEN RAISE(ABORT,'permission-granted source rights require a permission reference') END;
END;
CREATE TRIGGER IF NOT EXISTS technical_source_permission_reference_update
BEFORE UPDATE OF rights_status,permission_reference ON technical_source_rights
WHEN NEW.rights_status='approved'
BEGIN
 SELECT CASE WHEN(SELECT license_status FROM source_documents WHERE source_document_id=NEW.source_document_id)='permission_granted'
 AND(NEW.permission_reference IS NULL OR length(trim(NEW.permission_reference))=0)
 THEN RAISE(ABORT,'permission-granted source rights require a permission reference') END;
END;

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
  source_claim_hash TEXT NOT NULL CHECK (length(source_claim_hash)=64 AND source_claim_hash NOT GLOB '*[^a-f0-9]*'),
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

-- Publication requires a pinned source snapshot, detailed commercial/offline rights and explicit applicability.
CREATE TRIGGER IF NOT EXISTS prevent_unapproved_oem_dtc_publication
BEFORE UPDATE OF review_status ON oem_dtc_index
WHEN NEW.review_status = 'publication_approved'
BEGIN
  SELECT CASE
    WHEN NOT EXISTS (
      SELECT 1
      FROM source_documents s
      JOIN technical_source_rights r ON r.source_document_id = s.source_document_id
      WHERE s.source_document_id = NEW.source_document_id
        AND s.market_scope = NEW.market_scope
        AND s.redistribution_allowed = 1
        AND s.license_status IN ('cc0','public_domain','open_license','permission_granted')
        AND s.source_sha256 IS NOT NULL
        AND length(s.source_sha256) = 64
        AND s.source_sha256 NOT GLOB '*[^a-f0-9]*'
        AND length(trim(s.revision)) > 0
        AND r.rights_status = 'approved'
        AND r.commercial_use_allowed = 1
        AND r.display_allowed = 1
        AND r.offline_cache_allowed = 1
        AND r.bulk_reuse_allowed = 1
        AND r.redistribution_allowed = 1
        AND r.store_structured_data_allowed = 1
        AND (NEW.description IS NULL OR length(trim(NEW.description)) = 0 OR r.store_text_allowed = 1)
        AND r.license_text_sha256 IS NOT NULL
        AND length(r.license_text_sha256) = 64
        AND r.license_text_sha256 NOT GLOB '*[^a-f0-9]*'
        AND length(trim(r.rights_revision)) > 0
        AND length(trim(r.reviewed_at_utc)) > 0
        AND (s.license_status <> 'permission_granted'
             OR (r.permission_reference IS NOT NULL AND length(trim(r.permission_reference)) > 0))
    )
    THEN RAISE(ABORT, 'publication blocked: source reuse rights not cleared')
  END;
  SELECT CASE
    WHEN NEW.market_scope = 'UNKNOWN'
      OR length(trim(NEW.evidence_locator)) = 0
      OR NEW.applicability_level IN ('generic_only','unknown','model_year_only')
    THEN RAISE(ABORT, 'publication blocked: insufficient exact applicability evidence')
  END;
  SELECT CASE
    WHEN NEW.applicability_level = 'exact_vin'
      AND NEW.vin_range_explicit <> 1
    THEN RAISE(ABORT, 'exact VIN applicability requires an explicit VIN range')
  END;
  SELECT CASE
    WHEN NEW.applicability_level = 'exact_ecu_hw_sw'
      AND (
        NEW.ecu_identity_id IS NULL
        OR NEW.ecu_hw_sw_explicit <> 1
        OR NOT EXISTS (
          SELECT 1 FROM ecu_identities e
          WHERE e.ecu_identity_id = NEW.ecu_identity_id
            AND e.identity_status = 'exact'
            AND length(trim(coalesce(e.hardware_number,''))) > 0
            AND length(trim(coalesce(e.software_number,''))) > 0
        )
      )
    THEN RAISE(ABORT, 'exact ECU HW/SW applicability requires an exact ECU identity')
  END;
  SELECT CASE
    WHEN NEW.applicability_level = 'engine_transmission_variant'
      AND (
        length(trim(coalesce(NEW.engine_code,''))) = 0
        OR length(trim(coalesce(NEW.transmission_code,''))) = 0
        OR NEW.engine_code_explicit <> 1
        OR NEW.transmission_code_explicit <> 1
      )
    THEN RAISE(ABORT, 'engine/transmission applicability requires both explicit factory codes')
  END;
END;

-- Once a DTC claim has been approved, preserve the exact reviewed claim and its source snapshot.
CREATE TABLE IF NOT EXISTS oem_dtc_publication_locks (
  oem_dtc_id INTEGER PRIMARY KEY REFERENCES oem_dtc_index(oem_dtc_id) ON DELETE RESTRICT,
  source_claim_hash TEXT NOT NULL CHECK(length(source_claim_hash)=64 AND source_claim_hash NOT GLOB '*[^a-f0-9]*'),
  approved_at_utc TEXT NOT NULL
);
CREATE TRIGGER IF NOT EXISTS oem_dtc_publication_locks_source_claim_hash_insert_guard
BEFORE INSERT ON oem_dtc_publication_locks
WHEN NEW.source_claim_hash IS NULL OR length(NEW.source_claim_hash)<>64 OR NEW.source_claim_hash GLOB '*[^a-f0-9]*'
BEGIN SELECT RAISE(ABORT,'published DTC source-claim hash must be 64 lowercase hexadecimal characters'); END;
CREATE TRIGGER IF NOT EXISTS oem_dtc_publication_locks_source_claim_hash_update_guard
BEFORE UPDATE OF source_claim_hash ON oem_dtc_publication_locks
WHEN length(NEW.source_claim_hash)<>64 OR NEW.source_claim_hash GLOB '*[^a-f0-9]*'
BEGIN SELECT RAISE(ABORT,'published DTC source-claim hash must be 64 lowercase hexadecimal characters'); END;

CREATE TRIGGER IF NOT EXISTS record_oem_dtc_publication_lock
AFTER UPDATE OF review_status ON oem_dtc_index
WHEN NEW.review_status='publication_approved' AND OLD.review_status<>'publication_approved'
BEGIN
  INSERT OR IGNORE INTO oem_dtc_publication_locks(oem_dtc_id,source_claim_hash,approved_at_utc)
  VALUES(NEW.oem_dtc_id,NEW.source_claim_hash,strftime('%Y-%m-%dT%H:%M:%fZ','now'));
END;
INSERT OR IGNORE INTO oem_dtc_publication_locks(oem_dtc_id,source_claim_hash,approved_at_utc)
SELECT oem_dtc_id,source_claim_hash,created_at_utc
FROM oem_dtc_index WHERE review_status='publication_approved';

CREATE TRIGGER IF NOT EXISTS oem_dtc_published_claim_immutable
BEFORE UPDATE OF dtc_code,dtc_namespace,manufacturer,market_scope,model,generation_or_type_code,
 model_year_from,model_year_to,production_date_from,production_date_to,engine_code,transmission_code,
 drive_configuration,pr_codes_json,ecu_identity_id,source_document_id,description,symptoms_json,
 causes_json,test_plan_reference,evidence_locator,applicability_level,vin_range_explicit,
 engine_code_explicit,transmission_code_explicit,ecu_hw_sw_explicit,source_claim_hash,created_at_utc
ON oem_dtc_index
WHEN EXISTS(SELECT 1 FROM oem_dtc_publication_locks l WHERE l.oem_dtc_id=OLD.oem_dtc_id)
BEGIN
  SELECT RAISE(ABORT,'published OEM DTC claim is immutable; create a new source revision');
END;
CREATE TRIGGER IF NOT EXISTS oem_dtc_published_source_immutable
BEFORE UPDATE ON source_documents
WHEN EXISTS(
  SELECT 1 FROM oem_dtc_publication_locks l
  JOIN oem_dtc_index d ON d.oem_dtc_id=l.oem_dtc_id
  WHERE d.source_document_id=OLD.source_document_id
)
BEGIN
  SELECT RAISE(ABORT,'source snapshot metadata is immutable after OEM DTC publication');
END;
CREATE TRIGGER IF NOT EXISTS oem_dtc_publication_lock_no_update
BEFORE UPDATE ON oem_dtc_publication_locks
BEGIN SELECT RAISE(ABORT,'OEM DTC publication lock is append-only'); END;
CREATE TRIGGER IF NOT EXISTS oem_dtc_publication_lock_no_delete
BEFORE DELETE ON oem_dtc_publication_locks
BEGIN SELECT RAISE(ABORT,'OEM DTC publication lock is append-only'); END;

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

-- Additive guards also protect databases created by an earlier schema revision:
-- CREATE TABLE IF NOT EXISTS cannot retrofit CHECK constraints into an existing SQLite table.
CREATE TRIGGER IF NOT EXISTS source_documents_sha256_insert_guard
BEFORE INSERT ON source_documents
WHEN NEW.source_sha256 IS NOT NULL
 AND (length(NEW.source_sha256)<>64 OR NEW.source_sha256 GLOB '*[^a-f0-9]*')
BEGIN
  SELECT RAISE(ABORT, 'source SHA-256 must be 64 lowercase hexadecimal characters');
END;

CREATE TRIGGER IF NOT EXISTS source_documents_sha256_update_guard
BEFORE UPDATE OF source_sha256 ON source_documents
WHEN NEW.source_sha256 IS NOT NULL
 AND (length(NEW.source_sha256)<>64 OR NEW.source_sha256 GLOB '*[^a-f0-9]*')
BEGIN
  SELECT RAISE(ABORT, 'source SHA-256 must be 64 lowercase hexadecimal characters');
END;

CREATE TRIGGER IF NOT EXISTS oem_dtc_source_claim_hash_insert_guard
BEFORE INSERT ON oem_dtc_index
WHEN length(NEW.source_claim_hash)<>64 OR NEW.source_claim_hash GLOB '*[^a-f0-9]*'
BEGIN
  SELECT RAISE(ABORT, 'source claim hash must be 64 lowercase hexadecimal characters');
END;

CREATE TRIGGER IF NOT EXISTS oem_dtc_source_claim_hash_update_guard
BEFORE UPDATE OF source_claim_hash ON oem_dtc_index
WHEN length(NEW.source_claim_hash)<>64 OR NEW.source_claim_hash GLOB '*[^a-f0-9]*'
BEGIN
  SELECT RAISE(ABORT, 'source claim hash must be 64 lowercase hexadecimal characters');
END;

-- Runtime-safe public surface: revoking rights immediately removes a DTC from this view.
CREATE VIEW IF NOT EXISTS v_published_oem_dtc_index AS
SELECT d.*,
       s.publisher AS source_publisher,
       s.document_id AS source_document_id_text,
       s.revision AS source_revision,
       s.source_url,
       s.source_sha256,
       s.license_status,
       s.license_name,
       r.rights_revision,
       r.license_text_sha256
FROM oem_dtc_index d
JOIN source_documents s ON s.source_document_id = d.source_document_id
JOIN technical_source_rights r ON r.source_document_id = s.source_document_id
WHERE d.review_status = 'publication_approved'
  AND s.license_status IN ('cc0','public_domain','open_license','permission_granted')
  AND s.redistribution_allowed = 1
  AND s.market_scope = d.market_scope
  AND length(trim(s.revision)) > 0
  AND s.source_sha256 IS NOT NULL
  AND length(s.source_sha256) = 64
  AND s.source_sha256 NOT GLOB '*[^a-f0-9]*'
  AND r.rights_status = 'approved'
  AND r.commercial_use_allowed = 1
  AND r.display_allowed = 1
  AND r.offline_cache_allowed = 1
  AND r.bulk_reuse_allowed = 1
  AND r.redistribution_allowed = 1
  AND r.store_structured_data_allowed = 1
  AND (d.description IS NULL OR length(trim(d.description)) = 0 OR r.store_text_allowed = 1)
  AND (s.license_status <> 'permission_granted' OR (r.permission_reference IS NOT NULL AND length(trim(r.permission_reference)) > 0))
  AND length(trim(r.rights_revision)) > 0
  AND length(trim(r.reviewed_at_utc)) > 0
  AND r.license_text_sha256 IS NOT NULL
  AND length(r.license_text_sha256) = 64
  AND r.license_text_sha256 NOT GLOB '*[^a-f0-9]*'
  AND d.market_scope <> 'UNKNOWN'
  AND length(trim(d.evidence_locator)) > 0
  AND d.applicability_level NOT IN ('generic_only','unknown','model_year_only')
  AND (d.applicability_level <> 'exact_vin' OR d.vin_range_explicit = 1)
  AND (d.applicability_level <> 'exact_ecu_hw_sw' OR (
       d.ecu_identity_id IS NOT NULL AND d.ecu_hw_sw_explicit = 1
       AND EXISTS(SELECT 1 FROM ecu_identities e WHERE e.ecu_identity_id=d.ecu_identity_id
                  AND e.identity_status='exact'
                  AND length(trim(coalesce(e.hardware_number,'')))>0
                  AND length(trim(coalesce(e.software_number,'')))>0)))
  AND (d.applicability_level <> 'engine_transmission_variant' OR (
       length(trim(coalesce(d.engine_code,'')))>0
       AND length(trim(coalesce(d.transmission_code,'')))>0
       AND d.engine_code_explicit=1 AND d.transmission_code_explicit=1));

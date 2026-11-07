PRAGMA foreign_keys = ON;

-- Apply after data/sql/oem-dtc-index.sql and data/sql/vehicle-catalog.sql.
-- This bridge is VIN-free and links DTC records to the normalized vehicle catalog.

CREATE TABLE IF NOT EXISTS oem_dtc_vehicle_applicability (
  applicability_id INTEGER PRIMARY KEY,
  oem_dtc_id INTEGER NOT NULL REFERENCES oem_dtc_index(oem_dtc_id) ON DELETE CASCADE,
  variant_id INTEGER NOT NULL REFERENCES vehicle_variants(variant_id),
  engine_id INTEGER REFERENCES engine_codes(engine_id),
  transmission_id INTEGER REFERENCES transmission_codes(transmission_id),
  ecu_identity_id INTEGER REFERENCES ecu_identities(ecu_identity_id),
  evidence_id INTEGER NOT NULL REFERENCES vehicle_catalog_evidence(evidence_id),
  market_scope TEXT NOT NULL CHECK (
    market_scope IN ('RU','EAEU','EU','NAR','CN','ROW','MULTI','UNKNOWN')
  ),
  applicability_level TEXT NOT NULL CHECK (
    applicability_level IN ('exact_ecu_hw_sw','engine_transmission_variant',
                            'variant_only','market_only','unknown')
  ),
  note TEXT,
  UNIQUE(oem_dtc_id, variant_id, engine_id, transmission_id, ecu_identity_id, evidence_id)
);

CREATE INDEX IF NOT EXISTS idx_dtc_applicability_dtc
  ON oem_dtc_vehicle_applicability(oem_dtc_id, market_scope);
CREATE INDEX IF NOT EXISTS idx_dtc_applicability_variant
  ON oem_dtc_vehicle_applicability(variant_id, engine_id, transmission_id);

-- This bridge is deliberately VAG-specific. Generic SAE/ISO DTC rows remain
-- searchable in their own namespace and cannot acquire VAG vehicle fitment here.
CREATE TRIGGER IF NOT EXISTS require_vag_specific_dtc_for_vehicle_link
BEFORE INSERT ON oem_dtc_vehicle_applicability
WHEN NOT EXISTS (
  SELECT 1 FROM oem_dtc_index d
  WHERE d.oem_dtc_id=NEW.oem_dtc_id
    AND d.dtc_namespace='manufacturer_specific_vag'
    AND d.manufacturer IN ('VOLKSWAGEN','AUDI','SKODA','SEAT','CUPRA')
)
BEGIN
  SELECT RAISE(ABORT, 'VAG vehicle applicability bridge accepts only manufacturer-specific VAG DTC records');
END;

CREATE TRIGGER IF NOT EXISTS prevent_reclassifying_linked_vag_dtc
BEFORE UPDATE OF dtc_namespace, manufacturer ON oem_dtc_index
WHEN (NEW.dtc_namespace<>'manufacturer_specific_vag'
   OR NEW.manufacturer NOT IN ('VOLKSWAGEN','AUDI','SKODA','SEAT','CUPRA'))
 AND EXISTS (
   SELECT 1 FROM oem_dtc_vehicle_applicability a
   WHERE a.oem_dtc_id=OLD.oem_dtc_id
 )
BEGIN
  SELECT RAISE(ABORT, 'linked VAG DTC cannot be reclassified outside the VAG-specific namespace');
END;

CREATE TRIGGER IF NOT EXISTS validate_dtc_catalog_link_evidence
BEFORE INSERT ON oem_dtc_vehicle_applicability
WHEN NOT EXISTS (
  SELECT 1 FROM vehicle_catalog_evidence e
  WHERE e.evidence_id=NEW.evidence_id
    AND e.claim_type='dtc_applicability'
)
BEGIN
  SELECT RAISE(ABORT, 'DTC-to-vehicle link requires explicit DTC applicability evidence');
END;

CREATE TRIGGER IF NOT EXISTS prevent_unreviewed_dtc_catalog_link
BEFORE INSERT ON oem_dtc_vehicle_applicability
WHEN NOT EXISTS (
  SELECT 1 FROM vehicle_catalog_evidence e
  WHERE e.evidence_id=NEW.evidence_id
    AND e.review_status IN ('technically_verified','publication_approved')
)
BEGIN
  SELECT RAISE(ABORT, 'DTC-to-vehicle link requires technically verified evidence');
END;

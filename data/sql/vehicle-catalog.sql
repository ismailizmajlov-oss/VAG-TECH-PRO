PRAGMA foreign_keys = ON;

-- VIN-free vehicle taxonomy and powertrain catalog.
-- All technical relationships are evidence-backed; this schema contains no VIN fields.

CREATE TABLE IF NOT EXISTS vehicle_catalog_sources (
  source_id TEXT PRIMARY KEY,
  publisher TEXT NOT NULL,
  source_title TEXT NOT NULL,
  source_url TEXT NOT NULL,
  source_version TEXT,
  market_scope TEXT NOT NULL CHECK (
    market_scope IN ('RU','EAEU','EU','NAR','CN','ROW','MULTI','UNKNOWN')
  ),
  license_status TEXT NOT NULL CHECK (
    license_status IN ('cc0','public_domain','open_license','permission_granted',
                       'proprietary','unknown','permission_required')
  ),
  license_name TEXT,
  attribution_required INTEGER NOT NULL DEFAULT 0 CHECK (attribution_required IN (0,1)),
  redistribution_allowed INTEGER NOT NULL DEFAULT 0 CHECK (redistribution_allowed IN (0,1)),
  reuse_scope TEXT NOT NULL,
  permission_reference TEXT,
  checked_at_utc TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS vehicle_makes (
  make_id INTEGER PRIMARY KEY,
  make_key TEXT NOT NULL UNIQUE,
  display_name TEXT NOT NULL,
  group_name TEXT NOT NULL DEFAULT 'VOLKSWAGEN_GROUP',
  status TEXT NOT NULL DEFAULT 'research' CHECK (status IN ('research','verified','published')),
  created_at_utc TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS vehicle_models (
  model_id INTEGER PRIMARY KEY,
  make_id INTEGER NOT NULL REFERENCES vehicle_makes(make_id),
  model_key TEXT NOT NULL,
  display_name TEXT NOT NULL,
  body_family TEXT,
  status TEXT NOT NULL DEFAULT 'research' CHECK (status IN ('research','verified','published')),
  UNIQUE(make_id, model_key)
);

CREATE TABLE IF NOT EXISTS vehicle_generations (
  generation_id INTEGER PRIMARY KEY,
  model_id INTEGER NOT NULL REFERENCES vehicle_models(model_id),
  generation_key TEXT NOT NULL,
  type_code TEXT,
  platform_code TEXT,
  production_from TEXT,
  production_to TEXT,
  market_scope TEXT NOT NULL CHECK (
    market_scope IN ('RU','EAEU','EU','NAR','CN','ROW','MULTI','UNKNOWN')
  ),
  notes TEXT,
  status TEXT NOT NULL DEFAULT 'research' CHECK (status IN ('research','verified','published')),
  UNIQUE(model_id, generation_key, market_scope)
);

CREATE TABLE IF NOT EXISTS vehicle_variants (
  variant_id INTEGER PRIMARY KEY,
  generation_id INTEGER NOT NULL REFERENCES vehicle_generations(generation_id),
  variant_key TEXT NOT NULL,
  model_year_from INTEGER,
  model_year_to INTEGER,
  body_code TEXT,
  drive_configuration TEXT,
  fuel_type TEXT,
  emissions_variant TEXT,
  market_scope TEXT NOT NULL CHECK (
    market_scope IN ('RU','EAEU','EU','NAR','CN','ROW','MULTI','UNKNOWN')
  ),
  status TEXT NOT NULL DEFAULT 'research' CHECK (status IN ('research','verified','published')),
  UNIQUE(generation_id, variant_key, market_scope),
  CHECK (model_year_from IS NULL OR model_year_to IS NULL OR model_year_from <= model_year_to)
);

CREATE TABLE IF NOT EXISTS engine_codes (
  engine_id INTEGER PRIMARY KEY,
  engine_code TEXT NOT NULL,
  manufacturer TEXT NOT NULL DEFAULT 'VOLKSWAGEN_GROUP',
  engine_family TEXT,
  displacement_cc INTEGER,
  fuel_type TEXT,
  aspiration TEXT,
  power_kw INTEGER,
  power_hp INTEGER,
  status TEXT NOT NULL DEFAULT 'research' CHECK (status IN ('research','verified','published')),
  UNIQUE(engine_code, manufacturer)
);

CREATE TABLE IF NOT EXISTS transmission_codes (
  transmission_id INTEGER PRIMARY KEY,
  transmission_code TEXT NOT NULL,
  manufacturer TEXT NOT NULL DEFAULT 'VOLKSWAGEN_GROUP',
  transmission_family TEXT,
  gear_count INTEGER,
  transmission_type TEXT,
  drive_layout TEXT,
  status TEXT NOT NULL DEFAULT 'research' CHECK (status IN ('research','verified','published')),
  UNIQUE(transmission_code, manufacturer)
);

CREATE TABLE IF NOT EXISTS vehicle_catalog_evidence (
  evidence_id INTEGER PRIMARY KEY,
  source_id TEXT NOT NULL REFERENCES vehicle_catalog_sources(source_id),
  document_id TEXT NOT NULL,
  document_revision TEXT,
  issue_date TEXT,
  retrieved_at_utc TEXT NOT NULL,
  evidence_locator TEXT NOT NULL,
  source_sha256 TEXT CHECK (source_sha256 IS NULL OR length(source_sha256)=64),
  claim_type TEXT NOT NULL CHECK (
    claim_type IN ('make','model','generation','variant','engine_code',
                   'transmission_code','engine_fitment','transmission_fitment','vin_range',
                   'engine_transmission_pair','market_scope','ecu_fitment','dtc_applicability','repair_document_applicability','other')
  ),
  review_status TEXT NOT NULL DEFAULT 'candidate' CHECK (
    review_status IN ('candidate','source_checked','technically_verified',
                      'publication_approved','rejected')
  ),
  reviewer_note TEXT
);

CREATE TABLE IF NOT EXISTS vehicle_generation_evidence (
  generation_id INTEGER NOT NULL REFERENCES vehicle_generations(generation_id) ON DELETE CASCADE,
  evidence_id INTEGER NOT NULL REFERENCES vehicle_catalog_evidence(evidence_id),
  PRIMARY KEY(generation_id, evidence_id)
);

CREATE TABLE IF NOT EXISTS vehicle_variant_evidence (
  variant_id INTEGER NOT NULL REFERENCES vehicle_variants(variant_id) ON DELETE CASCADE,
  evidence_id INTEGER NOT NULL REFERENCES vehicle_catalog_evidence(evidence_id),
  PRIMARY KEY(variant_id, evidence_id)
);

CREATE TABLE IF NOT EXISTS engine_fitments (
  fitment_id INTEGER PRIMARY KEY,
  variant_id INTEGER NOT NULL REFERENCES vehicle_variants(variant_id),
  engine_id INTEGER NOT NULL REFERENCES engine_codes(engine_id),
  evidence_id INTEGER NOT NULL REFERENCES vehicle_catalog_evidence(evidence_id),
  fitment_note TEXT,
  UNIQUE(variant_id, engine_id, evidence_id)
);

CREATE TABLE IF NOT EXISTS transmission_fitments (
  fitment_id INTEGER PRIMARY KEY,
  variant_id INTEGER NOT NULL REFERENCES vehicle_variants(variant_id),
  transmission_id INTEGER NOT NULL REFERENCES transmission_codes(transmission_id),
  evidence_id INTEGER NOT NULL REFERENCES vehicle_catalog_evidence(evidence_id),
  fitment_note TEXT,
  UNIQUE(variant_id, transmission_id, evidence_id)
);

CREATE TABLE IF NOT EXISTS powertrain_pair_evidence (
  pair_id INTEGER PRIMARY KEY,
  variant_id INTEGER NOT NULL REFERENCES vehicle_variants(variant_id),
  engine_id INTEGER NOT NULL REFERENCES engine_codes(engine_id),
  transmission_id INTEGER NOT NULL REFERENCES transmission_codes(transmission_id),
  evidence_id INTEGER NOT NULL REFERENCES vehicle_catalog_evidence(evidence_id),
  UNIQUE(variant_id, engine_id, transmission_id, evidence_id)
);

CREATE INDEX IF NOT EXISTS idx_models_make ON vehicle_models(make_id, display_name);
CREATE INDEX IF NOT EXISTS idx_generations_model ON vehicle_generations(model_id, market_scope);
CREATE INDEX IF NOT EXISTS idx_variants_generation ON vehicle_variants(generation_id, market_scope);
CREATE INDEX IF NOT EXISTS idx_engine_code ON engine_codes(engine_code);
CREATE INDEX IF NOT EXISTS idx_transmission_code ON transmission_codes(transmission_code);
CREATE INDEX IF NOT EXISTS idx_engine_fitments_variant ON engine_fitments(variant_id, engine_id);
CREATE INDEX IF NOT EXISTS idx_transmission_fitments_variant ON transmission_fitments(variant_id, transmission_id);

-- Fitment links require evidence of the corresponding claim type.
CREATE TRIGGER IF NOT EXISTS validate_engine_fitment_evidence
BEFORE INSERT ON engine_fitments
WHEN NOT EXISTS (
  SELECT 1 FROM vehicle_catalog_evidence e
  WHERE e.evidence_id=NEW.evidence_id
    AND e.claim_type IN ('engine_fitment','engine_code','engine_transmission_pair')
)
BEGIN
  SELECT RAISE(ABORT, 'engine fitment requires engine-fitment evidence');
END;

CREATE TRIGGER IF NOT EXISTS validate_transmission_fitment_evidence
BEFORE INSERT ON transmission_fitments
WHEN NOT EXISTS (
  SELECT 1 FROM vehicle_catalog_evidence e
  WHERE e.evidence_id=NEW.evidence_id
    AND e.claim_type IN ('transmission_fitment','transmission_code','engine_transmission_pair')
)
BEGIN
  SELECT RAISE(ABORT, 'transmission fitment requires transmission-fitment evidence');
END;

CREATE TRIGGER IF NOT EXISTS validate_powertrain_pair_evidence
BEFORE INSERT ON powertrain_pair_evidence
WHEN NOT EXISTS (
  SELECT 1 FROM vehicle_catalog_evidence e
  WHERE e.evidence_id=NEW.evidence_id
    AND e.claim_type='engine_transmission_pair'
)
BEGIN
  SELECT RAISE(ABORT, 'engine/transmission pair requires explicit pair evidence');
END;

-- Publication requires a reviewed claim and an explicitly reusable source.
CREATE TRIGGER IF NOT EXISTS prevent_unlicensed_vehicle_evidence_publication
BEFORE UPDATE OF review_status ON vehicle_catalog_evidence
WHEN NEW.review_status='publication_approved'
BEGIN
  SELECT CASE WHEN NOT EXISTS (
    SELECT 1 FROM vehicle_catalog_sources s
    WHERE s.source_id=NEW.source_id
      AND s.redistribution_allowed=1
      AND s.license_status IN ('cc0','public_domain','open_license','permission_granted')
  ) THEN RAISE(ABORT, 'publication blocked: source reuse rights not cleared') END;
  SELECT CASE WHEN NEW.evidence_locator='' OR NEW.evidence_locator IS NULL
    THEN RAISE(ABORT, 'publication blocked: evidence locator is required') END;
END;

-- A model-year range alone is not an engine or transmission fitment claim.


-- Publication approval must pass through the UPDATE trigger so source rights are checked.
CREATE TRIGGER IF NOT EXISTS vehicle_catalog_evidence_publication_insert_requires_guarded_transition
BEFORE INSERT ON vehicle_catalog_evidence
WHEN NEW.review_status='publication_approved'
BEGIN
  SELECT RAISE(ABORT, 'vehicle catalog evidence publication must use guarded review-status transition');
END;

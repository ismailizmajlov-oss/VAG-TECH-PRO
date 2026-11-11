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
  source_sha256 TEXT CHECK (
    source_sha256 IS NULL OR
    (length(source_sha256)=64 AND source_sha256 NOT GLOB '*[^a-f0-9]*')
  ),
  market_scope TEXT NOT NULL DEFAULT 'UNKNOWN' CHECK (
    market_scope IN ('RU','EAEU','EU','NAR','CN','ROW','MULTI','UNKNOWN')
  ),
  applicability_precision TEXT NOT NULL DEFAULT 'unknown' CHECK (
    applicability_precision IN ('unknown','make_only','model_only','generation','variant',
      'exact_engine','exact_transmission','exact_pairing','exact_ecu','exact_configuration',
      'type_approval_descriptor','document_metadata_only')
  ),
  claim_type TEXT NOT NULL CHECK (
    claim_type IN ('make','model','generation','variant','engine_code',
                   'transmission_code','engine_fitment','transmission_fitment','vin_range',
                   'engine_transmission_pair','market_scope','ecu_fitment','dtc_applicability','repair_document_applicability','other')
  ),
  review_status TEXT NOT NULL DEFAULT 'candidate' CHECK (
    review_status IN ('candidate','source_checked','technically_verified',
                      'publication_approved','rejected')
  ),
  reviewer_note TEXT,
  reviewed_at_utc TEXT
);

CREATE TRIGGER IF NOT EXISTS vehicle_catalog_evidence_source_sha256_insert_guard
BEFORE INSERT ON vehicle_catalog_evidence
WHEN NEW.source_sha256 IS NOT NULL
 AND (length(NEW.source_sha256)<>64 OR NEW.source_sha256 GLOB '*[^a-f0-9]*')
BEGIN
  SELECT RAISE(ABORT, 'vehicle evidence source SHA-256 must be 64 lowercase hexadecimal characters');
END;
CREATE TRIGGER IF NOT EXISTS vehicle_catalog_evidence_source_sha256_update_guard
BEFORE UPDATE OF source_sha256 ON vehicle_catalog_evidence
WHEN NEW.source_sha256 IS NOT NULL
 AND (length(NEW.source_sha256)<>64 OR NEW.source_sha256 GLOB '*[^a-f0-9]*')
BEGIN
  SELECT RAISE(ABORT, 'vehicle evidence source SHA-256 must be 64 lowercase hexadecimal characters');
END;

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

-- Fitment rows are active catalog relationships, not a place to store unreviewed candidates.
-- Keep this canonical schema in lockstep with the Windows local-core evidence policy.
-- Rights revocation preserves historical links while current evidence status gates all lookups.
-- Structured-data storage permission is mandatory in addition to display, cache and redistribution rights.
-- The cited claim must be technically verified, market-exact, revision/hash-bound,
-- rights-cleared for commercial display and offline redistribution, and linked only
-- to verified parent catalog entities.
DROP TRIGGER IF EXISTS validate_engine_fitment_evidence;
DROP TRIGGER IF EXISTS validate_transmission_fitment_evidence;
DROP TRIGGER IF EXISTS validate_powertrain_pair_evidence;
DROP TRIGGER IF EXISTS prevent_unlicensed_vehicle_evidence_publication;
DROP TRIGGER IF EXISTS vehicle_catalog_evidence_publication_insert_requires_guarded_transition;

CREATE TRIGGER validate_engine_fitment_evidence
BEFORE INSERT ON engine_fitments
WHEN NOT EXISTS (
  SELECT 1
  FROM vehicle_catalog_evidence e
  JOIN vehicle_catalog_sources s ON s.source_id=e.source_id
  JOIN vehicle_catalog_source_rights r ON r.source_id=e.source_id
  JOIN vehicle_variants v ON v.variant_id=NEW.variant_id
  JOIN vehicle_generations g ON g.generation_id=v.generation_id
  JOIN vehicle_models m ON m.model_id=g.model_id
  JOIN vehicle_makes mk ON mk.make_id=m.make_id
  JOIN engine_codes ec ON ec.engine_id=NEW.engine_id
  WHERE e.evidence_id=NEW.evidence_id
    AND e.claim_type IN ('engine_fitment','engine_transmission_pair')
    AND e.review_status IN ('technically_verified','publication_approved')
    AND e.market_scope=v.market_scope
    AND e.applicability_precision IN ('exact_engine','exact_pairing')
    AND e.document_revision IS NOT NULL AND length(trim(e.document_revision))>0
    AND e.source_sha256 IS NOT NULL AND length(e.source_sha256)=64 AND e.source_sha256 NOT GLOB '*[^a-f0-9]*'
    AND e.evidence_locator IS NOT NULL AND length(trim(e.evidence_locator))>0
    AND e.reviewed_at_utc IS NOT NULL AND length(trim(e.reviewed_at_utc))>0
    AND e.reviewer_note IS NOT NULL AND length(trim(e.reviewer_note))>0
    AND (s.market_scope=e.market_scope OR (s.market_scope='EAEU' AND e.market_scope IN ('RU','EAEU')) OR s.market_scope='MULTI')
    AND s.redistribution_allowed=1
    AND s.license_status IN ('cc0','public_domain','open_license','permission_granted')
    AND r.rights_status='approved'
    AND r.commercial_use_allowed=1 AND r.display_allowed=1
    AND r.offline_cache_allowed=1 AND r.bulk_reuse_allowed=1
    AND r.store_structured_data_allowed=1
    AND r.license_text_sha256 IS NOT NULL AND length(r.license_text_sha256)=64 AND r.license_text_sha256 NOT GLOB '*[^a-f0-9]*'
    AND r.rights_revision IS NOT NULL AND length(trim(r.rights_revision))>0
    AND r.reviewed_at_utc IS NOT NULL AND length(trim(r.reviewed_at_utc))>0
    AND ec.status IN ('verified','published')
    AND v.status IN ('verified','published')
    AND g.status IN ('verified','published')
    AND m.status IN ('verified','published')
    AND mk.status IN ('verified','published')
)
BEGIN SELECT RAISE(ABORT, 'engine fitment requires technically verified exact-market evidence, cleared rights and verified parent records'); END;

CREATE TRIGGER validate_engine_fitment_evidence_update
BEFORE UPDATE OF variant_id,engine_id,evidence_id ON engine_fitments
WHEN NOT EXISTS (
  SELECT 1
  FROM vehicle_catalog_evidence e
  JOIN vehicle_catalog_sources s ON s.source_id=e.source_id
  JOIN vehicle_catalog_source_rights r ON r.source_id=e.source_id
  JOIN vehicle_variants v ON v.variant_id=NEW.variant_id
  JOIN vehicle_generations g ON g.generation_id=v.generation_id
  JOIN vehicle_models m ON m.model_id=g.model_id
  JOIN vehicle_makes mk ON mk.make_id=m.make_id
  JOIN engine_codes ec ON ec.engine_id=NEW.engine_id
  WHERE e.evidence_id=NEW.evidence_id
    AND e.claim_type IN ('engine_fitment','engine_transmission_pair')
    AND e.review_status IN ('technically_verified','publication_approved')
    AND e.market_scope=v.market_scope
    AND e.applicability_precision IN ('exact_engine','exact_pairing')
    AND e.document_revision IS NOT NULL AND length(trim(e.document_revision))>0
    AND e.source_sha256 IS NOT NULL AND length(e.source_sha256)=64 AND e.source_sha256 NOT GLOB '*[^a-f0-9]*'
    AND e.evidence_locator IS NOT NULL AND length(trim(e.evidence_locator))>0
    AND e.reviewed_at_utc IS NOT NULL AND length(trim(e.reviewed_at_utc))>0
    AND e.reviewer_note IS NOT NULL AND length(trim(e.reviewer_note))>0
    AND (s.market_scope=e.market_scope OR (s.market_scope='EAEU' AND e.market_scope IN ('RU','EAEU')) OR s.market_scope='MULTI')
    AND s.redistribution_allowed=1
    AND s.license_status IN ('cc0','public_domain','open_license','permission_granted')
    AND r.rights_status='approved'
    AND r.commercial_use_allowed=1 AND r.display_allowed=1
    AND r.offline_cache_allowed=1 AND r.bulk_reuse_allowed=1
    AND r.store_structured_data_allowed=1
    AND r.license_text_sha256 IS NOT NULL AND length(r.license_text_sha256)=64 AND r.license_text_sha256 NOT GLOB '*[^a-f0-9]*'
    AND r.rights_revision IS NOT NULL AND length(trim(r.rights_revision))>0
    AND r.reviewed_at_utc IS NOT NULL AND length(trim(r.reviewed_at_utc))>0
    AND ec.status IN ('verified','published')
    AND v.status IN ('verified','published')
    AND g.status IN ('verified','published')
    AND m.status IN ('verified','published')
    AND mk.status IN ('verified','published')
)
BEGIN SELECT RAISE(ABORT, 'engine fitment update requires technically verified exact-market evidence, cleared rights and verified parent records'); END;

CREATE TRIGGER validate_transmission_fitment_evidence
BEFORE INSERT ON transmission_fitments
WHEN NOT EXISTS (
  SELECT 1
  FROM vehicle_catalog_evidence e
  JOIN vehicle_catalog_sources s ON s.source_id=e.source_id
  JOIN vehicle_catalog_source_rights r ON r.source_id=e.source_id
  JOIN vehicle_variants v ON v.variant_id=NEW.variant_id
  JOIN vehicle_generations g ON g.generation_id=v.generation_id
  JOIN vehicle_models m ON m.model_id=g.model_id
  JOIN vehicle_makes mk ON mk.make_id=m.make_id
  JOIN transmission_codes tc ON tc.transmission_id=NEW.transmission_id
  WHERE e.evidence_id=NEW.evidence_id
    AND e.claim_type IN ('transmission_fitment','engine_transmission_pair')
    AND e.review_status IN ('technically_verified','publication_approved')
    AND e.market_scope=v.market_scope
    AND e.applicability_precision IN ('exact_transmission','exact_pairing')
    AND e.document_revision IS NOT NULL AND length(trim(e.document_revision))>0
    AND e.source_sha256 IS NOT NULL AND length(e.source_sha256)=64 AND e.source_sha256 NOT GLOB '*[^a-f0-9]*'
    AND e.evidence_locator IS NOT NULL AND length(trim(e.evidence_locator))>0
    AND e.reviewed_at_utc IS NOT NULL AND length(trim(e.reviewed_at_utc))>0
    AND e.reviewer_note IS NOT NULL AND length(trim(e.reviewer_note))>0
    AND (s.market_scope=e.market_scope OR (s.market_scope='EAEU' AND e.market_scope IN ('RU','EAEU')) OR s.market_scope='MULTI')
    AND s.redistribution_allowed=1
    AND s.license_status IN ('cc0','public_domain','open_license','permission_granted')
    AND r.rights_status='approved'
    AND r.commercial_use_allowed=1 AND r.display_allowed=1
    AND r.offline_cache_allowed=1 AND r.bulk_reuse_allowed=1
    AND r.store_structured_data_allowed=1
    AND r.license_text_sha256 IS NOT NULL AND length(r.license_text_sha256)=64 AND r.license_text_sha256 NOT GLOB '*[^a-f0-9]*'
    AND r.rights_revision IS NOT NULL AND length(trim(r.rights_revision))>0
    AND r.reviewed_at_utc IS NOT NULL AND length(trim(r.reviewed_at_utc))>0
    AND tc.status IN ('verified','published')
    AND v.status IN ('verified','published')
    AND g.status IN ('verified','published')
    AND m.status IN ('verified','published')
    AND mk.status IN ('verified','published')
)
BEGIN SELECT RAISE(ABORT, 'transmission fitment requires technically verified exact-market evidence, cleared rights and verified parent records'); END;

CREATE TRIGGER validate_transmission_fitment_evidence_update
BEFORE UPDATE OF variant_id,transmission_id,evidence_id ON transmission_fitments
WHEN NOT EXISTS (
  SELECT 1
  FROM vehicle_catalog_evidence e
  JOIN vehicle_catalog_sources s ON s.source_id=e.source_id
  JOIN vehicle_catalog_source_rights r ON r.source_id=e.source_id
  JOIN vehicle_variants v ON v.variant_id=NEW.variant_id
  JOIN vehicle_generations g ON g.generation_id=v.generation_id
  JOIN vehicle_models m ON m.model_id=g.model_id
  JOIN vehicle_makes mk ON mk.make_id=m.make_id
  JOIN transmission_codes tc ON tc.transmission_id=NEW.transmission_id
  WHERE e.evidence_id=NEW.evidence_id
    AND e.claim_type IN ('transmission_fitment','engine_transmission_pair')
    AND e.review_status IN ('technically_verified','publication_approved')
    AND e.market_scope=v.market_scope
    AND e.applicability_precision IN ('exact_transmission','exact_pairing')
    AND e.document_revision IS NOT NULL AND length(trim(e.document_revision))>0
    AND e.source_sha256 IS NOT NULL AND length(e.source_sha256)=64 AND e.source_sha256 NOT GLOB '*[^a-f0-9]*'
    AND e.evidence_locator IS NOT NULL AND length(trim(e.evidence_locator))>0
    AND e.reviewed_at_utc IS NOT NULL AND length(trim(e.reviewed_at_utc))>0
    AND e.reviewer_note IS NOT NULL AND length(trim(e.reviewer_note))>0
    AND (s.market_scope=e.market_scope OR (s.market_scope='EAEU' AND e.market_scope IN ('RU','EAEU')) OR s.market_scope='MULTI')
    AND s.redistribution_allowed=1
    AND s.license_status IN ('cc0','public_domain','open_license','permission_granted')
    AND r.rights_status='approved'
    AND r.commercial_use_allowed=1 AND r.display_allowed=1
    AND r.offline_cache_allowed=1 AND r.bulk_reuse_allowed=1
    AND r.store_structured_data_allowed=1
    AND r.license_text_sha256 IS NOT NULL AND length(r.license_text_sha256)=64 AND r.license_text_sha256 NOT GLOB '*[^a-f0-9]*'
    AND r.rights_revision IS NOT NULL AND length(trim(r.rights_revision))>0
    AND r.reviewed_at_utc IS NOT NULL AND length(trim(r.reviewed_at_utc))>0
    AND tc.status IN ('verified','published')
    AND v.status IN ('verified','published')
    AND g.status IN ('verified','published')
    AND m.status IN ('verified','published')
    AND mk.status IN ('verified','published')
)
BEGIN SELECT RAISE(ABORT, 'transmission fitment update requires technically verified exact-market evidence, cleared rights and verified parent records'); END;

CREATE TRIGGER validate_powertrain_pair_evidence
BEFORE INSERT ON powertrain_pair_evidence
WHEN NOT EXISTS (
  SELECT 1
  FROM vehicle_catalog_evidence e
  JOIN vehicle_catalog_sources s ON s.source_id=e.source_id
  JOIN vehicle_catalog_source_rights r ON r.source_id=e.source_id
  JOIN vehicle_variants v ON v.variant_id=NEW.variant_id
  JOIN vehicle_generations g ON g.generation_id=v.generation_id
  JOIN vehicle_models m ON m.model_id=g.model_id
  JOIN vehicle_makes mk ON mk.make_id=m.make_id
  JOIN engine_codes ec ON ec.engine_id=NEW.engine_id
  JOIN transmission_codes tc ON tc.transmission_id=NEW.transmission_id
  WHERE e.evidence_id=NEW.evidence_id
    AND e.claim_type='engine_transmission_pair'
    AND e.review_status IN ('technically_verified','publication_approved')
    AND e.market_scope=v.market_scope
    AND e.applicability_precision='exact_pairing'
    AND e.document_revision IS NOT NULL AND length(trim(e.document_revision))>0
    AND e.source_sha256 IS NOT NULL AND length(e.source_sha256)=64 AND e.source_sha256 NOT GLOB '*[^a-f0-9]*'
    AND e.evidence_locator IS NOT NULL AND length(trim(e.evidence_locator))>0
    AND e.reviewed_at_utc IS NOT NULL AND length(trim(e.reviewed_at_utc))>0
    AND e.reviewer_note IS NOT NULL AND length(trim(e.reviewer_note))>0
    AND (s.market_scope=e.market_scope OR (s.market_scope='EAEU' AND e.market_scope IN ('RU','EAEU')) OR s.market_scope='MULTI')
    AND s.redistribution_allowed=1
    AND s.license_status IN ('cc0','public_domain','open_license','permission_granted')
    AND r.rights_status='approved'
    AND r.commercial_use_allowed=1 AND r.display_allowed=1
    AND r.offline_cache_allowed=1 AND r.bulk_reuse_allowed=1
    AND r.store_structured_data_allowed=1
    AND r.license_text_sha256 IS NOT NULL AND length(r.license_text_sha256)=64 AND r.license_text_sha256 NOT GLOB '*[^a-f0-9]*'
    AND r.rights_revision IS NOT NULL AND length(trim(r.rights_revision))>0
    AND r.reviewed_at_utc IS NOT NULL AND length(trim(r.reviewed_at_utc))>0
    AND ec.status IN ('verified','published')
    AND tc.status IN ('verified','published')
    AND v.status IN ('verified','published')
    AND g.status IN ('verified','published')
    AND m.status IN ('verified','published')
    AND mk.status IN ('verified','published')
)
BEGIN SELECT RAISE(ABORT, 'powertrain pair requires same-variant exact-pair evidence, cleared rights and verified parent records'); END;

CREATE TRIGGER validate_powertrain_pair_evidence_update
BEFORE UPDATE OF variant_id,engine_id,transmission_id,evidence_id ON powertrain_pair_evidence
WHEN NOT EXISTS (
  SELECT 1
  FROM vehicle_catalog_evidence e
  JOIN vehicle_catalog_sources s ON s.source_id=e.source_id
  JOIN vehicle_catalog_source_rights r ON r.source_id=e.source_id
  JOIN vehicle_variants v ON v.variant_id=NEW.variant_id
  JOIN vehicle_generations g ON g.generation_id=v.generation_id
  JOIN vehicle_models m ON m.model_id=g.model_id
  JOIN vehicle_makes mk ON mk.make_id=m.make_id
  JOIN engine_codes ec ON ec.engine_id=NEW.engine_id
  JOIN transmission_codes tc ON tc.transmission_id=NEW.transmission_id
  WHERE e.evidence_id=NEW.evidence_id
    AND e.claim_type='engine_transmission_pair'
    AND e.review_status IN ('technically_verified','publication_approved')
    AND e.market_scope=v.market_scope
    AND e.applicability_precision='exact_pairing'
    AND e.document_revision IS NOT NULL AND length(trim(e.document_revision))>0
    AND e.source_sha256 IS NOT NULL AND length(e.source_sha256)=64 AND e.source_sha256 NOT GLOB '*[^a-f0-9]*'
    AND e.evidence_locator IS NOT NULL AND length(trim(e.evidence_locator))>0
    AND e.reviewed_at_utc IS NOT NULL AND length(trim(e.reviewed_at_utc))>0
    AND e.reviewer_note IS NOT NULL AND length(trim(e.reviewer_note))>0
    AND (s.market_scope=e.market_scope OR (s.market_scope='EAEU' AND e.market_scope IN ('RU','EAEU')) OR s.market_scope='MULTI')
    AND s.redistribution_allowed=1
    AND s.license_status IN ('cc0','public_domain','open_license','permission_granted')
    AND r.rights_status='approved'
    AND r.commercial_use_allowed=1 AND r.display_allowed=1
    AND r.offline_cache_allowed=1 AND r.bulk_reuse_allowed=1
    AND r.store_structured_data_allowed=1
    AND r.license_text_sha256 IS NOT NULL AND length(r.license_text_sha256)=64 AND r.license_text_sha256 NOT GLOB '*[^a-f0-9]*'
    AND r.rights_revision IS NOT NULL AND length(trim(r.rights_revision))>0
    AND r.reviewed_at_utc IS NOT NULL AND length(trim(r.reviewed_at_utc))>0
    AND ec.status IN ('verified','published')
    AND tc.status IN ('verified','published')
    AND v.status IN ('verified','published')
    AND g.status IN ('verified','published')
    AND m.status IN ('verified','published')
    AND mk.status IN ('verified','published')
)
BEGIN SELECT RAISE(ABORT, 'powertrain pair update requires same-variant exact-pair evidence, cleared rights and verified parent records'); END;

-- Evidence can only advance through explicit review stages. Technical verification
-- requires exact market scope, document revision/hash, a precise claim and approved rights.
CREATE TRIGGER validate_vehicle_catalog_evidence_review_transition
BEFORE UPDATE OF review_status ON vehicle_catalog_evidence
WHEN NEW.review_status<>OLD.review_status
BEGIN
  SELECT CASE WHEN NOT (
    NEW.review_status='candidate'
    OR (OLD.review_status='candidate' AND NEW.review_status IN ('source_checked','rejected'))
    OR (OLD.review_status='source_checked' AND NEW.review_status IN ('technically_verified','rejected'))
    OR (OLD.review_status='technically_verified' AND NEW.review_status IN ('publication_approved','rejected'))
    OR (OLD.review_status='publication_approved' AND NEW.review_status='rejected')
    OR (OLD.review_status IN ('source_checked','technically_verified','publication_approved') AND NEW.review_status='candidate')
    OR (OLD.review_status='rejected' AND NEW.review_status='candidate')
  ) THEN RAISE(ABORT, 'invalid vehicle catalog evidence review-state transition') END;

  SELECT CASE WHEN NEW.review_status IN ('source_checked','technically_verified','publication_approved')
    AND (
      NEW.document_revision IS NULL OR length(trim(NEW.document_revision))=0
      OR NEW.source_sha256 IS NULL OR length(NEW.source_sha256)<>64
      OR NEW.source_sha256 GLOB '*[^a-f0-9]*'
      OR NEW.evidence_locator IS NULL OR length(trim(NEW.evidence_locator))=0
      OR NEW.market_scope='UNKNOWN' OR NEW.applicability_precision='unknown'
      OR NEW.reviewed_at_utc IS NULL OR length(trim(NEW.reviewed_at_utc))=0
      OR NEW.reviewer_note IS NULL OR length(trim(NEW.reviewer_note))=0
    ) THEN RAISE(ABORT, 'reviewed vehicle evidence requires document revision, SHA-256, market, precision, locator and review note') END;

  SELECT CASE WHEN NEW.review_status IN ('technically_verified','publication_approved')
    AND NOT EXISTS (
      SELECT 1 FROM vehicle_catalog_sources s
      JOIN vehicle_catalog_source_rights r ON r.source_id=s.source_id
      WHERE s.source_id=NEW.source_id
        AND (s.market_scope=NEW.market_scope OR (s.market_scope='EAEU' AND NEW.market_scope IN ('RU','EAEU')) OR s.market_scope='MULTI')
        AND s.redistribution_allowed=1
        AND s.license_status IN ('cc0','public_domain','open_license','permission_granted')
        AND r.rights_status='approved'
        AND r.commercial_use_allowed=1 AND r.display_allowed=1
        AND r.offline_cache_allowed=1 AND r.bulk_reuse_allowed=1
    AND r.store_structured_data_allowed=1
        AND r.license_text_sha256 IS NOT NULL AND length(r.license_text_sha256)=64 AND r.license_text_sha256 NOT GLOB '*[^a-f0-9]*'
        AND r.rights_revision IS NOT NULL AND length(trim(r.rights_revision))>0
        AND r.reviewed_at_utc IS NOT NULL AND length(trim(r.reviewed_at_utc))>0
    ) THEN RAISE(ABORT, 'technical verification requires approved source rights for this market and offline product use') END;

  SELECT CASE WHEN NEW.review_status IN ('technically_verified','publication_approved')
    AND NOT (
      (NEW.claim_type='make' AND NEW.applicability_precision='make_only')
      OR (NEW.claim_type='model' AND NEW.applicability_precision='model_only')
      OR (NEW.claim_type='generation' AND NEW.applicability_precision='generation')
      OR (NEW.claim_type='variant' AND NEW.applicability_precision='variant')
      OR (NEW.claim_type IN ('engine_code','engine_fitment') AND NEW.applicability_precision='exact_engine')
      OR (NEW.claim_type IN ('transmission_code','transmission_fitment') AND NEW.applicability_precision='exact_transmission')
      OR (NEW.claim_type='engine_transmission_pair' AND NEW.applicability_precision='exact_pairing')
      OR (NEW.claim_type='ecu_fitment' AND NEW.applicability_precision='exact_ecu')
      OR (NEW.claim_type='dtc_applicability' AND NEW.applicability_precision IN ('exact_ecu','exact_configuration'))
      OR (NEW.claim_type='repair_document_applicability' AND NEW.applicability_precision='exact_configuration')
      OR (NEW.claim_type IN ('market_scope','vin_range') AND NEW.applicability_precision='exact_configuration')
    ) THEN RAISE(ABORT, 'technical verification requires claim-specific applicability precision') END;

  SELECT CASE WHEN NEW.review_status='publication_approved' AND OLD.review_status<>'technically_verified'
    THEN RAISE(ABORT, 'publication approval requires prior technical verification') END;
END;

CREATE TRIGGER prevent_verified_vehicle_catalog_evidence_mutation
BEFORE UPDATE ON vehicle_catalog_evidence
WHEN OLD.review_status IN ('technically_verified','publication_approved')
  AND NEW.review_status<>'candidate'
  AND (
    NEW.source_id IS NOT OLD.source_id
    OR NEW.document_id IS NOT OLD.document_id
    OR NEW.document_revision IS NOT OLD.document_revision
    OR NEW.issue_date IS NOT OLD.issue_date
    OR NEW.retrieved_at_utc IS NOT OLD.retrieved_at_utc
    OR NEW.evidence_locator IS NOT OLD.evidence_locator
    OR NEW.source_sha256 IS NOT OLD.source_sha256
    OR NEW.market_scope IS NOT OLD.market_scope
    OR NEW.applicability_precision IS NOT OLD.applicability_precision
    OR NEW.claim_type IS NOT OLD.claim_type
  )
BEGIN
  SELECT RAISE(ABORT, 'verified vehicle evidence is immutable; demote to candidate before correction');
END;

CREATE TRIGGER vehicle_catalog_evidence_publication_insert_requires_guarded_transition
BEFORE INSERT ON vehicle_catalog_evidence
WHEN NEW.review_status='publication_approved'
BEGIN
  SELECT RAISE(ABORT, 'vehicle catalog evidence publication must use guarded review-status transition');
END;

-- A model-year range alone is not an engine or transmission fitment claim.


-- Publication approval must pass through the UPDATE trigger so source rights are checked.
CREATE TRIGGER IF NOT EXISTS vehicle_catalog_evidence_publication_insert_requires_guarded_transition
BEFORE INSERT ON vehicle_catalog_evidence
WHEN NEW.review_status='publication_approved'
BEGIN
  SELECT RAISE(ABORT, 'vehicle catalog evidence publication must use guarded review-status transition');
END;

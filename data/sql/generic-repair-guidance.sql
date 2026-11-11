PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS pack_metadata (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS source_registry (
  source_id TEXT PRIMARY KEY,
  publisher TEXT NOT NULL,
  repository_url TEXT NOT NULL,
  source_revision TEXT NOT NULL,
  data_license TEXT NOT NULL CHECK (data_license='ODbL-1.0'),
  license_url TEXT NOT NULL,
  rights_status TEXT NOT NULL CHECK (rights_status='approved_by_published_license'),
  commercial_use_allowed INTEGER NOT NULL CHECK (commercial_use_allowed=1),
  display_allowed INTEGER NOT NULL CHECK (display_allowed=1),
  offline_cache_allowed INTEGER NOT NULL CHECK (offline_cache_allowed=1),
  redistribution_allowed INTEGER NOT NULL CHECK (redistribution_allowed=1),
  share_alike_required INTEGER NOT NULL CHECK (share_alike_required=1),
  attribution_required INTEGER NOT NULL CHECK (attribution_required=1),
  attribution_text TEXT NOT NULL,
  market_scope TEXT NOT NULL CHECK (market_scope='UNKNOWN'),
  applicability_precision TEXT NOT NULL CHECK (applicability_precision='generic_code_only'),
  technical_review_status TEXT NOT NULL CHECK (technical_review_status='not_independently_reviewed'),
  safety_review_status TEXT NOT NULL CHECK (safety_review_status='not_assessed')
);

CREATE TABLE IF NOT EXISTS source_files (
  source_file_id TEXT PRIMARY KEY,
  source_id TEXT NOT NULL REFERENCES source_registry(source_id),
  source_url TEXT NOT NULL,
  git_blob_sha1 TEXT NOT NULL CHECK (length(git_blob_sha1)=40 AND git_blob_sha1 NOT GLOB '*[^a-f0-9]*'),
  sha256 TEXT NOT NULL CHECK (length(sha256)=64 AND sha256 NOT GLOB '*[^a-f0-9]*'),
  byte_size INTEGER NOT NULL CHECK (byte_size > 0),
  record_count INTEGER,
  purpose TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS generic_dtc_references (
  dtc_code TEXT PRIMARY KEY CHECK (
    length(dtc_code)=5 AND substr(dtc_code,1,1) IN ('P','B','C','U')
  ),
  source_record_id TEXT NOT NULL,
  system_category TEXT NOT NULL,
  namespace TEXT NOT NULL CHECK (namespace='generic_sae_iso'),
  manufacturer TEXT NOT NULL CHECK (manufacturer='UNKNOWN'),
  market_scope TEXT NOT NULL CHECK (market_scope='UNKNOWN'),
  applicability_level TEXT NOT NULL CHECK (applicability_level='generic_only'),
  vag_specific INTEGER NOT NULL CHECK (vag_specific=0),
  diagnostic_execution_allowed INTEGER NOT NULL CHECK (diagnostic_execution_allowed=0),
  technical_review_status TEXT NOT NULL CHECK (technical_review_status='not_independently_reviewed'),
  source_file_id TEXT NOT NULL REFERENCES source_files(source_file_id),
  source_revision TEXT NOT NULL,
  source_file_sha256 TEXT NOT NULL CHECK (length(source_file_sha256)=64 AND source_file_sha256 NOT GLOB '*[^a-f0-9]*'),
  source_line_no INTEGER NOT NULL CHECK (source_line_no > 1),
  source_line_sha256 TEXT NOT NULL CHECK (length(source_line_sha256)=64 AND source_line_sha256 NOT GLOB '*[^a-f0-9]*')
);

CREATE TABLE IF NOT EXISTS generic_repair_guidance (
  guidance_id TEXT PRIMARY KEY,
  dtc_code TEXT NOT NULL REFERENCES generic_dtc_references(dtc_code),
  consideration_order INTEGER NOT NULL CHECK (consideration_order > 0),
  skill_level TEXT NOT NULL,
  title TEXT NOT NULL,
  instructions TEXT NOT NULL,
  action_type TEXT,
  rationale TEXT,
  namespace TEXT NOT NULL CHECK (namespace='generic_sae_iso'),
  manufacturer TEXT NOT NULL CHECK (manufacturer='UNKNOWN'),
  market_scope TEXT NOT NULL CHECK (market_scope='UNKNOWN'),
  applicability_level TEXT NOT NULL CHECK (applicability_level='generic_only'),
  vag_specific INTEGER NOT NULL CHECK (vag_specific=0),
  diagnostic_execution_allowed INTEGER NOT NULL CHECK (diagnostic_execution_allowed=0),
  technical_review_status TEXT NOT NULL CHECK (technical_review_status='not_independently_reviewed'),
  safety_review_status TEXT NOT NULL CHECK (safety_review_status='not_assessed'),
  source_file_id TEXT NOT NULL REFERENCES source_files(source_file_id),
  source_revision TEXT NOT NULL,
  source_file_sha256 TEXT NOT NULL CHECK (length(source_file_sha256)=64 AND source_file_sha256 NOT GLOB '*[^a-f0-9]*'),
  source_line_no INTEGER NOT NULL CHECK (source_line_no > 1),
  source_line_sha256 TEXT NOT NULL CHECK (length(source_line_sha256)=64 AND source_line_sha256 NOT GLOB '*[^a-f0-9]*'),
  source_license TEXT NOT NULL CHECK (source_license='ODbL-1.0')
);

CREATE INDEX IF NOT EXISTS idx_generic_guidance_code_order
  ON generic_repair_guidance(dtc_code, consideration_order);

CREATE TRIGGER IF NOT EXISTS immutable_generic_dtc_references
BEFORE UPDATE ON generic_dtc_references
BEGIN
  SELECT RAISE(ABORT, 'research source pack is immutable; create a reviewed successor pack');
END;

CREATE TRIGGER IF NOT EXISTS immutable_generic_repair_guidance
BEFORE UPDATE ON generic_repair_guidance
BEGIN
  SELECT RAISE(ABORT, 'research source pack is immutable; create a reviewed successor pack');
END;

CREATE TRIGGER IF NOT EXISTS immutable_source_registry
BEFORE UPDATE ON source_registry
BEGIN
  SELECT RAISE(ABORT, 'source provenance is immutable; create a reviewed successor pack');
END;

import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REGISTRY = json.loads(
    (ROOT / "data" / "source-manifests" / "vag-factory-source-register.json").read_text(encoding="utf-8")
)
LOCK = json.loads(
    (ROOT / "data" / "source-manifests" / "vehiclesdb-vag-identity.lock.json").read_text(encoding="utf-8")
)
SOURCES = {item["source_id"]: item for item in REGISTRY["sources"]}


class VehiclesDbVagIdentitySourceRightsTests(unittest.TestCase):
    def test_cc_by_4_rights_and_attribution_are_explicit(self):
        source = SOURCES["vehiclesdb-vag-identity-cc-by-4.0"]
        rights = source["rights"]
        self.assertEqual(source["release_tag"], LOCK["upstream_tag"])
        self.assertEqual(LOCK["upstream_tag"], "v2026.11.3")
        self.assertEqual(rights["data_license"], "CC-BY-4.0")
        for key in ("commercial_use_allowed", "display_allowed", "offline_cache_allowed",
                    "redistribution_allowed", "attribution_required", "unconditional_upstream_source_notices_required"):
            self.assertIs(rights[key], True)
        self.assertIs(rights["share_alike_required"], False)
        self.assertIn("Vehicle data by VehiclesDB", rights["attribution"])
        self.assertTrue(source["source_snapshot_sha256"])
        self.assertTrue(source["upstream_catalog_sha256"])
        self.assertTrue(source["upstream_manifest_sha256"])
        self.assertTrue(source["attribution_file_sha256"])
        self.assertTrue(source["license_file_sha256"])
        pinned = LOCK["expected_source_files"]
        self.assertEqual(set(pinned), {"catalog.sqlite", "manifest.json", "ATTRIBUTION.md", "LICENSE"})
        self.assertEqual(pinned["catalog.sqlite"]["sha256"], source["upstream_catalog_sha256"])
        self.assertEqual(pinned["manifest.json"]["sha256"], source["upstream_manifest_sha256"])
        self.assertEqual(pinned["ATTRIBUTION.md"]["sha256"], source["attribution_file_sha256"])
        self.assertEqual(pinned["LICENSE"]["sha256"], source["license_file_sha256"])
        self.assertTrue(all(item["byte_size"] > 0 for item in pinned.values()))
        self.assertEqual(source["upstream_source_files"], pinned)
        self.assertEqual(
            source["source_snapshot_sha256"],
            hashlib.sha256(json.dumps(pinned, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest(),
        )
        self.assertIn("canonical UTF-8 JSON", source["source_snapshot_digest_method"])
        self.assertTrue(source["identity_only_use"])
        self.assertFalse(source["safety_critical_reliance"])
        self.assertFalse(source["repair_decision_use"])
        self.assertIn("not designed or warranted for safety-critical", source["open_data_policy_notice"])
        research = source["research_pack"]
        self.assertEqual(research["status"], "built_and_verified")
        self.assertEqual(research["upstream_tag"], LOCK["upstream_tag"])
        self.assertEqual(research["counts"], {
            "approved_source_registers": 14,
            "model_name_candidates": 307,
            "market_presence_evidence_rows": 1621,
        })
        self.assertEqual(research["source_manifest_sha256"], source["upstream_manifest_sha256"])
        self.assertEqual(research["source_catalog_sha256"], source["upstream_catalog_sha256"])
        self.assertEqual(research["market_scope"], source["market_scope"])
        self.assertFalse(source["data_ingested"])
        for key in ("artifact_sha256", "database_sha256", "source_manifest_sha256", "source_catalog_sha256", "lock_sha256"):
            self.assertRegex(research[key], r"^[0-9a-f]{64}$")
        self.assertEqual(research["workflow_run_id"], 42874459366)
        self.assertGreater(research["artifact_size_bytes"], 0)
        bundle = source["offline_bundle"]
        self.assertEqual(bundle["status"], "verified_offline_research_bundle_not_installer")
        self.assertEqual(bundle["workflow_run_number"], 573)
        self.assertEqual(bundle["workflow_run_id"], 42874459366)
        self.assertEqual(bundle["target_platform"], "windows-x64")
        self.assertEqual(bundle["separate_database_count"], 3)
        self.assertEqual(bundle["pack_ids"], ["obdb-vag-signals-cc-by-sa", "obdex-generic-cc0", "vehiclesdb-vag-identity"])
        self.assertEqual(bundle["vehiclesdb_database_sha256"], research["database_sha256"])
        self.assertEqual(bundle["vehiclesdb_upstream_catalog_sha256"], source["upstream_catalog_sha256"])
        self.assertEqual(bundle["obdb_database_sha256"], "1a5cb45b03ab9439251d329de57d667ebea3e67b1a2b2dd9aa5333c14f2ed195")
        for key in ("artifact_sha256", "vehiclesdb_database_sha256", "vehiclesdb_upstream_catalog_sha256", "obdb_database_sha256"):
            self.assertRegex(bundle[key], r"^[0-9a-f]{64}$")
        self.assertGreater(bundle["artifact_size_bytes"], 0)

    def test_foreign_market_scope_is_not_misrepresented_as_ru_eaeu(self):
        source = SOURCES["vehiclesdb-vag-identity-cc-by-4.0"]
        self.assertEqual(
            source["market_scope"],
            ["AR", "AU", "CA", "DE", "ES", "FI", "GB", "IE", "LU", "MY", "NL", "NZ", "UA", "US"],
        )
        self.assertIs(source["ru_eaeu_market_evidence_present"], False)
        self.assertEqual(source["market_scope_policy"], "per_record_country_evidence_only")
        self.assertNotIn("RU", source["market_scope"])
        self.assertNotIn("KZ", source["market_scope"])
        self.assertNotIn("BY", source["market_scope"])
        self.assertEqual(source["verification_status"], "identity_candidate")

    def test_no_exact_fitment_or_repair_claims(self):
        source = SOURCES["vehiclesdb-vag-identity-cc-by-4.0"]
        scope = source["technical_scope"]
        for key in ("exact_vehicle_fitment", "generation_data", "production_years", "engine_codes",
                    "gearbox_codes", "ecu_fitment", "pr_code_fitment", "dtc_definitions",
                    "repair_procedures", "wiring_diagrams", "diagnostic_execution_allowed",
                    "ru_eaeu_market_evidence"):
            self.assertIs(scope[key], False)
        self.assertEqual(source["counts"]["model_name_candidates"], 307)
        self.assertEqual(source["counts"]["market_presence_evidence_rows"], 1621)
        self.assertEqual(source["applicability_precision"], "make_model_name_only_and_market_presence_only")

    def test_locked_upstream_manifest_matches_scope_and_licence(self):
        self.assertEqual(LOCK["dataset_id"], "vehiclesdb-vag-identity-cc-by-4.0")
        self.assertEqual(LOCK["data_license"], "CC-BY-4.0")
        self.assertEqual(LOCK["upstream_tag"], "v2026.11.3")
        self.assertIs(LOCK["scope"]["fitment_claim"], False)
        self.assertIs(LOCK["scope"]["ru_eaeu_market_evidence_expected"], False)
        self.assertEqual(LOCK["expected_counts"]["models"], 307)
        self.assertEqual(LOCK["expected_counts"]["market_evidence"], 1621)
        self.assertTrue(LOCK["build_policy"]["identity_only_use"])
        self.assertFalse(LOCK["build_policy"]["safety_critical_reliance"])
        self.assertFalse(LOCK["build_policy"]["repair_decision_use"])
        self.assertIn("il_mot", LOCK["excluded_source_reasons"])
        self.assertIn("th_dlt", LOCK["excluded_source_reasons"])
        self.assertIn("de_kba_nfz", LOCK["excluded_source_reasons"])


if __name__ == "__main__":
    unittest.main()

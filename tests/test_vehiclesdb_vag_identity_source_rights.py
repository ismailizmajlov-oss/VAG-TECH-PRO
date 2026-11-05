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
        self.assertEqual(source["release_tag"], "v2026.10.3")
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
        self.assertEqual(
            set(pinned),
            {"catalog.sqlite", "manifest.json", "ATTRIBUTION.md", "LICENSE"},
        )
        self.assertEqual(pinned["catalog.sqlite"]["sha256"], source["upstream_catalog_sha256"])
        self.assertEqual(pinned["manifest.json"]["sha256"], source["upstream_manifest_sha256"])
        self.assertEqual(pinned["ATTRIBUTION.md"]["sha256"], source["attribution_file_sha256"])
        self.assertEqual(pinned["LICENSE"]["sha256"], source["license_file_sha256"])
        self.assertTrue(all(item["byte_size"] > 0 for item in pinned.values()))

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
        self.assertEqual(source["counts"]["model_name_candidates"], 260)
        self.assertEqual(source["counts"]["market_presence_evidence_rows"], 1524)
        self.assertEqual(source["applicability_precision"], "make_model_name_only_and_market_presence_only")

    def test_locked_upstream_manifest_matches_scope_and_licence(self):
        self.assertEqual(LOCK["dataset_id"], "vehiclesdb-vag-identity-cc-by-4.0")
        self.assertEqual(LOCK["data_license"], "CC-BY-4.0")
        self.assertEqual(LOCK["upstream_tag"], "v2026.10.3")
        self.assertIs(LOCK["scope"]["fitment_claim"], False)
        self.assertIs(LOCK["scope"]["ru_eaeu_market_evidence_expected"], False)
        self.assertEqual(LOCK["expected_counts"]["models"], 260)
        self.assertEqual(LOCK["expected_counts"]["market_evidence"], 1524)
        self.assertIn("il_mot", LOCK["excluded_source_reasons"])
        self.assertIn("th_dlt", LOCK["excluded_source_reasons"])


if __name__ == "__main__":
    unittest.main()

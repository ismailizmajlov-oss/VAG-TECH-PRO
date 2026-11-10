import json
import unittest
from pathlib import Path


class OwnerSpecsSourceRightsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]
        cls.manifest = json.loads(
            (cls.root / "data" / "source-manifests" / "ownerspecs-verified-vehicle-specs-cc-by-sa-4.0.json").read_text(encoding="utf-8")
        )
        cls.registry = json.loads(
            (cls.root / "data" / "source-manifests" / "vag-factory-source-register.json").read_text(encoding="utf-8")
        )
        cls.review = (
            cls.root / "docs" / "research" / "OWNERSPECS_VAG_DATASET_RIGHTS_REVIEW_2026-11-10.md"
        ).read_text(encoding="utf-8").casefold()
        matches = [
            item for item in cls.registry["sources"]
            if item.get("source_id") == "ownerspecs-verified-vehicle-specs-cc-by-sa-4.0"
        ]
        if len(matches) != 1:
            raise AssertionError("OwnerSpecs must have exactly one central source-register entry")
        cls.entry = matches[0]

    def test_published_cc_by_sa_license_allows_separate_commercial_research_pack(self):
        rights = self.manifest["rights"]
        self.assertEqual(rights["rights_status"], "approved_by_published_CC_BY_SA_4_0_for_separate_research_pack")
        self.assertEqual(rights["license_id"], "CC-BY-SA-4.0")
        for field in (
            "commercial_use_allowed", "display_allowed", "offline_cache_allowed",
            "bulk_reuse_allowed", "redistribution_allowed", "attribution_required",
            "share_alike_required", "separate_pack_required",
        ):
            self.assertIs(rights[field], True)
        self.assertIn("ownerspecs.com", rights["attribution_text"])
        self.assertIn("CC BY-SA 4.0", rights["attribution_text"])

    def test_live_html_and_json_generation_counts_are_reconciled(self):
        snapshot = self.manifest["snapshot"]
        self.assertEqual(snapshot["html_page_generation_count"], 111)
        self.assertEqual(snapshot["json_descriptor_generation_count"], 111)
        self.assertEqual(snapshot["html_page_brand_count"], 27)
        self.assertEqual(snapshot["html_page_verified_datapoint_count"], 2369)
        self.assertEqual(snapshot["status"], "source_snapshot_acquired_schema_verified")
        self.assertEqual(snapshot["source_snapshot_sha256"], "7b39e1183bd2a7617d43fdbe1f2ae64662520cb62f89ba8fec4dadbcce79204d")
        self.assertEqual(snapshot["source_file_bytes"], 683641)
        self.assertTrue(snapshot["retrieved_at_utc"].endswith("+00:00"))
        policy = self.manifest["import_policy"]
        self.assertIs(policy["acquisition_allowed"], True)
        self.assertIs(policy["research_pack_import_allowed"], True)
        self.assertIs(policy["product_import_allowed"], False)
        self.assertIs(policy["data_ingested"], False)

    def test_dataset_does_not_establish_exact_vag_repair_applicability(self):
        scope = self.manifest["data_scope"]
        self.assertEqual(scope["normalized_market_scope"], "UNKNOWN")
        self.assertIs(scope["primary_document_locator_per_value_in_json"], False)
        self.assertIs(scope["primary_document_revision_per_value_in_json"], False)
        self.assertIs(scope["source_count_per_value"], True)
        self.assertIs(scope["provenance_kind_per_value"], True)
        applicability = self.manifest["applicability_policy"]
        for field in (
            "model_generation_verified", "model_year_verified",
            "exact_factory_engine_code_mapping", "exact_factory_gearbox_code_mapping",
            "exact_engine_gearbox_pair", "exact_vehicle_fitment",
            "ru_eaeu_applicability", "ecu_fitment", "dtc_fitment",
            "repair_procedure_applicability", "critical_technical_values_publishable",
        ):
            self.assertIs(applicability[field], False)

    def test_central_register_preserves_rights_and_separate_pack_boundary(self):
        rights = self.entry["rights"]
        self.assertEqual(rights["data_license"], "CC-BY-SA-4.0")
        self.assertEqual(rights["permission_status"], "approved_by_published_license_for_reuse")
        for field in (
            "commercial_use_allowed", "display_allowed", "offline_cache_allowed",
            "bulk_reuse_allowed", "redistribution_allowed", "attribution_required",
            "share_alike_required", "separate_pack_required",
        ):
            self.assertIs(rights[field], True)
        self.assertIs(self.entry["data_ingested"], False)
        self.assertEqual(self.entry["source_snapshot_sha256"], self.manifest["snapshot"]["source_snapshot_sha256"])
        self.assertIs(self.entry["research_pack_acquisition_allowed"], True)
        self.assertIs(self.entry["research_pack_acquired"], True)
        self.assertEqual(self.entry["research_pack_artifact_sha256"], "3ac33a190f4621dc1b6fc69f59c90425001fd171b335c10e48268ecd62eaa82f")
        self.assertEqual(self.entry["research_pack_database_sha256"], "eba46aace1e2a28d288e64b2dcb179177ddc577a9b90771d6908d18319c96ecf")
        self.assertEqual(self.entry["research_pack_source_manifest_sha256"], "3cccc31845fad9328db2e81dc70e787552ec192c780c140904baa6c9132abdeb")
        self.assertEqual(self.entry["research_pack_workflow_run_id"], 42736946351)
        self.assertEqual(self.entry["research_pack_artifact_id"], 13727965683)
        self.assertEqual(self.entry["research_pack_run_number"], 31)
        self.assertEqual(self.entry["research_pack_source_commit"], "a1c91b0c6039640be63996571dc0607a33d64948")
        self.assertEqual(self.entry["research_pack_artifact_name"], "ownerspecs-vag-vehicle-specs-research-pack")
        self.assertIs(self.entry["product_database_ingested"], False)
        self.assertIs(self.entry["product_import_allowed"], False)
        self.assertEqual(self.entry["applicability"]["market_scope"], "UNKNOWN")
        self.assertIs(self.entry["applicability"]["exact_engine_gearbox_pair"], False)
        self.assertIs(self.entry["content_review"]["metadata_consistent"], True)

    def test_review_records_current_counts_and_no_unverified_promotion(self):
        for phrase in (
            "111 generations",
            "27 brands",
            "2,369 verified datapoints",
            "current live page/json pair",
            "source snapshot sha-256 is pinned",
            "20 vag generation candidates",
            "233 vag facts",
            "market_scope=unknown",
            "must not be promoted to repair instructions",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, self.review)


if __name__ == "__main__":
    unittest.main()

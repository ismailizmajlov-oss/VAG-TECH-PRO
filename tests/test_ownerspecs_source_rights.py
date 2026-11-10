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
        self.assertEqual(snapshot["source_snapshot_sha256"], "6ed73e4cd634e64501edd3b0e03405afa0aad3b8d1a103f78b839c87c8588c95")
        self.assertEqual(snapshot["source_file_bytes"], 683533)
        self.assertEqual(snapshot["retrieved_at_utc"],"2026-11-10T06:28:05.310530+00:00")
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

    def test_central_register_preserves_rights_and_marks_verified_research_pack_non_production(self):
        rights=self.entry["rights"]
        self.assertEqual(rights["data_license"],"CC-BY-SA-4.0")
        self.assertEqual(rights["permission_status"],"approved_by_published_license_for_reuse")
        for field in ("commercial_use_allowed","display_allowed","offline_cache_allowed","bulk_reuse_allowed","redistribution_allowed","attribution_required","share_alike_required","separate_pack_required"):
            self.assertIs(rights[field],True)
        self.assertFalse(self.entry["data_ingested"])
        self.assertEqual(self.entry["source_snapshot_sha256"],self.manifest["snapshot"]["source_snapshot_sha256"])
        self.assertEqual(self.entry["source_snapshot_sha256"],"6ed73e4cd634e64501edd3b0e03405afa0aad3b8d1a103f78b839c87c8588c95")
        self.assertEqual(self.entry["source_file_bytes"],683533)
        self.assertTrue(self.entry["research_pack_acquisition_allowed"])
        self.assertTrue(self.entry["research_pack_acquired"]); self.assertTrue(self.entry["research_pack_current"])
        self.assertEqual(self.entry["research_pack_status"],"verified_research_only")
        self.assertFalse(self.entry["research_database_included_in_desktop"])
        self.assertEqual(self.entry["research_pack_source_manifest_sha256"],"3d744c8b813508daefaebcd690d10c2cef6d0a731e87eda59015622bffeabbdc")
        self.assertEqual(self.entry["research_pack_workflow_run_id"],42770457166)
        self.assertEqual(self.entry["research_pack_run_number"],115)
        self.assertEqual(self.entry["research_pack_artifact_id"],13742090427)
        self.assertEqual(self.entry["research_pack_artifact_sha256"],"93c4050130a8d372888ffd3126e18d4ef03de434558adfc98f7bb51e0a6918d1")
        self.assertEqual(self.entry["research_pack_database_sha256"],"572455b8054bd93600fb5ef25d38c6aa478a5bc98a0d26d678a220b008d4d683")
        self.assertEqual(self.entry["research_pack_manifest_sha256"],"35bbe697d046891c1f49e8f5a318fa2f6f1afab087a7c20d8718ab4c02c9f6dd")
        self.assertEqual(self.entry["research_pack_artifact_size_bytes"],114062)
        self.assertEqual(self.entry["research_pack_database_byte_size"],323584)
        self.assertEqual(self.entry["research_pack_source_snapshot_sha256"],"6ed73e4cd634e64501edd3b0e03405afa0aad3b8d1a103f78b839c87c8588c95")
        previous=self.entry["previous_verified_research_pack"]
        self.assertEqual(previous["artifact_id"],13733448981); self.assertEqual(previous["artifact_run_number"],64)
        self.assertEqual(previous["source_snapshot_sha256"],"7b39e1183bd2a7617d43fdbe1f2ae64662520cb62f89ba8fec4dadbcce79204d")
        self.assertEqual(previous["database_sha256"],"eba46aace1e2a28d288e64b2dcb179177ddc577a9b90771d6908d18319c96ecf")
        self.assertEqual(self.entry["previous_desktop_lifecycle_evidence"]["run_number"],1208)
        self.assertIsNone(self.entry["desktop_lifecycle_evidence"])
        self.assertEqual(self.entry["research_pack_desktop_integration_status"],"verified_pack_available_desktop_sync_pending")
        self.assertEqual(self.entry["verification_status"],"licensed_source_snapshot_reacquired_pack_built_verified_candidate_only_no_production_import")
        self.assertFalse(self.entry["product_database_ingested"]); self.assertFalse(self.entry["product_import_allowed"])
        self.assertEqual(self.entry["applicability"]["market_scope"],"UNKNOWN")
        self.assertFalse(self.entry["applicability"]["exact_engine_gearbox_pair"])
        self.assertTrue(self.entry["content_review"]["metadata_consistent"])
    def test_review_records_current_counts_and_no_unverified_promotion(self):
        review = self.review.casefold()
        for phrase in ("111 generations","27 brands","2,369 verified datapoints","current live page/json pair","6ed73e4cd634e64501edd3b0e03405afa0aad3b8d1a103f78b839c87c8588c95","vag subset: 20 generation candidates and 233 facts","233 vag facts","five records changed across four generations","four specification values changed","one non-vag unit-only normalization","three are vag","intermediate, unverified claim","market scope remains unknown","must not be promoted to factory engine/gearbox fitment"):
            with self.subTest(phrase=phrase): self.assertIn(phrase.casefold(), review)

    def test_latest_snapshot_review_records_four_value_changes_three_vag_values_and_one_unit_only_change(self):
        review=self.manifest["snapshot"]["latest_snapshot_review"]
        self.assertEqual(review["previous_snapshot_sha256"],"7b39e1183bd2a7617d43fdbe1f2ae64662520cb62f89ba8fec4dadbcce79204d")
        self.assertEqual(review["current_snapshot_sha256"],"6ed73e4cd634e64501edd3b0e03405afa0aad3b8d1a103f78b839c87c8588c95")
        self.assertEqual(review["changed_generations_total"],4); self.assertEqual(review["changed_datapoints_total"],5)
        self.assertEqual(review["vag_changed_generations"],2); self.assertEqual(review["vag_changed_datapoints"],3)
        self.assertEqual(review["non_vag_changed_datapoints"],2)
        self.assertEqual(review["generations_added"],0); self.assertEqual(review["generations_removed"],0)
        self.assertEqual(review["datapoints_added"],0); self.assertEqual(review["datapoints_removed"],0)
        self.assertFalse(review["all_changes_are_range_collapses_to_upper_value"])
        self.assertTrue(review["all_specification_value_changes_are_range_collapses_to_upper_value"])
        self.assertEqual(review["changed_unit_only_records_total"],1)
        self.assertEqual(review["changed_units"][0]["brand"],"Hyundai")
        self.assertEqual(review["changed_units"][0]["old_unit"],"L")
        self.assertEqual(review["changed_units"][0]["new_unit"],"l")
        self.assertFalse(review["primary_document_locator_per_value_in_json"])
        self.assertFalse(review["primary_document_revision_per_value_in_json"])
        self.assertEqual(review["market_scope"],"UNKNOWN"); self.assertFalse(review["critical_repair_values_publishable"])
        self.assertEqual({(x["brand"],x["model"],x["field"]) for x in review["changed_values"] if x["vag"]},{("Audi","A1","co2"),("Audi","A1","fuel_consumption"),("Volkswagen","Polo","co2")})



if __name__ == "__main__":
    unittest.main()

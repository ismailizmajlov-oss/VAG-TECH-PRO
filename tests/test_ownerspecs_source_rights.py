import hashlib
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CURRENT_MANIFEST = ROOT / "data/source-manifests/ownerspecs-verified-vehicle-specs-cc-by-sa-4.0.json"
VERSIONED_MANIFEST = ROOT / "data/source-manifests/history/ownerspecs-verified-vehicle-specs-cc-by-sa-4.0-2026-11-11.json"
PREVIOUS_MANIFEST = ROOT / "data/source-manifests/history/ownerspecs-verified-vehicle-specs-cc-by-sa-4.0-2026-11-10.json"
REGISTER = ROOT / "data/source-manifests/vag-factory-source-register.json"
REVIEW = ROOT / "docs/research/OWNERSPECS_VAG_DATASET_RIGHTS_REVIEW_2026-11-10.md"

class OwnerSpecsSourceRightsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads(CURRENT_MANIFEST.read_text(encoding="utf-8"))
        cls.versioned = json.loads(VERSIONED_MANIFEST.read_text(encoding="utf-8"))
        cls.previous_manifest = json.loads(PREVIOUS_MANIFEST.read_text(encoding="utf-8"))
        registry = json.loads(REGISTER.read_text(encoding="utf-8"))
        entries = [x for x in registry["sources"] if x.get("source_id") == "ownerspecs-verified-vehicle-specs-cc-by-sa-4.0"]
        if len(entries) != 1:
            raise AssertionError("OwnerSpecs must have exactly one central source-register entry")
        cls.entry = entries[0]
        cls.review = REVIEW.read_text(encoding="utf-8").casefold()

    def test_published_cc_by_sa_license_allows_only_a_separate_attributed_sharealike_pack(self):
        rights = self.manifest["rights"]
        self.assertEqual(rights["rights_status"], "approved_by_published_CC_BY_SA_4_0_for_separate_research_pack")
        self.assertEqual(rights["license_id"], "CC-BY-SA-4.0")
        for field in ("commercial_use_allowed", "display_allowed", "offline_cache_allowed", "bulk_reuse_allowed",
                      "redistribution_allowed", "attribution_required", "share_alike_required", "separate_pack_required"):
            self.assertIs(rights[field], True)
        self.assertIn("ownerspecs.com", rights["attribution_text"])
        self.assertIn("CC BY-SA 4.0", rights["attribution_text"])
        policy = self.manifest["import_policy"]
        self.assertIs(policy["research_pack_read_only"], True)
        self.assertIs(policy["production_import"], False)
        self.assertIs(policy["product_import_allowed"], False)
        self.assertIs(policy["product_database_ingested"], False)
        self.assertIs(policy["data_ingested"], False)

    def test_current_snapshot_hash_counts_and_previous_manifest_are_pinned(self):
        snapshot = self.manifest["snapshot"]
        self.assertEqual(snapshot["status"], "source_snapshot_acquired_schema_verified")
        self.assertEqual(snapshot["publisher_generated_date"], "2026-11-11")
        self.assertEqual(snapshot["html_page_generation_count"], 111)
        self.assertEqual(snapshot["json_descriptor_generation_count"], 111)
        self.assertEqual(snapshot["html_page_brand_count"], 27)
        self.assertEqual(snapshot["html_page_verified_datapoint_count"], 2273)
        self.assertEqual(snapshot["source_file_bytes"], 659973)
        self.assertEqual(snapshot["source_snapshot_sha256"], "d702e4572a4e640c0295c40970ef3c0da2db3703c829c5e3d96cebb4acccacc9")
        self.assertEqual(snapshot["vag_generation_count"], 20)
        self.assertEqual(snapshot["vag_fact_count"], 186)
        self.assertEqual(hashlib.sha256(CURRENT_MANIFEST.read_bytes()).hexdigest(), "ed221369ae9195cad18194602a75b17d4ab8aa5908dceb503fc2ca0bfa725697")
        self.assertEqual(self.versioned, self.manifest)
        previous = self.previous_manifest["snapshot"]
        self.assertEqual(previous["source_snapshot_sha256"], "6ed73e4cd634e64501edd3b0e03405afa0aad3b8d1a103f78b839c87c8588c95")
        self.assertEqual(previous["html_page_verified_datapoint_count"], 2369)
        self.assertEqual(hashlib.sha256(PREVIOUS_MANIFEST.read_bytes()).hexdigest(), "3d744c8b813508daefaebcd690d10c2cef6d0a731e87eda59015622bffeabbdc")

    def test_snapshot_delta_is_reconciled_without_generation_membership_or_fitment_promotion(self):
        review = self.manifest["snapshot"]["latest_snapshot_review"]
        self.assertEqual(review["datapoints_removed"], 99)
        self.assertEqual(review["datapoints_added"], 3)
        self.assertEqual(review["changed_datapoints_total"], 3)
        self.assertEqual(review["net_datapoint_change"], -96)
        self.assertEqual(review["vag_datapoints_removed"], 47)
        self.assertEqual(review["vag_datapoints_added"], 0)
        self.assertEqual(review["vag_changed_datapoints"], 0)
        self.assertFalse(review["generation_membership_changed"])
        self.assertEqual(review["market_scope"], "UNKNOWN")
        self.assertFalse(review["critical_repair_values_publishable"])
        self.assertTrue(review["candidate_only"])
        self.assertEqual(review["acquisition_evidence"]["workflow_run_id"], 42968938274)

    def test_vag_removed_facts_and_non_vag_changed_values_are_auditable(self):
        review = self.manifest["snapshot"]["latest_snapshot_review"]
        self.assertEqual(
            {(x["brand"], x["model"], x["removed_facts"]) for x in review["vag_removed_fact_groups"]},
            {("Audi", "Q7", 5), ("Audi", "Q8", 5), ("Porsche", "Cayenne", 17), ("Volkswagen", "Touareg", 20)}
        )
        self.assertEqual(
            {(x["brand"], x["model"], x["field"]) for x in review["changed_values"]},
            {("BMW", "X5", "running_order"), ("BMW", "X5", "max_laden_permissible"), ("BMW", "X5", "tow_braked")}
        )

    def test_current_pack_is_hash_verified_but_desktop_integration_is_not_claimed_early(self):
        entry = self.entry
        self.assertTrue(entry["research_pack_allowed"])
        self.assertTrue(entry["research_pack_acquisition_allowed"])
        self.assertFalse(entry["data_ingested"])
        self.assertFalse(entry["product_database_ingested"])
        self.assertFalse(entry["product_import_allowed"])
        self.assertEqual(entry["source_snapshot_sha256"], "d702e4572a4e640c0295c40970ef3c0da2db3703c829c5e3d96cebb4acccacc9")
        self.assertEqual(entry["source_manifest_sha256"], "ed221369ae9195cad18194602a75b17d4ab8aa5908dceb503fc2ca0bfa725697")
        self.assertEqual(entry["source_file_bytes"], 659973)
        self.assertTrue(entry["research_pack_current"])
        self.assertEqual(entry["research_pack_status"], "verified_research_only")
        self.assertEqual(entry["research_pack_source_commit"], "9f9aa8136e5c084def52e5fdb983ede737c817ec")
        self.assertEqual(entry["research_pack_workflow_run_id"], 42971572740)
        self.assertEqual(entry["research_pack_run_number"], 3)
        self.assertEqual(entry["research_pack_artifact_id"], 13833552555)
        self.assertEqual(entry["research_pack_artifact_name"], "ownerspecs-vag-research-pack-refresh-2026-11-11")
        self.assertEqual(entry["research_pack_artifact_sha256"], "66c764501b3071958b9c1949f3be15908a27ee280c1e2fdd1985c5b934be8c77")
        self.assertEqual(entry["research_pack_manifest_sha256"], "21c94e2ec39ea1b231b96d3fe5f830e5ac62ae5cfc1d8e91312de977d8819fd4")
        self.assertEqual(entry["research_pack_database_sha256"], "9b7da5b490d3dd805865f23389cb8cc7ca9b368137be8307adb07e0c8e683c4a")
        self.assertEqual(entry["research_pack_source_manifest_sha256"], "ed221369ae9195cad18194602a75b17d4ab8aa5908dceb503fc2ca0bfa725697")
        self.assertEqual(entry["research_pack_source_snapshot_sha256"], "d702e4572a4e640c0295c40970ef3c0da2db3703c829c5e3d96cebb4acccacc9")
        self.assertEqual(entry["research_pack_database_byte_size"], 262144)
        self.assertEqual(entry["research_pack_artifact_size_bytes"], 101843)
        self.assertEqual(entry["research_pack_source_snapshot_manifest_sha256"], "77ea356babebed51fd9f6f6b1afad75aaed69038b4f27a2d67621fb37c1ad195")
        self.assertEqual(entry["research_pack_acquisition_snapshot_sha256"], "3ad1725e22184aa601fd2ff0782646c20b69f6930f91b9aab8d23ce34c3e7b70")
        self.assertEqual(entry["research_pack_attribution_sha256"], "6e9005e67b6dfa8704bcd83be166ec61749dedeeeebe0f6ddd80c7b3725c2eeb")
        self.assertEqual(entry["research_pack_license_reference_sha256"], "7802316f0a49ea293c239db64b24756ff2621983892a0aa649adf74b30d99762")
        self.assertTrue(entry["research_database_included_in_desktop"])
        self.assertFalse(entry["current_research_pack_in_desktop"])
        self.assertTrue(entry["previous_pack_still_in_desktop"])
        self.assertEqual(entry["research_pack_desktop_integration_status"], "pending_current_snapshot_desktop_integration")
        self.assertIsNone(entry["desktop_integration_evidence"])
        self.assertEqual(entry["previous_desktop_integration_evidence"]["workflow_run_id"], 42964628461)
        self.assertEqual(entry["previous_verified_research_pack"]["artifact_id"], 13742090427)
        self.assertEqual(entry["older_verified_research_pack"]["artifact_id"], 13733448981)
        self.assertEqual(entry["previous_desktop_lifecycle_evidence"]["run_number"], 1208)
        self.assertIsNone(entry["desktop_lifecycle_evidence"])
        self.assertEqual(entry["applicability"]["market_scope"], "UNKNOWN")
        self.assertFalse(entry["applicability"]["exact_engine_gearbox_pair"])
        self.assertFalse(entry["applicability"]["ru_eaeu_applicability"])
        self.assertFalse(entry["applicability"]["exact_vehicle_fitment"])

    def test_rights_review_document_records_current_publisher_snapshot_and_delta(self):
        for phrase in ("2,273 verified datapoints", "47 vag facts were removed", "99 facts removed",
                       "3 replacement facts added", "market unknown", "candidate-only",
                       "no production import", "share-alike"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, self.review)

if __name__ == "__main__":
    unittest.main()

import hashlib
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CURRENT_MANIFEST = ROOT / "data/source-manifests/ownerspecs-verified-vehicle-specs-cc-by-sa-4.0.json"
VERSIONED_MANIFEST = ROOT / "data/source-manifests/history/ownerspecs-verified-vehicle-specs-cc-by-sa-4.0-2026-11-11.json"
PREVIOUS_MANIFEST = ROOT / "data/source-manifests/history/ownerspecs-verified-vehicle-specs-cc-by-sa-4.0-2026-11-10.json"
PACK3_MANIFEST = ROOT / "data/source-manifests/history/ownerspecs-verified-vehicle-specs-cc-by-sa-4.0-pack3-2026-11-11.json"
REGISTER = ROOT / "data/source-manifests/vag-factory-source-register.json"
REVIEW = ROOT / "docs/research/OWNERSPECS_VAG_DATASET_RIGHTS_REVIEW_2026-11-10.md"

CURRENT_SNAPSHOT_SHA = "fa53aef8eb1d8b8c028ded086cdc3f1e2fc726caa637cdc96ca860336711882f"
PREVIOUS_PACK_SNAPSHOT_SHA = "d702e4572a4e640c0295c40970ef3c0da2db3703c829c5e3d96cebb4acccacc9"
PREVIOUS_PUBLISHER_SNAPSHOT_SHA = "835fe7452b3370dbf921049a72ca365d6f69b6b63ef8a3a37b5714265272814c"
CURRENT_MANIFEST_SHA = "6b659aa7ecedcf36d1a611c2be1546caa76b54a8d19c16a00b484587ac833bc8"

class OwnerSpecsSourceRightsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads(CURRENT_MANIFEST.read_text(encoding="utf-8"))
        cls.versioned = json.loads(VERSIONED_MANIFEST.read_text(encoding="utf-8"))
        cls.previous_manifest = json.loads(PREVIOUS_MANIFEST.read_text(encoding="utf-8"))
        cls.pack3_manifest = json.loads(PACK3_MANIFEST.read_text(encoding="utf-8"))
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

    def test_latest_snapshot_hash_counts_and_previous_manifest_are_pinned(self):
        snapshot = self.manifest["snapshot"]
        self.assertEqual(snapshot["status"], "source_snapshot_acquired_schema_verified")
        self.assertEqual(snapshot["publisher_generated_date"], "2026-11-11")
        self.assertEqual(snapshot["html_page_generation_count"], 111)
        self.assertEqual(snapshot["json_descriptor_generation_count"], 111)
        self.assertEqual(snapshot["html_page_brand_count"], 27)
        self.assertEqual(snapshot["html_page_verified_datapoint_count"], 2273)
        self.assertEqual(snapshot["source_file_bytes"], 659973)
        self.assertEqual(snapshot["source_snapshot_sha256"], CURRENT_SNAPSHOT_SHA)
        self.assertEqual(snapshot["vag_generation_count"], 20)
        self.assertEqual(snapshot["vag_fact_count"], 186)
        self.assertEqual(hashlib.sha256(CURRENT_MANIFEST.read_bytes()).hexdigest(), CURRENT_MANIFEST_SHA)
        self.assertEqual(self.versioned, self.manifest)
        previous = self.previous_manifest["snapshot"]
        self.assertEqual(previous["source_snapshot_sha256"], "6ed73e4cd634e64501edd3b0e03405afa0aad3b8d1a103f78b839c87c8588c95")
        self.assertEqual(previous["html_page_verified_datapoint_count"], 2369)
        self.assertEqual(hashlib.sha256(PREVIOUS_MANIFEST.read_bytes()).hexdigest(), "3d744c8b813508daefaebcd690d10c2cef6d0a731e87eda59015622bffeabbdc")
        self.assertEqual(hashlib.sha256(PACK3_MANIFEST.read_bytes()).hexdigest(), "ed221369ae9195cad18194602a75b17d4ab8aa5908dceb503fc2ca0bfa725697")

    def test_latest_snapshot_delta_is_reconciled_and_does_not_change_vag_facts(self):
        review = self.manifest["snapshot"]["latest_snapshot_review"]
        self.assertEqual(review["previous_snapshot_sha256"], PREVIOUS_PUBLISHER_SNAPSHOT_SHA)
        self.assertEqual(review["current_snapshot_sha256"], CURRENT_SNAPSHOT_SHA)
        self.assertEqual(review["datapoints_removed"], 0)
        self.assertEqual(review["datapoints_added"], 0)
        self.assertEqual(review["changed_datapoints_total"], 1)
        self.assertEqual(review["net_datapoint_change"], 0)
        self.assertEqual(review["vag_datapoints_removed"], 0)
        self.assertEqual(review["vag_datapoints_added"], 0)
        self.assertEqual(review["vag_changed_datapoints"], 0)
        self.assertFalse(review["generation_membership_changed"])
        self.assertFalse(review["datapoint_membership_changed"])
        self.assertEqual(review["market_scope"], "UNKNOWN")
        self.assertFalse(review["critical_repair_values_publishable"])
        self.assertTrue(review["candidate_only"])
        self.assertEqual(review["acquisition_evidence"]["workflow_run_id"], 42975872025)

    def test_previous_vag_removals_and_non_vag_mass_changes_remain_in_history(self):
        review = next(x for x in self.manifest["snapshot"]["snapshot_review_history"]
                      if x.get("current_snapshot_sha256") == PREVIOUS_PACK_SNAPSHOT_SHA)
        self.assertEqual(review["datapoints_removed"], 99)
        self.assertEqual(review["datapoints_added"], 3)
        self.assertEqual(review["vag_datapoints_removed"], 47)
        self.assertEqual(
            {(x["brand"], x["model"], x["removed_facts"]) for x in review["vag_removed_fact_groups"]},
            {("Audi", "Q7", 5), ("Audi", "Q8", 5), ("Porsche", "Cayenne", 17), ("Volkswagen", "Touareg", 20)}
        )
        self.assertEqual(
            {(x["brand"], x["model"], x["field"]) for x in review["changed_values"]},
            {("BMW", "X5", "running_order"), ("BMW", "X5", "max_laden_permissible"), ("BMW", "X5", "tow_braked")}
        )

    def test_last_verified_pack_is_explicitly_older_than_latest_publisher_snapshot(self):
        entry = self.entry
        self.assertTrue(entry["research_pack_allowed"])
        self.assertTrue(entry["research_pack_acquisition_allowed"])
        self.assertFalse(entry["data_ingested"])
        self.assertFalse(entry["product_database_ingested"])
        self.assertFalse(entry["product_import_allowed"])
        self.assertEqual(entry["source_snapshot_sha256"], CURRENT_SNAPSHOT_SHA)
        self.assertEqual(entry["source_manifest_sha256"], CURRENT_MANIFEST_SHA)
        self.assertEqual(entry["source_file_bytes"], 659973)
        self.assertFalse(entry["research_pack_current"])
        self.assertTrue(entry["research_pack_current_for_vag_subset"])
        self.assertEqual(entry["research_pack_status"], "verified_research_only_previous_snapshot")
        self.assertEqual(entry["research_pack_source_snapshot_sha256"], PREVIOUS_PACK_SNAPSHOT_SHA)
        self.assertEqual(entry["research_pack_source_manifest_sha256"], "ed221369ae9195cad18194602a75b17d4ab8aa5908dceb503fc2ca0bfa725697")
        self.assertEqual(entry["research_pack_source_commit"], "9f9aa8136e5c084def52e5fdb983ede737c817ec")
        self.assertEqual(entry["research_pack_workflow_run_id"], 42971572740)
        self.assertEqual(entry["research_pack_run_number"], 3)
        self.assertEqual(entry["research_pack_artifact_id"], 13833552555)
        self.assertEqual(entry["research_pack_artifact_name"], "ownerspecs-vag-research-pack-refresh-2026-11-11")
        self.assertEqual(entry["research_pack_artifact_sha256"], "66c764501b3071958b9c1949f3be15908a27ee280c1e2fdd1985c5b934be8c77")
        self.assertEqual(entry["research_pack_manifest_sha256"], "21c94e2ec39ea1b231b96d3fe5f830e5ac62ae5cfc1d8e91312de977d8819fd4")
        self.assertEqual(entry["research_pack_database_sha256"], "9b7da5b490d3dd805865f23389cb8cc7ca9b368137be8307adb07e0c8e683c4a")
        self.assertTrue(entry["research_database_included_in_desktop"])
        self.assertFalse(entry["current_research_pack_in_desktop"])
        self.assertTrue(entry["previous_pack_still_in_desktop"])
        self.assertEqual(entry["research_pack_desktop_integration_status"], "pending_current_snapshot_desktop_integration")
        latest = entry["latest_publisher_snapshot"]
        self.assertEqual(latest["source_snapshot_sha256"], CURRENT_SNAPSHOT_SHA)
        self.assertEqual(latest["source_file_bytes"], 659973)
        self.assertEqual(latest["vag_fact_count"], 186)
        self.assertEqual(latest["acquisition_evidence"]["artifact_id"], 13835491309)
        self.assertTrue(latest["acquisition_evidence"]["source_revision_field_stale"])
        self.assertEqual(entry["applicability"]["market_scope"], "UNKNOWN")
        self.assertFalse(entry["applicability"]["exact_engine_gearbox_pair"])
        self.assertFalse(entry["applicability"]["ru_eaeu_applicability"])
        self.assertFalse(entry["applicability"]["exact_vehicle_fitment"])

    def test_rights_review_document_records_latest_snapshot_and_non_vag_only_delta(self):
        for phrase in ("2,273 verified datapoints", "835fe745", "two non-vag unit-case changes",
                       "no vag fact changes", "47 vag facts were removed", "market unknown",
                       "candidate-only", "no production import", "share-alike"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, self.review)

if __name__ == "__main__":
    unittest.main()

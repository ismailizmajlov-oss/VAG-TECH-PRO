import json
import unittest
from pathlib import Path


class OpenVAGSourceRightsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]
        manifest_path = (
            cls.root
            / "data"
            / "source-manifests"
            / "openvag-dtc-candidate.json"
        )
        registry_path = (
            cls.root
            / "data"
            / "source-manifests"
            / "vag-factory-source-register.json"
        )
        cls.manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        cls.registry = json.loads(registry_path.read_text(encoding="utf-8"))
        matches = [
            item for item in cls.registry["sources"]
            if item.get("source_id") == "openvag-riz4d-dtc-candidate"
        ]
        if len(matches) != 1:
            raise AssertionError("OpenVAG must have exactly one central source-register entry")
        cls.registry_entry = matches[0]

    def test_source_is_pinned_but_not_data_licensed(self):
        self.assertEqual(
            self.manifest["pinned_revision"],
            "407d5e042cf46d55087ed4ae4e056605f2b04f08",
        )
        self.assertEqual(
            self.manifest["repository_license"]["id"],
            "MIT",
        )
        self.assertEqual(
            self.manifest["repository_license"]["data_license"],
            "not_separately_declared",
        )
        self.assertEqual(
            self.manifest["repository_license"]["data_reuse_status"],
            "not_approved",
        )

    def test_missing_database_artifact_fails_closed(self):
        evidence = self.manifest["repository_evidence"]
        self.assertFalse(evidence["tracked_data_artifact"])
        self.assertTrue(evidence["expected_database_is_gitignored"])
        self.assertFalse(evidence["database_generation_script_present"])
        self.assertFalse(evidence["release_artifact_present"])
        self.assertIsNone(self.manifest["provenance_review"]["data_snapshot_sha256"])
        latest = self.manifest["latest_recheck"]
        self.assertEqual(latest["observed_at"], "2026-11-10")
        self.assertEqual(latest["repository_revision"], self.manifest["pinned_revision"])
        self.assertEqual(latest["database_path"], "db/openvag.db")
        self.assertFalse(latest["database_file_present_in_default_branch"])
        self.assertEqual(latest["database_fetch_result"], "GitHub Contents API returned HTTP 404 Not Found")
        self.assertTrue(latest["gitignore_explicitly_excludes_database"])
        self.assertEqual(latest["generation_script_path_referenced"], "scripts/init_db.py")
        self.assertFalse(latest["generation_script_present_in_default_branch"])
        self.assertFalse(latest["database_bytes_received"])
        self.assertIsNone(latest["database_sha256"])
        self.assertEqual(latest["import_eligibility"], "blocked_quarantine_only")

    def test_no_record_level_provenance_or_fitment_is_claimed(self):
        provenance = self.manifest["provenance_review"]
        self.assertFalse(provenance["per_record_source_url"])
        self.assertFalse(provenance["per_record_source_revision"])
        self.assertFalse(provenance["per_record_source_file_hash"])
        self.assertFalse(provenance["per_record_license"])
        applicability = self.manifest["data_model_review"]
        self.assertFalse(applicability["generic_and_manufacturer_namespaces_separated"])
        self.assertEqual(applicability["market_scope"], "UNKNOWN")
        self.assertEqual(applicability["applicability_precision"], "unverified_make_label_only")
        self.assertFalse(applicability["ecu_applicability"])
        self.assertFalse(applicability["diagnostic_execution_authorized"])
        self.assertFalse(applicability["repair_instruction_use_authorized"])

    def test_central_source_register_preserves_quarantine(self):
        entry = self.registry_entry
        rights = entry["rights"]
        applicability = entry["applicability"]
        self.assertEqual(entry["repository_revision"], self.manifest["pinned_revision"])
        self.assertFalse(entry["data_ingested"])
        self.assertIsNone(entry["source_snapshot_sha256"])
        self.assertEqual(rights["repository_code_license"], "MIT")
        self.assertEqual(rights["dataset_specific_license"], "not_established")
        self.assertEqual(rights["permission_status"], "not_cleared")
        for key in (
            "commercial_use_of_database",
            "display_allowed",
            "offline_cache_allowed",
            "bulk_reuse_allowed",
            "redistribution_allowed",
        ):
            self.assertEqual(rights[key], "not_established")
        self.assertEqual(applicability["market_scope"], "UNKNOWN")
        self.assertFalse(applicability["exact_model_generation_year_fitment"])
        self.assertFalse(applicability["exact_engine_code_fitment"])
        self.assertFalse(applicability["exact_gearbox_code_fitment"])
        self.assertFalse(applicability["engine_gearbox_pairing"])
        self.assertFalse(applicability["exact_ecu_part_number_hw_sw_fitment"])
        self.assertIn("quarantined_no_import", entry["project_decision"])
        latest = entry["latest_review"]
        self.assertEqual(latest["observed_at"], "2026-11-10")
        self.assertEqual(latest["repository_revision"], self.manifest["pinned_revision"])
        self.assertFalse(latest["database_file_present"])
        self.assertEqual(latest["database_fetch_result"], "HTTP_404_NOT_FOUND")
        self.assertTrue(latest["database_path_gitignored"])
        self.assertFalse(latest["referenced_generation_script_present"])
        self.assertFalse(latest["database_bytes_received"])
        self.assertIsNone(latest["database_sha256"])
        for field in ("data_import_allowed", "display_allowed", "offline_cache_allowed", "redistribution_allowed"):
            self.assertFalse(latest[field])

    def test_publisher_counts_are_not_treated_as_verified_rows(self):
        claims = self.manifest["claimed_counts_from_upstream_documentation"]
        self.assertEqual(claims["dtc_codes"], 995)
        self.assertEqual(claims["dtc_variants"], 1103)
        self.assertEqual(
            claims["verification_status"],
            "upstream_documentation_claim_only_not_independently_reproduced",
        )
        self.assertFalse(
            self.manifest["repository_evidence"]["tracked_data_artifact"]
        )

    def test_candidate_cannot_enter_product_or_offline_packs(self):
        policy = self.manifest["product_policy"]
        self.assertFalse(policy["product_eligibility"])
        self.assertFalse(policy["import_allowed"])
        self.assertFalse(policy["display_allowed"])
        self.assertFalse(policy["offline_cache_allowed"])
        self.assertFalse(policy["redistribution_allowed"])
        self.assertIn("Do not ingest or display", policy["decision"])

    def test_latest_recheck_document_records_missing_bytes_and_no_promotion(self):
        review = (self.root / "docs" / "research" / "OPENVAG_DTC_SOURCE_RIGHTS_REVIEW_2026-11-05.md").read_text(encoding="utf-8").casefold()
        for phrase in (
            "recheck — 2026-11-10",
            "returned http 404",
            "no database sha-256 can be recorded",
            "not treated as a dataset-specific licence",
            "keep the source quarantined",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, review)

    def test_no_openvag_snapshot_is_materialized_in_research_tree(self):
        research_dir = self.root / "data" / "research"
        if research_dir.exists():
            candidates = [
                path for path in research_dir.rglob("*")
                if "openvag" in path.name.lower()
            ]
            self.assertEqual(candidates, [])


if __name__ == "__main__":
    unittest.main()

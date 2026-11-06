import json
import re
import unittest
from pathlib import Path


class Wal33DDtcCandidateRightsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        manifest_path = (
            Path(__file__).resolve().parents[1]
            / "data"
            / "source-manifests"
            / "wal33d-dtc-candidate.json"
        )
        cls.manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    def test_snapshot_is_pinned_and_source_file_hash_is_well_formed(self):
        self.assertEqual(
            self.manifest["pinned_revision"],
            "04c43d72e7db7197658b6f72fe582c5076d9eee8",
        )
        self.assertRegex(self.manifest["source_file"]["sha256"], re.compile(r"^[a-f0-9]{64}$"))
        self.assertEqual(
            self.manifest["source_file"]["git_blob_sha1"],
            "a8afd432644e8cad718e42cdd18cc1931a75bb08",
        )

    def test_repository_mit_does_not_promote_dataset_rights(self):
        license_info = self.manifest["license"]
        self.assertEqual(license_info["id"], "MIT-1.0")
        self.assertEqual(
            license_info["rights_status"],
            "repository_level_MIT_declared; dataset_specific_rights_not_independently_confirmed",
        )
        self.assertFalse(license_info["project_commercial_use_approved"])
        self.assertFalse(license_info["project_display_approved"])
        self.assertFalse(license_info["project_offline_cache_approved"])
        self.assertFalse(license_info["project_redistribution_approved"])

    def test_filename_derived_manufacturer_is_not_oem_provenance(self):
        evidence = self.manifest["reviewed_upstream_evidence"]
        self.assertEqual(
            evidence["repository_evidence"]["readme_declared_source_text_file_count"],
            37,
        )
        self.assertTrue(
            evidence["repository_evidence"]["all_other_file_stems_marked_manufacturer_specific"]
        )
        self.assertFalse(
            evidence["repository_evidence"]["per_row_source_attribution_found"]
        )
        self.assertFalse(
            evidence["technical_boundary"]["five_character_P1_code_alone_proves_vag_specific"]
        )
        self.assertFalse(
            evidence["technical_boundary"]["manufacturer_filename_proves_oem_origin"]
        )

    def test_candidate_has_no_exact_vehicle_or_ecu_applicability(self):
        self.assertEqual(self.manifest["market_scope"], "UNKNOWN")
        self.assertEqual(
            self.manifest["applicability_precision"],
            "manufacturer_make_candidate",
        )
        for key in (
            "exact_vehicle_fitment",
            "generation_year_fitment",
            "engine_gearbox_fitment",
            "ecu_fitment",
            "pr_code_vin_fitment",
        ):
            self.assertFalse(self.manifest[key], key)
        self.assertFalse(
            self.manifest["reviewed_upstream_evidence"]["technical_boundary"]["diagnostic_execution_allowed"]
        )

    def test_candidate_remains_quarantined_and_out_of_product(self):
        self.assertEqual(
            self.manifest["display_status"],
            "quarantined_not_integrated",
        )
        self.assertEqual(
            self.manifest["verification_status"],
            "community_reference_unverified",
        )
        self.assertFalse(self.manifest["data_ingested"])
        self.assertIn("quarantined", self.manifest["decision"].lower())
        self.assertFalse(
            self.manifest["reviewed_upstream_evidence"]["technical_boundary"]["diagnostic_execution_allowed"]
        )


if __name__ == "__main__":
    unittest.main()

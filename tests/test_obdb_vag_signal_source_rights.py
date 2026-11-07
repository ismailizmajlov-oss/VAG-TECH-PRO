import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REGISTRY = json.loads(
    (ROOT / "data" / "source-manifests" / "vag-factory-source-register.json").read_text(encoding="utf-8")
)
SOURCES = {item["source_id"]: item for item in REGISTRY["sources"]}


class ObdbVagSignalSourceRightsTests(unittest.TestCase):
    def test_all_pinned_repositories_have_cc_by_sa_license_evidence(self):
        source = SOURCES["obdb-vag-signalsets-cc-by-sa"]
        rights = source["rights"]
        self.assertEqual(rights["data_license"], "CC-BY-SA-4.0")
        self.assertIs(rights["license_files_reviewed_at_each_pinned_commit"], True)
        for key in ("commercial_use_allowed", "display_allowed", "offline_cache_allowed",
                    "redistribution_allowed", "attribution_required", "share_alike_required",
                    "separate_pack_required"):
            self.assertIs(rights[key], True)
        self.assertEqual(len(source["pinned_source_repositories"]), 6)
        self.assertEqual(source["source_file_count"], 24)
        self.assertEqual(source["source_repository_count"], 6)
        for repo in source["pinned_source_repositories"]:
            self.assertTrue(repo["commit_sha"])
            self.assertEqual(repo["license_file"], "LICENSE")
            self.assertEqual(repo["license_id"], "CC-BY-SA-4.0")

    def test_pack_is_candidate_only_and_never_executable(self):
        source = SOURCES["obdb-vag-signalsets-cc-by-sa"]
        scope = source["technical_scope"]
        self.assertEqual(source["market_scope"], ["UNKNOWN"])
        self.assertEqual(source["verification_status"], "unverified_community_candidate")
        self.assertEqual(source["display_status"], "read_only_research_candidate")
        self.assertIs(scope["diagnostic_execution_allowed"], False)
        self.assertIs(scope["test_plan_approved"], False)
        self.assertIs(scope["exact_vehicle_fitment"], False)
        self.assertIs(scope["exact_ecu_fitment"], False)
        self.assertIs(scope["exact_engine_gearbox_mapping"], False)
        self.assertEqual(scope["command_service"], "0x22")
        self.assertIs(scope["all_command_records_execution_allowed"], False)

    def test_no_dtc_repair_or_oem_wiring_data_is_claimed(self):
        source = SOURCES["obdb-vag-signalsets-cc-by-sa"]
        counts = source["counts"]
        scope = source["technical_scope"]
        self.assertEqual(counts["uds_command_candidates"], 2315)
        self.assertEqual(counts["signal_candidates"], 2480)
        self.assertEqual(counts["generation_candidates"], 32)
        self.assertEqual(counts["ecu_candidates"], 15)
        self.assertEqual(counts["dtc_definitions"], 0)
        self.assertEqual(counts["repair_procedures"], 0)
        self.assertEqual(counts["approved_test_plans"], 0)
        self.assertIs(scope["dtc_definitions"], False)
        self.assertIs(scope["repair_procedures"], False)
        self.assertIs(scope["wiring_diagrams"], False)
        self.assertIs(scope["factory_pinouts"], False)

    def test_share_alike_attribution_and_separate_pack_are_explicit(self):
        source = SOURCES["obdb-vag-signalsets-cc-by-sa"]
        rights = source["rights"]
        self.assertIn("OBDb community contributors", rights["attribution"])
        self.assertIn("CC BY-SA 4.0", rights["attribution"])
        self.assertIn("share_alike", source["project_decision"])
        self.assertIn("do not execute UDS commands", source["project_decision"])



    def test_verified_pack_artifact_is_recorded_but_not_imported_or_integrated(self):
        source = SOURCES["obdb-vag-signalsets-cc-by-sa"]
        build = source["research_pack_build_evidence"]
        self.assertEqual(build["workflow_run_number"], 4)
        self.assertEqual(build["artifact_id"], 13198105454)
        self.assertEqual(build["artifact_sha256"], "db6014167149322c8928d7f8762ea33421f7e142bd8864b0ae60307207578069")
        self.assertEqual(build["database_sha256"], "d3c54051e2f3f73c211e6d84c4e84541a60901e01eeee843b8357efa1e421aa1")
        self.assertEqual(build["manifest_sha256"], "29ec10e68214c66a5c3c14734b9f30e0eb9d25f0d03be3384a454c3ef1833f46")
        self.assertEqual(build["license_id"], "CC-BY-SA-4.0")
        self.assertIs(build["share_alike_required"], True)
        self.assertIs(build["separate_pack_required"], True)
        self.assertIs(build["execution_allowed"], False)
        self.assertIs(build["product_database_import"], False)
        self.assertEqual(build["desktop_integration_status"], "not_integrated")
        self.assertIs(source["product_import_allowed"], False)
        self.assertIs(source["data_ingested"], False)
        self.assertEqual(build["counts"]["dtc_definitions"], 0)
        self.assertEqual(build["counts"]["approved_test_plans"], 0)
        self.assertEqual(build["counts"]["exact_vehicle_fitment"], 0)

if __name__ == "__main__":
    unittest.main()

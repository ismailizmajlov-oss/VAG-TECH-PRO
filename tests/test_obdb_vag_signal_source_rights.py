import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REGISTRY = json.loads(
    (ROOT / "data" / "source-manifests" / "vag-factory-source-register.json").read_text(encoding="utf-8")
)
SOURCES = {item["source_id"]: item for item in REGISTRY["sources"]}
OBDB_MANIFEST = json.loads(
    (ROOT / "data" / "source-manifests" / "obdb-vag-signalsets.json").read_text(encoding="utf-8")
)


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
        self.assertEqual(len(source["pinned_source_repositories"]), 13)
        self.assertEqual(source["source_file_count"], 52)
        self.assertEqual(source["source_repository_count"], 13)
        for repo in source["pinned_source_repositories"]:
            self.assertTrue(repo["commit_sha"])
            self.assertEqual(repo["license_file"], "LICENSE")
            self.assertEqual(repo["license_id"], "CC-BY-SA-4.0")
            self.assertRegex(repo["commit_sha"], r"^[0-9a-f]{40}$")
        manifest_sources = {item["repository"]: item for item in OBDB_MANIFEST["sources"]}
        pinned_sources = {item["repository"]: item for item in source["pinned_source_repositories"]}
        self.assertEqual(set(manifest_sources), set(pinned_sources))
        self.assertEqual(len(manifest_sources), 13)
        for repository, item in manifest_sources.items():
            pinned = pinned_sources[repository]
            for key in ("commit_sha", "commit_date", "make", "model", "generation_reference_url"):
                self.assertEqual(pinned[key], item[key])

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
        self.assertEqual(counts["uds_command_candidates"], 7890)
        self.assertEqual(counts["signal_candidates"], 8446)
        self.assertEqual(counts["generation_candidates"], 67)
        self.assertEqual(counts["ecu_candidates"], 44)
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
        self.assertEqual(build["workflow_run_number"], 239)
        self.assertEqual(build["workflow_run_id"], 42440287999)
        self.assertEqual(build["artifact_id"], 13601506999)
        self.assertEqual(build["artifact_sha256"], "f7ec36322ec04adc4999f6de753e18a122e1203c3ea1f38a1d1ea933c7b466b8")
        self.assertEqual(build["artifact_size_bytes"], 2665251)
        self.assertEqual(build["database_sha256"], "9bbc9ae273e43f442f55928b683420b3a8b9ac5ba16b3ccab20d67ccfa2d2d48")
        self.assertEqual(build["manifest_sha256"], "5af1913fc0d083fe2698ffd6c8abadf9ddb6a5523f48347cf5e3d7a2d317da84")
        self.assertEqual(build["attribution_sha256"], "50852ca5d674e7f88e124ab198e2f66a269fce2543b95d63b7d9f29e2a57d7de")
        self.assertEqual(build["license_id"], "CC-BY-SA-4.0")
        self.assertIs(build["share_alike_required"], True)
        self.assertIs(build["separate_pack_required"], True)
        self.assertIs(build["execution_allowed"], False)
        self.assertIs(build["product_database_import"], False)
        self.assertEqual(build["desktop_integration_status"], "not_integrated")
        self.assertIs(source["product_import_allowed"], False)
        self.assertIs(source["data_ingested"], False)
        self.assertEqual(build["counts"]["source_repositories"], 13)
        self.assertEqual(build["counts"]["upstream_files"], 52)
        self.assertEqual(build["counts"]["generation_candidates"], 67)
        self.assertEqual(build["counts"]["ecu_candidates"], 44)
        self.assertEqual(build["counts"]["uds_command_candidates"], 7890)
        self.assertEqual(build["counts"]["signal_candidates"], 8446)
        self.assertEqual(build["counts"]["dtc_definitions"], 0)
        self.assertEqual(build["counts"]["approved_test_plans"], 0)
        self.assertEqual(build["counts"]["exact_vehicle_fitment"], 0)

if __name__ == "__main__":
    unittest.main()

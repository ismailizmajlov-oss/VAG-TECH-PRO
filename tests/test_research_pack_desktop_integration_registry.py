from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTER_PATH = ROOT / "data/source-manifests/vag-factory-source-register.json"
WORKFLOW_PATH = ROOT / ".github/workflows/windows-desktop-ci-run71.yml"

EXPECTED_RUN_ID = 42964628461
EXPECTED_HEAD = "cdf8f973102796339333112836e9256c0c5dae5a"
EXPECTED_RUN_URL = "https://github.com/ismailizmajlov-oss/VAG-TECH-PRO/actions/runs/42964628461"


def load_sources():
    payload = json.loads(REGISTER_PATH.read_text(encoding="utf-8"))
    return {item["source_id"]: item for item in payload["sources"]}


def assert_integration_evidence(test: unittest.TestCase, evidence: dict, step: str) -> None:
    test.assertEqual(evidence["status"], "verified_in_successful_windows_x64_desktop_build")
    test.assertEqual(evidence["workflow_run_id"], EXPECTED_RUN_ID)
    test.assertEqual(evidence["workflow_run_url"], EXPECTED_RUN_URL)
    test.assertEqual(evidence["head_sha"], EXPECTED_HEAD)
    test.assertEqual(evidence["job_name"], "build-and-lifecycle")
    test.assertEqual(evidence["runner_label"], "windows-2025")
    test.assertEqual(evidence["successful_step"], step)
    test.assertFalse(evidence["product_database_imported"])
    test.assertFalse(evidence["production_fitment_published"])
    test.assertFalse(evidence["native_windows_10_11_verified"])


class ResearchPackDesktopIntegrationRegistryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = load_sources()
        cls.workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

    def test_cardir_is_integrated_as_read_only_research_not_production_data(self):
        source = self.sources["cardir-vag-owner-manual-facts-cc-by-4.0"]
        self.assertTrue(source["research_pack_ingested"])
        self.assertTrue(source["research_database_included_in_desktop"])
        self.assertEqual(source["desktop_integration_status"],
                         "verified_read_only_research_pack_integrated_in_offline_desktop")
        self.assertFalse(source["data_ingested"])
        self.assertFalse(source["product_import_allowed"])
        self.assertEqual(source["research_pack"]["status"], "verified_research_only")
        self.assertEqual(source["research_pack"]["source_snapshot_sha256"],
                         "902adb1ea1c20eeb98f803a12ffb787a5d082fb184f914091ff8e79bc67ccbbb")
        self.assertEqual(source["applicability"]["market_scope"], "UNKNOWN")
        self.assertFalse(source["applicability"]["exact_engine_gearbox_pair"])
        self.assertFalse(source["applicability"]["exact_vehicle_fitment"])
        assert_integration_evidence(
            self, source["desktop_integration_evidence"],
            "Integrate CarDir VAG reference facts into offline desktop",
        )
        self.assertTrue((ROOT / "desktop/cardir-vag-reference-facts-db.cjs").is_file())

    def test_ownerspecs_is_integrated_as_separate_sharealike_research_not_oem_fitment(self):
        source = self.sources["ownerspecs-verified-vehicle-specs-cc-by-sa-4.0"]
        self.assertTrue(source["research_pack_ingested"])
        self.assertTrue(source["research_database_included_in_desktop"])
        self.assertEqual(source["research_pack_desktop_integration_status"],
                         "verified_read_only_research_pack_integrated_in_offline_desktop")
        self.assertFalse(source["data_ingested"])
        self.assertFalse(source["product_database_ingested"])
        self.assertFalse(source["product_import_allowed"])
        self.assertEqual(source["source_snapshot_sha256"],
                         "6ed73e4cd634e64501edd3b0e03405afa0aad3b8d1a103f78b839c87c8588c95")
        self.assertEqual(source["applicability"]["market_scope"], "UNKNOWN")
        self.assertFalse(source["applicability"]["exact_engine_gearbox_pair"])
        self.assertFalse(source["applicability"]["ru_eaeu_applicability"])
        assert_integration_evidence(
            self, source["desktop_integration_evidence"],
            "Integrate OwnerSpecs VAG research pack into offline desktop",
        )
        self.assertTrue((ROOT / "desktop/ownerspecs-vag-research-db.cjs").is_file())

    def test_wikidata_identity_candidates_are_seeded_but_not_promoted(self):
        source = self.sources["wikidata-vag-model-taxonomy"]
        self.assertTrue(source["candidate_seed_integrated_in_local_sqlite"])
        seed = source["candidate_seed_integration"]
        self.assertEqual(seed["status"], "verified_candidate_identity_seed_in_local_sqlite")
        self.assertEqual(seed["counts"]["model_candidates"], 521)
        self.assertEqual(seed["counts"]["manufacturer_candidates"], 6)
        self.assertEqual(seed["counts"]["source_bindings"], 530)
        self.assertEqual(seed["counts"]["verified_models"], 0)
        self.assertEqual(seed["counts"]["exact_fitments"], 0)
        self.assertEqual(seed["market_scope"], "UNKNOWN")
        self.assertEqual(seed["applicability_precision"], "candidate_identity_only")
        self.assertEqual(seed["review_status"], "candidate")
        self.assertFalse(source["data_ingested"])
        self.assertFalse(source["product_import_allowed"])
        self.assertFalse(source["production_catalog_published"])
        self.assertFalse(source["applicability"]["exact_vehicle_fitment"])
        self.assertFalse(source["applicability"]["generation_verified"])
        assert_integration_evidence(
            self, seed["evidence"],
            "Seed CC0 Wikidata model identity candidates into local SQLite core",
        )
        self.assertTrue((ROOT / "desktop/wikidata-candidate-seed.cjs").is_file())

    def test_wikidata_generation_members_remain_candidate_only_in_desktop(self):
        source = self.sources["wikidata-vag-generation-candidates"]
        self.assertTrue(source["research_pack_integrated_in_desktop"])
        self.assertEqual(source["desktop_integration_status"],
                         "verified_candidate_only_pack_integrated_in_offline_desktop")
        self.assertFalse(source["data_ingested"])
        self.assertFalse(source["product_import_allowed"])
        self.assertFalse(source["production_catalog_published"])
        self.assertEqual(source["applicability"]["market_scope"], "UNKNOWN")
        self.assertEqual(source["applicability"]["precision"], "series_member_candidate")
        self.assertFalse(source["applicability"]["generation_verified"])
        self.assertFalse(source["applicability"]["exact_vehicle_fitment"])
        assert_integration_evidence(
            self, source["desktop_integration_evidence"],
            "Integrate verified CC0 Wikidata VAG generation candidates (run71)",
        )

    def test_windows_workflow_runs_this_registry_contract_and_integration_steps(self):
        self.assertIn("python tests/test_research_pack_desktop_integration_registry.py -v", self.workflow)
        self.assertIn("Integrate CarDir VAG reference facts into offline desktop", self.workflow)
        self.assertIn("Integrate OwnerSpecs VAG research pack into offline desktop", self.workflow)
        self.assertIn("Seed CC0 Wikidata model identity candidates into local SQLite core", self.workflow)
        self.assertIn("Integrate verified CC0 Wikidata VAG generation candidates (run71)", self.workflow)


if __name__ == "__main__":
    unittest.main()

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTER = ROOT / "data" / "source-manifests" / "vag-factory-source-register.json"


class ObdbDesktopIntegrationStateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        registry = json.loads(REGISTER.read_text(encoding="utf-8"))
        matches = [
            source for source in registry["sources"]
            if source.get("source_id") == "obdb-vag-signalsets-cc-by-sa"
        ]
        if len(matches) != 1:
            raise AssertionError("Expected exactly one OBDb VAG signal-set source")
        cls.source = matches[0]

    def test_research_pack_is_integrated_but_not_merged_into_product_database(self):
        source = self.source
        self.assertTrue(source["research_pack_ingested"])
        self.assertFalse(source["data_ingested"])
        self.assertFalse(source["product_database_ingested"])
        self.assertFalse(source["product_import_allowed"])
        self.assertEqual(
            source["desktop_integration_status"],
            "integrated_separate_read_only_research_catalog",
        )

    def test_desktop_integration_has_auditable_workflow_and_ui_evidence(self):
        evidence = self.source["desktop_integration_evidence"]
        self.assertEqual(evidence["workflow_run_number"], 701)
        self.assertEqual(evidence["workflow_run_id"], 42420697350)
        self.assertEqual(evidence["source_audit_artifact_id"], 13593733504)
        self.assertEqual(evidence["desktop_ui_dataset_id"], "uds")
        self.assertEqual(evidence["api_route"], "/api/local-research?dataset=uds")
        self.assertEqual(evidence["counts"]["source_repositories"], 6)
        self.assertEqual(evidence["counts"]["upstream_files"], 24)
        self.assertEqual(evidence["counts"]["uds_command_candidates"], 2315)
        self.assertEqual(evidence["counts"]["signal_candidates"], 2480)
        self.assertEqual(evidence["counts"]["dtc_definitions"], 0)
        self.assertEqual(evidence["counts"]["repair_procedures"], 0)
        self.assertEqual(evidence["counts"]["exact_vehicle_fitment_rows"], 0)
        self.assertRegex(evidence["database_sha256"], re.compile(r"^[a-f0-9]{64}$"))
        self.assertFalse(evidence["execution_allowed"])
        self.assertFalse(evidence["product_database_import"])
        self.assertTrue(evidence["separate_read_only_database"])

    def test_share_alike_and_candidate_only_boundaries_remain_explicit(self):
        source = self.source
        rights = source["rights"]
        scope = source["technical_scope"]
        self.assertEqual(rights["data_license"], "CC-BY-SA-4.0")
        self.assertTrue(rights["attribution_required"])
        self.assertTrue(rights["share_alike_required"])
        self.assertTrue(rights["separate_pack_required"])
        self.assertEqual(
            source["verification_status"],
            "unverified_community_candidate",
        )
        self.assertEqual(source["display_status"], "read_only_research_candidate")
        self.assertFalse(scope["exact_vehicle_fitment"])
        self.assertFalse(scope["exact_ecu_fitment"])
        self.assertFalse(scope["exact_engine_gearbox_mapping"])
        self.assertFalse(scope["diagnostic_execution_allowed"])
        self.assertFalse(scope["test_plan_approved"])
        self.assertEqual(source["counts"]["dtc_definitions"], 0)
        self.assertEqual(source["counts"]["repair_procedures"], 0)


if __name__ == "__main__":
    unittest.main()

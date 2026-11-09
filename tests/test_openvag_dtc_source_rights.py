import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REGISTER = ROOT / "data" / "source-manifests" / "vag-factory-source-register.json"


class OpenVagDtcSourceRightsTests(unittest.TestCase):
    def test_unavailable_database_and_missing_provenance_block_import(self):
        manifest = json.loads(REGISTER.read_text(encoding="utf-8"))
        source = next(item for item in manifest["sources"] if item["source_id"] == "openvag-github-dtc-api-schema-only")
        self.assertEqual(source["pinned_revision"], "407d5e042cf46d55087ed4ae4e056605f2b04f08")
        self.assertTrue(source["access"]["repository_public"])
        self.assertFalse(source["access"]["tracked_database_file_present"])
        self.assertTrue(source["access"]["gitignore_excludes_database"])
        self.assertFalse(source["access"]["database_regeneration_script_present"])
        self.assertEqual(source["access"]["database_release_artifacts"], [])
        self.assertEqual(source["rights"]["tracked_repository_code_license"], "MIT")
        self.assertEqual(source["rights"]["database_data_license_status"], "not_established")
        self.assertEqual(source["rights"]["data_provenance_status"], "not_documented")
        self.assertEqual(source["rights"]["permission_status"], "not_obtained")
        self.assertFalse(source["data_ingested"])
        self.assertFalse(source["research_pack_ingested"])
        self.assertFalse(source["product_database_ingested"])
        self.assertFalse(source["product_import_allowed"])
        self.assertIsNone(source["source_snapshot_sha256"])
        self.assertEqual(source["hash_status"], "not_available_no_database_bytes")
        self.assertEqual(source["applicability"]["market_scope"], "UNKNOWN")
        self.assertFalse(source["applicability"]["exact_vehicle_fitment"])
        self.assertFalse(source["applicability"]["engine_gearbox_fitment"])
        self.assertFalse(source["applicability"]["ecu_fitment"])
        self.assertFalse(source["applicability"]["diagnostic_execution_allowed"])


if __name__ == "__main__":
    unittest.main()

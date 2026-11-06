import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CENTRAL = ROOT / "data" / "source-manifests" / "vag-factory-source-register.json"
RU_EAEU = ROOT / "data" / "source-manifests" / "russian-eaeu-otts-sources.json"
SOURCE_ID = "kyrgyzstan-single-window-otts-registry"


class KyrgyzSingleWindowRightsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        central = json.loads(CENTRAL.read_text(encoding="utf-8"))
        ru_eaeu = json.loads(RU_EAEU.read_text(encoding="utf-8"))
        central_matches = [s for s in central["sources"] if s["source_id"] == SOURCE_ID]
        ru_matches = [s for s in ru_eaeu["sources"] if s["source_id"] == SOURCE_ID]
        if len(central_matches) != 1 or len(ru_matches) != 1:
            raise AssertionError("Kyrgyz Single Window source must occur exactly once in both registries")
        cls.central = central_matches[0]
        cls.ru = ru_matches[0]

    def test_operator_public_registry_pilot_is_recorded(self):
        observed = self.central["observed_claims"]
        self.assertEqual(observed["public_registry_status"], "pilot")
        self.assertTrue(observed["public_query_without_login"])
        self.assertEqual(observed["record_view_fields_independently_inspected"], False)
        self.assertEqual(observed["record_view_captcha_status"], "not_verified_on_new_pilot_route")
        self.assertTrue(observed["legacy_record_view_requires_captcha"])
        self.assertIn("document_number", observed["public_search_fields_claimed"])

    def test_public_visibility_does_not_clear_reuse_rights(self):
        rights = self.central["rights"]
        self.assertEqual(rights["dataset_license"], "not_found")
        self.assertEqual(rights["permission_status"], "not_obtained")
        self.assertEqual(rights["bulk_export_allowed"], "not_established")
        self.assertEqual(rights["automated_extraction_allowed"], "not_authorized")
        self.assertEqual(rights["offline_cache_allowed"], "not_established")
        self.assertEqual(rights["commercial_display_allowed"], "not_established")
        self.assertEqual(rights["redistribution_allowed"], "not_established")

    def test_no_data_or_hash_is_claimed(self):
        for source in (self.central, self.ru):
            self.assertFalse(source["data_ingested"])
            self.assertFalse(source["product_import_allowed"])
            self.assertIsNone(source["source_snapshot_sha256"])
            self.assertEqual(source["hash_status"], "not_downloaded_no_ingestion")

    def test_no_exact_vag_or_repair_fitment_is_claimed(self):
        applicability = self.central["applicability"]
        self.assertFalse(applicability["exact_vag_vehicle_fitment"])
        self.assertFalse(applicability["exact_engine_code_fitment"])
        self.assertFalse(applicability["exact_gearbox_code_fitment"])
        self.assertFalse(applicability["engine_gearbox_pairing"])
        self.assertFalse(applicability["ecu_dtc_repair_applicability"])
        self.assertFalse(applicability["russian_market_scope"])

    def test_russian_eaeu_register_keeps_permission_required_state(self):
        self.assertEqual(self.ru["status"], "permission_required")
        self.assertEqual(self.ru["license"]["identifier"], None)
        self.assertEqual(self.ru["access_and_reuse"]["documented_api"], "not_identified")
        self.assertEqual(self.ru["access_and_reuse"]["offline_cache"], "not_confirmed")
        self.assertEqual(self.ru["access_and_reuse"]["redistribution"], "not_confirmed")


if __name__ == "__main__":
    unittest.main()

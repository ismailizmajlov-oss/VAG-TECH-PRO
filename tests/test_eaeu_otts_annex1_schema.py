import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REGISTER_PATH = ROOT / "data" / "source-manifests" / "vag-factory-source-register.json"


class EaeuOttsAnnex1SchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.register = json.loads(REGISTER_PATH.read_text(encoding="utf-8"))
        cls.eaeu = next(
            source for source in cls.register["sources"]
            if source["source_id"] == "eaeu-otts-unified-register-public-portal"
        )
        cls.elpts = next(
            source for source in cls.register["sources"]
            if source["source_id"] == "elpts-national-otts-register-public-query"
        )

    def test_annex1_records_powertrain_fields_without_promoting_vag_codes(self):
        schema = self.eaeu["normative_attachment_schema"]
        fields = set(schema["observed_form_fields_ru"])
        self.assertIn("Двигатель внутреннего сгорания (марка, тип)", fields)
        self.assertIn("Блок управления (маркировка)", fields)
        self.assertIn("Коробка передач (марка, тип)", fields)
        self.assertIn("Число передач и передаточные числа", fields)
        self.assertIn("Главная передача (тип)", fields)
        self.assertIn("raw_value_semantics", schema)
        self.assertIn("not automatically a VAG", schema["raw_value_semantics"])
        self.assertIn("same", schema["pairing_rule"].lower())
        self.assertFalse(schema["data_imported"])
        self.assertIsNone(schema["source_snapshot_sha256"])

    def test_normative_form_does_not_clear_filled_document_reuse_rights(self):
        rights = self.eaeu["rights"]
        self.assertEqual(rights["data_license_status"], "not_established")
        self.assertEqual(rights["permission_status"], "not_obtained")
        self.assertTrue(rights["permission_required_before_product_import_or_distribution"])
        self.assertEqual(rights["bulk_reuse_allowed"], "not_established")
        self.assertEqual(rights["offline_cache_allowed"], "not_established")
        self.assertEqual(rights["display_and_redistribution_allowed"], "not_established")
        self.assertFalse(self.eaeu["data_ingested"])

    def test_elpts_summary_is_not_misrepresented_as_attachment_data(self):
        observation = self.elpts["public_page_observations"]["ot_ts"]
        self.assertFalse(observation["public_table_exposes_engine_code"])
        self.assertFalse(observation["public_table_exposes_gearbox_code"])
        self.assertFalse(observation["public_table_exposes_engine_gearbox_pair"])
        self.assertFalse(observation["public_table_exposes_ecu"])
        self.assertFalse(self.elpts["data_ingested"])
        self.assertEqual(self.elpts["rights"]["permission_status"], "not_obtained")


if __name__ == "__main__":
    unittest.main()

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTER = ROOT / "data" / "source-manifests" / "vag-factory-source-register.json"
MANIFEST = ROOT / "data" / "source-manifests" / "astra-ch-tas-open-data.json"
SOURCE_ID = "astra-fedro-tas-type-approvals-open-data-ch"


class AstraChTasSourceRightsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.register = json.loads(REGISTER.read_text(encoding="utf-8"))
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.source = next(s for s in cls.register["sources"] if s["source_id"] == SOURCE_ID)

    def test_official_published_ogd_terms_allow_reuse_with_fedro_attribution(self):
        rights = self.source["rights"]
        self.assertEqual(rights["rights_status"], "approved_by_published_ogd_terms")
        for key in ("commercial_use_allowed", "display_allowed", "offline_cache_allowed",
                    "bulk_reuse_allowed", "redistribution_allowed", "attribution_required"):
            self.assertIs(rights[key], True)
        self.assertIn("FEDRO", rights["attribution"])
        self.assertIn("2026-02-23", rights["evidence"])

    def test_market_and_applicability_are_strictly_swiss_type_approval_scope(self):
        self.assertEqual(self.source["market_scope"], ["CH"])
        policy = self.manifest["applicability_policy"]
        self.assertEqual(policy["market_scope"], "CH only")
        self.assertIs(policy["vin_fitment"], False)
        self.assertIs(policy["individual_vehicle_fitment"], False)
        self.assertIs(policy["diagnostic_execution_allowed"], False)
        self.assertFalse(self.manifest["import_policy"]["ru_eaeu_applicability"])

    def test_engine_and_gearbox_fields_are_not_assumed_before_schema_probe(self):
        fields = self.manifest["field_status"]
        self.assertEqual(fields["engine_code"], "schema_probe_pending")
        self.assertEqual(fields["gearbox_code_and_variant_linkage"], "schema_probe_pending")
        self.assertTrue(self.manifest["import_policy"]["never_cross_join_engine_and_gearbox_variants"])

    def test_source_products_are_official_machine_readable_astra_products(self):
        products = self.manifest["data_products"]
        self.assertIn("opendata.astra.admin.ch/ivzod/4000-Typengenehmigungen_TAS", products["json_records_directory"])
        self.assertTrue(products["passenger_car_index"].endswith("TAS_Personenwagen.xlsb"))
        self.assertTrue(products["json_schema"].endswith("govServices_TypeApproval_Schema.json"))
        self.assertTrue(self.manifest["coverage"]["monthly_updates"])
        self.assertFalse(self.manifest["coverage"]["holder_code_disclosed"])


if __name__ == "__main__":
    unittest.main()

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CENTRAL = ROOT / "data" / "source-manifests" / "vag-factory-source-register.json"
REGIONAL = ROOT / "data" / "source-manifests" / "russian-eaeu-otts-sources.json"


class RosstandartOrder2038SchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.central = json.loads(CENTRAL.read_text(encoding="utf-8"))
        cls.regional = json.loads(REGIONAL.read_text(encoding="utf-8"))
        cls.central_source = next(s for s in cls.central["sources"] if s["source_id"] == "rosstandart-fgis-registers-kts")
        cls.regional_source = next(s for s in cls.regional["sources"] if s["source_id"] == "rosstandart-fgis-reestr-kts")

    def test_otts_internal_and_public_namespaces_are_separate(self):
        source = self.regional_source
        public_fields = source["publication_contract"]["public_site_search_fields"]
        self.assertEqual(len(public_fields), 28)
        self.assertEqual(next(f for f in public_fields if f["field"] == 19)["name"], "annex_1_pdf")
        self.assertFalse(any("engine" in f["name"] or "gearbox" in f["name"] for f in public_fields))
        internal_engine = next(f for f in source["ot_ts_attribute_map"] if f["field"] == 50)
        self.assertEqual(internal_engine["name"], "ice_engine_make_and_type")
        self.assertEqual(internal_engine["precision"], "engine_descriptor_not_factory_code")
        self.assertFalse(any(f["field"] == 68 for f in source["ot_ts_attribute_map"]))
        self.assertFalse(source["schema_recheck_2026_11_10"]["confirmed_distinction"]["ot_ts_internal_gearbox_field_present"])
        self.assertEqual(source["schema_recheck_2026_11_10"]["confirmed_distinction"]["ot_ts_internal_gearbox_pdf_fields"], [49, 80])

    def test_sbkts_gearbox_fields_are_not_otts_fitment_evidence(self):
        review = self.regional_source["schema_recheck_2026_11_10"]["confirmed_distinction"]
        self.assertEqual(review["sbkts_gearbox_field"], 68)
        self.assertEqual(review["sbkts_vin_field"], 15)
        self.assertEqual(review["sbkts_personal_data_fields"], [21, 28])
        self.assertFalse(self.central_source["rosstandart_order_2038_schema_review"]["sbkts_internal_fgis_fields"]["allowed_as_otts_fitment_evidence"])

    def test_no_bulk_reuse_or_ingestion_permission_is_inferred(self):
        source = self.regional_source
        self.assertEqual(source["status"], "permission_required")
        self.assertFalse(source["data_ingested"])
        self.assertIsNone(source["source_snapshot_sha256"])
        self.assertEqual(source["license"]["offline_cache"], "not_confirmed")
        self.assertEqual(source["license"]["bulk_export"], "not_confirmed")
        self.assertEqual(source["publication_contract"]["access_and_reuse"]["pdf_redistribution"], "not_confirmed")
        self.assertFalse(self.central_source["data_ingested"])
        self.assertEqual(self.central_source["rights"]["permission_status"], "not_obtained")

    def test_review_document_preserves_secondary_source_and_endpoint_limits(self):
        doc = (ROOT / "docs" / "research" / "ROSSTANDART_ORDER_2038_FGIS_SCHEMA_REVIEW_2026-11-10.md").read_text(encoding="utf-8")
        self.assertIn("secondary republication", doc)
        self.assertIn("no dedicated structured gearbox make/type field", doc)
        self.assertIn("SBKTS", doc)
        self.assertIn("not a license to bulk extract", doc)


if __name__ == "__main__":
    unittest.main()

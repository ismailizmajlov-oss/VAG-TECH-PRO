import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTER_PATH = ROOT / "data/source-manifests/vag-factory-source-register.json"
MANIFEST_DIR = ROOT / "data/source-manifests"
SOURCES = {
    "kba-de-whole-vehicle-type-approvals": "kba-de-whole-vehicle-type-approvals.json",
    "kba-de-fz-hersteller-handelsnamen-pkw": "kba-de-fz-hersteller-handelsnamen-pkw.json",
}


class KbaGermanyOpenDataSourceRightsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.register = json.loads(REGISTER_PATH.read_text(encoding="utf-8"))
        cls.registered = {s["source_id"]: s for s in cls.register["sources"]}
        cls.manifests = {
            source_id: json.loads((MANIFEST_DIR / filename).read_text(encoding="utf-8"))
            for source_id, filename in SOURCES.items()
        }

    def test_both_sources_are_registered_and_rights_cleared(self):
        for source_id, manifest in self.manifests.items():
            with self.subTest(source_id=source_id):
                self.assertIn(source_id, self.registered)
                source = self.registered[source_id]
                self.assertEqual(manifest["source_id"], source_id)
                self.assertEqual(source["market_scope"], ["DE"])
                self.assertEqual(manifest["market_scope"], ["DE"])
                for record in (source, manifest):
                    rights = record["rights"]
                    self.assertEqual(rights["rights_status"], "approved_by_published_DL_DE_BY_2_0")
                    self.assertIn("DL-DE BY 2.0", rights["data_license_status"])
                    for key in ("commercial_use_allowed", "display_allowed", "offline_cache_allowed",
                                "bulk_reuse_allowed", "redistribution_allowed", "attribution_required"):
                        self.assertIs(rights[key], True)
                    self.assertEqual(rights["permission_status"], "not_required_under_published_open_license")
                    self.assertFalse(rights["account_created"])
                    self.assertFalse(rights["paid_terms_accepted"])
                    self.assertIn("https://www.govdata.de/dl-de/by-2-0", rights["evidence_urls"])

    def test_no_data_or_hash_is_claimed_before_download(self):
        for source_id, manifest in self.manifests.items():
            with self.subTest(source_id=source_id):
                source = self.registered[source_id]
                for record in (source, manifest):
                    self.assertFalse(record["data_ingested"])
                    self.assertFalse(record["product_import_allowed"])
                    self.assertIsNone(record["source_snapshot_sha256"])
                    self.assertIn("No source bytes retrieved", record["hash_status"])
                    self.assertEqual(record["verification_status"],
                                     "rights_cleared_metadata_only_source_resource_unavailable_schema_not_verified")
                self.assertFalse(manifest["snapshot"]["downloaded"])
                self.assertIsNone(manifest["snapshot"]["file_sha256"])
                self.assertIsNone(manifest["snapshot"]["source_snapshot_sha256"])

    def test_whole_vehicle_approval_list_is_not_a_powertrain_catalogue(self):
        manifest = self.manifests["kba-de-whole-vehicle-type-approvals"]
        policy = manifest["applicability_policy"]
        self.assertEqual(manifest["snapshot"]["coverage_start"], "2019-01-01")
        self.assertEqual(manifest["snapshot"]["resource_format"], "XLSX")
        self.assertEqual(manifest["snapshot"]["resource_access_status"], "HTTP_503_on_2026-11-07")
        self.assertFalse(policy["individual_vehicle_fitment"])
        self.assertFalse(policy["exact_engine_gearbox_pair"])
        self.assertFalse(policy["production_fitment"])
        self.assertFalse(policy["ru_eaeu_applicability"])
        self.assertEqual(manifest["field_status"]["engine_code"], "not_provided_or_not_verified")
        self.assertEqual(manifest["field_status"]["gearbox_code"], "not_provided_or_not_verified")

    def test_hsn_tsn_source_is_german_identity_only(self):
        manifest = self.manifests["kba-de-fz-hersteller-handelsnamen-pkw"]
        policy = manifest["applicability_policy"]
        self.assertEqual(manifest["snapshot"]["temporal_coverage"], "2023-01-01")
        self.assertEqual(manifest["snapshot"]["reference_date_rule"], "annual reference date of 1 January")
        self.assertEqual(manifest["snapshot"]["resource_access_status"], "HTTP_400_on_2026-11-07")
        self.assertEqual(manifest["field_status"]["model_year"], "reference_date_is_not_model_year")
        self.assertFalse(policy["individual_vehicle_fitment"])
        self.assertFalse(policy["exact_engine_gearbox_pair"])
        self.assertFalse(policy["ru_eaeu_applicability"])
        self.assertEqual(policy["hsn_tsn_semantics"], "registration identity keys only; not engine or gearbox codes")

    def test_attribution_and_urls_are_preserved(self):
        for manifest in self.manifests.values():
            rights = manifest["rights"]
            self.assertIn("Kraftfahrt-Bundesamt", rights["attribution"])
            self.assertIn("DL-DE BY 2.0", rights["attribution"])
            self.assertIn("GovData", rights["attribution"])
            self.assertTrue(manifest["catalog_url"].startswith("https://www.govdata.de/"))
            self.assertTrue(manifest["resource_url"].startswith("https://"))


if __name__ == "__main__":
    unittest.main()

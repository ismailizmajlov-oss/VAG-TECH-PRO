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

    def test_whole_vehicle_approval_snapshot_is_pinned_but_not_ingested(self):
        source_id = "kba-de-whole-vehicle-type-approvals"
        manifest = self.manifests[source_id]
        source = self.registered[source_id]
        expected_sha = "127ae4a1beb236b35c1983f897b7bd234d9f8809e888920a155e4b7d72ff43b4"
        for record in (source, manifest):
            self.assertFalse(record["data_ingested"])
            self.assertFalse(record["product_import_allowed"])
            self.assertEqual(record["source_snapshot_sha256"], expected_sha)
            self.assertIn("SHA-256 verified", record["hash_status"])
            self.assertEqual(
                record["verification_status"],
                "resource_acquired_schema_verified_exact_manufacturer_label_filter_reviewed_research_only",
            )
        self.assertTrue(manifest["snapshot"]["downloaded"])
        self.assertEqual(manifest["snapshot"]["file_sha256"], expected_sha)
        self.assertEqual(manifest["snapshot"]["source_snapshot_sha256"], expected_sha)
        self.assertEqual(manifest["snapshot"]["resource_access_status"], "HTTP_200_on_2026-11-08")
        self.assertEqual(manifest["snapshot"]["byte_size"], 909912)
        self.assertEqual(manifest["snapshot"]["source_row_count"], 3782)
        self.assertEqual(manifest["snapshot"]["vag_related_label_candidate_count"], 918)
        self.assertEqual(manifest["import_policy"]["research_pack_status"],
                         "verified_de_only_research_pack_built; product_database_not_ingested")
        self.assertFalse(manifest["import_policy"]["research_pack_build_pending"])
        self.assertTrue(source["research_pack_built"])
        self.assertFalse(source["research_pack_ingested"])
        self.assertFalse(manifest["product_database_ingested"] if "product_database_ingested" in manifest else False)

    def test_whole_vehicle_approval_list_is_not_a_powertrain_catalogue(self):
        manifest = self.manifests["kba-de-whole-vehicle-type-approvals"]
        policy = manifest["applicability_policy"]
        self.assertEqual(manifest["snapshot"]["coverage_start"], "2019-01-01")
        self.assertEqual(manifest["snapshot"]["resource_format"], "XLSX")
        self.assertEqual(manifest["snapshot"]["resource_access_status"], "HTTP_200_on_2026-11-08")
        self.assertTrue(manifest["snapshot"]["downloaded"])
        self.assertEqual(manifest["snapshot"]["source_snapshot_sha256"], manifest["source_snapshot_sha256"])
        self.assertEqual(manifest["snapshot"]["header_status"], "verified_by_openpyxl_and_independent_probe")
        self.assertFalse(policy["individual_vehicle_fitment"])
        self.assertFalse(policy["exact_engine_gearbox_pair"])
        self.assertFalse(policy["production_fitment"])
        self.assertFalse(policy["ru_eaeu_applicability"])
        self.assertEqual(manifest["field_status"]["engine_code"], "not_provided_or_not_verified")
        self.assertEqual(manifest["field_status"]["gearbox_code"], "not_provided_or_not_verified")

    def test_downloaded_kba_stock_snapshot_is_germany_only_identity_evidence(self):
        source_id = "kba-de-fz-hersteller-handelsnamen-pkw"
        manifest = self.manifests[source_id]
        source = self.registered[source_id]
        snapshot = manifest["snapshot"]
        expected_sha = "03bd9f85e384b2b8bcd0e7d80b5f755eca568e9ad1c45e7fb3fe512e7fedc468"
        expected_labels = [
            "VOLKSWAGEN (D)", "AUDI (D)", "AUDI (H)", "SKODA (CZ)",
            "SEAT (E)", "PORSCHE", "BENTLEY (UK)", "LAMBORGHINI (I)",
        ]
        expected_columns = [
            "Berichtszeitpunkt", "Hersteller", "Handelsname", "Typschlüssel",
            "Bundesland", "Anzahl", "ZS Anzahl", "ObjectId",
        ]
        self.assertEqual(snapshot["status"], "source_snapshot_acquired_schema_verified")
        self.assertTrue(snapshot["downloaded"])
        self.assertEqual(snapshot["resource_access_status"],
                         "HTTP_200_on_2026-11-07_via_hub_arcgis_legacy_download_api")
        self.assertEqual(snapshot["file_sha256"], expected_sha)
        self.assertEqual(snapshot["source_snapshot_sha256"], expected_sha)
        self.assertEqual(snapshot["file_bytes"], 65366675)
        self.assertEqual(snapshot["source_row_count"], 1047991)
        self.assertEqual(snapshot["filtered_vag_row_count"], 264847)
        self.assertEqual(snapshot["observed_columns"], expected_columns)
        self.assertEqual(snapshot["vag_manufacturer_labels"], expected_labels)
        self.assertEqual(snapshot["temporal_coverage_observed"], ["2023-01-01", "2026-01-01"])
        self.assertEqual(manifest["source_snapshot_sha256"], expected_sha)
        self.assertEqual(source["source_snapshot_sha256"], expected_sha)
        for record in (source, manifest):
            self.assertFalse(record["data_ingested"])
            self.assertFalse(record["product_import_allowed"])
            self.assertEqual(record["verification_status"],
                             "rights_cleared_source_snapshot_acquired_schema_verified_research_only_no_vehicle_fitment")
        fields = manifest["field_status"]
        self.assertEqual(fields["hsn"], "not_present_in_downloaded_column_schema")
        self.assertIn("raw source value", fields["type_key"])
        self.assertFalse(manifest["applicability_policy"]["individual_vehicle_fitment"])
        self.assertFalse(manifest["applicability_policy"]["exact_engine_gearbox_pair"])
        self.assertFalse(manifest["applicability_policy"]["ru_eaeu_applicability"])
        self.assertFalse(manifest["applicability_policy"]["production_fitment"])
        expected_pack_status = "separate_de_identity_research_pack_built_verified_desktop_integration_pending"
        self.assertEqual(manifest["import_policy"]["research_pack_status"], expected_pack_status)
        self.assertEqual(manifest["research_pack_status"], expected_pack_status)
        self.assertEqual(source["research_pack_status"], expected_pack_status)
        self.assertIs(source["research_pack_ingested"], True)
        self.assertIs(manifest["research_pack_ingested"], True)
        self.assertIs(source["product_database_ingested"], False)
        self.assertIs(manifest["product_database_ingested"], False)
        self.assertIs(source["data_ingested"], False)
        self.assertIs(manifest["data_ingested"], False)
        self.assertEqual(manifest["source_revision"],
                         "ArcGIS item modified 2026-08-05T07:52:21Z; CSV downloaded 2026-11-07")

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

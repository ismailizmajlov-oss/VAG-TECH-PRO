import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "data" / "source-manifests" / "vag-factory-source-register.json"


class EeaCo2SourceRightsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
        cls.source = next(
            item for item in cls.registry["sources"]
            if item["source_id"] == "eea-co2-passenger-cars-2019-2025"
        )

    def test_published_cc_by_4_rights_are_explicit(self):
        rights = self.source["rights"]
        self.assertEqual(rights["data_license"], "CC-BY-4.0")
        self.assertEqual(rights["license_status"], "official_eea_metadata_declares_CC_BY_4_0")
        for field in (
            "commercial_use_allowed",
            "third_party_display_allowed",
            "offline_cache_allowed",
            "bulk_reuse_allowed",
            "redistribution_allowed",
        ):
            self.assertTrue(rights[field], field)
        self.assertTrue(rights["attribution_required"])
        self.assertFalse(rights["share_alike_required"])

    def test_no_dataset_snapshot_or_product_import_is_claimed(self):
        acquisition = self.source["acquisition"]
        self.assertFalse(acquisition["data_ingested"])
        self.assertFalse(acquisition["full_snapshot_downloaded"])
        self.assertIsNone(acquisition["source_snapshot_sha256"])
        self.assertFalse(acquisition["product_import_allowed"])
        self.assertTrue(acquisition["research_pack_import_allowed"])
        self.assertFalse(self.source["data_ingested"])
        self.assertFalse(self.source["product_import_allowed"])
        self.assertIsNone(self.source["source_snapshot_sha256"])
        attempt = acquisition["last_acquisition_attempt"]
        self.assertEqual(attempt["http_status"], 403)
        self.assertFalse(attempt["dataset_bytes_received"])
        self.assertIsNone(attempt["response_body_sha256"])
        self.assertEqual(acquisition["last_acquisition_attempt_status"], "http_403_forbidden_from_azure_application_gateway_v2_on_github_hosted_windows_2025_runner")
        self.assertIn("Microsoft-Azure-Application-Gateway/v2", attempt["response_summary"])
        self.assertIn("self-hosted runner", attempt["next_step"])

    def test_type_approval_variant_is_not_engine_gearbox_fitment(self):
        applicability = self.source["applicability"]
        self.assertTrue(applicability["official_type_approval_variant_reference"])
        for field in (
            "exact_vehicle_fitment",
            "exact_factory_engine_code",
            "exact_factory_gearbox_code",
            "engine_gearbox_pairing",
            "exact_ecu_dtc_fitment",
            "exact_repair_procedure_applicability",
            "model_generation_verified",
        ):
            self.assertFalse(applicability[field], field)
        self.assertIn("not_oem_powertrain_fitment", applicability["applicability_precision"])

    def test_registration_year_and_provisional_status_are_preserved(self):
        scope = self.source["data_scope"]
        self.assertTrue(scope["registration_year_is_not_model_year"])
        self.assertEqual(scope["year_status"]["2025"], "P_provisional")
        self.assertEqual(scope["year_status"]["2019-2024"], "F_final")
        self.assertEqual(scope["market_scope"], "EU-27 plus Iceland and Norway")
        self.assertEqual(scope["vag_make_filter_status"], "pending_raw_make_discovery")
        self.assertTrue(scope["no_vin"])
        self.assertTrue(scope["no_owner_or_applicant_data"])

    def test_no_factory_codes_are_listed_as_source_fields(self):
        fields = " ".join(self.source["data_scope"]["fields"]).lower()
        self.assertNotIn("engine_code", fields)
        self.assertNotIn("gearbox_code", fields)
        self.assertNotIn("ecu", fields)
        self.assertNotIn("dtc", fields)

    def test_official_evidence_urls_are_present(self):
        urls = {item["url"] for item in self.source["evidence_reviewed"]}
        self.assertIn(
            "https://sdi.eea.europa.eu/catalogue/datahub/api/records/5018ec17-2348-4c92-8761-6f2377bbd1c0?language=eng",
            urls,
        )
        self.assertIn(
            "https://sdi.eea.europa.eu/catalogue/datahub/api/records/b4044b06-2e6b-4f8e-a6e6-66e0e98bb0dd?language=eng",
            urls,
        )
        self.assertIn("https://creativecommons.org/licenses/by/4.0/", urls)


if __name__ == "__main__":
    unittest.main()

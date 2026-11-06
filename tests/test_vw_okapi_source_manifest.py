import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data" / "source-manifests" / "vw-okapi-product-catalog.json"


class VolkswagenOkapiSourceManifestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = json.loads(MANIFEST.read_text(encoding="utf-8"))

    def test_source_is_registered_but_not_approved_or_imported(self):
        source = self.source
        self.assertEqual(source["source_id"], "volkswagen-okapi-product-catalog")
        self.assertEqual(source["ingestion"]["status"], "permission_required")
        self.assertFalse(source["ingestion"]["data_ingested"])
        self.assertIsNone(source["ingestion"]["source_snapshot_sha256"])
        self.assertEqual(source["ingestion"]["production_fitment_rows_added"], 0)
        self.assertFalse(source["ingestion"]["publishable"])

    def test_company_only_access_and_non_sublicensable_offline_distribution_gate(self):
        source = self.source
        self.assertEqual(source["reviewed_at"], "2026-11-06")
        self.assertTrue(source["access"]["requires_company_access_request"])
        self.assertTrue(source["access"]["requires_volkswagen_approval"])
        self.assertTrue(source["access"]["approval_is_discretionary"])
        self.assertEqual(source["contract"]["offline_distribution_of_cached_database"], "not_confirmed_requires_written_clarification")
        self.assertFalse(source["cache_contract"]["redistributable_offline_pack_rights_confirmed"])
        self.assertEqual(source["data_scope"]["market_scope"], "unknown_until_authenticated_country_list_is_observed")
        self.assertEqual(len(source["evidence_reviewed"]), 4)
    def test_canonical_okapi_source_is_registered_with_offline_distribution_blocked(self):
        register = json.loads((ROOT / "data" / "source-manifests" / "vag-factory-source-register.json").read_text(encoding="utf-8"))
        entries = [item for item in register["sources"] if item["source_id"] == "volkswagen-okapi-product-data-api"]
        self.assertEqual(len(entries), 1)
        source = entries[0]
        self.assertEqual(source["source_manifest_path"], "data/source-manifests/vw-okapi-product-catalog.json")
        self.assertFalse(source["product_import_allowed"])
        self.assertFalse(source["data_ingested"])
        self.assertFalse(source["rights"]["offline_cache_allowed"])
        self.assertEqual(source["rights"]["offline_distribution_of_cached_database"], "not_confirmed_requires_written_clarification")
        self.assertEqual(source["market_scope"], ["UNKNOWN"])
    def test_oem_diagnostics_data_requires_eligible_company_and_contract(self):
        manifest = json.loads((ROOT / "data" / "source-manifests" / "vw-oem-repair-data-access.json").read_text(encoding="utf-8"))
        dda = next(item for item in manifest["products"] if item["source_id"] == "volkswagen-group-diagnostics-data")
        self.assertEqual(dda["market_scope"], ["EEA", "UK", "CH"])
        self.assertTrue(dda["access"]["subscription_required"])
        self.assertTrue(dda["access"]["SFD_agreement_required"] if "SFD_agreement_required" in dda["access"] else dda["rights"]["SFD_agreement_required"])
        self.assertTrue(dda["rights"]["volkswagen_encryption_key_agreement_required"])
        self.assertFalse(dda["product_import_allowed"])
        self.assertFalse(dda["data_ingested"])
        self.assertIsNone(dda["source_snapshot_sha256"])

    def test_rmi_license_explicitly_excludes_russia(self):
        manifest = json.loads((ROOT / "data" / "source-manifests" / "vw-oem-repair-data-access.json").read_text(encoding="utf-8"))
        rmi = next(item for item in manifest["products"] if item["source_id"] == "volkswagen-group-rmi-license")
        self.assertFalse(rmi["rights"]["russia_market_allowed"])
        self.assertIn("RUSSIA", rmi["market_scope"][0] + "_" + rmi["market_scope"][1])
        self.assertFalse(rmi["product_import_allowed"])
        self.assertFalse(rmi["data_ingested"])

    def test_erwin_is_not_treated_as_a_data_feed(self):
        manifest = json.loads((ROOT / "data" / "source-manifests" / "vw-oem-repair-data-access.json").read_text(encoding="utf-8"))
        erwin = next(item for item in manifest["products"] if item["source_id"] == "volkswagen-erwin-portal")
        self.assertFalse(erwin["access"]["api_data_feed"])
        self.assertFalse(erwin["rights"]["offline_cache_allowed"])
        self.assertFalse(erwin["rights"]["third_party_redistribution_allowed"])
        self.assertFalse(erwin["product_import_allowed"])

    def test_no_credentials_or_external_account_are_created(self):
        access = self.source["access"]
        self.assertTrue(access["requires_company_access_request"])
        self.assertTrue(access["requires_volkswagen_approval"])
        self.assertTrue(access["requires_client_id_and_secret"])
        self.assertFalse(access["credentials_created"])
        self.assertFalse(access["account_created"])
        self.assertTrue(access["owner_action_required"])
        serialized = json.dumps(self.source).lower()
        for forbidden in ("access_token", "client_secret_value", "bearer "):
            self.assertNotIn(forbidden, serialized)

    def test_contract_does_not_overstate_offline_redistribution_rights(self):
        contract = self.source["contract"]
        self.assertEqual(contract["data_owner"], "Volkswagen AG")
        self.assertEqual(contract["grant"], "non_exclusive_non_transferable_revocable_non_sublicensable")
        self.assertEqual(contract["display_and_evaluate_in_registered_application"], "permitted_subject_to_terms")
        self.assertEqual(contract["disclose_product_data_to_third_parties"], "permitted_subject_to_terms")
        self.assertEqual(contract["offline_cache"], "documented_by_official_caching_guide_for_the_users_application")
        self.assertEqual(contract["offline_distribution_of_cached_database"], "not_confirmed_requires_written_clarification")
        self.assertFalse(contract["paid_terms_accepted"])

    def test_unknown_market_and_repair_fitment_are_not_inferred(self):
        scope = self.source["data_scope"]
        self.assertEqual(scope["market_scope"], "unknown_until_authenticated_country_list_is_observed")
        self.assertFalse(scope["russia_market_confirmed"])
        self.assertFalse(scope["eaeu_market_confirmed"])
        self.assertEqual(scope["engine_code_precision"], "not_established_by_public_api_schema")
        self.assertEqual(scope["gearbox_code_precision"], "not_established_by_public_api_schema")
        self.assertEqual(scope["ecu_precision"], "not_provided")
        self.assertEqual(scope["repair_documentation"], "not_provided")
        self.assertFalse(scope["repair_fitment_claim"])

    def test_cache_refresh_metadata_is_documented(self):
        cache = self.source["cache_contract"]
        self.assertTrue(cache["etag_documented"])
        self.assertTrue(cache["conditional_get_if_none_match_documented"])
        self.assertTrue(cache["catalog_last_update_headers_documented"])
        self.assertTrue(cache["offline_cache_in_registered_application_documented"])
        self.assertFalse(cache["redistributable_offline_pack_rights_confirmed"])


if __name__ == "__main__":
    unittest.main()

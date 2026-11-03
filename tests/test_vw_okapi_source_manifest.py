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

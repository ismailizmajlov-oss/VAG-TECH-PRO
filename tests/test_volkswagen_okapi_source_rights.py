import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REGISTRY = json.loads(
    (ROOT / "data" / "source-manifests" / "vag-factory-source-register.json").read_text(encoding="utf-8")
)
SOURCES = {item["source_id"]: item for item in REGISTRY["sources"]}


class VolkswagenOkapiSourceRightsTests(unittest.TestCase):
    def test_okapi_requires_approved_company_credentials(self):
        source = SOURCES["volkswagen-okapi-product-data-api"]
        access = source["access"]
        self.assertIs(access["authentication_required"], True)
        self.assertIs(access["company_access_request_required"], True)
        self.assertIs(access["volkswagen_approval_required"], True)
        self.assertIs(access["approval_may_be_rejected"], True)
        self.assertIs(access["credentials_obtained"], False)
        self.assertIs(access["api_requests_made"], False)
        self.assertIs(access["external_account_created"], False)
        self.assertIs(access["contract_accepted"], False)
        self.assertIs(access["paid_terms_accepted"], False)

    def test_offline_bundle_rights_fail_closed(self):
        source = SOURCES["volkswagen-okapi-product-data-api"]
        rights = source["rights"]
        self.assertEqual(rights["license_type"], "contractual_access_terms_not_open_data_license")
        self.assertIs(rights["display_allowed_after_approval"], True)
        self.assertIs(rights["third_party_disclosure_allowed_after_approval"], True)
        self.assertIs(rights["cache_mechanism_documented"], True)
        self.assertIs(rights["offline_cache_allowed"], False)
        self.assertIs(rights["redistribution_of_offline_database_allowed"], False)
        self.assertIs(rights["api_right_non_transferable"], True)
        self.assertIs(rights["api_right_revocable"], True)
        self.assertIs(rights["api_right_non_sublicensable"], True)
        self.assertIn("reserves_right_to_charge", rights["current_price_status"])

    def test_no_ru_eaeu_or_factory_code_claims(self):
        source = SOURCES["volkswagen-okapi-product-data-api"]
        self.assertEqual(source["market_scope"], ["UNKNOWN"])
        self.assertIs(source["ru_eaeu_support_confirmed"], False)
        self.assertNotIn("RU", source["publicly_listed_markets"])
        self.assertNotIn("KZ", source["publicly_listed_markets"])
        self.assertNotIn("BY", source["publicly_listed_markets"])
        self.assertIs(source["product_scope"]["engine_factory_code_mapping"], False)
        self.assertIs(source["product_scope"]["gearbox_factory_code_mapping"], False)
        self.assertIs(source["product_scope"]["type_and_option_codes_are_not_proven_engine_or_gearbox_codes"], True)
        self.assertIs(source["data_ingested"], False)
        self.assertIsNone(source["source_snapshot_sha256"])
        self.assertEqual(source["applicability"]["review_status"], "permission_required")

    def test_no_repair_data_is_claimed(self):
        source = SOURCES["volkswagen-okapi-product-data-api"]
        scope = source["product_scope"]
        self.assertIs(scope["repair_procedures"], False)
        self.assertIs(scope["wiring_diagrams"], False)
        self.assertIs(scope["pinouts"], False)
        self.assertIs(scope["dtc_definitions"], False)


if __name__ == "__main__":
    unittest.main()

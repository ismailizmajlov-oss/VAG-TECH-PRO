import json
import unittest
from pathlib import Path

from scripts.probe_rdw_vag_type_approvals import (
    build_soda_url,
    exact_scope_where,
    filter_exact_scope,
    select_nonidentifying_fields,
)

ROOT = Path(__file__).resolve().parents[1]
SOURCE_ID = "rdw-eu-vag-type-approval-open-data-nl"


class RdwEuVagTypeApprovalSourceRightsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.register = json.loads((ROOT / "data/source-manifests/vag-factory-source-register.json").read_text(encoding="utf-8"))
        cls.manifest = json.loads((ROOT / "data/source-manifests/rdw-eu-vag-type-approval-open-data.json").read_text(encoding="utf-8"))
        cls.source = next(s for s in cls.register["sources"] if s["source_id"] == SOURCE_ID)

    def test_live_probe_and_filtered_pack_are_recorded_without_promoting_candidates(self):
        probe = self.manifest["probe"]
        sample = probe["sample_approval_scope"]
        self.assertEqual(probe["status"], "schema_and_exact_scope_verified")
        self.assertEqual(sample["make"], "VOLKSWAGEN")
        self.assertEqual(sample["dutch_trade_name"], "TAYRON")
        self.assertEqual(sample["engine_designation_candidate"], "DUC")
        self.assertEqual(sample["gearbox_type_classification"], "A")
        self.assertFalse(sample["exact_engine_gearbox_pair_claim"])
        self.assertEqual(self.manifest["snapshot"]["status"], "filtered_research_snapshot_acquired")
        self.assertEqual(self.manifest["snapshot"]["source_snapshot_sha256"], "896a34b9b8377f2ed20c34d7e0e33b4cf2ce1958e2cdd2b7326ee8c3157b0706")
        self.assertEqual(len(self.manifest["snapshot"]["source_files"]), 6)
        self.assertEqual(self.manifest["source_snapshot_sha256"], self.manifest["snapshot"]["source_snapshot_sha256"])
        self.assertEqual(self.source["source_snapshot_sha256"], self.manifest["snapshot"]["source_snapshot_sha256"])
        self.assertFalse(self.source["product_import_allowed"])
        self.assertFalse(self.source["data_ingested"])
        self.assertEqual(self.source["verification_status"], "rights_cleared_filtered_research_pack_built_research_only_not_oem_fitment")
        self.assertIn("Run 30 built a separate CC0 NL-only research pack", self.source["project_decision"])
        self.assertFalse(self.source["applicability"]["production_fitment"])
        self.assertFalse(self.source["applicability"]["ru_eaeu_applicability"])

    def test_published_cc0_rights_cover_offline_reuse_and_redistribution(self):
        rights = self.source["rights"]
        self.assertEqual(rights["rights_status"], "approved_by_published_CC0_license")
        for key in ("commercial_use_allowed", "display_allowed", "offline_cache_allowed", "bulk_reuse_allowed", "redistribution_allowed"):
            self.assertIs(rights[key], True)
        self.assertEqual(self.manifest["rights"]["rights_status"], rights["rights_status"])
        self.assertEqual(self.manifest["rights"]["data_license_status"], "CC0 1.0 for each listed dataset, as published in the Dutch national data catalogue")
        self.assertEqual(self.source["market_scope"], ["NL"])

    def test_all_six_dataset_ids_are_pinned_to_rdW_catalogue_cc0_entries(self):
        expected = {
            "registered_vehicle_identity": "m9d7-ebf2",
            "tgk_drive": "4by9-ammk",
            "tgk_gearbox": "7rjk-eycs",
            "tgk_base": "byxc-wwua",
            "tgk_make": "kyri-nuah",
            "tgk_trade_name": "x5v3-sewk",
        }
        products = self.manifest["data_products"]
        for key, dataset_id in expected.items():
            self.assertEqual(products[key]["dataset_id"], dataset_id)
            self.assertEqual(products[key]["catalog_license"], "CC0 1.0")
            self.assertIn("data.overheid.nl/dataset/", products[key]["catalog_url"])
            self.assertIn(dataset_id, products[key]["api_url"])

    def test_registration_query_allowlist_excludes_plate_vin_and_holder_data(self):
        fields = self.manifest["data_products"]["registered_vehicle_identity"]["use_fields"]
        self.assertEqual(fields, [
            "merk", "handelsbenaming", "typegoedkeuringsnummer", "variant", "uitvoering",
            "volgnummer_wijziging_eu_typegoedkeuring", "datum_eerste_toelating", "voertuigsoort",
            "cilinderinhoud", "aantal_cilinders",
        ])
        self.assertFalse(any(token in field.lower() for field in fields for token in ("kenteken", "vin", "houder", "owner")))
        url = build_soda_url("m9d7-ebf2", {"$select": ",".join(fields), "$limit": "5"})
        self.assertNotIn("kenteken", url.lower())
        self.assertNotIn("vin", url.lower())

    def test_engine_and_gearbox_are_not_promoted_or_paired(self):
        policy = self.manifest["applicability_policy"]
        self.assertFalse(policy["exact_vag_engine_code"])
        self.assertFalse(policy["exact_vag_gearbox_code"])
        self.assertFalse(policy["exact_engine_gearbox_pair"])
        self.assertIn("NEVER cross-join", policy["engine_gearbox_pairing"])
        self.assertFalse(self.manifest["import_policy"]["production_import"])
        self.assertFalse(self.manifest["import_policy"]["ru_eaeu_applicability"])
        self.assertFalse(self.source["applicability"]["production_fitment"])
        self.assertFalse(self.source["applicability"]["ru_eaeu_applicability"])

    def test_model_year_and_generation_are_not_inferred(self):
        semantics = self.manifest["field_semantics"]
        self.assertIn("not model year", semantics["model_year"])
        self.assertIn("not generation", semantics["manufacturer_trade_name"])
        self.assertEqual(self.manifest["applicability_policy"]["model_year"], "not_assumed")
        self.assertEqual(self.manifest["applicability_policy"]["generation"], "not_assumed")

    def test_probe_does_not_store_forbidden_registration_fields(self):
        selected = select_nonidentifying_fields({
            "merk": "VOLKSWAGEN",
            "handelsbenaming": "PASSAT",
            "typegoedkeuringsnummer": "e1*2018/858*00366*01",
            "variant": "ACDUCBX0",
            "uitvoering": "FD6FD6DD001NPMN4WEB",
            "volgnummer_wijziging_eu_typegoedkeuring": "0",
            "datum_eerste_toelating": "20240425",
            "voertuigsoort": "Personenauto",
            "cilinderinhoud": "1984",
            "aantal_cilinders": "4",
            "kenteken": "XX-123-X",
        })
        self.assertNotIn("kenteken", selected)
        self.assertEqual(selected["merk"], "VOLKSWAGEN")

    def test_exact_scope_filter_does_not_cross_variants_or_versions(self):
        key = {
            "typegoedkeuringsnummer": "e1*2018/858*00366*01",
            "variant": "ACDUCBX0",
            "uitvoering": "FD6FD6DD001NPMN4WEB",
            "revision": "0",
        }
        rows = [
            {"typegoedkeuringsnummer": key["typegoedkeuringsnummer"], "codevarianttgk": key["variant"],
             "codeuitvoeringtgk": key["uitvoering"], "volgnummerrevisieuitvoering": "0", "motorcode": "CAXA"},
            {"typegoedkeuringsnummer": key["typegoedkeuringsnummer"], "codevarianttgk": "OTHER",
             "codeuitvoeringtgk": key["uitvoering"], "volgnummerrevisieuitvoering": "0", "motorcode": "OTHER"},
            {"typegoedkeuringsnummer": key["typegoedkeuringsnummer"], "codevarianttgk": key["variant"],
             "codeuitvoeringtgk": "OTHER_VERSION", "volgnummerrevisieuitvoering": "0", "motorcode": "OTHER"},
        ]
        matches = filter_exact_scope(rows, key, "codevarianttgk")
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["motorcode"], "CAXA")

    def test_exact_scope_query_uses_all_four_key_fields_and_escapes_values(self):
        key = {
            "typegoedkeuringsnummer": "e1*2018/858*00366*01",
            "variant": "A'B",
            "uitvoering": "V1",
            "revision": "0",
        }
        where = exact_scope_where(key, "codevarianttgk")
        self.assertIn("typegoedkeuringsnummer=", where)
        self.assertIn("codevarianttgk='A''B'", where)
        self.assertIn("codeuitvoeringtgk='V1'", where)
        self.assertIn("volgnummerrevisieuitvoering='0'", where)


if __name__ == "__main__":
    unittest.main()

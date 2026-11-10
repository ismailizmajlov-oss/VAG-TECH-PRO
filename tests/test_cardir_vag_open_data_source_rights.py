from __future__ import annotations
import json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SOURCE_ID="cardir-vag-owner-manual-facts-cc-by-4.0"
class CardirVagOpenDataSourceRightsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest=json.loads((ROOT/"data/source-manifests/cardir-vag-owner-manual-facts-cc-by-4.0.json").read_text(encoding="utf-8"))
        cls.register=json.loads((ROOT/"data/source-manifests/vag-factory-source-register.json").read_text(encoding="utf-8"))
        cls.ru=json.loads((ROOT/"data/source-manifests/russian-eaeu-otts-sources.json").read_text(encoding="utf-8"))
    def test_published_cc_by_4_0_grants_required_reference_pack_rights(self):
        self.assertEqual(self.manifest["rights"]["rights_status"],"approved_by_published_CC_BY_4_0")
        self.assertEqual(self.manifest["rights"]["license_id"],"CC-BY-4.0")
        for field in ("commercial_use_allowed","display_allowed","offline_cache_allowed","bulk_reuse_allowed","redistribution_allowed","attribution_required"):
            self.assertIs(self.manifest["rights"][field],True)
        self.assertIn("cardir.ru/dannye",self.manifest["rights"]["attribution_text"])
    def test_windows_acquired_snapshot_hash_and_counts_are_pinned(self):
        self.assertEqual(self.manifest["snapshot"]["source_snapshot_sha256"],"64a507e4191a9047fe62ec17868488140dd14f692b012d4e1954b6c4322673be")
        self.assertEqual(self.manifest["snapshot"]["source_file_bytes"],15165485)
        self.assertEqual(self.manifest["snapshot"]["status"],"source_snapshot_acquired_schema_verified")
        self.assertEqual(self.manifest["snapshot"]["expected_data_updated_at"],"2026-11-09")
        self.assertEqual(self.manifest["snapshot"]["expected_source_row_count"],44245)
        self.assertEqual(self.manifest["snapshot"]["expected_model_count"],610)
        self.assertEqual(self.manifest["snapshot"]["observed_vag_row_count"],948)
        self.assertEqual(self.manifest["snapshot"]["observed_vag_model_count"],26)
        self.assertIs(self.manifest["import_policy"]["data_ingested"],False)
    def test_central_register_has_one_research_only_entry(self):
        matches=[s for s in self.register["sources"] if s.get("source_id")==SOURCE_ID]
        self.assertEqual(len(matches),1); source=matches[0]
        self.assertIs(source["data_ingested"],False); self.assertIs(source["product_import_allowed"],False)
        self.assertEqual(source["rights"]["permission_status"],"not_required_under_published_CC_BY_4_0")
        self.assertEqual(source["research_pack"]["status"],"source_snapshot_acquired_schema_verified")
        self.assertEqual(source["research_pack"]["vag_fact_rows"],948)
        self.assertEqual(source["research_pack"]["vag_models"],26)
        self.assertEqual(source["research_pack"]["source_snapshot_sha256"],"64a507e4191a9047fe62ec17868488140dd14f692b012d4e1954b6c4322673be")
        self.assertIs(source["research_pack"]["production_import"],False)
    def test_not_misclassified_as_russian_or_eaeu_otts(self):
        self.assertNotIn(SOURCE_ID,{s.get("source_id") for s in self.ru["sources"]})
        self.assertEqual(self.manifest["applicability_policy"]["market_scope"],"UNKNOWN")
        self.assertIs(self.manifest["applicability_policy"]["ru_eaeu_applicability"],False)
    def test_exact_brand_allowlist_matches_pack_builder(self):
        import importlib.util
        spec=importlib.util.spec_from_file_location("cardir_builder",ROOT/"scripts/build_cardir_vag_open_data_pack.py")
        builder=importlib.util.module_from_spec(spec); spec.loader.exec_module(builder)
        manifest_allowlist={builder.normalize_brand(x) for x in self.manifest["data_scope"]["vag_brand_allowlist"]}
        self.assertEqual(manifest_allowlist,builder.ALLOWED_BRANDS)

    def test_no_factory_fitment_or_repair_claims(self):
        policy=self.manifest["applicability_policy"]
        for field in ("exact_engine_code_mapping","exact_gearbox_code_mapping","exact_engine_gearbox_pair","model_generation_inferred","model_year_inferred","exact_vehicle_fitment","ecu_fitment","dtc_fitment","wiring_or_pinout_content","repair_procedure_content","production_fitment"):
            self.assertIs(policy[field],False)
if __name__=="__main__": unittest.main()

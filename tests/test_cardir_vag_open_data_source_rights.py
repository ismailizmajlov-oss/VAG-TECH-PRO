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
        self.assertEqual(self.manifest["snapshot"]["source_snapshot_sha256"],"d4b3f7baf3b278d404bedc512e57bc0cf007b1b95114da0ad1d5a13d160800bf")
        self.assertEqual(self.manifest["data_revision"],"CarDir open-data snapshot 2026-11-09; retrieved 2026-11-10T04:37:02Z; SHA-256 d4b3f7baf3b278d404bedc512e57bc0cf007b1b95114da0ad1d5a13d160800bf")
        self.assertEqual(self.manifest["snapshot"]["source_rows_multiset_sha256"],"af09d2f806e22e294193f7b50faefc9581743427946be5f770fc671d2209e54f")
        self.assertEqual(self.manifest["snapshot"]["vag_rows_multiset_sha256"],"6826b00fbab01c356ec52067e9829441e1c12a8b8c31cf981ab71cceb4f068d0")
        self.assertEqual(self.manifest["snapshot"]["source_file_bytes"],15178035)
        self.assertEqual(self.manifest["snapshot"]["retrieved_at_utc"],"2026-11-10T04:37:02.355843+00:00")
        self.assertEqual(self.manifest["snapshot"]["status"],"source_snapshot_acquired_schema_verified")
        self.assertEqual(self.manifest["snapshot"]["expected_data_updated_at"],"2026-11-09")
        self.assertEqual(self.manifest["snapshot"]["expected_source_row_count"],44272)
        self.assertEqual(self.manifest["snapshot"]["expected_model_count"],611)
        self.assertEqual(self.manifest["snapshot"]["observed_vag_row_count"],948)
        self.assertEqual(self.manifest["snapshot"]["observed_vag_model_count"],26)
        self.assertEqual(self.manifest["snapshot"]["observed_vag_brand_values"],["Audi","Porsche","SEAT","Skoda","Volkswagen"])
        review=self.manifest["snapshot"]["latest_snapshot_review"]
        self.assertEqual(review["previous_snapshot_sha256"],"5b82f00adee26d165cc187e27952f9b2d9a2f3e6c6da216f3030b72cacac370a")
        self.assertEqual(review["current_snapshot_sha256"],"d4b3f7baf3b278d404bedc512e57bc0cf007b1b95114da0ad1d5a13d160800bf")
        self.assertEqual(review["page_url_changed_rows"],354)
        self.assertEqual(review["non_page_url_field_changes"],0)
        self.assertEqual(review["vag_page_url_changed_groups"],13)
        self.assertEqual(review["vag_value_or_unit_changed_groups"],0)
        self.assertIs(review["exact_vag_values_unchanged"],True)
        self.assertIs(review["exact_vag_subset_unchanged_except_page_url"],True)
        self.assertIs(self.manifest["import_policy"]["data_ingested"],False)
    def test_central_register_has_one_research_only_entry(self):
        matches=[s for s in self.register["sources"] if s.get("source_id")==SOURCE_ID]
        self.assertEqual(len(matches),1); source=matches[0]
        self.assertIs(source["data_ingested"],False); self.assertIs(source["product_import_allowed"],False)
        self.assertEqual(source["rights"]["permission_status"],"not_required_under_published_CC_BY_4_0")
        self.assertEqual(source["research_pack"]["status"],"verified_research_only")
        self.assertEqual(source["research_pack"]["vag_fact_rows"],948)
        self.assertEqual(source["research_pack"]["vag_models"],26)
        self.assertEqual(source["research_pack"]["source_snapshot_sha256"],"5b82f00adee26d165cc187e27952f9b2d9a2f3e6c6da216f3030b72cacac370a")
        self.assertEqual(source["verification_status"],"licensed_source_snapshot_and_sqlite_pack_verified_research_only_desktop_integration_pending")
        self.assertEqual(source["research_pack"]["pack_build_status"],"verified_research_only")
        self.assertEqual(source["research_pack"]["desktop_integration_status"],"pending_windows_desktop_lifecycle")
        self.assertEqual(source["research_pack"]["latest_snapshot_refresh_status"],"verified_research_only_pack_built_for_latest_order_only_snapshot")
        self.assertEqual(source["research_pack"]["latest_source_snapshot_sha256"],"5b82f00adee26d165cc187e27952f9b2d9a2f3e6c6da216f3030b72cacac370a")
        self.assertEqual(source["research_pack"]["latest_source_rows_multiset_sha256"],"d147ca79d44472bc049d2dfd600a9a87ac5f1c7db6c2f21fc1b9f0e77fd02a74")
        self.assertEqual(source["research_pack"]["latest_vag_rows_multiset_sha256"],"ded1df125225426b5bfae4377a7309c73453f7f7fc3800babe07633107c8a20b")
        self.assertEqual(source["research_pack"]["source_snapshot_sha256"],"5b82f00adee26d165cc187e27952f9b2d9a2f3e6c6da216f3030b72cacac370a")
        self.assertEqual(source["research_pack"]["database_sha256"],"0aab9c87e863586f1db059499800b1161f52e99e941c5773350ea42bd441da9f")
        self.assertEqual(source["research_pack"]["artifact_sha256"],"6613fb01c9b1555e5afb872356df841c49edd5c83f92a7786966daec2826a251")
        self.assertEqual(source["research_pack"]["artifact_id"],13733081894)
        self.assertEqual(source["research_pack"]["source_snapshot_manifest_sha256"],"c586cd707824df0ef5e3ad85dcd81abcf7927b5da5947691b66d9b1ecf1768ee")
        self.assertEqual(source["research_pack"]["build_report_sha256"],"b3551d1cc2aa6fdda3930c18e43d2d2fe5c2f754a8aefa6f39d2a99712e8626b")
        self.assertEqual(source["research_pack"]["artifact_run_number"],83)
        self.assertEqual(source["research_pack"]["artifact_size_bytes"],1858479)
        self.assertEqual(source["research_pack"]["database_byte_size"],1949696)
        self.assertEqual(source["research_pack"]["artifact_run_id"],42749534305)
        self.assertEqual(source["research_pack"]["source_row_hashes_verified"],948)
        self.assertIs(source["research_pack"]["source_row_number_mapping_verified"],True)
        self.assertEqual(source["research_pack"]["previous_verified_pack"]["source_snapshot_sha256"],"30f502729f08fa7a061ab0f6c19f62eab6385dea646c15878b8c3430b4b064f4")
        self.assertEqual(source["research_pack"]["previous_verified_pack"]["database_sha256"],"bc6df970cff98f71980e402ac8744937d17741ccb0361e301610c65b1f0f8850")
        self.assertEqual(source["research_pack"]["previous_verified_pack"]["source_manifest_sha256"],"9ea9a26e8bd75e95016f3925fed4ee2b3119343fb67329bedfdb40ce0eb310fe")
        self.assertEqual(source["research_pack"]["previous_verified_pack"]["pack_manifest_sha256"],"463f527fe8582f58cf67320894c6ec0edc9b958ae5162926216105fc3e5a3524")
        self.assertEqual(source["research_pack"]["previous_verified_pack"]["artifact_sha256"],"32f2e3e5b39ad1fb8caedcc6bd8da28fc5f32eb3d8cd1360906950c32506487d")
        self.assertEqual(source["research_pack"]["database_sha256"],"0aab9c87e863586f1db059499800b1161f52e99e941c5773350ea42bd441da9f")
        self.assertEqual(source["research_pack"]["source_manifest_sha256"],"527240b1784c435ba747fc033d29f25e369dc84476b4a5e123f780c1aee206a1")
        self.assertEqual(source["research_pack"]["pack_manifest_sha256"],"070eca034f11acc9f4345896c71166a0269c20a1ce52412735cfd9ca8528ed4b")
        self.assertEqual(source["research_pack"]["artifact_sha256"],"6613fb01c9b1555e5afb872356df841c49edd5c83f92a7786966daec2826a251")
        self.assertFalse(source["data_ingested"])
        self.assertFalse(source["product_import_allowed"])
        self.assertIs(source["research_pack"]["production_import"],False)
    def test_current_snapshot_change_review_is_conservative_and_does_not_claim_unavailable_delta(self):
        change = self.manifest["snapshot"]["change_review"]
        self.assertEqual(change["comparison_baseline_sha256"], "64a507e4191a9047fe62ec17868488140dd14f692b012d4e1954b6c4322673be")
        self.assertEqual(change["current_snapshot_sha256"], "30f502729f08fa7a061ab0f6c19f62eab6385dea646c15878b8c3430b4b064f4")
        self.assertEqual(change["vag_rows_added"], 0)
        self.assertEqual(change["vag_rows_removed"], 0)
        self.assertEqual(change["vag_identity_groups_added"], 0)
        self.assertEqual(change["vag_identity_groups_removed"], 0)
        self.assertEqual(change["vag_value_or_unit_changed_groups"], 0)
        self.assertEqual(change["vag_verified_at_changed_groups"], 0)
        self.assertEqual(change["vag_page_url_changed_groups"], 0)
        self.assertIs(change["exact_delta_from_previous_pinned_snapshot_available"], True)
        self.assertEqual(change["source_rows_added"], 52)
        self.assertEqual(change["source_rows_removed"], 25)
        self.assertEqual(change["source_rows_net_change"], 27)
        self.assertEqual(change["vag_rows_net_change"], 0)
        self.assertEqual(change["vag_subset_canonical_rows_sha256"], "92720634c6f6ba907ea554e3bf59afea1ff312444897c365ffe4970b95c108ad")


    def test_latest_order_only_snapshot_is_pinned_with_exact_multiset_evidence(self):
        review = self.manifest["snapshot"]["latest_reorder_review"]
        self.assertEqual(review["previous_snapshot_sha256"], "30f502729f08fa7a061ab0f6c19f62eab6385dea646c15878b8c3430b4b064f4")
        self.assertEqual(review["current_snapshot_sha256"], "5b82f00adee26d165cc187e27952f9b2d9a2f3e6c6da216f3030b72cacac370a")
        self.assertEqual(review["source_rows_multiset_sha256"], "d147ca79d44472bc049d2dfd600a9a87ac5f1c7db6c2f21fc1b9f0e77fd02a74")
        self.assertEqual(review["vag_subset_multiset_sha256"], "ded1df125225426b5bfae4377a7309c73453f7f7fc3800babe07633107c8a20b")
        self.assertEqual(review["source_rows_added"], 0)
        self.assertEqual(review["source_rows_removed"], 0)
        self.assertEqual(review["vag_rows_added"], 0)
        self.assertEqual(review["vag_rows_removed"], 0)
        self.assertIs(review["row_order_changed"], True)
        self.assertIs(review["exact_vag_subset_unchanged"], True)
        self.assertIs(self.manifest["import_policy"]["production_import"], False)
        self.assertIs(self.manifest["import_policy"]["product_import_allowed"], False)

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

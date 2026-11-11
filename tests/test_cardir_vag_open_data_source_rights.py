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
        self.assertEqual(self.manifest["snapshot"]["source_snapshot_sha256"],"902adb1ea1c20eeb98f803a12ffb787a5d082fb184f914091ff8e79bc67ccbbb")
        self.assertEqual(self.manifest["data_revision"],"CarDir open-data snapshot 2026-11-09; retrieved 2026-11-10T05:51:15Z; SHA-256 902adb1ea1c20eeb98f803a12ffb787a5d082fb184f914091ff8e79bc67ccbbb")
        self.assertEqual(self.manifest["snapshot"]["source_rows_multiset_sha256"],"c84a7c2add81f5400234a608b4f0ea1669fead4434779f26cf29ef341cc43b5f")
        self.assertEqual(self.manifest["snapshot"]["vag_rows_multiset_sha256"],"af5102dba4f010cb0909f7a91a3f9cbc1efd692e1e298600946fdd94c9204dca")
        self.assertEqual(self.manifest["snapshot"]["source_file_bytes"],15179458)
        self.assertEqual(self.manifest["snapshot"]["retrieved_at_utc"],"2026-11-10T05:51:15.423849+00:00")
        self.assertEqual(self.manifest["snapshot"]["status"],"source_snapshot_acquired_schema_verified")
        self.assertEqual(self.manifest["snapshot"]["expected_data_updated_at"],"2026-11-09")
        self.assertEqual(self.manifest["snapshot"]["expected_source_row_count"],44272)
        self.assertEqual(self.manifest["snapshot"]["expected_model_count"],611)
        self.assertEqual(self.manifest["snapshot"]["observed_vag_row_count"],948)
        self.assertEqual(self.manifest["snapshot"]["observed_vag_model_count"],26)
        self.assertEqual(self.manifest["snapshot"]["observed_vag_brand_values"],["Audi","Porsche","SEAT","Skoda","Volkswagen"])
        review=self.manifest["snapshot"]["latest_snapshot_review"]
        self.assertEqual(review["previous_snapshot_sha256"],"d4b3f7baf3b278d404bedc512e57bc0cf007b1b95114da0ad1d5a13d160800bf")
        self.assertEqual(review["current_snapshot_sha256"],"902adb1ea1c20eeb98f803a12ffb787a5d082fb184f914091ff8e79bc67ccbbb")
        self.assertEqual(review["page_url_changed_rows"],252)
        self.assertEqual(review["non_page_url_field_changes"],0)
        self.assertEqual(review["vag_page_url_changed_groups"],13)
        self.assertEqual(review["vag_value_or_unit_changed_groups"],0)
        self.assertIs(review["exact_vag_values_unchanged"],True)
        self.assertIs(review["exact_vag_subset_unchanged_except_page_url"],True)
        self.assertIs(self.manifest["import_policy"]["data_ingested"],False)
    def test_central_register_records_verified_research_pack_without_production_promotion(self):
        matches=[s for s in self.register["sources"] if s.get("source_id")==SOURCE_ID]
        self.assertEqual(len(matches),1); source=matches[0]
        self.assertFalse(source["data_ingested"]); self.assertFalse(source["product_import_allowed"])
        self.assertEqual(source["verification_status"],"licensed_source_snapshot_updated_pack_verified_read_only_desktop_research_integration_verified_no_production_import")
        self.assertTrue(source["research_pack_ingested"])
        self.assertTrue(source["research_database_included_in_desktop"])
        self.assertEqual(source["desktop_integration_status"],"verified_read_only_research_pack_integrated_in_offline_desktop")
        pack=source["research_pack"]
        self.assertEqual(pack["status"],"verified_research_only")
        self.assertEqual(pack["pack_build_status"],"verified_research_only")
        self.assertTrue(pack["research_pack_current"])
        self.assertTrue(pack["research_database_included_in_desktop"])
        self.assertEqual(pack["source_snapshot_sha256"],"902adb1ea1c20eeb98f803a12ffb787a5d082fb184f914091ff8e79bc67ccbbb")
        self.assertEqual(pack["source_manifest_sha256"],"64fb51903d237befed7712baafa998d069e3f64bf26fd7974656a418f7feb209")
        self.assertEqual(pack["source_snapshot_manifest_sha256"],"319e01f3656d9bb3dc87b10e637d85679152848442f9d08e7708bbcf87c6b9f3")
        self.assertEqual(pack["pack_manifest_sha256"],"b156a4abcadabd6189fae5627091818eccf7bc1cbcf7e25b5fef876dd1f3949c")
        self.assertEqual(pack["build_report_sha256"],"db34e09c644ae3e1c7100e85e993a36282bf74db5afe0544095dd01379dd0a68")
        self.assertEqual(pack["database_sha256"],"20b5f84ec5e265ea7455cdfa149bf357864d4c9d7571933d65d4f75d80025b4f")
        self.assertEqual(pack["database_byte_size"],1961984)
        self.assertEqual(pack["artifact_id"],13740955733)
        self.assertEqual(pack["artifact_run_number"],145)
        self.assertEqual(pack["artifact_sha256"],"530614ac8ecbdc82ca099a58433558694808bd36b687c16fd8c5db1927c596eb")
        self.assertEqual(pack["source_row_hashes_verified"],948)
        self.assertTrue(pack["source_row_number_mapping_verified"])
        self.assertEqual(pack["sqlite_integrity_check"],"ok")
        self.assertEqual(pack["foreign_key_violations"],0)
        self.assertEqual(pack["desktop_integration_status"],"verified_read_only_research_pack_integrated_in_offline_desktop")
        self.assertEqual(pack["desktop_integration_evidence"]["workflow_run_id"],42964628461)
        self.assertEqual(pack["previous_verified_pack"]["artifact_run_number"],126)
        self.assertEqual(pack["previous_verified_pack_history"][-1]["artifact_run_number"],83)
        self.assertEqual(pack["previous_desktop_lifecycle_evidence"]["run_number"],1208)
        self.assertIsNone(pack["desktop_lifecycle_evidence"])
        self.assertFalse(source["applicability"]["exact_engine_gearbox_pair"])
        self.assertFalse(source["applicability"]["ru_eaeu"])
        self.assertEqual(source["market_scope"],["UNKNOWN"])
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

    def test_latest_snapshot_review_records_only_page_url_changes(self):
        review=self.manifest["snapshot"]["latest_snapshot_review"]
        self.assertEqual(review["previous_snapshot_sha256"],"d4b3f7baf3b278d404bedc512e57bc0cf007b1b95114da0ad1d5a13d160800bf")
        self.assertEqual(review["current_snapshot_sha256"],"902adb1ea1c20eeb98f803a12ffb787a5d082fb184f914091ff8e79bc67ccbbb")
        self.assertEqual(review["page_url_changed_groups"],126)
        self.assertEqual(review["page_url_changed_rows"],252)
        self.assertEqual(review["vag_page_url_changed_groups"],13)
        self.assertEqual(review["vag_page_url_changed_rows"],26)
        self.assertEqual(review["vag_page_url_changed_brands"],["Skoda"])
        self.assertEqual(review["non_page_url_field_changes"],0)
        self.assertTrue(review["exact_vag_values_unchanged"])
        self.assertTrue(review["exact_vag_subset_unchanged_except_page_url"])
        self.assertTrue(review["semantic_rows_unchanged_excluding_page_url"])
        self.assertEqual(review["source_rows_multiset_excluding_page_url_sha256"],"9a4eb1b268758404bced45802070d77bdfff5d386aeec10d3c1cafaf4d9d0eec")
        self.assertEqual(review["vag_rows_multiset_excluding_page_url_sha256"],"8033e6628dca374804fb0282c47b12d315be136a155ee6c3e17e1244984a3a3")
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

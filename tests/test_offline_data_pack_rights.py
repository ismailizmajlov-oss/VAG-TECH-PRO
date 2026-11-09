from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("offline_pack_builder", ROOT / "scripts" / "build_offline_data_pack_index.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class OfflineDataPackRightsTests(unittest.TestCase):
    def test_only_explicitly_licensed_sources_enter_windows_bundle(self):
        self.assertEqual(set(MODULE.ARTIFACTS), {"obdex", "vehiclesdb", "obdb"})
        self.assertNotIn("wal33d", MODULE.ARTIFACTS)

    def test_manufacturer_specific_dtc_candidate_is_excluded(self):
        source = (ROOT / "scripts" / "build_offline_data_pack_index.py").read_text(encoding="utf-8")
        self.assertNotIn("inspect_wal33d", source)
        self.assertNotIn("MANUFACTURER_CODE_RE", source)
        self.assertEqual(
            MODULE.REQUIRED_EXCLUSIONS["wal33d-vag-oem-dtc-mit"],
            "permission_required",
        )
        self.assertIn("No manufacturer-specific DTC pack is included", source)

    def test_restricted_sources_fail_closed_when_missing_mislabeled_or_included(self):
        valid = [
            {
                "source_id": "wal33d-vag-oem-dtc-mit",
                "status": "permission_required",
                "included": False,
            },
            {
                "source_id": "gor3a-vehicle-makes-models-odbl",
                "status": "quarantined_pending_upstream_permission",
                "included": False,
            },
            {
                "source_id": "vag-wiki-community-technical-hub",
                "status": "quarantined_no_reuse_permission",
                "included": False,
            },
        ]
        MODULE.validate_required_exclusions(valid)
        with self.assertRaisesRegex(ValueError, "wal33d-vag-oem-dtc-mit"):
            MODULE.validate_required_exclusions(valid[1:])
        wrong_status = [dict(item) for item in valid]
        wrong_status[0]["status"] = "approved"
        with self.assertRaisesRegex(ValueError, "wal33d-vag-oem-dtc-mit"):
            MODULE.validate_required_exclusions(wrong_status)
        included = [dict(item) for item in valid]
        included[0]["included"] = True
        with self.assertRaisesRegex(ValueError, "wal33d-vag-oem-dtc-mit"):
            MODULE.validate_required_exclusions(included)
        with self.assertRaisesRegex(ValueError, "excluded_sources must be a list"):
            MODULE.validate_required_exclusions(None)

    def test_vag_wiki_reference_is_excluded_from_every_offline_bundle(self):
        self.assertEqual(
            MODULE.REQUIRED_EXCLUSIONS["vag-wiki-community-technical-hub"],
            "quarantined_no_reuse_permission",
        )
        source = (ROOT / "scripts" / "build_offline_data_pack_index.py").read_text(encoding="utf-8")
        self.assertIn('"source_id": "vag-wiki-community-technical-hub"', source)
        self.assertIn("no dataset-specific license or written permission", source)
        self.assertIn("VAG-Wiki independent reference data is quarantined", source)

    def test_vehiclesdb_absent_source_is_not_misclassified_as_excluded(self):
        lock = json.loads((ROOT / "data" / "source-manifests" / "vehiclesdb-vag-identity.lock.json").read_text(encoding="utf-8"))
        self.assertIn("ro_drpciv", lock["not_in_release_sources"])
        self.assertNotIn("ro_drpciv", lock["excluded_source_reasons"])

    def test_generic_obdex_remains_explicitly_generic(self):
        source = (ROOT / "scripts" / "build_offline_data_pack_index.py").read_text(encoding="utf-8")
        self.assertIn("generic_sae_iso_obd2", source)
        self.assertIn("manufacturer-controlled or malformed DTC ranges", source)
        self.assertIn("raw_references_preserved_not_fetched_not_linked", source)

    def test_autoevolution_derived_identity_dataset_is_excluded(self):
        source = (ROOT / "scripts" / "build_offline_data_pack_index.py").read_text(encoding="utf-8")
        artifact_block = source.split("ARTIFACTS =", 1)[1].split("GENERIC_OBD_CODE_RE", 1)[0]
        self.assertNotIn('"odbl":', artifact_block)
        self.assertNotIn('"vag-engine-candidates-odbl": inspect_odbl', source)
        self.assertIn('"source_id": "gor3a-vehicle-makes-models-odbl"', source)
        self.assertIn('"status": "quarantined_pending_upstream_permission"', source)
        self.assertIn("Autoevolution-derived ODbL generation/engine candidate data is quarantined and excluded", source)

    def test_bundle_requires_exactly_three_separate_pack_ids(self):
        source = (ROOT / "scripts" / "build_offline_data_pack_index.py").read_text(encoding="utf-8")
        self.assertIn('index.get("database_count") != 3', source)
        self.assertIn('"database_count": 3', source)
        self.assertIn('"obdb-vag-signals-cc-by-sa"', source)


    def test_obdex_lock_pins_generic_ranges_and_external_reference_quarantine(self):
        lock = json.loads((ROOT / "data" / "source-manifests" / "obdex-generic-cc0.lock.json").read_text(encoding="utf-8"))
        self.assertEqual(lock["scope"]["generic_code_ranges"], ["P0xxx", "P2xxx", "P34xx", "B0xxx", "C0xxx", "U0xxx", "U3xxx"])
        self.assertEqual(lock["scope"]["excluded_manufacturer_controlled_ranges"], ["P1xxx", "P30xx-P33xx", "P35xx-P39xx", "B1xxx-B2xxx", "C1xxx-C2xxx", "U1xxx-U2xxx"])
        self.assertIs(lock["normalization_policy"]["research_pack_only"], True)
        self.assertIs(lock["normalization_policy"]["normalized_product_dtc_import_allowed"], False)
        self.assertEqual(lock["normalization_policy"]["unverified_ranges_for_normalized_import"], ["P34xx-P39xx", "U3xxx", "B3xxx", "C3xxx"])
        display = lock["normalization_policy"]["display_policy"]
        self.assertEqual(display["policy_id"], "vag-tech-pro-dtc-namespace-ranges")
        self.assertEqual(display["policy_revision"], "run87-2026-11-08")
        self.assertEqual(display["allowed_generic_ranges"], ["P0xxx", "P2xxx", "B0xxx", "C0xxx", "U0xxx"])
        self.assertEqual(display["quarantined_unresolved_ranges"], ["P34xx-P39xx", "U3xxx", "B3xxx", "C3xxx"])
        self.assertEqual(lock["expected_counts"]["searchable_generic_dtcs"], 9204)
        self.assertEqual(lock["expected_counts"]["quarantined_unresolved_namespace_rows"], 329)
        self.assertIs(display["upstream_generic_label_is_not_authoritative"], True)
        self.assertIs(display["searchable_generic_only"], True)
        self.assertEqual(lock["source_reference_policy"], {
            "validation": "syntax_only",
            "external_fetch": False,
            "rights_review": "not_inherited_from_cc0_dataset",
            "allowed_schemes": ["https", "http"],
            "display_policy": "external_reference_link_only",
        })
        workflow = (ROOT / ".github" / "workflows" / "acquire-obdex-cc0.yml").read_text(encoding="utf-8")
        self.assertIn("source_reference_policy = $lock.source_reference_policy", workflow)
        self.assertIn("const p3GenericCode = /^P34[0-9A-F]{2}$/;", workflow)
        for code in ("P0ABC", "P2ABC", "B0ABC", "C0ABC", "U0ABC"):
            self.assertTrue(MODULE.GENERIC_OBD_CODE_RE.fullmatch(code))
        self.assertFalse(MODULE.GENERIC_OBD_CODE_RE.fullmatch("P34C8"))
        self.assertFalse(MODULE.GENERIC_OBD_CODE_RE.fullmatch("U3000"))
        self.assertTrue(MODULE.UNRESOLVED_RESERVED_DTC_RE.fullmatch("P34C8"))
        self.assertTrue(MODULE.UNRESOLVED_RESERVED_DTC_RE.fullmatch("P39AB"))
        self.assertTrue(MODULE.UNRESOLVED_RESERVED_DTC_RE.fullmatch("U3ABC"))
        self.assertTrue(MODULE.UNRESOLVED_RESERVED_DTC_RE.fullmatch("B3ABC"))
        self.assertTrue(MODULE.UNRESOLVED_RESERVED_DTC_RE.fullmatch("C3ABC"))
        self.assertTrue(MODULE.UPSTREAM_OBDEX_LABELLED_CODE_RE.fullmatch("P34C8"))
        self.assertTrue(MODULE.UPSTREAM_OBDEX_LABELLED_CODE_RE.fullmatch("U3ABC"))
        self.assertFalse(MODULE.UPSTREAM_OBDEX_LABELLED_CODE_RE.fullmatch("P3500"))
        self.assertFalse(MODULE.UPSTREAM_OBDEX_LABELLED_CODE_RE.fullmatch("P33FF"))
        self.assertIn("sourceManifest.scope.generic_code_ranges", workflow)
        self.assertIn("Non-generic or manufacturer-controlled DTC", workflow)


    def test_obdex_acquisition_is_called_once_by_offline_pack_workflow(self):
        workflow = (ROOT / ".github" / "workflows" / "acquire-obdex-cc0.yml").read_text(encoding="utf-8")
        trigger_block = workflow.split("jobs:", 1)[0]
        self.assertIn("workflow_call:", trigger_block)
        self.assertIn("workflow_dispatch:", trigger_block)
        self.assertNotIn("pull_request:", trigger_block)
        self.assertNotIn("push:", trigger_block)
        pack_workflow = (ROOT / ".github" / "workflows" / "build-windows-offline-data-packs.yml").read_text(encoding="utf-8")
        self.assertNotIn("scripts/sync-desktop-research-manifest.cjs", pack_workflow.split("permissions:", 1)[0])
        self.assertIn("obdex-generic-cc0.lock.json", pack_workflow)

    def test_obdex_refresh_lock_and_artifact_are_revision_pinned(self):
        lock = json.loads((ROOT / "data" / "source-manifests" / "obdex-generic-cc0.lock.json").read_text(encoding="utf-8"))
        self.assertEqual(lock["commit_sha"], "9ba1ffa095f3140d9e21b985b322ddea3134bb60")
        self.assertEqual(lock["commit_date_utc"], "2026-11-07T13:43:17Z")
        self.assertEqual(lock["license_url"], "https://github.com/foerbsnavi/OBDex/blob/9ba1ffa095f3140d9e21b985b322ddea3134bb60/LICENSE-DATA")
        self.assertEqual(MODULE.ARTIFACTS["obdex"][0], "vag-tech-pro-obdex-cc0-2026-11-07")
        workflow = (ROOT / ".github" / "workflows" / "acquire-obdex-cc0.yml").read_text(encoding="utf-8")
        self.assertIn("vag-tech-pro-obdex-cc0-2026-11-07", workflow)

    def test_desktop_obdex_revision_test_tracks_the_pack_manifest(self):
        patch = (ROOT / "apply-research-pack-hash-fix-run44.cjs").read_text(encoding="utf-8")
        self.assertIn("rows[0].upstreamRevision, obdexPack.upstream_revision", patch)
        self.assertIn(r'tests.match(/^  assert\.equal\(rows\[0\]\.upstreamRevision', patch)
        self.assertIn("oldRevisionAssertions.length === 1", patch)
        self.assertIn("stale or ambiguous desktop test patch", patch)

    def test_obdex_source_register_is_generic_and_not_vag_fitment(self):
        registry = json.loads((ROOT / "data" / "source-manifests" / "vag-factory-source-register.json").read_text(encoding="utf-8"))
        source = next(item for item in registry["sources"] if item["source_id"] == "obdex-generic-cc0")
        self.assertEqual(source["pinned_revision"], "9ba1ffa095f3140d9e21b985b322ddea3134bb60")
        self.assertEqual(source["rights"]["data_license_status"], "CC0-1.0 for upstream data files only")
        self.assertEqual(source["market_scope"], ["UNKNOWN"])
        self.assertFalse(source["applicability"]["vag_specific"])
        self.assertFalse(source["applicability"]["exact_vehicle_fitment"])
        self.assertEqual(source["data_counts_as_published"]["vag_specific_dtc_rows"], 0)
        self.assertEqual(source["data_counts_as_published"]["production_rows"], 0)
        self.assertEqual(source["data_counts_as_published"]["searchable_generic_dtc_rows"], 9204)
        self.assertEqual(source["data_counts_as_published"]["unresolved_reserved_quarantined_rows"], 329)
        self.assertFalse(source["rights"]["source_reference_policy"]["external_fetch"])
        self.assertTrue(source["rights"]["source_references_quarantined"])


    def test_desktop_research_sync_guard_matches_obdex_locked_ranges(self):
        lock = json.loads((ROOT / "data" / "source-manifests" / "obdex-generic-cc0.lock.json").read_text(encoding="utf-8"))
        sync_source = (ROOT / "scripts" / "sync-desktop-research-manifest.cjs").read_text(encoding="utf-8")
        self.assertIn("(sourceManifest.sources || []).length !== 16", sync_source)
        allowed = json.dumps(lock["scope"]["generic_code_ranges"])
        excluded = json.dumps(lock["scope"]["excluded_manufacturer_controlled_ranges"])
        self.assertIn(f"JSON.stringify(scope.generic_code_ranges) !== JSON.stringify({allowed})", sync_source)
        self.assertIn(f"JSON.stringify(scope.excluded_manufacturer_controlled_ranges) !== JSON.stringify({excluded})", sync_source)
        self.assertIn("P35xx-P39xx", excluded)
        self.assertIn("P34xx", allowed)
        self.assertNotIn("P34xx-P39xx", allowed)
        self.assertIn("normalization.normalized_product_dtc_import_allowed", sync_source)
        self.assertIn("namespacePolicy.policy_id", sync_source)
        self.assertIn("searchable_generic_dtcs", sync_source)
        self.assertIn("quarantined_unresolved_namespace_rows", sync_source)
        display = lock["normalization_policy"]["display_policy"]
        self.assertIn("P34xx-P39xx", display["quarantined_unresolved_ranges"])
        self.assertNotIn("P34xx", display["allowed_generic_ranges"])
        builder_source = (ROOT / "scripts" / "build_offline_data_pack_index.py").read_text(encoding="utf-8")
        self.assertIn("OBDEX_LOCK_PATH", builder_source)
        self.assertIn("normalization_policy", builder_source)
        self.assertIn("U3xxx", lock["normalization_policy"]["unverified_ranges_for_normalized_import"])


    def test_obdex_run257_acquisition_evidence_matches_independently_verified_bundle(self):
        registry = json.loads((ROOT / "data" / "source-manifests" / "vag-factory-source-register.json").read_text(encoding="utf-8"))
        source = next(item for item in registry["sources"] if item["source_id"] == "obdex-generic-cc0")
        evidence = source["acquisition_evidence"]
        bundle = source["offline_bundle"]
        self.assertEqual(evidence["workflow_run_id"], 42449826346)
        self.assertEqual(evidence["workflow_run_number"], 257)
        self.assertEqual(evidence["source_artifact_id"], 13605022128)
        self.assertEqual(evidence["source_artifact_sha256"], "c90764e2c2a7ea924ee59544be9119b15fccc2a58c301670576014b9af6f1a6c")
        self.assertEqual(evidence["source_artifact_size_bytes"], 33741187)
        self.assertEqual(evidence["offline_bundle_artifact_id"], 13604839352)
        self.assertEqual(evidence["offline_bundle_sha256"], "675b83b5c255148da4750056e4942a398c71017e7da6a1c6a711ca95a2112909")
        self.assertEqual(evidence["offline_bundle_size_bytes"], 39103188)
        self.assertEqual(evidence["database_sha256"], "fb2797cd9ea5ff7a1cc92f9197f382150f1745d661dba7bc1310bb1d895dc046")
        self.assertEqual(evidence["source_manifest_sha256"], "4c62614574095cc077c56506785a78041ddf0b68d0be158c1edc928a15865c15")
        self.assertEqual(evidence["package_sha256"], "501007f853ce66523576d2971f6bdf1adeb999dc42a5963f0f6d37c605c428f1")
        self.assertEqual(evidence["offline_bundle_index_sha256"], "27e9ee82377595f81ea1c71256fedd7c7ccc8936387bcd3e77b6567ae17eac88")
        self.assertEqual(evidence["counts"]["p34_generic_rows"], 155)
        self.assertEqual(evidence["counts"]["u3_research_rows"], 174)
        self.assertEqual(evidence["counts"]["u3_normalized_rows"], 0)
        self.assertFalse(evidence["normalized_product_dtc_import_allowed"])
        self.assertEqual(source["data_counts_as_published"]["u3_quarantined_research_rows"], 174)
        self.assertEqual(source["data_counts_as_published"]["vag_specific_dtc_rows"], 0)
        self.assertEqual(source["data_counts_as_published"]["production_rows"], 0)
        self.assertEqual(bundle["artifact_id"], 13604839352)
        self.assertEqual(bundle["bundle_index_sha256"], evidence["offline_bundle_index_sha256"])
        self.assertEqual(bundle["obdex_database_sha256"], evidence["database_sha256"])
        self.assertEqual(bundle["obdex_manifest_sha256"], evidence["source_manifest_sha256"])
        self.assertEqual(bundle["separate_database_count"], 3)
        self.assertFalse(source["product_import_allowed"])


    def test_autodiag2_latest_branch_rows_remain_quarantined_without_upstream_rights(self):
        registry = json.loads((ROOT / "data" / "source-manifests" / "vag-factory-source-register.json").read_text(encoding="utf-8"))
        source = next(item for item in registry["sources"] if item["source_id"] == "autodiag2-vag-community-v6")
        review = source["latest_branch_review"]
        self.assertEqual(review["commit_sha"], "11e73fd6d105a071fa472f426d23225344921a19")
        self.assertEqual(review["license_ids"], ["ODbL-1.0", "DbCL-1.0"])
        self.assertEqual(review["license_file_sha256"], "50a8762802c3303f5612c002bd35a3e617dcc7315ff7073f784b8682ea646cb5")
        self.assertEqual(review["upstream_evidence_rights_status"], "not_established_for_obdcodex_and_flex_referenced_materials")
        self.assertFalse(review["product_import_allowed"])
        self.assertFalse(review["data_ingested"])
        self.assertIsNone(review["source_snapshot_sha256"])
        records = {item["path"]: item for item in review["sampled_records"]}
        self.assertEqual(records["data-src/ecu/generic/volkswagen/def.yml"]["sha256"], "b1d01c525b1f1404ffa21d654c21f98c6eede4049b9cc5ee1af845a7f17c4f09")
        self.assertEqual(records["data-src/ecu/generic/audi/codes/P1639.yml"]["sha256"], "75692736477dda18b9c9db8b972daab21010e9c431c4414ec3c5a4afe2c9cafb")
        self.assertIn("obdcodex", records["data-src/ecu/generic/audi/codes/P1639.yml"]["observed_evidence"])
        golf = records["data-src/vehicle/Volkswagen/Golf/versions/V/BVX_MED9.5.yml"]
        self.assertEqual(golf["sha256"], "e533584deae0a48fa3c6e4e4a59f21ea22bfde2a1a382e59d6501cf1f1a1771d")
        self.assertIn("transmission_code", golf["missing_fields"])
        self.assertIn("FLEX-FULL-vehicle-list-2020-11-9.pdf", golf["observed_evidence"][0])
        self.assertFalse(source["data_ingested"])
        self.assertFalse(source["diagnostic_execution_allowed"])
        self.assertFalse(source["repair_advice_approved"])


    def test_obdex_upstream_labelled_p34_and_u3_rows_are_not_searchable_generic(self):
        lock = json.loads((ROOT / "data" / "source-manifests" / "obdex-generic-cc0.lock.json").read_text(encoding="utf-8"))
        display = lock["normalization_policy"]["display_policy"]
        self.assertEqual(display["expected_searchable_generic_dtcs"], 9204)
        self.assertEqual(display["expected_quarantined_unresolved_namespace_rows"], 329)
        self.assertEqual(display["expected_unclassified_rows"], 0)
        self.assertTrue(MODULE.GENERIC_OBD_CODE_RE.fullmatch("P0300"))
        self.assertTrue(MODULE.GENERIC_OBD_CODE_RE.fullmatch("U0100"))
        self.assertFalse(MODULE.GENERIC_OBD_CODE_RE.fullmatch("P3400"))
        self.assertFalse(MODULE.GENERIC_OBD_CODE_RE.fullmatch("U3000"))
        self.assertTrue(MODULE.UNRESOLVED_RESERVED_DTC_RE.fullmatch("P3400"))
        self.assertTrue(MODULE.UNRESOLVED_RESERVED_DTC_RE.fullmatch("U3000"))
        builder = (ROOT / "scripts" / "build_offline_data_pack_index.py").read_text(encoding="utf-8")
        self.assertIn("DTC_NAMESPACE_POLICY_PATH", builder)
        self.assertIn("unclassified_codes", builder)
        self.assertIn("quarantined_unresolved_namespace_rows", builder)
        sync = (ROOT / "scripts" / "sync-desktop-research-manifest.cjs").read_text(encoding="utf-8")
        self.assertIn("namespace_policy: obdex.namespace_policy", sync)
        self.assertIn("quarantined_unresolved_namespace_rows: obdex.counts.quarantined_unresolved_namespace_rows", sync)


if __name__ == "__main__":
    unittest.main()

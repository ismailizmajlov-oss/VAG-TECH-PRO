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
        self.assertIn("U3xxx", lock["normalization_policy"]["unverified_ranges_for_normalized_import"])
        self.assertIn("(sourceManifest.sources || []).length !== 16", sync_source)
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
        self.assertTrue(MODULE.GENERIC_OBD_CODE_RE.fullmatch("P34C8"))
        self.assertFalse(MODULE.GENERIC_OBD_CODE_RE.fullmatch("P3500"))
        self.assertFalse(MODULE.GENERIC_OBD_CODE_RE.fullmatch("P33FF"))
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
        self.assertFalse(source["rights"]["source_reference_policy"]["external_fetch"])
        self.assertTrue(source["rights"]["source_references_quarantined"])


    def test_desktop_research_sync_guard_matches_obdex_locked_ranges(self):
        lock = json.loads((ROOT / "data" / "source-manifests" / "obdex-generic-cc0.lock.json").read_text(encoding="utf-8"))
        sync_source = (ROOT / "scripts" / "sync-desktop-research-manifest.cjs").read_text(encoding="utf-8")
        allowed = json.dumps(lock["scope"]["generic_code_ranges"])
        excluded = json.dumps(lock["scope"]["excluded_manufacturer_controlled_ranges"])
        self.assertIn(f"JSON.stringify(scope.generic_code_ranges) !== JSON.stringify({allowed})", sync_source)
        self.assertIn(f"JSON.stringify(scope.excluded_manufacturer_controlled_ranges) !== JSON.stringify({excluded})", sync_source)
        self.assertIn("P35xx-P39xx", excluded)
        self.assertIn("P34xx", allowed)
        self.assertNotIn("P34xx-P39xx", allowed)
        self.assertIn("normalization.normalized_product_dtc_import_allowed", sync_source)
        builder_source = (ROOT / "scripts" / "build_offline_data_pack_index.py").read_text(encoding="utf-8")
        self.assertIn("OBDEX_LOCK_PATH", builder_source)
        self.assertIn("normalization_policy", builder_source)
        self.assertIn("U3xxx", lock["normalization_policy"]["unverified_ranges_for_normalized_import"])


if __name__ == "__main__":
    unittest.main()

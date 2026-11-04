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
        self.assertEqual(lock["scope"]["generic_code_ranges"], ["P0xxx", "P2xxx", "P34xx-P39xx", "B0xxx", "C0xxx", "U0xxx", "U3xxx"])
        self.assertEqual(lock["scope"]["excluded_manufacturer_controlled_ranges"], ["P1xxx", "P30xx-P33xx", "B1xxx-B2xxx", "C1xxx-C2xxx", "U1xxx-U2xxx"])
        self.assertEqual(lock["source_reference_policy"], {
            "validation": "syntax_only",
            "external_fetch": False,
            "rights_review": "not_inherited_from_cc0_dataset",
            "allowed_schemes": ["https", "http"],
            "display_policy": "external_reference_link_only",
        })
        workflow = (ROOT / ".github" / "workflows" / "acquire-obdex-cc0.yml").read_text(encoding="utf-8")
        self.assertIn("source_reference_policy = $lock.source_reference_policy", workflow)


if __name__ == "__main__":
    unittest.main()

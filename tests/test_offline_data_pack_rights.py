from __future__ import annotations

import importlib.util
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
        self.assertIn('"source_id": "wal33d-vag-oem-dtc-mit"', source)
        self.assertIn('"status": "permission_required"', source)
        self.assertIn('"included": False', source)
        self.assertIn("Permission-required manufacturer DTC source is not explicitly excluded", source)
        self.assertIn("No manufacturer-specific DTC pack is included", source)

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


if __name__ == "__main__":
    unittest.main()

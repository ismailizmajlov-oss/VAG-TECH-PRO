import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from scripts.filter_autodiag2_vag_dtc_candidates import filter_pack


class AutoDiag2VagDtcPolicyTests(unittest.TestCase):
    def build_pack(self, root: Path) -> None:
        (root / "upstream").mkdir()
        (root / "upstream" / "LICENSE").write_text("ODbL-1.0 / DbCL-1.0 fixture\n", encoding="utf-8")
        (root / "upstream" / "README.md").write_text("synthetic fixture only\n", encoding="utf-8")
        (root / "ATTRIBUTION.txt").write_text("synthetic fixture only\n", encoding="utf-8")
        manifest = {
            "pack_id": "autodiag2-vag-community-v6",
            "license": {
                "database": "ODbL-1.0",
                "contents": "DbCL-1.0",
                "commercial_use_allowed": True,
                "display_allowed": True,
                "offline_cache_allowed": True,
                "redistribution_allowed": True,
                "separate_pack_required": True,
            },
            "counts": {"vehicle_models": 1, "vehicle_versions": 1, "engines": 1, "ecus": 1},
            "excluded_dtc_counts": {},
        }
        (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        db = sqlite3.connect(root / "autodiag2-vag-community.sqlite")
        db.execute("PRAGMA foreign_keys=ON")
        db.executescript("""
            CREATE TABLE source_registry(
              source_id TEXT, database_license TEXT, contents_license TEXT
            );
            CREATE TABLE dtc_candidates(
              id INTEGER PRIMARY KEY, source_scope TEXT NOT NULL,
              ecu_manufacturer TEXT, namespace TEXT NOT NULL
            );
            CREATE TABLE engine_candidates(
              id INTEGER PRIMARY KEY, engine_code TEXT, engine_code_quality TEXT NOT NULL
            );
            CREATE TABLE dtc_fitment_candidates(
              dtc_candidate_id INTEGER NOT NULL REFERENCES dtc_candidates(id),
              vehicle_config_candidate_id INTEGER NOT NULL
            );
            INSERT INTO source_registry VALUES(
              'autodiag2-vag-community-v6','ODbL-1.0','DbCL-1.0'
            );
            INSERT INTO dtc_candidates VALUES
              (1,'make_level','generic','manufacturer_controlled_candidate'),
              (2,'vehicle_ecu_linked','generic','manufacturer_controlled_candidate'),
              (3,'vehicle_ecu_linked','Bosch','manufacturer_controlled_candidate'),
              (4,'vehicle_ecu_linked','Bosch','uds_ecu_specific_candidate'),
              (5,'vehicle_ecu_linked','unknown','manufacturer_controlled_candidate');
            INSERT INTO dtc_fitment_candidates VALUES (1,10),(2,20),(4,40),(5,50);
            INSERT INTO engine_candidates VALUES
              (1,'AFN','factory_code_shape_candidate'),
              (2,'8HP45','factory_code_shape_candidate'),
              (3,'1000 TFSI','unclassified_source_label'),
              (4,NULL,'unclassified_source_label');
        """)
        db.commit()
        db.close()

    def test_removes_make_level_generic_and_unlinked_candidates(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.build_pack(root)
            result = filter_pack(root)
            self.assertEqual(result["status"], "passed")
            self.assertEqual(result["before"]["dtc_candidates"], 5)
            self.assertEqual(result["after"]["dtc_candidates"], 1)
            self.assertEqual(result["after"]["vehicle_ecu_linked_dtc_candidates"], 1)
            self.assertEqual(result["after"]["make_level_dtc_candidates"], 0)
            self.assertEqual(result["after"]["dtc_fitment_candidate_links"], 1)
            self.assertEqual(result["removed"]["unattributed_make_level"], 1)
            self.assertEqual(result["removed"]["generic_or_unknown_ecu_identity"], 2)
            self.assertEqual(result["removed"]["missing_vehicle_configuration_link"], 1)
            self.assertEqual(result["after"]["engine_code_candidates_unverified"], 3)
            self.assertEqual(result["after"]["engine_codes_verified"], 0)
            db = sqlite3.connect(root / "autodiag2-vag-community.sqlite")
            self.assertEqual(db.execute("PRAGMA integrity_check").fetchone()[0], "ok")
            self.assertEqual(db.execute("SELECT id FROM dtc_candidates").fetchall(), [(4,)])
            self.assertEqual(db.execute("SELECT dtc_candidate_id FROM dtc_fitment_candidates").fetchall(), [(4,)])
            self.assertEqual(
                db.execute("SELECT engine_code_quality FROM engine_candidates ORDER BY id").fetchall(),
                [('unverified_source_code_field',),('unverified_source_code_field',),
                 ('unverified_source_code_field',),('unclassified_source_label',)]
            )
            db.close()
            manifest = json.loads((root / "manifest.json").read_text())
            self.assertTrue(manifest["dtc_policy_filtered"])
            self.assertEqual(manifest["counts"]["vag_specific_dtc_verified_rows"], 0)
            self.assertEqual(manifest["counts"]["engine_codes_verified"], 0)
            self.assertTrue(manifest["engine_code_policy"]["shape_heuristic_is_not_used_for_verification"])
            self.assertEqual(manifest["dtc_policy_removal_counts"]["unattributed_make_level"], 1)
            self.assertEqual(manifest["candidate_database_sha256"], result["candidate_database_sha256"])
            checksum_lines = (root / "SHA256SUMS.txt").read_text().splitlines()
            self.assertEqual(len(checksum_lines), 5)

    def test_rejects_license_without_offline_cache_right(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.build_pack(root)
            manifest_path = root / "manifest.json"
            manifest = json.loads(manifest_path.read_text())
            manifest["license"]["offline_cache_allowed"] = False
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "Offline-cache right"):
                filter_pack(root)

    def test_rejects_wrong_source_registry(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.build_pack(root)
            db = sqlite3.connect(root / "autodiag2-vag-community.sqlite")
            db.execute("UPDATE source_registry SET source_id='other-source'")
            db.commit()
            db.close()
            with self.assertRaisesRegex(RuntimeError, "source registry"):
                filter_pack(root)


if __name__ == "__main__":
    unittest.main()

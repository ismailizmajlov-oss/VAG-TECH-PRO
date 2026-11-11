"""Regression tests for the read-only VehiclesDB release count probe."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from probe_vag_identity_vehiclesdb import probe_counts
from test_vag_identity_vehiclesdb import fixture


class VehiclesDBProbeTests(unittest.TestCase):
    def test_probe_matches_synthetic_lock_without_writing_a_pack(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            lock, source_db, upstream, attribution, license_file = fixture(root)
            output_dir = root / "must-not-be-created"
            report = probe_counts(lock, source_db, upstream, attribution, license_file)
            self.assertEqual(report["status"], "read_only_source_count_probe")
            self.assertTrue(report["counts_match"])
            self.assertEqual(report["counts"], {
                "sources": 2,
                "source_files": 4,
                "models": 2,
                "market_evidence": 2,
            })
            self.assertEqual(report["market_scope_countries"], ["nl", "us"])
            self.assertTrue(report["no_pack_written"])
            self.assertFalse(output_dir.exists())

    def test_probe_rejects_source_snapshot_drift_before_counting(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            lock, source_db, upstream, attribution, license_file = fixture(root)
            with source_db.open("ab") as stream:
                stream.write(b"tampered source")
            with self.assertRaisesRegex(ValueError, "pinned source file mismatch: catalog.sqlite"):
                probe_counts(lock, source_db, upstream, attribution, license_file)


if __name__ == "__main__":
    unittest.main(verbosity=2)

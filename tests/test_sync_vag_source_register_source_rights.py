import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.sync_vag_source_register import sync


def write_manifest(path: Path, sources=None):
    payload = {
        "updated_at": "2026-11-06",
        "sources": sources if sources is not None else [
            {
                "source_id": "open-source",
                "publisher": "Example",
                "data_ingested": True,
                "rights": {"permission_status": "verified"},
            },
            {
                "source_id": "quarantined-source",
                "publisher": "Example",
                "data_ingested": False,
                "verification_status": "quarantined_unverified",
                "rights": {"permission_status": "not_cleared"},
            },
        ],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return payload


class SyncVagSourceRegisterTests(unittest.TestCase):
    def test_copies_exact_bytes_and_reports_sha256(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "source-register.json"
            desktop = root / "desktop"
            desktop.mkdir()
            write_manifest(source)
            result = sync(source, desktop)
            destination = desktop / "data/source-manifests/vag-factory-source-register.json"
            expected = hashlib.sha256(source.read_bytes()).hexdigest()
            self.assertEqual(result["status"], "synced_verified")
            self.assertEqual(result["sha256"], expected)
            self.assertEqual(hashlib.sha256(destination.read_bytes()).hexdigest(), expected)
            self.assertEqual(result["source_count"], 2)
            self.assertEqual(result["data_ingested_count"], 1)

    def test_duplicate_source_ids_fail_without_replacing_previous_file(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "source-register.json"
            desktop = root / "desktop"
            destination = desktop / "data/source-manifests/vag-factory-source-register.json"
            destination.parent.mkdir(parents=True)
            destination.write_text("previous-good-register", encoding="utf-8")
            write_manifest(source, sources=[
                {"source_id": "duplicate", "data_ingested": False},
                {"source_id": "duplicate", "data_ingested": False},
            ])
            with self.assertRaisesRegex(ValueError, "Duplicate source_id"):
                sync(source, desktop)
            self.assertEqual(destination.read_text(encoding="utf-8"), "previous-good-register")

    def test_repository_source_register_has_explicit_boolean_ingest_state(self):
        manifest_path = ROOT / "data" / "source-manifests" / "vag-factory-source-register.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertGreater(len(manifest["sources"]), 0)
        for source in manifest["sources"]:
            self.assertIs(type(source.get("data_ingested")), bool, source.get("source_id"))

    def test_missing_ingest_state_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "source-register.json"
            desktop = root / "desktop"
            desktop.mkdir()
            write_manifest(source, sources=[
                {"source_id": "missing-ingest-state", "rights": {"permission_status": "not_cleared"}}
            ])
            with self.assertRaisesRegex(ValueError, "boolean data_ingested"):
                sync(source, desktop)

    def test_restricted_source_cannot_be_marked_ingested(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "source-register.json"
            desktop = root / "desktop"
            desktop.mkdir()
            write_manifest(source, sources=[
                {
                    "source_id": "restricted",
                    "data_ingested": True,
                    "verification_status": "quarantined_unverified",
                    "rights": {"permission_status": "not_cleared"},
                }
            ])
            with self.assertRaisesRegex(ValueError, "cannot be marked ingested"):
                sync(source, desktop)
            self.assertFalse((desktop / "data/source-manifests/vag-factory-source-register.json").exists())

    def test_malformed_json_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "source-register.json"
            desktop = root / "desktop"
            desktop.mkdir()
            source.write_text("{not-json", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "valid UTF-8 JSON"):
                sync(source, desktop)


if __name__ == "__main__":
    unittest.main()

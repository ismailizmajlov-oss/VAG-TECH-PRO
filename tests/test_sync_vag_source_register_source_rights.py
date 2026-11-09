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

    def test_astra_targa_legacy_remains_ch_only_and_never_forms_engine_gearbox_pairs(self):
        manifest_path = ROOT / "data" / "source-manifests" / "astra-targa-legacy-open-data.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(manifest["source_id"], "astra-fedro-targa-legacy-type-approvals-ch")
        self.assertEqual(manifest["market_scope"], ["CH"])
        self.assertEqual(manifest["rights"]["rights_status"], "approved_by_official_astra_ogd_publication_and_swiss_ogd_reuse_terms")
        for field in ("commercial_use_allowed", "display_allowed", "offline_cache_allowed", "bulk_reuse_allowed", "redistribution_allowed", "attribution_required"):
            self.assertIs(manifest["rights"][field], True)
        self.assertEqual(manifest["snapshot"]["file_sha256"], "5851dc2bf2cd06efee42a380e75b661eafa4b577a2edc8ecca2269cb9f950b4b")
        self.assertEqual(manifest["coverage"]["approval_records"], 45041)
        self.assertEqual(manifest["coverage"]["gearbox_classifications"], 53476)
        self.assertEqual(manifest["coverage"]["exact_engine_gearbox_pair_rows"], 0)
        self.assertIs(manifest["applicability_policy"]["exact_engine_gearbox_pair"], False)
        self.assertIs(manifest["applicability_policy"]["ru_eaeu_applicability"], False)
        register = json.loads((ROOT / "data" / "source-manifests" / "vag-factory-source-register.json").read_text(encoding="utf-8"))
        matches = [item for item in register["sources"] if item["source_id"] == manifest["source_id"]]
        self.assertEqual(len(matches), 1)
        source = matches[0]
        self.assertIs(source["data_ingested"], False)
        self.assertEqual(source["research_pack"]["status"], "verified_research_only")
        self.assertEqual(source["research_pack"]["counts"]["exact_engine_gearbox_pair_rows"], 0)
        self.assertIs(source["research_pack"]["production_import"], False)


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

    def test_restricted_source_cannot_be_marked_product_importable(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "source-register.json"
            desktop = root / "desktop"
            desktop.mkdir()
            write_manifest(source, sources=[
                {
                    "source_id": "restricted-product-import",
                    "data_ingested": False,
                    "product_import_allowed": True,
                    "verification_status": "quarantined_rights_unresolved",
                    "rights": {"permission_status": "not_obtained"},
                }
            ])
            with self.assertRaisesRegex(ValueError, "cannot be marked product-importable"):
                sync(source, desktop)
            self.assertFalse((desktop / "data/source-manifests/vag-factory-source-register.json").exists())

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


    def test_bolidenforum_vag_reference_remains_metadata_only_until_written_rights(self):
        manifest_path = ROOT / "data" / "source-manifests" / "bolidenforum-vag-code-databases.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(manifest["source_id"], "bolidenforum-vag-engine-transmission-pr")
        self.assertEqual(manifest["observed_public_metadata"]["engine_code_entries_claimed"], 966)
        self.assertEqual(manifest["observed_public_metadata"]["transmission_entries_claimed"], 19)
        self.assertEqual(manifest["observed_public_metadata"]["pr_code_entries_claimed"], 138)
        self.assertIn("Alle Rechte vorbehalten", manifest["observed_public_metadata"]["copyright_notice"])
        self.assertEqual(manifest["rights"]["permission_status"], "not_obtained")
        self.assertEqual(manifest["rights"]["data_license_status"], "all_rights_reserved_no_open_license_found")
        for field in ("commercial_use_allowed", "display_allowed", "offline_cache_allowed", "bulk_reuse_allowed", "derived_fact_export_allowed"):
            self.assertEqual(manifest["rights"][field], "not_established")
        self.assertIs(manifest["rights"]["redistribution_allowed"], False)
        self.assertIs(manifest["data_ingested"], False)
        self.assertIs(manifest["product_import_allowed"], False)
        self.assertIsNone(manifest["snapshot"]["source_snapshot_sha256"])
        self.assertEqual(manifest["snapshot"]["hash_status"], "not_downloaded_no_snapshot")
        self.assertIs(manifest["applicability"]["exact_engine_transmission_pairs"], False)
        self.assertIs(manifest["applicability"]["ru_eaeu_applicability"], False)

        register = json.loads((ROOT / "data" / "source-manifests" / "vag-factory-source-register.json").read_text(encoding="utf-8"))
        matches = [item for item in register["sources"] if item["source_id"] == manifest["source_id"]]
        self.assertEqual(len(matches), 1)
        source = matches[0]
        self.assertIs(source["data_ingested"], False)
        self.assertIs(source["product_import_allowed"], False)
        self.assertEqual(source["rights"]["permission_status"], "not_obtained")
        self.assertIsNone(source.get("source_snapshot_sha256"))


if __name__ == "__main__":
    unittest.main()

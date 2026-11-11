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


    def test_openvag_database_file_and_data_rights_remain_quarantined(self):
        manifest_path = ROOT / "data" / "source-manifests" / "vag-factory-source-register.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        source = next(item for item in manifest["sources"] if item["source_id"] == "riz4d-openvag-dtc-quarantine")
        self.assertEqual(source["repository_revision_checked"], "407d5e042cf46d55087ed4ae4e056605f2b04f08")
        self.assertEqual(source["data_file_presence"]["claimed_database_path"], "db/openvag.db")
        self.assertEqual(source["data_file_presence"]["default_branch_status"], "not_present")
        self.assertFalse(source["data_file_presence"]["database_bytes_obtained"])
        self.assertIsNone(source["data_file_presence"]["database_sha256"])
        self.assertTrue(source["data_file_presence"]["historical_release_assets_checked"])
        release_review = source["data_file_presence"]["release_collection_review"]
        self.assertEqual(release_review["status"], "empty_release_collection")
        self.assertEqual(release_review["release_count"], 0)
        self.assertFalse(release_review["release_assets_available"])
        self.assertFalse(release_review["tags_checked"])
        self.assertEqual(source["rights"]["repository_code_license"], "MIT")
        self.assertEqual(source["rights"]["database_data_license"], "not_separately_established_in_review")
        self.assertEqual(source["rights"]["underlying_record_authority"], "not_established")
        self.assertFalse(source["rights"]["redistribution_allowed"])
        self.assertEqual(source["project_decision"], "quarantine_only; MIT covers the repository software but does not establish rights in the absent database or its underlying DTC/repair content; do not import definitions, repair solutions or mappings into production until the actual database bytes, record-level provenance and reuse rights are independently established")
        self.assertFalse(source["data_ingested"])
        self.assertFalse(source["product_import_allowed"])

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


    def test_kyrgyz_public_registry_privacy_recheck_keeps_reuse_rights_unresolved(self):
        regional_path = ROOT / "data" / "source-manifests" / "russian-eaeu-otts-sources.json"
        regional = json.loads(regional_path.read_text(encoding="utf-8"))
        source = next(item for item in regional["sources"] if item["source_id"] == "kyrgyz-single-window-public-registry")
        latest = source["observed_public_query"]["latest_official_recheck"]
        privacy = latest["privacy_policy_review"]

        self.assertEqual(source["market_scope"], ["KG", "EAEU_TR_TS_018_2011"])
        self.assertEqual(source["status"], "permission_required")
        self.assertEqual(source["project_decision"], "discovery_only_no_automation_no_import_until_documented_record_schema_and_written_reuse_rights_are_confirmed")
        self.assertFalse(source["data_ingested"])
        self.assertFalse(source["product_import_allowed"])
        self.assertIsNone(source["source_snapshot_sha256"])
        self.assertEqual(source["hash_status"], "not_downloaded_no_ingestion")
        self.assertEqual(latest["observed_at"], "2026-11-10")
        self.assertFalse(latest["record_rows_observed"])
        self.assertFalse(latest["record_schema_retrieved"])
        self.assertFalse(latest["documented_api_identified"])
        self.assertFalse(latest["bulk_export_documented"])
        self.assertFalse(latest["source_bytes_downloaded"])
        self.assertFalse(latest["vin_or_document_query_submitted"])
        self.assertFalse(latest["personal_values_collected"])
        self.assertTrue(privacy["search_request_sent_to_server"])
        self.assertTrue(privacy["analytics_excludes_search_text_document_number_and_vin"])
        self.assertTrue(privacy["query_document_number_and_vin_not_linked_to_visitor"])
        self.assertFalse(privacy["reuse_license_granted"])
        for right in ("commercial_use", "display", "offline_cache", "bulk_export", "redistribution"):
            with self.subTest(right=right):
                self.assertEqual(source["license"][right], "not_confirmed")

    def test_central_kyrgyz_registry_does_not_infer_vag_fitment_or_reuse(self):
        central_path = ROOT / "data" / "source-manifests" / "vag-factory-source-register.json"
        central = json.loads(central_path.read_text(encoding="utf-8"))
        source = next(item for item in central["sources"] if item["source_id"] == "kyrgyz-single-window-public-registry")
        latest = source["observed_claims"]["public_registry"]["latest_official_recheck"]

        self.assertFalse(source["data_ingested"])
        self.assertFalse(source["product_import_allowed"])
        self.assertIsNone(source["source_snapshot_sha256"])
        self.assertFalse(latest["record_rows_observed"])
        self.assertFalse(latest["record_schema_retrieved"])
        self.assertFalse(latest["documented_api_identified"])
        self.assertFalse(latest["bulk_export_documented"])
        self.assertFalse(latest["source_bytes_downloaded"])
        self.assertFalse(latest["privacy_policy_review"]["reuse_license_granted"])
        self.assertEqual(source["rights"]["permission_status"], "not_obtained")
        self.assertEqual(source["rights"]["offline_cache_allowed"], "not_established")
        self.assertEqual(source["rights"]["redistribution_allowed"], "not_established")
        self.assertFalse(source["applicability"]["exact_vag_vehicle_fitment"])
        self.assertFalse(source["applicability"]["engine_gearbox_pairing"])
        self.assertFalse(source["applicability"]["russian_market_scope"])

    def test_kyrgyz_registry_recheck_document_records_no_query_or_download(self):
        review_path = ROOT / "docs" / "research" / "KYRGYZ_PUBLIC_OTTS_REGISTRY_RECHECK_2026-11-10.md"
        review = review_path.read_text(encoding="utf-8").casefold()
        for phrase in (
            "no vin or document query was submitted",
            "no source bytes or records were downloaded",
            "not a data-reuse licence",
            "not a data-reuse licence",
            "not evidence that engine fields appear in the public record schema",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, review)



if __name__ == "__main__":
    unittest.main()

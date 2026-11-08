import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from openpyxl import Workbook

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_kba_de_vag_approval_research_pack.py"
SPEC = importlib.util.spec_from_file_location("kba_approval_builder", SCRIPT)
BUILDER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILDER)

VERIFY_SCRIPT = ROOT / "scripts" / "verify_kba_probe_manifest.py"
VERIFY_SPEC = importlib.util.spec_from_file_location("kba_probe_manifest_verifier", VERIFY_SCRIPT)
VERIFIER = importlib.util.module_from_spec(VERIFY_SPEC)
VERIFY_SPEC.loader.exec_module(VERIFIER)


class KbaApprovalResearchPackTests(unittest.TestCase):
    def make_workbook(self, path: Path):
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Tabelle1"
        for index, value in enumerate(BUILDER.HEADER, 1):
            if value is not None:
                sheet.cell(3, index).value = value
        rows = [
            ["Volkswagen AG", "Golf", "AU", "Kraftfahrzeuge der Klasse M1", "e1*2007/46*1234*01", "KBA", "Neuerteilung", "2020-01-02", "e1", None, "KBA", None, "", ""],
            ["Mercedes-Benz AG", "C-Class", "W206", "Kraftfahrzeuge der Klasse M1", "e1*2007/46*5678*01", "KBA", "Erweiterung", "2021-02-03", "e1", None, "KBA", None, "", ""],
            ["Audi_Sport", "RS model", "F5", "Kraftfahrzeuge der Klasse M1", "e1*2007/46*9999*01", "KBA", "Erweiterung", "2022-03-04", "e1", None, "KBA", None, "", ""],
            ["Bugatti Automobiles S.A.S.", "Chiron", "C", "Kraftfahrzeuge der Klasse M1", "e1*2007/46*7777*01", "KBA", "Erweiterung", "2023-04-05", "e1", None, "KBA", None, "", ""],
            ["Seat S.A.", "Leon", "KL", "Kraftfahrzeuge der Klasse M1", "e1*2007/46*2222*01", "KBA", "Erweiterung", "2024-05-06", "e1", None, "KBA", None, "", ""],
        ]
        for row_number, row in enumerate(rows, 4):
            for column, value in enumerate(row, 1):
                if value is not None:
                    sheet.cell(row_number, column).value = value
        workbook.save(path)

    def make_probe_and_manifest(self, directory: Path, last_modified: str = "Mon, 17 Aug 2026 04:28:44 GMT"):
        source_hash = "127ae4a1beb236b35c1983f897b7bd234d9f8809e888920a155e4b7d72ff43b4"
        etag = '"70d6df0340b32bbd12e01b41e42ba210"'
        header = [
            "Hersteller", "Handelsname", "Typbezeichnung", "Genehmigungsobjekt",
            "Typgenehmigungsnummer", "Technischer Dienst", "Vorgangsart",
            "Datum der Genehmigung", "Mitgliedstaat Typgenehmigung(en) Emissionen",
            None, "Technischer Dienst Emission", None,
            "Zuordnung Handelsnamen zu Typgenehmigung Emissionen",
            "Zuordnung Handelsnamen zu Typgenehmigung Emissionen",
        ]
        probe = {
            "source_id": "kba-de-whole-vehicle-type-approvals",
            "status": "resource_acquired_schema_available",
            "probe_only": True,
            "product_import_allowed": False,
            "data_ingested": False,
            "market_scope": ["DE"],
            "resource": {
                "status": 200,
                "final_url": "https://www.kba.de/DE/Themen/Typgenehmigung/example.xlsx",
                "sha256": source_hash,
                "bytes": 909912,
                "last_modified": last_modified,
                "etag": etag,
            },
            "workbook_schema": {
                "sheet_count": 1,
                "sheets": [{
                    "name": "Tabelle1",
                    "header_row_number": 3,
                    "header": [value or "" for value in header],
                }],
            },
        }
        raw_probe = json.dumps(probe, ensure_ascii=False, indent=2).encode("utf-8")
        probe_path = directory / "probe-report.json"
        probe_path.write_bytes(raw_probe)
        manifest = {
            "source_id": "kba-de-whole-vehicle-type-approvals",
            "market_scope": ["DE"],
            "source_snapshot_sha256": source_hash,
            "rights": {
                "rights_status": "approved_by_published_DL_DE_BY_2_0",
                "commercial_use_allowed": True,
                "display_allowed": True,
                "offline_cache_allowed": True,
                "bulk_reuse_allowed": True,
                "redistribution_allowed": True,
                "attribution_required": True,
            },
            "snapshot": {
                "probe_report_sha256": hashlib.sha256(raw_probe).hexdigest(),
                "probe_run_id": 42481409966,
                "probe_artifact_id": 13618031218,
                "file_sha256": source_hash,
                "source_snapshot_sha256": source_hash,
                "byte_size": 909912,
                "last_modified": "2026-08-17T04:28:44Z",
                "etag": etag,
                "status": "resource_acquired_schema_available",
                "downloaded": True,
                "sheet_name": "Tabelle1",
                "header_row_number": 3,
                "header": header,
                "source_row_count": 3782,
                "vag_related_label_candidate_count": 918,
                "source_revision": "last-modified:2026-08-17T04:28:44Z;etag:70d6df0340b32bbd12e01b41e42ba210",
            },
        }
        manifest_path = directory / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
        return probe_path, manifest_path

    def test_row_hash_binds_row_number_and_cells(self):
        cells = ["Volkswagen AG", "Golf", None]
        self.assertEqual(BUILDER.row_sha(4, cells), BUILDER.row_sha(4, cells))
        self.assertNotEqual(BUILDER.row_sha(4, cells), BUILDER.row_sha(5, cells))
        self.assertNotEqual(BUILDER.row_sha(4, cells), BUILDER.row_sha(4, ["Volkswagen AG", "Polo", None]))

    def test_exact_label_filter_does_not_fuzzy_map_or_include_bugatti(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "fixture.xlsx"
            self.make_workbook(path)
            records, summary = BUILDER.extract(path)
        self.assertEqual(len(records), 3)
        self.assertEqual({item["manufacturer_label"] for item in records}, {"Volkswagen AG", "Audi_Sport", "Seat S.A."})
        self.assertEqual(summary["source_rows"], 5)
        self.assertEqual(summary["excluded_source_label_counts"], {"Bugatti Automobiles S.A.S.": 1})
        audi = next(item for item in records if item["manufacturer_label"] == "Audi_Sport")
        self.assertEqual(audi["manufacturer_label_mapping_status"], "unresolved_source_label")

    def test_invalid_zip_path_is_rejected(self):
        import zipfile
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "unsafe.xlsx"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("../escape.txt", "x")
            with self.assertRaises(ValueError):
                BUILDER.safe_xlsx(path)

    def test_source_rights_gate_rejects_product_import(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "source.json"
            manifest = {
                "source_id": BUILDER.SOURCE_ID,
                "resource_url": BUILDER.SOURCE_URL,
                "catalog_url": BUILDER.CATALOG_URL,
                "market_scope": ["DE"],
                "product_import_allowed": True,
                "data_ingested": False,
                "rights": {},
                "snapshot": {},
            }
            path.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaises(ValueError):
                BUILDER.read_manifest(path)

    def test_http_last_modified_matches_equivalent_iso_manifest_timestamp(self):
        with tempfile.TemporaryDirectory() as temp:
            probe_path, manifest_path = self.make_probe_and_manifest(Path(temp))
            result = VERIFIER.verify(probe_path, manifest_path)
        self.assertEqual(result["status"], "probe_matches_pinned_manifest")
        self.assertEqual(result["market_scope"], "DE")
        self.assertFalse(result["product_import_allowed"])

    def test_http_last_modified_mismatch_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            probe_path, manifest_path = self.make_probe_and_manifest(
                Path(temp), "Tue, 18 Aug 2026 04:28:44 GMT"
            )
            with self.assertRaisesRegex(ValueError, "last_modified"):
                VERIFIER.verify(probe_path, manifest_path)


    def test_builder_source_hash_is_recorded_and_reverified(self):
        expected = hashlib.sha256(SCRIPT.resolve().read_bytes()).hexdigest()
        self.assertEqual(BUILDER.builder_sha256(), expected)
        self.assertEqual(BUILDER.builder_sha256(), BUILDER.fsha(SCRIPT.resolve()))
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertIn('"build_script_sha256":builder_sha256()', source)
        self.assertIn('m.get("build_script_sha256")!=builder_sha256()', source)


if __name__ == "__main__":
    unittest.main()

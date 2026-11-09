import importlib.util
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "build_eea_vag_approval_research_pack.py"
SPEC = importlib.util.spec_from_file_location("eea_pack", SCRIPT)
eea = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(eea)


class EeaVagApprovalResearchPackTests(unittest.TestCase):
    def test_exact_core_make_mapping_only(self):
        self.assertEqual(eea.map_vag_make("Volkswagen"), "VOLKSWAGEN")
        self.assertEqual(eea.map_vag_make("AUDI"), "AUDI")
        self.assertEqual(eea.map_vag_make("ŠKODA"), "SKODA")
        self.assertEqual(eea.map_vag_make("Seat"), "SEAT")
        self.assertEqual(eea.map_vag_make("CUPRA"), "CUPRA")
        self.assertIsNone(eea.map_vag_make("VW"))
        self.assertIsNone(eea.map_vag_make("Porsche"))
        self.assertIsNone(eea.map_vag_make("AUDI AG"))

    def test_make_filter_escapes_labels_and_pins_year_status(self):
        table = {
            "sql_name": "[CO2Emission].[latest].[co2cars_2024Fv30]",
            "year": 2024,
            "status": "F",
        }
        query = eea.make_filter_sql(["AUDI", "O'REILLY"], table, "count")
        self.assertIn("[Year] = 2024", query)
        self.assertIn("[Status] = 'F'", query)
        self.assertIn("'O''REILLY'", query)
        self.assertIn("[Mk] IN ('AUDI', 'O''REILLY')", query)

    def test_personal_and_vehicle_identifiers_are_rejected(self):
        for row in (
            {"Mk": "AUDI", "VIN": "not-stored"},
            {"Mk": "AUDI", "ApplicantName": "not-stored"},
            {"Mk": "AUDI", "OwnerAddress": "not-stored"},
        ):
            with self.subTest(row=row):
                with self.assertRaises(ValueError):
                    eea.reject_personal_fields(row)

    def test_source_rights_gate_requires_published_cc_by_and_no_product_promotion(self):
        fixture = {
            "sources": [{
                "source_id": eea.SOURCE_ID,
                "source_url": "https://sdi.eea.europa.eu/catalogue/datahub/api/records/5018ec17-2348-4c92-8761-6f2377bbd1c0?language=eng",
                "rights": {
                    "data_license": "CC-BY-4.0",
                    "license_url": eea.LICENSE_URL,
                    "permission_status": "approved_by_published_license_for_reuse_with_attribution",
                    "commercial_use_allowed": True,
                    "third_party_display_allowed": True,
                    "offline_cache_allowed": True,
                    "bulk_reuse_allowed": True,
                    "redistribution_allowed": True,
                    "attribution_required": True,
                },
                "acquisition": {
                    "authentication_required": False,
                    "paid_access_required": False,
                    "research_pack_import_allowed": True,
                    "product_import_allowed": False,
                },
                "product_import_allowed": False,
                "data_ingested": False,
            }]
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sources.json"
            path.write_text(json.dumps(fixture), encoding="utf-8")
            source, raw = eea.validate_source_manifest(path)
            self.assertEqual(source["source_id"], eea.SOURCE_ID)
            self.assertTrue(raw)
            fixture["sources"][0]["rights"]["offline_cache_allowed"] = False
            path.write_text(json.dumps(fixture), encoding="utf-8")
            with self.assertRaises(ValueError):
                eea.validate_source_manifest(path)

    def test_database_keeps_variant_rows_candidate_only_with_full_provenance(self):
        row = {
            "MS": "DE",
            "Year": 2024,
            "Status": "F",
            "Mk": "VOLKSWAGEN",
            "Cn": "Golf",
            "T": "CD",
            "Va": "ABC",
            "Ve": "1.0",
            "TAN": "e1*2018/858*00001*00",
            "Ft": "petrol",
            "Fm": "P",
            "Ec": 1498,
            "Ep": 110,
            "M": 1400,
            "W": 2636,
            "At1": 1530,
            "Ewltp": 130,
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw_dir = root / "raw" / "2024F"
            raw_dir.mkdir(parents=True)
            raw_path = raw_dir / "page-0001.json"
            raw_bytes = eea.canonical_json({"results": [row]})
            raw_path.write_bytes(raw_bytes)
            page = {
                "table_id": "2024F",
                "page": 1,
                "file": "raw/2024F/page-0001.json",
                "sha256": eea.sha256_bytes(raw_bytes),
                "query_sha256": "b" * 64,
                "row_count": 1,
                "retrieved_at_utc": "2026-11-10T00:00:00+00:00",
            }
            table = {
                "table_id": "2024F",
                "sql_name": "[CO2Emission].[latest].[co2cars_2024Fv30]",
                "metadata_url": "https://sdi.eea.europa.eu/catalogue/datahub/api/records/5018ec17-2348-4c92-8761-6f2377bbd1c0?language=eng",
                "year": 2024,
                "status": "F",
                "revision": "2024F_co2cars_2024Fv30_metadata_revised_2026-08-19",
            }
            source = {
                "source_url": "https://sdi.eea.europa.eu/catalogue/datahub/api/records/5018ec17-2348-4c92-8761-6f2377bbd1c0?language=eng",
                "rights": {"permission_status": "approved_by_published_license_for_reuse_with_attribution"},
            }
            counts = eea.build_database(
                root / "pack.sqlite",
                source,
                "a" * 64,
                [{
                    "table": table,
                    "pages": [page],
                    "total_rows": 1,
                    "query_sha256": "b" * 64,
                }],
                {"2024F": ["VOLKSWAGEN"]},
                "c" * 64,
                "2026-11-10T00:00:00+00:00",
            )
            self.assertEqual(counts["total_rows"], 1)
            self.assertEqual(counts["by_brand"], {"VOLKSWAGEN": 1})
            db = sqlite3.connect(root / "pack.sqlite")
            try:
                self.assertEqual(db.execute("PRAGMA integrity_check").fetchone()[0], "ok")
                record = db.execute(
                    "SELECT registration_year,data_status,model_year,engine_code,gearbox_code,exact_vehicle_fitment,engine_gearbox_pairing,review_status,applicability_precision FROM approval_variants"
                ).fetchone()
                self.assertEqual(record, (2024, "F", None, None, None, 0, 0, "candidate_only", eea.APPLICABILITY))
                registry = db.execute("SELECT product_import_allowed,exact_vehicle_fitment,engine_gearbox_pairing FROM source_registry").fetchone()
                self.assertEqual(registry, (0, 0, 0))
            finally:
                db.close()

    def test_final_and_provisional_tables_are_separate(self):
        self.assertEqual([(item["year"], item["status"]) for item in eea.TABLES], [(2024, "F"), (2025, "P")])
        self.assertNotEqual(eea.TABLES[0]["sql_name"], eea.TABLES[1]["sql_name"])


if __name__ == "__main__":
    unittest.main()

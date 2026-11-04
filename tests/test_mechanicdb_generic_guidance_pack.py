import hashlib
import json
import sqlite3
import unittest
from pathlib import Path


PACK_DIR = Path("build/generic-repair-guidance")
MANIFEST_PATH = PACK_DIR / "manifest.json"
DATABASE_PATH = PACK_DIR / "generic-repair-guidance.sqlite"


def sha256_file(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class MechanicDbGenericGuidancePackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not MANIFEST_PATH.is_file() or not DATABASE_PATH.is_file():
            raise RuntimeError("Build the pinned generic guidance pack before running these tests")
        cls.manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        cls.connection = sqlite3.connect(DATABASE_PATH)
        cls.connection.row_factory = sqlite3.Row

    @classmethod
    def tearDownClass(cls):
        cls.connection.close()

    def test_pinned_source_and_pack_hashes(self):
        manifest = self.manifest
        self.assertEqual(manifest["source_revision"], "c788dfe9ed1517d4cd0be27f5aacb4776abf4864")
        self.assertEqual(manifest["data_license"], "ODbL-1.0")
        self.assertEqual(manifest["rights_status"], "approved_by_published_license")
        self.assertEqual(sha256_file(DATABASE_PATH), manifest["database_sha256"])
        self.assertEqual(
            manifest["pack_files"]["generic-repair-guidance.sqlite"]["sha256"],
            manifest["database_sha256"],
        )
        for name, item in manifest["source_files"].items():
            self.assertEqual(len(item["sha256"]), 64, name)
            self.assertEqual(len(item["git_blob_sha1"]), 40, name)
            self.assertGreater(item["byte_size"], 0, name)

    def test_sqlite_integrity_and_foreign_keys(self):
        self.assertEqual(self.connection.execute("PRAGMA integrity_check").fetchone()[0], "ok")
        self.assertEqual(self.connection.execute("PRAGMA foreign_key_check").fetchall(), [])
        self.assertEqual(self.connection.execute("PRAGMA user_version").fetchone()[0], 1)

    def test_exact_generic_only_counts_and_exclusions(self):
        counts = self.manifest["counts"]
        self.assertEqual(counts["generic_sae_dtc_references"], 75)
        self.assertEqual(counts["generic_authored_guidance"], 275)
        self.assertEqual(counts["manufacturer_labelled_dtc_rows_excluded"], 15)
        self.assertEqual(counts["manufacturer_labelled_guidance_rows_excluded"], 51)
        self.assertEqual(counts["orphan_guidance_rows"], 0)
        self.assertEqual(counts["generic_dtc_descriptions_copied"], 0)
        self.assertEqual(counts["detailed_code_explanations_copied"], 0)
        self.assertEqual(counts["replacement_parts_rows_copied"], 0)
        self.assertEqual(counts["cost_or_labor_estimates_copied"], 0)
        self.assertEqual(
            self.connection.execute("SELECT count(*) FROM generic_dtc_references").fetchone()[0],
            75,
        )
        self.assertEqual(
            self.connection.execute("SELECT count(*) FROM generic_repair_guidance").fetchone()[0],
            275,
        )

    def test_no_manufacturer_vag_or_vehicle_fitment_claims(self):
        scope = self.manifest["scope"]
        self.assertEqual(scope["namespace"], "generic_sae_iso")
        self.assertEqual(scope["manufacturer"], "UNKNOWN")
        self.assertEqual(scope["market_scope"], "UNKNOWN")
        self.assertEqual(scope["applicability_level"], "generic_only")
        for key in (
            "vag_specific", "exact_vehicle_fitment", "model_generation_year_fitment",
            "engine_gearbox_fitment", "ecu_fitment", "pr_code_fitment", "vin_fitment",
            "diagnostic_execution_allowed", "oem_repair_procedure",
        ):
            self.assertFalse(scope[key], key)

        for table in ("generic_dtc_references", "generic_repair_guidance"):
            row = self.connection.execute(
                f"SELECT count(*) FROM {table} WHERE namespace!='generic_sae_iso' "
                "OR manufacturer!='UNKNOWN' OR market_scope!='UNKNOWN' "
                "OR applicability_level!='generic_only' OR vag_specific!=0 "
                "OR diagnostic_execution_allowed!=0"
            ).fetchone()[0]
            self.assertEqual(row, 0, table)

        self.assertEqual(
            self.connection.execute(
                "SELECT count(*) FROM generic_repair_guidance "
                "WHERE technical_review_status!='not_independently_reviewed' "
                "OR safety_review_status!='not_assessed'"
            ).fetchone()[0],
            0,
        )

    def test_row_level_provenance_is_complete(self):
        code_rows = self.connection.execute(
            "SELECT * FROM generic_dtc_references"
        ).fetchall()
        fix_rows = self.connection.execute(
            "SELECT * FROM generic_repair_guidance"
        ).fetchall()
        self.assertEqual(len(code_rows), 75)
        self.assertEqual(len(fix_rows), 275)

        for row in code_rows:
            source = self.manifest["source_files"][row["source_file_id"]]
            self.assertEqual(row["source_revision"], self.manifest["source_revision"])
            self.assertEqual(row["source_file_sha256"], source["sha256"])
            self.assertGreater(row["source_line_no"], 1)
            self.assertEqual(len(row["source_line_sha256"]), 64)

        for row in fix_rows:
            source = self.manifest["source_files"][row["source_file_id"]]
            self.assertEqual(row["source_revision"], self.manifest["source_revision"])
            self.assertEqual(row["source_file_sha256"], source["sha256"])
            self.assertEqual(row["source_license"], "ODbL-1.0")
            self.assertGreater(row["source_line_no"], 1)
            self.assertEqual(len(row["source_line_sha256"]), 64)
            self.assertTrue(row["title"])
            self.assertTrue(row["instructions"])

    def test_no_description_cost_or_parts_columns(self):
        code_columns = {
            row["name"] for row in self.connection.execute("PRAGMA table_info(generic_dtc_references)")
        }
        guidance_columns = {
            row["name"] for row in self.connection.execute("PRAGMA table_info(generic_repair_guidance)")
        }
        self.assertFalse({"description", "short_description", "detailed_technical_explanation"} & code_columns)
        self.assertFalse({
            "est_parts_cost_min_usd", "est_parts_cost_max_usd", "est_labor_hours",
            "part_name", "oem_part_number",
        } & guidance_columns)
        self.assertFalse(
            self.connection.execute(
                "SELECT count(*) FROM sqlite_master WHERE type='table' "
                "AND name IN ('manufacturer_dtc','oem_repair_procedures','replacement_parts')"
            ).fetchone()[0]
        )

    def test_source_rights_and_attribution_files(self):
        source = self.connection.execute("SELECT * FROM source_registry").fetchone()
        self.assertEqual(source["data_license"], "ODbL-1.0")
        self.assertEqual(source["rights_status"], "approved_by_published_license")
        for field in (
            "commercial_use_allowed", "display_allowed", "offline_cache_allowed",
            "redistribution_allowed", "share_alike_required", "attribution_required",
        ):
            self.assertEqual(source[field], 1, field)
        self.assertEqual(source["market_scope"], "UNKNOWN")
        self.assertEqual(source["technical_review_status"], "not_independently_reviewed")

        for name in ("LICENSE-ODbL.txt", "LICENSE-MIT.txt", "ATTRIBUTION.md"):
            path = PACK_DIR / name
            self.assertTrue(path.is_file(), name)
            self.assertEqual(sha256_file(path), self.manifest["pack_files"][name]["sha256"])
        attribution = (PACK_DIR / "ATTRIBUTION.md").read_text(encoding="utf-8")
        self.assertIn("MechanicDB", attribution)
        self.assertIn("ODbL", attribution)
        self.assertIn("Share-Alike", attribution)

    def test_source_pack_cannot_be_promoted_in_place(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.connection.execute(
                "UPDATE generic_repair_guidance SET vag_specific=1 WHERE guidance_id=(SELECT guidance_id FROM generic_repair_guidance LIMIT 1)"
            )
        self.connection.rollback()


if __name__ == "__main__":
    unittest.main()

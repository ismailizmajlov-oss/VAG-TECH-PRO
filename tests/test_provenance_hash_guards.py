from __future__ import annotations

import re
import sqlite3
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SQL_PATHS = (
    ROOT / "data/sql/vehicle-catalog.sql",
    ROOT / "data/sql/technical-library.sql",
    ROOT / "data/sql/oem-dtc-index.sql",
    ROOT / "data/sql/otts-type-approval-evidence.sql",
    ROOT / "data/sql/generic-repair-guidance.sql",
)
TRIGGER_RE = re.compile(
    r"CREATE TRIGGER IF NOT EXISTS ([A-Za-z_][A-Za-z0-9_]*)\\s+.*?END;",
    re.IGNORECASE | re.DOTALL,
)


def hash_guard_triggers():
    for path in SQL_PATHS:
        sql = path.read_text(encoding="utf-8")
        for match in TRIGGER_RE.finditer(sql):
            name = match.group(1)
            if "sha256" in name.lower() or "hash" in name.lower():
                yield path, name, match.group(0)


class CanonicalProvenanceHashGuardTests(unittest.TestCase):
    def test_every_production_and_research_hash_family_has_insert_and_update_guards(self):
        found = {name for _, name, _ in hash_guard_triggers()}
        expected = {
            "vehicle_catalog_evidence_source_sha256_insert_guard",
            "vehicle_catalog_evidence_source_sha256_update_guard",
            "vehicle_catalog_source_rights_license_text_sha256_insert_guard",
            "vehicle_catalog_source_rights_license_text_sha256_update_guard",
            "technical_documents_content_sha256_insert_guard",
            "technical_documents_content_sha256_update_guard",
            "technical_applicability_evidence_sha256_insert_guard",
            "technical_applicability_evidence_sha256_update_guard",
            "technical_records_record_sha256_insert_guard",
            "technical_records_record_sha256_update_guard",
            "technical_source_rights_license_text_sha256_insert_guard",
            "technical_source_rights_license_text_sha256_update_guard",
            "oem_dtc_publication_locks_source_claim_hash_insert_guard",
            "oem_dtc_publication_locks_source_claim_hash_update_guard",
            "eaeu_otts_evidence_hashes_insert_guard",
            "eaeu_otts_evidence_hashes_update_guard",
            "generic_source_files_hashes_insert_guard",
            "generic_source_files_hashes_update_guard",
            "generic_dtc_references_hashes_insert_guard",
            "generic_dtc_references_hashes_update_guard",
            "generic_repair_guidance_hashes_insert_guard",
            "generic_repair_guidance_hashes_update_guard",
            "source_documents_sha256_insert_guard",
            "source_documents_sha256_update_guard",
            "oem_dtc_source_claim_hash_insert_guard",
            "oem_dtc_source_claim_hash_update_guard",
        }
        self.assertTrue(expected <= found, f"missing hash guards: {sorted(expected - found)}")

    def test_schema_hash_checks_do_not_normalize_uppercase_before_validation(self):
        for path in SQL_PATHS:
            sql = path.read_text(encoding="utf-8")
            self.assertIsNone(
                re.search(r"lower\\s*\\(\\s*(?:NEW\\.)?[A-Za-z_][A-Za-z0-9_]*sha(?:256|1)[A-Za-z0-9_]*\\s*\\)", sql, re.IGNORECASE),
                f"{path.name} still accepts uppercase hash text through lower()",
            )

    def test_additive_legacy_table_guards_reject_uppercase_and_non_hex_hashes(self):
        triggers = list(hash_guard_triggers())
        self.assertTrue(triggers, "no SQLite provenance hash triggers were discovered")

        for path, name, trigger_sql in triggers:
            with self.subTest(schema=path.name, trigger=name):
                table_match = re.search(r"\\bON\\s+([A-Za-z_][A-Za-z0-9_]*)", trigger_sql, re.IGNORECASE)
                self.assertIsNotNone(table_match, f"{name} has no target table")
                table = table_match.group(1)
                fields = sorted(set(re.findall(r"\\bNEW\\.([A-Za-z_][A-Za-z0-9_]*)", trigger_sql)))
                self.assertTrue(fields, f"{name} does not validate any NEW hash field")
                operation = "insert" if re.search(r"BEFORE\\s+INSERT", trigger_sql, re.IGNORECASE) else "update"
                self.assertRegex(trigger_sql, r"BEFORE\\s+(?:INSERT|UPDATE)", f"{name} is not a write guard")

                db = sqlite3.connect(":memory:")
                try:
                    columns = ", ".join(f'"{field}" TEXT' for field in fields)
                    db.execute(f'CREATE TABLE "{table}" (id INTEGER PRIMARY KEY, {columns})')
                    db.executescript(trigger_sql)
                    placeholders = ", ".join("?" for _ in fields)
                    field_sql = ", ".join(f'"{field}"' for field in fields)
                    valid_values = ["a" * (40 if "sha1" in field.lower() else 64) for field in fields]

                    if operation == "insert":
                        db.execute(
                            f'INSERT INTO "{table}" (id, {field_sql}) VALUES (1, {placeholders})',
                            valid_values,
                        )
                        for index, field in enumerate(fields):
                            length = 40 if "sha1" in field.lower() else 64
                            for invalid in ("A" * length, "g" * length):
                                values = list(valid_values)
                                values[index] = invalid
                                with self.assertRaises(sqlite3.IntegrityError):
                                    db.execute(
                                        f'INSERT INTO "{table}" (id, {field_sql}) VALUES (2, {placeholders})',
                                        values,
                                    )
                    else:
                        db.execute(
                            f'INSERT INTO "{table}" (id, {field_sql}) VALUES (1, {placeholders})',
                            valid_values,
                        )
                        for field in fields:
                            length = 40 if "sha1" in field.lower() else 64
                            for invalid in ("A" * length, "g" * length):
                                with self.assertRaises(sqlite3.IntegrityError):
                                    db.execute(
                                        f'UPDATE "{table}" SET "{field}"=? WHERE id=1',
                                        (invalid,),
                                    )
                finally:
                    db.close()


if __name__ == "__main__":
    unittest.main()

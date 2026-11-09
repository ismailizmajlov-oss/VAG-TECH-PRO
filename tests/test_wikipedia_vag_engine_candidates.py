import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from scripts.build_wikipedia_vag_engine_candidates import (
    LICENSE_ID,
    LICENSE_URL,
    PAGES,
    SOURCE_ID,
    build_database,
    extract_codes,
    parse_engine_code_candidates,
    validate_source_register,
)


class WikipediaVagEngineCandidatePackTests(unittest.TestCase):
    def test_extract_codes_excludes_engine_families_and_generic_terms(self):
        self.assertEqual(
            extract_codes("CAXA, CAVD, AEE, EA211, TDI, 2G, 3F, 195 kW"),
            ["CAXA", "CAVD", "AEE", "2G", "3F"],
        )

    def test_parser_only_extracts_explicit_engine_id_rows(self):
        html = """
        <html><body>
          <h2>1.8 litre petrol engine</h2>
          <table>
            <tr><th>Engine ID codes</th><td>CAXA, CAVD, AEE, EA211, TDI, 2G, 3F</td></tr>
            <tr><th>Applications</th><td>Volkswagen Golf 1.8</td></tr>
            <tr><th>Gearbox</th><td>02A, 02J</td></tr>
            <tr><th>Engine ID codes (see note)</th><td>AGB, AZB</td></tr>
          </table>
          <h3>Another engine</h3>
          <table>
            <tr><th>Engine ID codes</th><th>Power</th></tr>
            <tr><td>AGB, AZB</td><td>195 kW</td></tr>
          </table>
          <h3>VR6 timeline</h3>
          <table>
            <tr><th>cylinders &amp; valves</th><th>displacement &amp; ID code(s)</th><td>1990s</td><td>2000s</td><td>2010s</td></tr>
            <tr><td>2.8 : AAA</td><td></td><td>Passat B3</td><td></td><td></td></tr>
            <tr><td>2.9 : ABV</td><td></td><td>Corrado</td><td></td><td></td></tr>
          </table>
        </body></html>
        """
        rows, rows_seen = parse_engine_code_candidates(html)
        codes = [code for row in rows for code in row["candidate_codes"]]
        self.assertGreaterEqual(rows_seen, 5)
        self.assertEqual(codes, ["CAXA", "CAVD", "AEE", "2G", "3F", "AGB", "AZB", "AGB", "AZB", "AAA", "ABV"])
        self.assertEqual(rows[0]["section_heading"], "1.8 litre petrol engine")
        self.assertEqual(rows[1]["section_heading"], "1.8 litre petrol engine")
        self.assertEqual(rows[2]["section_heading"], "Another engine")
        self.assertEqual(rows[3]["section_heading"], "VR6 timeline")
        self.assertEqual(rows[4]["section_heading"], "VR6 timeline")
        self.assertTrue(all("Gearbox" not in row["source_row_text"] for row in rows))
        self.assertNotIn("1990S", codes)
        self.assertNotIn("2000S", codes)
        self.assertNotIn("2010S", codes)

    def test_source_register_requires_pinned_revisions_and_sharealike_rights(self):
        source = {
            "source_id": SOURCE_ID,
            "rights": {
                "data_license_status": LICENSE_ID,
                "license_url": LICENSE_URL,
                "commercial_use_allowed": True,
                "display_allowed": True,
                "offline_cache_allowed": True,
                "bulk_reuse_allowed": True,
                "redistribution_allowed": True,
                "attribution_required": True,
                "share_alike_required": True,
                "separate_pack_required": True,
            },
            "product_import_allowed": False,
            "market_scope": ["UNKNOWN"],
            "pages": [{"title": title, "revision_id": revision} for title, revision in PAGES.items()],
            "quality_review": {"status": "not_approved_for_technical_use", "blocking_warnings": ["community source"]},
        }
        with tempfile.TemporaryDirectory() as temp:
            register = Path(temp) / "register.json"
            register.write_text(json.dumps({"sources": [source]}), encoding="utf-8")
            self.assertEqual(validate_source_register(register)["source_id"], SOURCE_ID)

    def test_sqlite_rows_are_research_only_and_provenance_bound(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp)
            pages = [{
                "title": "List of Volkswagen Group petrol engines",
                "revision_id": 1383476161,
                "source_url": "https://en.wikipedia.org/w/index.php?oldid=1383476161",
                "revision_timestamp": "2026-11-01T00:00:00Z",
                "wikitext_sha256": "a" * 64,
                "rendered_html_sha256": "b" * 64,
                "wikitext_bytes": 100,
                "rendered_html_bytes": 200,
                "quality_warnings": ["community source"],
                "candidate_rows": [{
                    "section_heading": "1.8 litre petrol engine",
                    "source_row_number": 12,
                    "source_row_text": "Engine ID codes | CAXA, CAVD",
                    "candidate_value_text": "CAXA, CAVD",
                    "candidate_codes": ["CAXA", "CAVD"],
                }],
                "rows_seen": 20,
            }]
            counts = build_database(output, pages, "c" * 64, "d" * 64, "2026-11-09T00:00:00+00:00")
            self.assertEqual(counts["source_documents"], 1)
            self.assertEqual(counts["candidate_rows"], 2)
            db = sqlite3.connect(output / "wikipedia-vag-engine-candidates.sqlite")
            try:
                self.assertEqual(db.execute("PRAGMA integrity_check").fetchone()[0], "ok")
                self.assertEqual(db.execute("PRAGMA foreign_key_check").fetchall(), [])
                self.assertEqual(
                    db.execute(
                        "SELECT count(*) FROM engine_code_candidates WHERE market_scope='UNKNOWN' "
                        "AND review_status='candidate' AND product_import_allowed=0 "
                        "AND exact_vehicle_fitment=0 AND engine_gearbox_fitment=0 "
                        "AND diagnostic_execution_allowed=0 AND repair_use_allowed=0"
                    ).fetchone()[0],
                    2,
                )
                self.assertEqual(
                    db.execute("SELECT count(*) FROM engine_code_candidates WHERE source_row_sha256='c'").fetchone()[0],
                    0,
                )
                self.assertEqual(
                    db.execute("SELECT count(*) FROM source_registry WHERE share_alike_required=1 AND separate_pack_required=1").fetchone()[0],
                    1,
                )
            finally:
                db.close()


if __name__ == "__main__":
    unittest.main()

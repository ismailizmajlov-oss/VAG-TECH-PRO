import io
import json
import sys
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import probe_kba_open_data as probe


class KbaOpenDataProbeTests(unittest.TestCase):
    def test_exact_vag_manufacturer_allowlist_does_not_use_substrings(self):
        values = ["Volkswagen AG", "AUDI", "Audi supplier GmbH", "Skoda Auto", "VW Classic Parts", "SEAT"]
        self.assertEqual(
            probe.exact_vag_manufacturer_values(values),
            ["Volkswagen AG", "AUDI", "Skoda Auto", "SEAT"],
        )

    def test_csv_schema_and_rows_are_read_without_renaming_source_columns(self):
        payload = b"Hersteller;Handelsname;HSN;TSN\r\nVolkswagen AG;GOLF;0603;ADF\r\nAudi AG;A4;0588;AHU\r\n"
        parsed = probe.parse_csv_payload(payload)
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed["columns"], ["Hersteller", "Handelsname", "HSN", "TSN"])
        self.assertEqual(parsed["row_count"], 2)
        self.assertEqual(parsed["manufacturer_field_candidates"], ["Hersteller"])
        self.assertEqual(parsed["exact_vag_manufacturer_values"], ["Volkswagen AG", "Audi AG"])
        self.assertEqual(parsed["sample_rows"][0]["HSN"], "0603")
        self.assertEqual(parsed["csv_sha256"], probe.sha256(payload))

    def test_zip_payload_extracts_csv_for_schema_only(self):
        memory = io.BytesIO()
        with zipfile.ZipFile(memory, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("kba.csv", "Hersteller,Handelsname,HSN,TSN\nŠKODA,Octavia,8004,ABC\n")
        parsed = probe.parse_csv_payload(memory.getvalue())
        self.assertEqual(parsed["filename"], "kba.csv")
        self.assertEqual(parsed["row_count"], 1)
        self.assertEqual(parsed["exact_vag_manufacturer_values"], ["ŠKODA"])

    def test_arcgis_error_json_is_not_misread_as_vehicle_data(self):
        self.assertIsNone(probe.parse_csv_payload(json.dumps({"error": {"code": 400}}).encode()))

    def test_query_url_requests_one_non_identifying_sample_only(self):
        url = probe.query_url("https://services.arcgis.com/example/arcgis/rest/services/KBA/FeatureServer", 0)
        self.assertIn("resultRecordCount=1", url)
        self.assertIn("returnGeometry=false", url)
        self.assertNotIn("VIN", url.upper())
        self.assertNotIn("owner", url.lower())

    def test_query_url_rejects_unexpected_service_url(self):
        with self.assertRaises(ValueError):
            probe.query_url("https://example.com/private/export", 0)


if __name__ == "__main__":
    unittest.main()

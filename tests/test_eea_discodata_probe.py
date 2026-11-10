import hashlib
import json
import unittest
from urllib.error import URLError

from scripts.probe_eea_discodata_access import HOST, QUERY, QUERY_SHA256, probe


def sample_row():
    return {
        "MS": "DE",
        "Year": 2025,
        "Status": "P",
        "Mk": "VOLKSWAGEN",
        "Cn": "PRIVATE_MODEL_MARKER",
        "T": "CD",
        "Va": "ABC",
        "Ve": "1.0",
        "TAN": "e1*2018/858*00001*00",
    }


class EeaDiscodataProbeTests(unittest.TestCase):
    def test_probe_uses_one_row_allowlisted_non_personal_query(self):
        self.assertIn("SELECT TOP 1", QUERY)
        self.assertIn("[CO2Emission].[latest].[co2cars_2025Pv31]", QUERY)
        self.assertIn("[Year] = 2025", QUERY)
        self.assertIn("[Status] = 'P'", QUERY)
        self.assertNotIn("SELECT *", QUERY)
        self.assertEqual(len(QUERY_SHA256), 64)

    def test_reachable_response_is_hashed_but_row_values_are_not_retained(self):
        raw = b'{"results":[{"Mk":"VOLKSWAGEN","Year":2025,"Status":"P"}]}'
        calls = []

        def fake_api(sql, page, page_size):
            calls.append((sql, page, page_size))
            return raw, {"results": [sample_row()]}

        report = probe(fake_api)
        self.assertEqual(report["status"], "reachable")
        self.assertEqual(report["api_host"], HOST)
        self.assertEqual(report["row_count"], 1)
        self.assertEqual(report["response_sha256"], hashlib.sha256(raw).hexdigest())
        self.assertEqual(calls, [(QUERY, 1, 1)])
        self.assertNotIn("PRIVATE_MODEL_MARKER", json.dumps(report))
        self.assertNotIn("VOLKSWAGEN", json.dumps(report))

    def test_http_403_is_reported_as_blocked_without_failing_or_importing(self):
        def fake_api(*args, **kwargs):
            raise RuntimeError("EEA Discodata refused the documented public SQL request (HTTP 403)")

        report = probe(fake_api)
        self.assertEqual(report["status"], "blocked_http_403")
        self.assertIsNone(report["response_sha256"])
        self.assertEqual(report["row_count"], 0)
        self.assertIn("No source data acquired", report["detail"])

    def test_transient_http_and_network_errors_are_non_acquisition_states(self):
        for error, expected in (
            (RuntimeError("HTTP 502 Bad Gateway"), "transient_http_error"),
            (URLError("temporary network failure"), "transient_network_error"),
            (TimeoutError("timeout"), "transient_network_error"),
        ):
            with self.subTest(expected=expected):
                report = probe(lambda *args, _error=error, **kwargs: (_ for _ in ()).throw(_error))
                self.assertEqual(report["status"], expected)
                self.assertEqual(report["row_count"], 0)
                self.assertIsNone(report["response_sha256"])

    def test_personal_fields_are_rejected(self):
        raw = b'{"results":[{"Mk":"VOLKSWAGEN","Year":2025,"Status":"P","VIN":"must-not-pass"}]}'

        def fake_api(*args, **kwargs):
            row = sample_row()
            row["VIN"] = "must-not-pass"
            return raw, {"results": [row]}

        with self.assertRaisesRegex(ValueError, "excluded personal/vehicle identifier"):
            probe(fake_api)

    def test_non_vag_or_wrong_year_rows_are_rejected(self):
        for field, value in (("Mk", "PORSCHE"), ("Year", 2024), ("Status", "F")):
            with self.subTest(field=field):
                row = sample_row()
                row[field] = value
                with self.assertRaises(ValueError):
                    probe(lambda *args, _row=row, **kwargs: (b"{}", {"results": [_row]}))


if __name__ == "__main__":
    unittest.main()

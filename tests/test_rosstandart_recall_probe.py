import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "probe_rosstandart_recall_open_data.py"
SPEC = importlib.util.spec_from_file_location("rosstandart_probe", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class RosstandartRecallProbeTests(unittest.TestCase):
    def test_only_same_host_download_links_are_candidates(self):
        same_host = MODULE._candidate_link(
            "https://easy.gost.ru/opendata/7706406291-recallcampaigns/",
            {"href": "/files/recalls.csv", "text": "Скачать CSV", "rel": "", "type": "text/csv"},
        )
        external = MODULE._candidate_link(
            "https://easy.gost.ru/opendata/7706406291-recallcampaigns/",
            {"href": "https://mirror.example/recalls.csv", "text": "Скачать CSV", "rel": "", "type": "text/csv"},
        )
        self.assertEqual(same_host["url"], "https://easy.gost.ru/files/recalls.csv")
        self.assertIsNone(external)

    def test_html_parser_collects_license_and_download_links_without_fetching_them(self):
        parser = MODULE.LinkParser()
        parser.feed(
            '<a href="/files/recalls.csv" type="text/csv">Скачать CSV</a>'
            '<a href="https://data.gov.ru/information-usage">Условия использования</a>'
            '<link rel="license" href="/terms/open-data">'
        )
        self.assertEqual(len(parser.links), 3)
        candidates = [MODULE._candidate_link("https://easy.gost.ru/opendata/", item) for item in parser.links]
        self.assertTrue(any(item and item["url"].endswith("recalls.csv") for item in candidates))
        self.assertTrue(any(item["href"].endswith("/terms/open-data") for item in parser.links))

    def test_report_contract_is_metadata_only(self):
        page = {
            "requested_url": MODULE.PAGES[0],
            "retrieved": False,
            "status": None,
            "final_url": None,
            "content_type": None,
            "content_length_header": None,
            "last_modified": None,
            "etag": None,
            "html_sha256": None,
            "truncated": False,
            "candidate_file_links": [],
            "terms_links": [],
            "error": "TimeoutError",
        }
        self.assertFalse(page["retrieved"])
        self.assertIsNone(page["html_sha256"])
        self.assertEqual(MODULE.OFFICIAL_HOST, "easy.gost.ru")
        self.assertEqual(len(MODULE.PAGES), 2)


if __name__ == "__main__":
    unittest.main()

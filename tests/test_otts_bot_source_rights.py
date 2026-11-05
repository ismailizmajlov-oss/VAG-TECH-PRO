#!/usr/bin/env python3
"""Guard the OTTS.BOT source from accidental ingestion or redistribution."""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_json(relative_path: str):
    return json.loads((ROOT / relative_path).read_text(encoding="utf-8"))


class OttsBotRightsBoundaryTests(unittest.TestCase):
    def test_russian_eaeu_manifest_keeps_aggregator_quarantined(self):
        manifest = load_json("data/source-manifests/russian-eaeu-otts-sources.json")
        source = next(s for s in manifest["sources"] if s["source_id"] == "otts-bot")
        self.assertFalse(source["data_ingested"])
        self.assertIsNone(source["source_snapshot_sha256"])
        self.assertEqual(source["status"], "restricted_no_automated_collection_or_redistribution_without_written_permission")
        self.assertEqual(source["license"]["permission_status"], "not_cleared")
        self.assertIn("prohibited", source["license"]["automated_extraction"])
        self.assertEqual(source["license"]["redistribution"], "prohibited_under_published_user_agreement_clause_3")
        self.assertFalse(source["technical_scope"]["exact_vehicle_fitment"])
        self.assertEqual(source["technical_scope"]["engine_gearbox_pairing"], "not_established")

    def test_central_source_registry_keeps_aggregator_out_of_product(self):
        registry = load_json("data/source-manifests/vag-factory-source-register.json")
        source = next(s for s in registry["sources"] if s["source_id"] == "otts-bot")
        self.assertFalse(source["data_ingested"])
        self.assertIsNone(source["source_snapshot_sha256"])
        self.assertEqual(source["rights"]["permission_status"], "not_cleared")
        self.assertFalse(source["rights"]["third_party_display_allowed"])
        self.assertEqual(source["rights"]["redistribution"], "prohibited_under_published_user_agreement_clause_3")
        self.assertIn("no_offline_cache", source["project_decision"])
        self.assertFalse(source["applicability"]["engine_gearbox_pairing"])
        self.assertFalse(source["applicability"]["exact_ecu_dtc_fitment"])


if __name__ == "__main__":
    unittest.main()

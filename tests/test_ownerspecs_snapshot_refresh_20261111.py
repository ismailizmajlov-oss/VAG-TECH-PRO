from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSIONED = ROOT / "data/source-manifests/history/ownerspecs-verified-vehicle-specs-cc-by-sa-4.0-2026-11-11.json"
CURRENT = ROOT / "data/source-manifests/ownerspecs-verified-vehicle-specs-cc-by-sa-4.0.json"
PREVIOUS = ROOT / "data/source-manifests/history/ownerspecs-verified-vehicle-specs-cc-by-sa-4.0-2026-11-10.json"

class OwnerSpecsSnapshotRefresh20261111Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.snapshot_manifest = json.loads(VERSIONED.read_text(encoding="utf-8"))
        cls.current_manifest = json.loads(CURRENT.read_text(encoding="utf-8"))
        cls.previous_manifest = json.loads(PREVIOUS.read_text(encoding="utf-8"))

    def test_current_publisher_snapshot_is_pinned_to_exact_retained_bytes(self):
        snapshot = self.snapshot_manifest["snapshot"]
        self.assertEqual(snapshot["publisher_generated_date"], "2026-11-11")
        self.assertEqual(snapshot["html_page_generation_count"], 111)
        self.assertEqual(snapshot["json_descriptor_generation_count"], 111)
        self.assertEqual(snapshot["html_page_brand_count"], 27)
        self.assertEqual(snapshot["html_page_verified_datapoint_count"], 2273)
        self.assertEqual(snapshot["source_file_bytes"], 659973)
        self.assertEqual(snapshot["source_snapshot_sha256"], "d702e4572a4e640c0295c40970ef3c0da2db3703c829c5e3d96cebb4acccacc9")
        self.assertEqual(snapshot["vag_generation_count"], 20)
        self.assertEqual(snapshot["vag_fact_count"], 186)
        self.assertEqual(snapshot["retrieved_at_utc"], "2026-11-11T05:56:12+00:00")

    def test_row_level_snapshot_comparison_is_reconciled_and_vag_removals_are_explicit(self):
        review = self.snapshot_manifest["snapshot"]["latest_snapshot_review"]
        self.assertEqual(review["previous_snapshot_sha256"], "6ed73e4cd634e64501edd3b0e03405afa0aad3b8d1a103f78b839c87c8588c95")
        self.assertEqual(review["current_snapshot_sha256"], "d702e4572a4e640c0295c40970ef3c0da2db3703c829c5e3d96cebb4acccacc9")
        self.assertEqual(review["datapoints_removed"], 99)
        self.assertEqual(review["datapoints_added"], 3)
        self.assertEqual(review["changed_datapoints_total"], 3)
        self.assertEqual(review["net_datapoint_change"], -96)
        self.assertEqual(review["vag_datapoints_removed"], 47)
        self.assertEqual(review["vag_datapoints_added"], 0)
        self.assertEqual(review["vag_changed_datapoints"], 0)
        self.assertFalse(review["generation_membership_changed"])
        self.assertTrue(review["datapoint_membership_changed"])
        self.assertEqual(review["vag_generation_count"], 20)
        self.assertEqual(review["vag_fact_count"], 186)
        self.assertEqual(review["public_page_reconciliation"]["verified_datapoint_count"], 2273)
        self.assertTrue(review["public_page_reconciliation"]["reconciled"])
        self.assertFalse(review["critical_repair_values_publishable"])
        self.assertEqual(review["market_scope"], "UNKNOWN")
        self.assertTrue(review["candidate_only"])

    def test_removed_vag_facts_and_changed_non_vag_values_are_auditable(self):
        review = self.snapshot_manifest["snapshot"]["latest_snapshot_review"]
        removed = {(x["brand"], x["model"], x["removed_facts"]) for x in review["vag_removed_fact_groups"]}
        self.assertEqual(removed, {
            ("Audi", "Q7", 5), ("Audi", "Q8", 5),
            ("Porsche", "Cayenne", 17), ("Volkswagen", "Touareg", 20),
        })
        changed = {(x["brand"], x["model"], x["field"]) for x in review["changed_values"]}
        self.assertEqual(changed, {
            ("BMW", "X5", "running_order"),
            ("BMW", "X5", "max_laden_permissible"),
            ("BMW", "X5", "tow_braked"),
        })

    def test_failed_old_pin_acquisition_evidence_is_preserved(self):
        evidence = self.snapshot_manifest["snapshot"]["latest_snapshot_review"]["acquisition_evidence"]
        self.assertEqual(evidence["workflow_run_id"], 42968938274)
        self.assertEqual(evidence["workflow_run_number"], 141)
        self.assertEqual(evidence["artifact_id"], 13833035466)
        self.assertEqual(evidence["artifact_sha256"], "ee801173419bf17b8610f7eac80b813f24a9456633138a96078cfbc494ca5c85")
        self.assertEqual(evidence["artifact_bytes"], 33501)
        self.assertEqual(evidence["source_json_sha256"], "d702e4572a4e640c0295c40970ef3c0da2db3703c829c5e3d96cebb4acccacc9")
        self.assertEqual(evidence["source_json_bytes"], 659973)
        self.assertEqual(evidence["acquisition_log_sha256"], "7c559297e0884939cf8ac33a05978e0835beeb5ea933e6fb84c6e4513ed82c77")

    def test_previous_manifest_is_preserved_and_current_manifest_promotes_verified_snapshot(self):
        import hashlib
        previous = self.previous_manifest["snapshot"]
        current = self.current_manifest["snapshot"]
        self.assertEqual(self.current_manifest, self.snapshot_manifest)
        self.assertEqual(hashlib.sha256(CURRENT.read_bytes()).hexdigest(), "ed221369ae9195cad18194602a75b17d4ab8aa5908dceb503fc2ca0bfa725697")
        self.assertEqual(hashlib.sha256(PREVIOUS.read_bytes()).hexdigest(), "3d744c8b813508daefaebcd690d10c2cef6d0a731e87eda59015622bffeabbdc")
        self.assertEqual(current["source_snapshot_sha256"], "d702e4572a4e640c0295c40970ef3c0da2db3703c829c5e3d96cebb4acccacc9")
        self.assertEqual(previous["source_snapshot_sha256"], "6ed73e4cd634e64501edd3b0e03405afa0aad3b8d1a103f78b839c87c8588c95")
        self.assertEqual(previous["html_page_verified_datapoint_count"], 2369)
        self.assertFalse(self.snapshot_manifest["import_policy"]["production_import"])
        self.assertFalse(self.snapshot_manifest["import_policy"]["product_import_allowed"])
        self.assertEqual(self.snapshot_manifest["applicability_policy"]["market_scope"], "UNKNOWN")
        for key in ("exact_engine_gearbox_pair", "ru_eaeu_applicability", "dtc_fitment", "repair_procedure_applicability", "critical_technical_values_publishable"):
            self.assertFalse(self.snapshot_manifest["applicability_policy"][key])

if __name__ == "__main__":
    unittest.main()

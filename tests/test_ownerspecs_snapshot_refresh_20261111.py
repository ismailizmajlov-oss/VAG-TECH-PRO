from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSIONED = ROOT / "data/source-manifests/history/ownerspecs-verified-vehicle-specs-cc-by-sa-4.0-2026-11-11.json"
CURRENT = ROOT / "data/source-manifests/ownerspecs-verified-vehicle-specs-cc-by-sa-4.0.json"
PREVIOUS = ROOT / "data/source-manifests/history/ownerspecs-verified-vehicle-specs-cc-by-sa-4.0-2026-11-10.json"
PACK3 = ROOT / "data/source-manifests/history/ownerspecs-verified-vehicle-specs-cc-by-sa-4.0-pack3-2026-11-11.json"

class OwnerSpecsSnapshotRefresh20261111Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.snapshot_manifest = json.loads(VERSIONED.read_text(encoding="utf-8"))
        cls.current_manifest = json.loads(CURRENT.read_text(encoding="utf-8"))
        cls.previous_manifest = json.loads(PREVIOUS.read_text(encoding="utf-8"))
        cls.pack3_manifest = json.loads(PACK3.read_text(encoding="utf-8"))

    def test_latest_publisher_snapshot_is_pinned_to_exact_retained_bytes(self):
        snapshot = self.snapshot_manifest["snapshot"]
        self.assertEqual(snapshot["publisher_generated_date"], "2026-11-11")
        self.assertEqual(snapshot["html_page_generation_count"], 111)
        self.assertEqual(snapshot["json_descriptor_generation_count"], 111)
        self.assertEqual(snapshot["html_page_brand_count"], 27)
        self.assertEqual(snapshot["html_page_verified_datapoint_count"], 2273)
        self.assertEqual(snapshot["source_file_bytes"], 659973)
        self.assertEqual(snapshot["source_snapshot_sha256"], "835fe7452b3370dbf921049a72ca365d6f69b6b63ef8a3a37b5714265272814c")
        self.assertEqual(snapshot["vag_generation_count"], 20)
        self.assertEqual(snapshot["vag_fact_count"], 186)
        self.assertEqual(snapshot["retrieved_at_utc"], "2026-11-11T06:33:30.154805+00:00")

    def test_latest_row_level_delta_contains_only_two_non_vag_unit_case_changes(self):
        review = self.snapshot_manifest["snapshot"]["latest_snapshot_review"]
        self.assertEqual(review["previous_snapshot_sha256"], "d702e4572a4e640c0295c40970ef3c0da2db3703c829c5e3d96cebb4acccacc9")
        self.assertEqual(review["current_snapshot_sha256"], "835fe7452b3370dbf921049a72ca365d6f69b6b63ef8a3a37b5714265272814c")
        self.assertEqual(review["datapoints_removed"], 0)
        self.assertEqual(review["datapoints_added"], 0)
        self.assertEqual(review["changed_datapoints_total"], 2)
        self.assertEqual(review["net_datapoint_change"], 0)
        self.assertEqual(review["vag_datapoints_removed"], 0)
        self.assertEqual(review["vag_datapoints_added"], 0)
        self.assertEqual(review["vag_changed_datapoints"], 0)
        self.assertFalse(review["generation_membership_changed"])
        self.assertFalse(review["datapoint_membership_changed"])
        self.assertEqual(review["vag_generation_count"], 20)
        self.assertEqual(review["vag_fact_count"], 186)
        self.assertEqual(
            {(x["brand"], x["model"], x["field"], x["old_unit"], x["new_unit"]) for x in review["changed_units"]},
            {
                ("Hyundai", "i10", "coolant_capacity", "L", "l"),
                ("Hyundai", "i10", "engine_oil_capacity", "l", "L"),
            },
        )
        self.assertEqual(review["market_scope"], "UNKNOWN")
        self.assertFalse(review["critical_repair_values_publishable"])
        self.assertTrue(review["candidate_only"])

    def test_previous_vag_removals_and_bmw_changes_remain_auditable(self):
        review = next(
            item for item in self.snapshot_manifest["snapshot"]["snapshot_review_history"]
            if item.get("current_snapshot_sha256") == "d702e4572a4e640c0295c40970ef3c0da2db3703c829c5e3d96cebb4acccacc9"
        )
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

    def test_exact_acquisition_evidence_is_preserved_even_though_pack_build_was_rejected(self):
        evidence = self.snapshot_manifest["snapshot"]["latest_snapshot_review"]["acquisition_evidence"]
        self.assertEqual(evidence["workflow_run_id"], 42973238985)
        self.assertEqual(evidence["workflow_run_number"], 158)
        self.assertEqual(evidence["artifact_id"], 13834540968)
        self.assertEqual(evidence["artifact_sha256"], "81360d348655f3fe84ccfd926c026120677848ffff4e9f03cfad404158f7c803")
        self.assertEqual(evidence["artifact_bytes"], 34193)
        self.assertEqual(evidence["source_json_sha256"], "835fe7452b3370dbf921049a72ca365d6f69b6b63ef8a3a37b5714265272814c")
        self.assertEqual(evidence["source_json_bytes"], 659973)
        self.assertEqual(evidence["acquisition_snapshot_sha256"], "93bd94338641703d4a1a3cb47870fbf0a3782d65738dc382444e6e4060b10904")
        self.assertEqual(evidence["acquisition_log_sha256"], "5aed7971c3ff23321202a33483f2bd732c5f2ee319e8b15aba13f4b84a748fd8")
        self.assertTrue(evidence["source_revision_field_stale"])
        self.assertIn("raw source JSON SHA-256 and byte count are authoritative", evidence["source_revision_field_note"])

    def test_previous_pack_manifest_is_archived_and_current_manifest_matches_latest_snapshot(self):
        self.assertEqual(self.current_manifest, self.snapshot_manifest)
        self.assertEqual(hashlib.sha256(PACK3.read_bytes()).hexdigest(), "ed221369ae9195cad18194602a75b17d4ab8aa5908dceb503fc2ca0bfa725697")
        self.assertEqual(self.pack3_manifest["snapshot"]["source_snapshot_sha256"], "d702e4572a4e640c0295c40970ef3c0da2db3703c829c5e3d96cebb4acccacc9")
        self.assertEqual(self.snapshot_manifest["snapshot"]["source_snapshot_sha256"], "835fe7452b3370dbf921049a72ca365d6f69b6b63ef8a3a37b5714265272814c")
        previous = self.previous_manifest["snapshot"]
        self.assertEqual(previous["source_snapshot_sha256"], "6ed73e4cd634e64501edd3b0e03405afa0aad3b8d1a103f78b839c87c8588c95")
        self.assertEqual(previous["html_page_verified_datapoint_count"], 2369)
        self.assertFalse(self.snapshot_manifest["import_policy"]["production_import"])
        self.assertFalse(self.snapshot_manifest["import_policy"]["product_import_allowed"])
        self.assertEqual(self.snapshot_manifest["applicability_policy"]["market_scope"], "UNKNOWN")
        for key in ("exact_engine_gearbox_pair", "ru_eaeu_applicability", "dtc_fitment", "repair_procedure_applicability", "critical_technical_values_publishable"):
            self.assertFalse(self.snapshot_manifest["applicability_policy"][key])

if __name__ == "__main__":
    unittest.main()

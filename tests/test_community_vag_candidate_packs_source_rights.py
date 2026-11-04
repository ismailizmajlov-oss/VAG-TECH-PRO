import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REGISTRY = json.loads(
    (ROOT / "data" / "source-manifests" / "vag-factory-source-register.json").read_text(encoding="utf-8")
)
SOURCES = {item["source_id"]: item for item in REGISTRY["sources"]}


class CommunityVagCandidatePackRightsTests(unittest.TestCase):
    def test_autodiag2_pack_is_separately_licensed_candidate_data(self):
        source = SOURCES["autodiag2-vag-community-v6"]
        rights = source["rights"]
        self.assertEqual(source["pinned_revision"], "59b4e774c4023b2daaee179177615f17a5967ae1")
        self.assertEqual(source["market_scope"], ["UNKNOWN"])
        self.assertEqual(source["verification_status"], "community_reference_unverified")
        self.assertEqual(source["display_status"], "candidate_only_not_oem_verified")
        self.assertEqual(rights["database_license"], "ODbL-1.0")
        self.assertEqual(rights["database_contents_license"], "DbCL-1.0")
        for key in ("commercial_use_allowed", "display_allowed", "offline_cache_allowed", "redistribution_allowed",
                    "attribution_required", "share_alike_required", "separate_pack_required"):
            self.assertIs(rights[key], True)
        self.assertEqual(source["counts"]["vehicle_models"], 110)
        self.assertEqual(source["counts"]["vehicle_versions"], 259)
        self.assertEqual(source["counts"]["engine_candidates"], 1083)
        self.assertEqual(source["counts"]["ecu_candidates"], 179)
        self.assertEqual(source["counts"]["vehicle_configuration_candidates"], 3170)
        self.assertEqual(source["counts"]["dtc_candidates"], 0)
        self.assertEqual(source["counts"]["transmission_records"], 0)
        self.assertEqual(source["counts"]["verified_factory_engine_codes"], 0)
        self.assertEqual(source["counts"]["verified_vag_specific_dtc_rows"], 0)
        self.assertIs(source["exact_vehicle_fitment"], False)
        self.assertIs(source["ecu_fitment"], False)
        self.assertIs(source["diagnostic_execution_allowed"], False)
        self.assertIs(source["repair_advice_approved"], False)

    def test_mechanicdb_rows_remain_hidden_make_candidates(self):
        source = SOURCES["mechanicdb-vag-dtc-candidates-odbl"]
        rights = source["rights"]
        self.assertEqual(source["pinned_revision"], "c788dfe9ed1517d4cd0be27f5aacb4776abf4864")
        self.assertEqual(source["market_scope"], ["UNKNOWN"])
        self.assertEqual(source["applicability_precision"], "manufacturer_make_candidate")
        self.assertEqual(source["verification_status"], "community_reference_unverified")
        self.assertEqual(source["display_status"], "hidden_pending_technical_review")
        self.assertEqual(rights["database_license"], "ODbL-1.0")
        self.assertEqual(rights["documentation_license"], "CC-BY-4.0")
        for key in ("commercial_use_allowed", "display_allowed", "offline_cache_allowed",
                    "redistribution_allowed", "attribution_required", "share_alike_required",
                    "separate_pack_required"):
            self.assertIs(rights[key], True)
        self.assertEqual(source["counts"]["manufacturer_controlled_candidates"], 2)
        self.assertEqual(source["counts"]["generic_sae_iso_rows"], 0)
        self.assertEqual(source["counts"]["repair_procedure_rows"], 0)
        self.assertEqual(source["counts"]["oem_part_rows"], 0)
        self.assertEqual(source["counts"]["exact_vehicle_fitment_rows"], 0)
        self.assertEqual(source["counts"]["ecu_fitment_rows"], 0)
        self.assertEqual(source["counts"]["pr_code_fitment_rows"], 0)
        self.assertIs(source["exact_vehicle_fitment"], False)
        self.assertIs(source["ecu_fitment"], False)
        self.assertIs(source["pr_code_fitment"], False)
        self.assertIs(source["diagnostic_execution_allowed"], False)
        self.assertIs(source["repair_advice_approved"], False)
        self.assertEqual(
            [(row["make"], row["code"], row["physical_line"]) for row in source["source_line_evidence"]],
            [("Audi", "P3000", 77), ("Volkswagen", "P1128", 91)],
        )

    def test_generic_dtc_and_make_label_candidates_are_not_promoted(self):
        source = SOURCES["mechanicdb-vag-dtc-candidates-odbl"]
        self.assertEqual(source["counts"]["generic_sae_iso_rows"], 0)
        self.assertEqual(source["verification_status"], "community_reference_unverified")
        self.assertIn("candidate_pack_only", source["project_decision"])
        self.assertIn("never describe as verified VAG-specific", source["project_decision"])

    def test_global_policy_preserves_candidate_and_share_alike_boundaries(self):
        self.assertIs(REGISTRY["policy"]["community_source_candidates_are_not_oem_verified"], True)
        self.assertIs(REGISTRY["policy"]["odbl_derived_databases_must_remain_separate_and_share_alike"], True)


if __name__ == "__main__":
    unittest.main()

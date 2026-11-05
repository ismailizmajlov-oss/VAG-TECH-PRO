import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class RdwVagTypeApprovalSourceRightsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.register = json.loads((ROOT/"data/source-manifests/vag-factory-source-register.json").read_text(encoding="utf-8"))
        cls.lock = json.loads((ROOT/"data/source-manifests/rdw-vag-type-approval.lock.json").read_text(encoding="utf-8"))
        cls.source = next(x for x in cls.register["sources"] if x["source_id"]=="rdw-vag-type-approval-cc0")

    def test_cc0_rights_cover_all_required_reuse_modes(self):
        rights=self.source["rights"]
        self.assertEqual(rights["data_license_status"],"CC0-1.0")
        self.assertEqual(rights["license_url"],"https://creativecommons.org/publicdomain/zero/1.0/")
        for field in ("commercial_use_allowed","display_allowed","offline_cache_allowed","bulk_reuse_allowed","redistribution_allowed"):
            self.assertTrue(rights[field],field)
        self.assertFalse(rights["attribution_required"])
        self.assertTrue(rights["attribution_recommended"])
        self.assertFalse(rights["share_alike_required"])

    def test_live_metadata_gate_requires_official_rdW_owner_and_published_dataset(self):
        gate=self.lock["live_metadata_gate"]
        self.assertEqual(gate["expected_provenance"],"official")
        self.assertEqual(gate["expected_owner_name_contains"],"RDW")
        self.assertEqual(gate["expected_asset_type"],"dataset")
        self.assertEqual(gate["expected_publication_stage"],"published")
        self.assertTrue(gate["fail_closed_on_missing_or_conflicting_metadata"])

    def test_market_and_applicability_are_candidate_only_and_not_eaeu(self):
        self.assertEqual(set(self.source["market_scope"]),{"EU_TYPE_APPROVAL","NL_REGISTRATION_OBSERVATION"})
        self.assertFalse(self.source["ru_eaeu_market_evidence_present"])
        applicability=self.source["applicability"]
        self.assertEqual(applicability["precision"],"type_approval_variant_execution_candidate")
        self.assertEqual(applicability["review_status"],"candidate")
        for field in ("generation_verified","exact_vehicle_fitment","engine_code_fitment","transmission_code_fitment","ecu_fitment","dtc_fitment","repair_procedure_fitment","diagnostic_execution_allowed","production_years_inferred"):
            self.assertFalse(applicability[field],field)
        self.assertFalse(self.source["vehicle_scope"]["vag_factory_engine_codes"])
        self.assertFalse(self.source["vehicle_scope"]["vag_factory_gearbox_codes"])
        self.assertFalse(self.source["technical_scope"]["ru_eaeu_applicability"])

    def test_source_capture_is_minimised_and_fully_provenanced(self):
        access=self.source["access"]
        self.assertEqual(access["status"],"public_socrata_api")
        self.assertFalse(access["authentication_required"])
        self.assertTrue(access["offline_snapshot_retained"])
        self.assertIn("no full registry dump",access["method"].lower())
        provenance=self.source["provenance"]
        for field in ("metadata_sha256_required","query_sha256_required","raw_snapshot_sha256_required","source_snapshot_sha256_required","database_sha256_required","per_record_source_revision_required","no_license_plate_retention"):
            self.assertTrue(provenance[field],field)
        self.assertEqual(provenance["source_manifest"],"data/source-manifests/rdw-vag-type-approval.lock.json")

    def test_verified_pack_snapshot_counts_and_hashes_are_recorded(self):
        pack=self.source["latest_verified_pack"]
        self.assertEqual(pack["workflow_run_id"],41935787910)
        self.assertEqual(pack["source_revision"],"rdw-f22fe72ed46ca4f240c6")
        self.assertEqual(pack["counts"]["vehicle_variants"],99413)
        self.assertEqual(pack["counts"]["engine_candidates"],101395)
        self.assertEqual(pack["counts"]["transmission_candidates"],99482)
        self.assertEqual(pack["counts"]["unique_source_row_pair_candidates"],97905)
        self.assertEqual(pack["counts"]["ambiguous_or_incomplete_pair_keys"],1832)
        for key in ("database_sha256","source_snapshot_sha256","metadata_bundle_sha256","source_manifest_sha256","artifact_sha256"):
            self.assertRegex(pack[key],r"^[a-f0-9]{64}$")
        self.assertEqual(self.source["verification_status"],"verified_source_candidate_pack_only")
        self.assertEqual(self.source["display_status"],"candidate_only_read_only")

    def test_lock_matches_rights_and_namespaces(self):
        self.assertEqual(self.lock["pack_id"],"rdw-vag-type-approval-cc0")
        self.assertEqual(self.lock["data_license"],"CC0-1.0")
        self.assertEqual(self.lock["rights_status"],"approved_by_published_license")
        self.assertTrue(self.lock["rights"]["bulk_reuse_allowed"])
        self.assertFalse(self.lock["rights"]["share_alike_required"])
        policy=self.lock["applicability_policy"]
        self.assertFalse(policy["exact_vehicle_fitment"])
        self.assertFalse(policy["ru_eaeu_applicability"])
        self.assertEqual(policy["engine_code_namespace"],"RDW.motorcode")
        self.assertEqual(policy["transmission_code_namespace"],"RDW.codetypeversnellingsbak")
        self.assertFalse(policy["vag_factory_gearbox_code_verified"])

    def test_review_explicitly_excludes_ru_eaeu_and_factory_code_claims(self):
        review=(ROOT/"docs/research/RDW_VAG_TYPE_APPROVAL_SOURCE_REVIEW_2026-11-05.md").read_text(encoding="utf-8")
        self.assertIn("Russian or EAEU OTTS evidence",review)
        self.assertIn("not a VAG three-letter gearbox code",review)
        self.assertIn("not VIN-level fitment",review)
        self.assertIn("Windows CI run `41935787910`",review)
        self.assertIn("97,905",review)
        self.assertIn("1,832",review)
        self.assertIn("not a confirmed vag engine/gearbox pairing",review.lower())

if __name__=="__main__":
    unittest.main()

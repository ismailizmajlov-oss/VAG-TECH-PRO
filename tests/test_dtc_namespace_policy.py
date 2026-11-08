#!/usr/bin/env python3
from __future__ import annotations
import importlib.util
import json
import re
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
POLICY_PATH=ROOT/"data/policies/dtc-namespace-ranges.json"
SCHEMA_PATH=ROOT/"data/schemas/oem-dtc-index.schema.json"
SQL_PATH=ROOT/"data/sql/oem-dtc-index.sql"
AUDIT_PATH=ROOT/"scripts/audit-dtc-overlap.cjs"
REGISTER_PATH=ROOT/"data/source-manifests/vag-factory-source-register.json"

class DtcNamespacePolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.policy=json.loads(POLICY_PATH.read_text(encoding="utf-8"))
        cls.schema=json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        cls.sql=SQL_PATH.read_text(encoding="utf-8")
        cls.audit=AUDIT_PATH.read_text(encoding="utf-8")

    def test_policy_has_disjoint_normalized_and_quarantine_ranges(self):
        ranges=self.policy["namespaces"]
        generic=re.compile(ranges["generic_sae_iso"]["pattern"])
        manufacturer=re.compile(ranges["manufacturer_controlled"]["pattern"])
        unresolved=re.compile(ranges["unresolved_reserved"]["pattern"])
        for code in ("P0300","P2ABC","B0ABC","C0ABC","U0ABC"):
            self.assertTrue(generic.fullmatch(code),code)
        for code in ("P1ABC","P30AB","P33AB","B1ABC","B2ABC","C1ABC","C2ABC","U1ABC","U2ABC"):
            self.assertTrue(manufacturer.fullmatch(code),code)
        for code in ("P3400","P3497","P34C8","P35AB","P39AB","U3ABC","B3ABC","C3ABC"):
            self.assertTrue(unresolved.fullmatch(code),code)
            self.assertFalse(generic.fullmatch(code),code)
            self.assertFalse(manufacturer.fullmatch(code),code)
        self.assertTrue(self.policy["quarantine_policy"]["quarantine_p34xx_until_current_standard_assignment"])
        self.assertNotIn("P34",self.policy["namespaces"]["generic_sae_iso"]["pattern"])
        self.assertFalse(self.policy["quarantine_policy"]["manufacturer_controlled_range_proves_vag_authorship"])

    def test_json_schema_matches_policy(self):
        rules=self.schema["allOf"]
        patterns={r["if"]["properties"]["dtc_namespace"]["const"]:r["then"]["properties"]["dtc"]["pattern"] for r in rules}
        self.assertEqual(patterns["generic_sae_iso"],self.policy["namespaces"]["generic_sae_iso"]["pattern"])
        self.assertEqual(patterns["manufacturer_specific_vag"],self.policy["namespaces"]["manufacturer_controlled"]["pattern"])
        self.assertEqual(patterns["manufacturer_specific_other"],self.policy["namespaces"]["manufacturer_controlled"]["pattern"])

    def test_sql_triggers_do_not_admit_quarantined_ranges(self):
        self.assertIn("U0[0-9A-F][0-9A-F][0-9A-F]",self.sql)
        self.assertNotIn("NEW.dtc_code GLOB 'P34",self.sql)
        self.assertNotIn("U3[0-9A-F]",self.sql)
        self.assertNotIn("P3[5-9]",self.sql)
        self.assertIn("P3[0-3]",self.sql)
        self.assertIn("B[1-2]",self.sql)
        self.assertIn("C[1-2]",self.sql)

    def test_python_validator_and_node_auditor_load_canonical_policy(self):
        validator=(ROOT/"scripts/validate-oem-dtc-index.py").read_text(encoding="utf-8")
        self.assertIn('DTC_POLICY = json.loads(POLICY_PATH.read_text(encoding="utf-8"))',validator)
        self.assertIn("UNRESOLVED_RESERVED_DTC_PATTERN",validator)
        self.assertIn('policy.namespaces.generic_sae_iso.pattern',self.audit)
        self.assertIn('policy.namespaces.manufacturer_controlled.pattern',self.audit)
        self.assertIn('policy.namespaces.unresolved_reserved.pattern',self.audit)

    def test_openvag_database_candidate_is_not_ingested(self):
        register=json.loads(REGISTER_PATH.read_text(encoding="utf-8"))
        rows=[s for s in register["sources"] if s["source_id"]=="openvag-dtc-api-project"]
        self.assertEqual(len(rows),1)
        source=rows[0]
        self.assertEqual(source["code_license"]["license"],"MIT")
        self.assertEqual(source["database_data_license_status"],"not_stated")
        self.assertEqual(source["provenance_status"],"not_documented")
        self.assertIs(source["data_ingested"],False)
        self.assertIs(source["product_import_allowed"],False)
        self.assertIsNone(source["source_snapshot_sha256"])

    def test_eaeu_nsi_api_is_discovery_only(self):
        register=json.loads(REGISTER_PATH.read_text(encoding="utf-8"))
        rows=[s for s in register["sources"] if s["source_id"]=="eaeu-nsi-rest-api"]
        self.assertEqual(len(rows),1)
        source=rows[0]
        self.assertEqual(source["market_scope"],["EAEU"])
        self.assertIs(source["data_ingested"],False)
        self.assertIs(source["product_import_allowed"],False)
        self.assertIs(source["rights"]["access_authentication_required"],False)
        self.assertEqual(source["rights"]["permission_status"],"not_obtained")

    def test_obdex_u3_rows_remain_research_only(self):
        lock=json.loads((ROOT/"data/source-manifests/obdex-generic-cc0.lock.json").read_text(encoding="utf-8"))
        self.assertIn("U3xxx",lock["scope"]["generic_code_ranges"])
        self.assertIs(lock["normalization_policy"]["research_pack_only"],True)
        self.assertIs(lock["normalization_policy"]["normalized_product_dtc_import_allowed"],False)
        self.assertIn("U3xxx",lock["normalization_policy"]["unverified_ranges_for_normalized_import"])
        self.assertIn("P34xxx-P39xxx",lock["normalization_policy"]["unverified_ranges_for_normalized_import"])
        self.assertEqual(lock["normalization_policy"]["p3_family_review"]["upstream_p3_record_count"],155)
        self.assertFalse(lock["normalization_policy"]["p3_family_review"]["normalized_product_import_allowed"])

    def test_sae_source_is_metadata_only_and_not_ingested(self):
        register=json.loads(REGISTER_PATH.read_text(encoding="utf-8"))
        rows=[s for s in register["sources"] if s["source_id"]=="sae-j2012-dtc-standard"]
        self.assertEqual(len(rows),1)
        source=rows[0]
        self.assertIs(source["data_ingested"],False)
        self.assertIs(source["product_import_allowed"],False)
        self.assertIsNone(source["source_snapshot_sha256"])
        rights=source["rights"]
        for field in ("commercial_use_allowed","display_allowed","offline_cache_allowed","bulk_reuse_allowed","redistribution_allowed","standard_text_storage_allowed","dtc_definition_table_storage_allowed","allocation_spreadsheet_storage_allowed"):
            self.assertIs(rights[field],False)
        self.assertEqual(source["documents"][1]["current_revision"],"J2012DA_202607")

    def test_p34_family_is_quarantined_until_current_sae_assignment(self):
        generic=re.compile(self.policy["namespaces"]["generic_sae_iso"]["pattern"])
        manufacturer=re.compile(self.policy["namespaces"]["manufacturer_controlled"]["pattern"])
        unresolved=re.compile(self.policy["namespaces"]["unresolved_reserved"]["pattern"])
        for code in ("P3400","P3497","P34C8","P3500","P39FF"):
            self.assertTrue(unresolved.fullmatch(code),code)
            self.assertFalse(generic.fullmatch(code),code)
            self.assertFalse(manufacturer.fullmatch(code),code)

    def test_run87_desktop_patch_quarantines_the_mixed_p3_family(self):
        patch=(ROOT/"apply-dtc-namespace-range-guard-run87.cjs").read_text(encoding="utf-8")
        self.assertIn("P3[4-9][0-9A-F]{2}",patch)
        self.assertIn("P3400",patch)
        self.assertIn("P34C8",patch)
        self.assertIn("P39AB",patch)
        self.assertIn("P3[4-9]",patch)
        self.assertIn("ensureOemSchema",patch)
        self.assertIn("path.join(__dirname,rel)",patch)

    def test_dtc_range_documents_match_the_machine_policy(self):
        review=(ROOT/"docs/research/DTC_NAMESPACE_RANGE_REVIEW_2026-11-08.md").read_text(encoding="utf-8")
        policy=(ROOT/"docs/research/DTC_NAMESPACE_CODE_RANGE_POLICY_2026-11-08.md").read_text(encoding="utf-8")
        self.assertIn("P34xxx",review)
        self.assertIn("P34xxx-P39xxx",review)
        self.assertIn("P34xxx-P39xxx",policy)
        self.assertNotIn("P34xx is accepted as generic",review)

if __name__=="__main__":
    unittest.main()

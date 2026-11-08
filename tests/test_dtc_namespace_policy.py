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
        for code in ("P0300","P2ABC","P34C8","B0ABC","C0ABC","U0ABC"):
            self.assertTrue(generic.fullmatch(code),code)
        for code in ("P1ABC","P30AB","P33AB","B1ABC","B2ABC","C1ABC","C2ABC","U1ABC","U2ABC"):
            self.assertTrue(manufacturer.fullmatch(code),code)
        for code in ("P35AB","P39AB","U3ABC","B3ABC","C3ABC"):
            self.assertTrue(unresolved.fullmatch(code),code)
            self.assertFalse(generic.fullmatch(code),code)
            self.assertFalse(manufacturer.fullmatch(code),code)
        self.assertTrue(self.policy["quarantine_policy"]["require_exact_pinned_source_record_for_p34xx"])
        self.assertEqual(self.policy["namespaces"]["generic_sae_iso"]["exact_source_record_required_for"],["P34xx"])
        self.assertFalse(self.policy["quarantine_policy"]["manufacturer_controlled_range_proves_vag_authorship"])

    def test_json_schema_matches_policy(self):
        rules=self.schema["allOf"]
        patterns={r["if"]["properties"]["dtc_namespace"]["const"]:r["then"]["properties"]["dtc"]["pattern"] for r in rules}
        self.assertEqual(patterns["generic_sae_iso"],self.policy["namespaces"]["generic_sae_iso"]["pattern"])
        self.assertEqual(patterns["manufacturer_specific_vag"],self.policy["namespaces"]["manufacturer_controlled"]["pattern"])
        self.assertEqual(patterns["manufacturer_specific_other"],self.policy["namespaces"]["manufacturer_controlled"]["pattern"])

    def test_sql_triggers_do_not_admit_quarantined_ranges(self):
        self.assertIn("U0[0-9A-F][0-9A-F][0-9A-F]",self.sql)
        self.assertIn("P34[0-9A-F][0-9A-F]",self.sql)
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

if __name__=="__main__":
    unittest.main()

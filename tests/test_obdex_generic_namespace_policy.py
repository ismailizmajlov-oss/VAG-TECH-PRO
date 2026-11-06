#!/usr/bin/env python3
"""Regression contract for separating generic SAE/ISO DTCs from mixed/manufacturer-controlled families."""
from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def is_generic_sae_iso_code(code: str) -> bool:
    if not re.fullmatch(r"[PBCU][0-3][0-9A-F]{3}", code):
        return False
    if code.startswith(("P0", "P2", "B0", "C0", "U0")):
        return True
    return bool(re.fullmatch(r"P34[0-9A-F]{2}", code))


class ObdexGenericNamespacePolicyTests(unittest.TestCase):
    def test_locked_scope_excludes_mixed_u3_family(self) -> None:
        lock = json.loads((ROOT / "data/source-manifests/obdex-generic-cc0.lock.json").read_text(encoding="utf-8"))
        scope = lock["scope"]
        self.assertEqual(scope["generic_code_ranges"], ["P0xxx", "P2xxx", "P34xx", "B0xxx", "C0xxx", "U0xxx"])
        self.assertEqual(scope["excluded_mixed_or_reserved_ranges"], ["U3xxx", "P35xx-P39xx", "B3xxx", "C3xxx"])
        self.assertEqual(lock["expected_counts"], {
            "generic_dtcs": 9359,
            "pids_total": 132,
            "upstream_projection_dtcs": 9533,
            "quarantined_dtc_rows": 174,
        })
        self.assertIn("data/generic/U3xxx_enriched.yaml", lock["source_files"])

    def test_generic_range_boundaries(self) -> None:
        accepted = ["P0300", "P2000", "P3400", "B0001", "C0001", "U0001"]
        rejected = ["P1A00", "P3000", "P33FF", "P39FF", "P35FF", "B3000", "C3000", "U3000", "U3FFF", "B1000", "C1000", "U1000", "P3A00"]
        for code in accepted:
            with self.subTest(code=code):
                self.assertTrue(is_generic_sae_iso_code(code))
        for code in rejected:
            with self.subTest(code=code):
                self.assertFalse(is_generic_sae_iso_code(code))

    def test_pack_builder_and_desktop_importer_share_the_same_boundary(self) -> None:
        workflow = (ROOT / ".github/workflows/acquire-obdex-cc0.yml").read_text(encoding="utf-8")
        patcher = (ROOT / "apply-technical-payload-validation-run78.cjs").read_text(encoding="utf-8")
        sync_script = (ROOT / "scripts/sync-desktop-research-manifest.cjs").read_text(encoding="utf-8")
        self.assertIn('const allowedPrefixes = new Set(["P0","P2","B0","C0","U0"]);', workflow)
        self.assertIn('if (/^U3[0-9A-F]{3}$/.test(code))', workflow)
        self.assertIn("dtcs.length !== 9359", workflow)
        self.assertIn("quarantinedDtcRows.length !== 174", workflow)
        self.assertIn('code[1] === "3" && code[2] === "4"', patcher)
        self.assertIn("quarantined_dtc_rows !== 174", sync_script)
        self.assertIn("report.generic_dtcs !== 9359", sync_script)


if __name__ == "__main__":
    unittest.main()

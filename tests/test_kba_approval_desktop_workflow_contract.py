from __future__ import annotations

import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]


class KbaApprovalDesktopWorkflowContractTests(unittest.TestCase):
    def test_windows_workflow_resolves_and_verifies_latest_kba_approval_artifact(self) -> None:
        workflow = (ROOT / ".github/workflows/windows-desktop-ci-run71.yml").read_text(encoding="utf-8")
        self.assertIn("build-kba-de-vag-approval-research-pack.yml", workflow)
        self.assertIn("id: kba-approval-pack", workflow)
        self.assertIn("kba-de-vag-approval-research-pack-$($run.id)", workflow)
        self.assertIn("artifact_sha256=$digest", workflow)
        self.assertIn("Download verified KBA DE whole-vehicle approval SQLite research pack", workflow)
        self.assertIn("Rebuild downloaded KBA approval pack with the current pinned builder", workflow)
        self.assertIn("openpyxl==3.1.5", workflow)
        self.assertIn('test_kba_de_vag_approval_pack.py', workflow)
        self.assertIn("--verify --xlsx $xlsx --source-manifest $sourceManifest --out $rebuiltDir", workflow)
        self.assertIn("kba_approval_builder_sha256", workflow)
        self.assertIn("ConvertFrom-Json -AsHashtable", workflow)
        self.assertIn("caseDistinctLabels", workflow)
        self.assertIn("Integrate KBA DE whole-vehicle approval metadata into offline desktop", workflow)
        self.assertIn("integrate-kba-de-approval-research-pack.cjs", workflow)
        self.assertIn("apply-kba-de-approval-research-verification-run1.cjs", workflow)
        self.assertIn("verify-kba-de-approval-research-pack.cjs", workflow)
        self.assertIn("kba-de-approval-research-db.test.cjs", workflow)
        self.assertIn("kba-de-approval-ui-contract.test.cjs", workflow)
        self.assertIn("kba-de-vag-type-approval-research/source-snapshot.xlsx", workflow)

    def test_pull_request_filter_and_preflight_cover_kba_approval_integration(self) -> None:
        workflow = (ROOT / ".github/workflows/windows-desktop-ci-run71.yml").read_text(encoding="utf-8")
        self.assertIn('"scripts/integrate-kba-de-approval-research-pack.cjs"', workflow)
        self.assertIn('"scripts/apply-kba-de-approval-research-verification-run1.cjs"', workflow)
        self.assertIn('"tests/kba-approval-pack-integration-contract.test.cjs"', workflow)
        self.assertIn('"tests/test_kba_approval_desktop_workflow_contract.py"', workflow)
        self.assertIn("python tests/test_kba_approval_desktop_workflow_contract.py", workflow)
        self.assertIn("node --test tests/kba-approval-pack-integration-contract.test.cjs", workflow)

    def test_pack_builder_retains_the_artifact_long_enough_for_windows_integration(self) -> None:
        workflow = (ROOT / ".github/workflows/build-kba-de-vag-approval-research-pack.yml").read_text(encoding="utf-8")
        self.assertIn("retention-days: 90", workflow)
        self.assertIn("runs-on: windows-2025", workflow)


if __name__ == "__main__":
    unittest.main()

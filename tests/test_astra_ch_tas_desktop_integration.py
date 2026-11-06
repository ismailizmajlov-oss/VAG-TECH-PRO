import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]


class AstraChTasDesktopIntegrationTests(unittest.TestCase):
    def test_source_manifest_is_ch_only_and_ogd_attribution_is_required(self):
        manifest = json.loads((ROOT / "data/source-manifests/astra-ch-tas-open-data.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["market_scope"], ["CH"])
        rights = manifest["rights"]
        self.assertEqual(rights["rights_status"], "approved_by_published_ogd_terms")
        self.assertTrue(rights["commercial_use_allowed"])
        self.assertTrue(rights["display_allowed"])
        self.assertTrue(rights["offline_cache_allowed"])
        self.assertTrue(rights["bulk_reuse_allowed"])
        self.assertTrue(rights["redistribution_allowed"])
        self.assertTrue(rights["attribution_required"])
        self.assertIn("Federal Roads Office", rights["attribution"])
        policy = manifest["import_policy"]
        self.assertFalse(policy["production_import"])
        self.assertFalse(policy["ru_eaeu_applicability"])
        self.assertTrue(policy["never_cross_join_engine_and_gearbox_variants"])

    def test_desktop_adapter_never_promotes_swiss_data_to_vag_fitment(self):
        adapter = (ROOT / "desktop/astra-ch-tas-db.cjs").read_text(encoding="utf-8")
        self.assertIn('marketScope: "CH"', adapter)
        self.assertIn("productionImport: false", adapter)
        self.assertIn("ruEaeuApplicability: false", adapter)
        self.assertIn("factoryVagEngineCodeClaim: false", adapter)
        self.assertIn("factoryVagGearboxCodeClaim: false", adapter)
        self.assertIn("repairApplicability: false", adapter)
        self.assertIn("diagnosticExecutionAllowed: false", adapter)
        self.assertIn("chGearboxType", adapter)
        self.assertIn("not a VAG gearbox code", adapter)

    def test_builder_bundles_the_exact_source_manifest_in_the_artifact(self):
        workflow = (ROOT / ".github/workflows/acquire-astra-ch-tas-vag-probe.yml").read_text(encoding="utf-8")
        self.assertIn("source_manifest_sha256", workflow)
        self.assertIn('Copy-Item -LiteralPath $sourceManifestPath', workflow)
        self.assertIn('astra-ch-tas-open-data.json', workflow)

    def test_desktop_workflow_resolves_downloads_integrates_and_verifies_the_pack(self):
        workflow = (ROOT / ".github/workflows/windows-desktop-ci-run71.yml").read_text(encoding="utf-8")
        self.assertIn("Resolve latest ASTRA CH TAS pack run", workflow)
        self.assertIn("actions/download-artifact@v4", workflow)
        self.assertIn("scripts/integrate-astra-ch-tas-run72.cjs", workflow)
        self.assertIn("node scripts/verify-astra-ch-tas-pack.cjs", workflow)
        self.assertIn("astra-summary", workflow)
        self.assertIn("dataset=astra&q=1XZ904", (ROOT / "scripts/integrate-astra-ch-tas-run72.cjs").read_text(encoding="utf-8"))

    def test_integration_script_patches_ui_api_and_lifecycle(self):
        script = (ROOT / "scripts/integrate-astra-ch-tas-run72.cjs").read_text(encoding="utf-8")
        self.assertIn('id: "astra"', script)
        self.assertIn("astraResearch.getAstraSummary", script)
        self.assertIn("astraResearch.searchAstraApprovals", script)
        self.assertIn("ASTRA source manifest copy hash mismatch", script)
        self.assertIn("CH-only", script)


if __name__ == "__main__":
    unittest.main()

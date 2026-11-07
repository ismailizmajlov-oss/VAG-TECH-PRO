import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_ID = "astra-fedro-targa-emissionen-approval-variants-ch"


class AstraTargaEmissionenSourceRightsTests(unittest.TestCase):
    def test_source_manifest_has_published_ogd_rights_and_ch_only_scope(self):
        path = ROOT / "data" / "source-manifests" / "astra-targa-emissionen-open-data.json"
        manifest = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(manifest["source_id"], SOURCE_ID)
        self.assertEqual(manifest["market_scope"], ["CH"])
        self.assertEqual(manifest["rights"]["rights_status"], "approved_by_published_ogd_terms")
        for field in ("commercial_use_allowed", "display_allowed", "offline_cache_allowed", "bulk_reuse_allowed", "redistribution_allowed", "attribution_required"):
            self.assertIs(manifest["rights"][field], True)
        self.assertEqual(manifest["snapshot"]["file_sha256"], "a11c1727440d6d587a1bd0b37eaeb011afc050b8f356ef746fdd6e18898fdd92")
        self.assertEqual(manifest["snapshot"]["file_size_bytes"], 70829020)

    def test_source_register_keeps_targa_research_only_and_non_production(self):
        path = ROOT / "data" / "source-manifests" / "vag-factory-source-register.json"
        register = json.loads(path.read_text(encoding="utf-8"))
        matches = [item for item in register["sources"] if item["source_id"] == SOURCE_ID]
        self.assertEqual(len(matches), 1)
        source = matches[0]
        self.assertIs(source["data_ingested"], False)
        self.assertEqual(source["market_scope"], ["CH"])
        self.assertEqual(source["research_pack"]["status"], "verified_research_only")
        self.assertEqual(source["research_pack"]["counts"]["approval_powertrain_variant_rows"], 53240)
        self.assertEqual(source["research_pack"]["counts"]["exact_vag_factory_code_pair_rows"], 0)
        self.assertIs(source["research_pack"]["production_import"], False)
        self.assertIs(source["applicability_policy"]["ru_eaeu_applicability"], False)
        self.assertIs(source["applicability_policy"]["exact_vag_factory_code_pair"], False)
        self.assertIs(source["applicability_policy"]["exact_vehicle_fitment"], False)

    def test_no_factory_pair_table_or_dtc_claim_is_described(self):
        manifest = json.loads((ROOT / "data" / "source-manifests" / "astra-targa-emissionen-open-data.json").read_text(encoding="utf-8"))
        self.assertIs(manifest["applicability_policy"]["source_defined_variant_link"], True)
        self.assertIs(manifest["applicability_policy"]["exact_vag_factory_code_pair"], False)
        self.assertIs(manifest["applicability_policy"]["diagnostic_execution_allowed"], False)
        self.assertIs(manifest["applicability_policy"]["repair_procedure_applicability"], False)
        self.assertIs(manifest["applicability_policy"]["ru_eaeu_applicability"], False)
        self.assertEqual(manifest["coverage"]["vag_rows_in_research_pack"], 53240)


    def test_desktop_integration_script_binds_manifest_constants(self):
        manifest = json.loads((ROOT / "data" / "source-manifests" / "astra-targa-emissionen-open-data.json").read_text(encoding="utf-8"))
        script = (ROOT / "scripts" / "integrate-astra-targa-emissionen-vag-research-pack.cjs").read_text(encoding="utf-8")
        expected = {
            "SOURCE_ID": manifest["source_id"],
            "SOURCE_URL": manifest["source_url"],
            "PACK_ID": "astra-fedro-targa-emissionen-vag-research",
        }
        for name, value in expected.items():
            pattern = rf'const {name} = "{re.escape(value)}";'
            self.assertRegex(script, pattern, f"{name} must be defined and match the verified source manifest")

    def test_powershell_source_register_parsers_support_empty_json_property_names(self):
        register = json.loads((ROOT / "data" / "source-manifests" / "vag-factory-source-register.json").read_text(encoding="utf-8"))
        self.assertTrue(any(
            "" in item.get("coverage", {}).get("vehicle_class_counts", {})
            for item in register["sources"]
        ), "The current register includes an intentionally preserved empty source class key")
        workflow = (ROOT / ".github" / "workflows" / "windows-desktop-ci-run71.yml").read_text(encoding="utf-8")
        self.assertIn("$sourceRegister = Get-Content -LiteralPath $sourceRegisterPath -Raw | ConvertFrom-Json -AsHashtable", workflow)
        self.assertIn("$sourceRegisterJson = if (Test-Path $sourceRegisterPath) { Get-Content -LiteralPath $sourceRegisterPath -Raw | ConvertFrom-Json -AsHashtable } else { $null }", workflow)


    def test_lifecycle_patch_accepts_the_pinned_desktop_write_host_anchor(self):
        script = (ROOT / "scripts" / "integrate-astra-targa-emissionen-vag-research-pack.cjs").read_text(encoding="utf-8")
        self.assertIn("const anchorCandidates = [", script)
        self.assertIn('Write-Host "ASTRA offline CH approval search passed; no VAG factory fitment or repair claims."', script)
        self.assertIn('Write-Output "ASTRA offline CH approval search passed; no VAG factory fitment or repair claims."', script)
        self.assertIn("не является подтверждённым заводским кодом VAG", script)
        self.assertIn("не является кодом КПП VAG", script)
        self.assertIn('Write-Host "ASTRA TARGA offline CH source-row search passed; no OEM pair, RU/EAEU fitment or repair claims."', script)
        self.assertNotIn('Write-Output "ASTRA TARGA offline CH source-row search passed; no OEM pair, RU/EAEU fitment or repair claims."', script)


    def test_targa_ui_patch_preserves_research_row_type_closure(self):
        script = (ROOT / "scripts" / "integrate-astra-targa-emissionen-vag-research-pack.cjs").read_text(encoding="utf-8")
        self.assertIn("homologationDate?: string | null;\\n};", script)

    def test_targa_reader_checks_field_map_and_build_report_counts(self):
        reader = (ROOT / "desktop" / "astra-targa-emissionen-db.cjs").read_text(encoding="utf-8")
        self.assertIn("const fieldMap = readJson(fieldMapFile);", reader)
        self.assertIn("const reportMismatch", reader)
        self.assertIn("Array.isArray(fieldMap.required_headers?.[key])", reader)
        self.assertIn("reportCounts.exact_vag_factory_code_pair_rows !== counts.exactVagFactoryCodePairRows", reader)




    def test_run16_pack_hashes_counts_and_zero_pair_boundary_match_source_manifest(self):
        manifest = json.loads((ROOT / "data" / "source-manifests" / "astra-targa-emissionen-open-data.json").read_text(encoding="utf-8"))
        register = json.loads((ROOT / "data" / "source-manifests" / "vag-factory-source-register.json").read_text(encoding="utf-8"))
        source = next(item for item in register["sources"] if item["source_id"] == SOURCE_ID)
        build = source["research_pack_build_evidence"]
        self.assertEqual(build["workflow_run_number"], 16)
        self.assertEqual(build["artifact_id"], 13580905833)
        self.assertEqual(build["source_file_sha256"], manifest["snapshot"]["file_sha256"])
        self.assertEqual(build["database_sha256"], "408980e7a8923223b5f7f4fe5120be961b65317d8e96abb25e2b9e4965ccd926")
        self.assertEqual(build["pack_archive_sha256"], "5bf0a552cfc057b52c66640db36d6c671e9994a613f4c6d7b5d296948be33be3")
        self.assertEqual(build["artifact_sha256"], "fac173f744dcd5d7acb47702371771d684034c8a5141251ec1eb685dfe71d51c")
        self.assertEqual(build["counts"]["approval_powertrain_variant_rows"], 53240)
        self.assertEqual(build["counts"]["exact_vag_factory_code_pair_rows"], 0)
        self.assertEqual(build["counts"]["exact_vehicle_fitment_rows"], 0)
        self.assertEqual(build["counts"]["ru_eaeu_applicability_rows"], 0)
        self.assertEqual(build["sqlite_integrity_check"], "ok")
        self.assertEqual(build["foreign_key_violations"], 0)
        self.assertFalse(build["exact_vag_factory_code_pair"])
        self.assertFalse(build["ru_eaeu_applicability"])

    def test_source_register_pins_same_latest_run16_pack_without_production_import(self):
        register = json.loads((ROOT / "data" / "source-manifests" / "vag-factory-source-register.json").read_text(encoding="utf-8"))
        source = next(item for item in register["sources"] if item["source_id"] == SOURCE_ID)
        build = source["research_pack_build_evidence"]
        self.assertEqual(build["workflow_run_number"], 16)
        self.assertEqual(build["artifact_sha256"], "fac173f744dcd5d7acb47702371771d684034c8a5141251ec1eb685dfe71d51c")
        self.assertEqual(build["pack_archive_sha256"], "5bf0a552cfc057b52c66640db36d6c671e9994a613f4c6d7b5d296948be33be3")
        self.assertIs(build["production_import"], False)
        self.assertIs(build["ru_eaeu_applicability"], False)
        self.assertIs(build["exact_vag_factory_code_pair"], False)
        self.assertIs(source["product_import_allowed"], False)
        self.assertIs(source["data_ingested"], False)

if __name__ == "__main__":
    unittest.main()

from pathlib import Path
import json
import unittest

ROOT = Path(__file__).resolve().parents[1]


class WikipediaEngineCandidateIntegrationContract(unittest.TestCase):
    def test_candidate_pack_builder_binds_artifact_to_source_ref(self):
        workflow = (ROOT / ".github/workflows/build-wikipedia-vag-engine-candidates.yml").read_text(encoding="utf-8")
        for field in (
            "source_head_sha = $sourceHeadSha",
            "source_head_branch = $sourceHeadBranch",
            "source_base_sha = $sourceBaseSha",
            'source_event = "$env:GITHUB_EVENT_NAME"',
            'source_ref = "$env:GITHUB_REF"',
        ):
            self.assertIn(field, workflow)
        self.assertIn("CC-BY-SA-4.0", workflow)
        self.assertIn("product_import_allowed -ne $false", workflow)

    def test_windows_desktop_build_resolves_same_revision_artifact(self):
        workflow = (ROOT / ".github/workflows/windows-desktop-ci-run71.yml").read_text(encoding="utf-8")
        self.assertIn("Resolve current-revision Wikipedia engine candidate pack", workflow)
        self.assertIn("build-wikipedia-vag-engine-candidates.yml/runs", workflow)
        self.assertIn("$_.head_sha -eq $expectedHeadSha", workflow)
        self.assertIn("$_.event -eq $expectedEvent", workflow)
        self.assertIn("Download current-revision Wikipedia engine candidate artifact", workflow)
        self.assertIn("Verify and integrate isolated Wikipedia engine-code candidate pack", workflow)
        self.assertIn("source_head_sha", workflow)
        self.assertIn("source_ref", workflow)
        self.assertIn("integrate-wikipedia-vag-engine-candidates.cjs", workflow)
        self.assertIn("wikipedia_engine_candidates=241", workflow)

    def test_integration_script_pins_license_hashes_and_candidate_only_flags(self):
        script = (ROOT / "scripts/integrate-wikipedia-vag-engine-candidates.cjs").read_text(encoding="utf-8")
        for token in (
            "CC-BY-SA-4.0",
            "sourceSnapshotSha256",
            "sourceManifestSha256",
            "databaseSha256",
            "attributionSha256",
            "licenseNoticeSha256",
            "source-head-sha",
            "source-event",
            "source-ref",
            "product_import_allowed",
            "exact_vehicle_fitment",
            "engine_gearbox_fitment",
            "repair_use_allowed",
            "diagnostic_execution_allowed",
            "source-snapshots",
        ):
            self.assertIn(token, script)

    def test_desktop_reader_is_read_only_and_verifies_provenance(self):
        module = (ROOT / "desktop-patches/wikipedia-engine-candidates-db.cjs").read_text(encoding="utf-8")
        for token in (
            "new DatabaseSync(files.database, { readOnly: true })",
            "PRAGMA integrity_check",
            "PRAGMA foreign_key_check",
            "source_snapshot_sha256",
            "source_manifest_sha256",
            "build-provenance.json",
            "share_alike_required",
            "product_import_allowed",
            "engine_gearbox_fitment",
            "repair_use_allowed",
            "diagnostic_execution_allowed",
            "source-snapshots",
        ):
            self.assertIn(token, module)

    def test_central_source_register_has_sharealike_candidate_boundary(self):
        register = json.loads((ROOT / "data/source-manifests/vag-factory-source-register.json").read_text(encoding="utf-8"))
        serialized = json.dumps(register, ensure_ascii=False)
        self.assertIn("wikipedia-vag-engine-code-lists-cc-by-sa-4-0", serialized)
        self.assertIn("CC-BY-SA-4.0", serialized)
        self.assertIn("share_alike_required", serialized)
        self.assertIn("community_engine_code_candidate_only", serialized)


if __name__ == "__main__":
    unittest.main()

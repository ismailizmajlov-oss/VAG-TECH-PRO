import json
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
REGISTRY=json.loads((ROOT/"data"/"source-manifests"/"vag-factory-source-register.json").read_text(encoding="utf-8"))
SOURCES={item["source_id"]:item for item in REGISTRY["sources"]}
OBDB_MANIFEST=json.loads((ROOT/"data"/"source-manifests"/"obdb-vag-signalsets.json").read_text(encoding="utf-8"))

class ObdbVagSignalSourceRightsTests(unittest.TestCase):
    def test_all_pinned_repositories_have_cc_by_sa_license_evidence(self):
        source=SOURCES["obdb-vag-signalsets-cc-by-sa"]
        rights=source["rights"]
        self.assertEqual(rights["data_license"],"CC-BY-SA-4.0")
        self.assertIs(rights["license_files_reviewed_at_each_pinned_commit"],True)
        for key in ("commercial_use_allowed","display_allowed","offline_cache_allowed","redistribution_allowed","attribution_required","share_alike_required","separate_pack_required"):
            self.assertIs(rights[key],True)
        self.assertEqual(len(source["pinned_source_repositories"]),38)
        self.assertEqual(source["source_file_count"],152)
        self.assertEqual(source["source_repository_count"],38)
        self.assertEqual(set(source["generation_only_repositories"]),{"OBDb/Skoda-Octavia","OBDb/Skoda-Superb","OBDb/Skoda-Fabia","OBDb/Skoda-Kodiaq","OBDb/Skoda-Kamiq","OBDb/Skoda-Rapid","OBDb/Skoda-Scala"})
        for repo in source["pinned_source_repositories"]:
            self.assertTrue(repo["commit_sha"]); self.assertEqual(repo["license_file"],"LICENSE")
            self.assertEqual(repo["license_id"],"CC-BY-SA-4.0"); self.assertRegex(repo["commit_sha"],r"^[0-9a-f]{40}$")
        manifest_sources={item["repository"]:item for item in OBDB_MANIFEST["sources"]}
        pinned_sources={item["repository"]:item for item in source["pinned_source_repositories"]}
        self.assertEqual(set(manifest_sources),set(pinned_sources)); self.assertEqual(len(manifest_sources),38)
        for repository,item in manifest_sources.items():
            pinned=pinned_sources[repository]
            for key in ("commit_sha","commit_date","make","model","generation_reference_url"):
                self.assertEqual(pinned[key],item[key])
        self.assertEqual(OBDB_MANIFEST["command_namespace_policy"]["included_service_ids"],["22"])
        self.assertEqual(OBDB_MANIFEST["command_namespace_policy"]["excluded_service_ids"],["01"])
        self.assertFalse(OBDB_MANIFEST["command_namespace_policy"]["dtc_definitions_included"])
        excluded={x["repository"]:x["reason"] for x in OBDB_MANIFEST["excluded_repositories"]}
        self.assertIn("OBDb/Audi-A1",excluded)
        self.assertIn("generic OBD-II service 0x01",excluded["OBDb/Audi-A1"])

    def test_pack_is_candidate_only_and_never_executable(self):
        source=SOURCES["obdb-vag-signalsets-cc-by-sa"];scope=source["technical_scope"]
        self.assertEqual(source["market_scope"],["UNKNOWN"])
        self.assertEqual(source["verification_status"],"source_manifest_updated_rebuild_pending_research_only_no_production_import")
        self.assertEqual(source["display_status"],"read_only_research_candidate")
        self.assertFalse(scope["diagnostic_execution_allowed"]);self.assertFalse(scope["test_plan_approved"])
        self.assertFalse(scope["exact_vehicle_fitment"]);self.assertFalse(scope["exact_ecu_fitment"])
        self.assertFalse(scope["exact_engine_gearbox_mapping"])
        self.assertEqual(scope["command_service"],"0x22")
        self.assertFalse(scope["all_command_records_execution_allowed"])
        self.assertEqual(scope["excluded_generic_service_ids"],["01"])

    def test_no_dtc_repair_or_oem_wiring_data_is_claimed(self):
        source=SOURCES["obdb-vag-signalsets-cc-by-sa"];scope=source["technical_scope"]
        self.assertIsNone(source["counts"])
        self.assertEqual(source["previous_verified_pack"]["counts"]["uds_command_candidates"],7890)
        self.assertEqual(source["previous_verified_pack"]["counts"]["signal_candidates"],8446)
        self.assertFalse(scope["dtc_definitions"]);self.assertFalse(scope["repair_procedures"])
        self.assertFalse(scope["wiring_diagrams"]);self.assertFalse(scope["factory_pinouts"])

    def test_share_alike_attribution_and_separate_pack_are_explicit(self):
        source=SOURCES["obdb-vag-signalsets-cc-by-sa"];rights=source["rights"]
        self.assertIn("OBDb community contributors",rights["attribution"])
        self.assertIn("CC BY-SA 4.0",rights["attribution"])
        self.assertIn("share_alike",source["project_decision"])
        self.assertIn("do not execute UDS commands",source["project_decision"])

    def test_previous_verified_pack_is_retained_and_new_build_is_pending(self):
        source=SOURCES["obdb-vag-signalsets-cc-by-sa"];build=source["research_pack_build_evidence"]
        self.assertEqual(build["status"],"rebuild_pending_after_source_manifest_update")
        self.assertEqual(build["source_manifest_sha256"],"d3d6ff667837649d0ee6890daadb550eae9af13c544add12e3c5f2843e0e186f")
        previous=source["previous_verified_pack"]
        self.assertEqual(previous["workflow_run_number"],253)
        self.assertEqual(previous["workflow_run_id"],42443454970)
        self.assertEqual(previous["artifact_id"],13603020392)
        self.assertEqual(previous["artifact_sha256"],"cc52fb5fefee9da9aa732dee6dd9202ec6a832e7d3da73b8f96e4714d6a60c78")
        self.assertEqual(previous["database_sha256"],"6ee0de83b4e2fd055d0e54786d73fedc77428e3cac9d04948145a4f487cc4d14")
        self.assertEqual(previous["counts"]["source_repositories"],16)
        self.assertEqual(previous["counts"]["upstream_files"],64)
        self.assertEqual(previous["counts"]["generation_candidates"],82)
        self.assertEqual(previous["counts"]["ecu_candidates"],44)
        self.assertEqual(previous["counts"]["uds_command_candidates"],7890)
        self.assertEqual(previous["counts"]["signal_candidates"],8446)
        self.assertEqual(previous["counts"]["dtc_definitions"],0)
        self.assertFalse(source["product_import_allowed"]);self.assertFalse(source["data_ingested"])
        self.assertEqual(build["desktop_integration_status"],"not_integrated")

if __name__=="__main__": unittest.main()

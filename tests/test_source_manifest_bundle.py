#!/usr/bin/env python3
"""Bundle every source manifest into desktop staging with a deterministic SHA-256 index."""
from __future__ import annotations
import hashlib
import json
import tempfile
import unittest
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.sync_vag_source_register import sync

class SourceManifestBundleTests(unittest.TestCase):
    def write_json(self,path:Path,value:object)->bytes:
        raw=(json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2)+"\n").encode("utf-8")
        path.write_bytes(raw)
        return raw

    def register(self,source_dir:Path,*,ingested:bool=False)->Path:
        path=source_dir/"vag-factory-source-register.json"
        self.write_json(path,{"updated_at":"2026-11-06T00:00:00Z","sources":[
            {"source_id":"test-source","data_ingested":ingested,"verification_status":"candidate","rights":{"permission_status":"not_cleared"}}
        ]})
        return path

    def test_all_json_manifests_are_copied_and_indexed_atomically(self)->None:
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); source_dir=root/"source"; source_dir.mkdir()
            central=self.register(source_dir)
            russian_raw=self.write_json(source_dir/"russian-eaeu-otts-sources.json",{
                "updated_at":"2026-11-06T00:00:00Z",
                "sources":[{"source_id":"otts-test","data_ingested":False,"verification_status":"candidate"}]
            })
            self.write_json(source_dir/"wikidata-vag-generations.json",{"schema_version":1,"source_id":"wikidata-vag-generation-candidates"})
            history_source=source_dir/"history"; history_source.mkdir()
            self.write_json(history_source/"archived-snapshot.json",{"archived":True})
            (source_dir/"open-datasets.json").write_bytes(b"")
            desktop=root/"desktop"; desktop.mkdir()
            dest=desktop/"data"/"source-manifests"; dest.mkdir(parents=True)
            (dest/"README.md").write_text("preserve package note\n",encoding="utf-8")
            (dest/"stale-manifest.json").write_text('{"stale":true}\n',encoding="utf-8")
            dest_history=dest/"history"; dest_history.mkdir()
            (dest_history/"old.json").write_text('{"archived":true}\\n',encoding="utf-8")
            result=sync(central,desktop)
            index_path=dest/"source-manifest-index.json"
            index=json.loads(index_path.read_text(encoding="utf-8"))
            self.assertEqual(result["status"],"synced_verified")
            self.assertEqual(result["manifest_count"],3)
            self.assertEqual(result["skipped_empty_files"],["open-datasets.json"])
            self.assertEqual(index["skipped_files"],[{"name":"open-datasets.json","reason":"empty_file"}])
            self.assertEqual(result["russian_eaeu_otts_source_count"],1)
            self.assertEqual(result["russian_eaeu_otts_manifest_sha256"],hashlib.sha256(russian_raw).hexdigest())
            self.assertEqual(index["schema_version"],1)
            self.assertEqual(index["manifest_count"],3)
            self.assertEqual((dest/"vag-factory-source-register.json").read_bytes(),central.read_bytes())
            self.assertEqual((dest/"russian-eaeu-otts-sources.json").read_bytes(),russian_raw)
            self.assertTrue((dest/"README.md").is_file())
            self.assertFalse((dest/"stale-manifest.json").exists())
            self.assertTrue((dest/"history"/"old.json").is_file())
            self.assertNotIn("archived-snapshot.json",[item["name"] for item in index["files"]])
            for item in index["files"]:
                copied=dest/item["name"]
                self.assertEqual(copied.stat().st_size,item["bytes"])
                self.assertEqual(hashlib.sha256(copied.read_bytes()).hexdigest(),item["sha256"])
            self.assertEqual(hashlib.sha256(index_path.read_bytes()).hexdigest(),result["manifest_index_sha256"])

    def test_invalid_noncentral_manifest_fails_without_replacing_previous_bundle(self)->None:
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); source_dir=root/"source"; source_dir.mkdir()
            central=self.register(source_dir)
            (source_dir/"russian-eaeu-otts-sources.json").write_text("{broken",encoding="utf-8")
            desktop=root/"desktop"; desktop.mkdir()
            dest=desktop/"data"/"source-manifests"; dest.mkdir(parents=True)
            (dest/"KEEP.txt").write_text("previous bundle\n",encoding="utf-8")
            with self.assertRaises(ValueError): sync(central,desktop)
            self.assertEqual((dest/"KEEP.txt").read_text(encoding="utf-8"),"previous bundle\n")


    def test_kyrgyz_registry_statutory_access_does_not_clear_product_reuse(self)->None:
        central=ROOT/"data"/"source-manifests"/"vag-factory-source-register.json"
        registry=json.loads(central.read_text(encoding="utf-8"))
        source=next(item for item in registry["sources"] if item["source_id"]=="kyrgyz-single-window-public-registry")
        legal=source["legal_basis_review"]
        rights=source["rights"]
        self.assertEqual(legal["enabling_law"]["calculated_code_effective_date"],"2026-02-05")
        self.assertIn("1(14)",legal["articles"])
        self.assertIn("1(39)",legal["articles"])
        self.assertIn("62",legal["articles"])
        self.assertEqual(legal["interpretation"]["state_resource_classification"].split(";")[0],"not_formally_confirmed_under_article_1_14")
        self.assertEqual(legal["interpretation"]["open_data_status"].split(";")[0],"not_confirmed_under_article_1_39")
        self.assertEqual(rights["permission_status"],"not_obtained")
        self.assertFalse(rights["statutory_access_basis"]["product_import_cleared"])
        self.assertFalse(source["product_import_allowed"])
        self.assertFalse(source["data_ingested"])
        self.assertIsNone(source["source_snapshot_sha256"])
        self.assertFalse(source["applicability"]["russian_market_scope"])
        for key in ("bulk_export_allowed","offline_cache_allowed","commercial_display_allowed","redistribution_allowed"):
            self.assertEqual(rights[key],"not_established")

    def test_restricted_source_cannot_be_marked_ingested(self)->None:
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); source_dir=root/"source"; source_dir.mkdir()
            central=self.register(source_dir,ingested=True)
            desktop=root/"desktop"; desktop.mkdir()
            with self.assertRaisesRegex(ValueError,"Restricted/quarantined"): sync(central,desktop)
            self.assertFalse((desktop/"data"/"source-manifests").exists())

    def test_symlink_in_source_manifest_directory_fails_closed(self)->None:
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); source_dir=root/"source"; source_dir.mkdir()
            central=self.register(source_dir)
            outside=root/"outside.json"; self.write_json(outside,{"source_id":"outside"})
            try: (source_dir/"linked.json").symlink_to(outside)
            except (OSError,NotImplementedError): self.skipTest("symlink creation is not available on this runner")
            desktop=root/"desktop"; desktop.mkdir()
            with self.assertRaisesRegex(ValueError,"symlink"): sync(central,desktop)

    def test_eaeu_nsi_vehicle_reference_objects_remain_metadata_only(self)->None:
        central=ROOT/"data"/"source-manifests"/"vag-factory-source-register.json"
        registry=json.loads(central.read_text(encoding="utf-8"))
        matches=[item for item in registry["sources"] if item["source_id"]=="eaeu-nsi-rest-api"]
        self.assertEqual(len(matches),1)
        source=matches[0]
        discovery=source["catalog_discovery"]
        objects={item["object_code"]:item for item in discovery["objects"]}
        self.assertEqual(set(objects),{"2001","2024","2030"})
        self.assertEqual(objects["2030"]["observed_record_count"],3)
        self.assertEqual(objects["2030"]["relevance"],"vehicle_passport_document_type_only")
        self.assertEqual(objects["2001"]["observed_record_count"],10)
        self.assertEqual(objects["2001"]["relevance"],"conformity_document_type_only")
        self.assertIn({"code":"30","label":"одобрение типа транспортного средства ЕАЭС"},objects["2001"]["visible_codes"])
        self.assertEqual(objects["2024"]["observed_record_count"],41)
        self.assertEqual(objects["2024"]["relevance"],"broad_transport_category_only")
        self.assertFalse(discovery["endpoint_catalog_or_openapi_retrieved"])
        self.assertFalse(discovery["endpoints_called"])
        self.assertFalse(discovery["bounded_findings"]["dedicated_otts_otsh_dataset_confirmed"])
        self.assertTrue(discovery["bounded_findings"]["otts_document_type_code_observed"])
        self.assertFalse(discovery["bounded_findings"]["otts_records_present"])
        self.assertFalse(discovery["bounded_findings"]["factory_engine_codes"])
        self.assertFalse(discovery["bounded_findings"]["factory_gearbox_codes"])
        self.assertFalse(discovery["bounded_findings"]["engine_gearbox_pairs"])
        self.assertFalse(source["data_ingested"])
        self.assertFalse(source["product_import_allowed"])
        self.assertIsNone(source["source_snapshot_sha256"])
        self.assertEqual(source["rights"]["permission_status"],"not_obtained")
        for key in ("commercial_use_allowed","display_allowed","offline_cache_allowed","bulk_reuse_allowed","redistribution_allowed"):
            self.assertFalse(source["rights"][key])

if __name__=="__main__":
    unittest.main()

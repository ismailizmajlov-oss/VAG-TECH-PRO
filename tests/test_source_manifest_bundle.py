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

if __name__=="__main__":
    unittest.main()

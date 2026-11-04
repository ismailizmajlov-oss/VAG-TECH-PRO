from __future__ import annotations

import hashlib
import json
import sqlite3
import tempfile
import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from rdw_vag_type_approval_common import (
    build_database, normalize_vehicle_rows, normalize_engine_rows,
    normalize_transmission_rows, validate_lock, verify_pack
)

DATASET_IDS = ["m9d7-ebf2","4by9-ammk","7rjk-eycs","byxc-wwua","x5v3-sewk"]
KEY = {
    "typegoedkeuringsnummer":"e1*2007/46*0623*03",
    "variant":"AC4CJZAX0",
    "uitvoering":"FM6FM6AJ009N7MJOVLVR2",
}
KEY_TGK = {
    "typegoedkeuringsnummer":KEY["typegoedkeuringsnummer"],
    "codevarianttgk":KEY["variant"],
    "codeuitvoeringtgk":KEY["uitvoering"],
    "volgnummerrevisieuitvoering":"1",
}

def lock_file(path: Path) -> None:
    data = {
        "schema_version":1,
        "pack_id":"rdw-vag-type-approval-cc0",
        "data_license":"CC0-1.0",
        "rights_status":"approved_by_published_license",
        "rights":{"commercial_use_allowed":True,"display_allowed":True,"offline_cache_allowed":True,"bulk_reuse_allowed":True,"redistribution_allowed":True,"share_alike_required":False},
        "applicability_policy":{"ru_eaeu_applicability":False},
        "datasets":[{"id":x,"required":True} for x in DATASET_IDS],
    }
    path.write_text(json.dumps(data),encoding="utf-8")

def fixtures():
    vehicle = {
        "merk":"VOLKSWAGEN","handelsbenaming":"GOLF","type":"AU",
        "typegoedkeuringsnummer":KEY["typegoedkeuringsnummer"],
        "variant":KEY["variant"],"uitvoering":KEY["uitvoering"],
        "first_registration_seen":"2013-01-25T00:00:00.000",
        "last_registration_seen":"2016-10-20T00:00:00.000",
        "europese_voertuigcategorie":"M1","voertuigsoort":"Personenauto",
    }
    engine = {
        **KEY_TGK,"volgnummeraandrijving":"1","motorcode":"CAXA",
        "typegoedkeuringsnummermotor":"e1*2007/46*0623*03",
        "aantalcilinders":"4","cilinderinhoud":"1390",
    }
    transmission = {
        **KEY_TGK,"volgnummerversnelling":"1","codetypeversnellingsbak":"DSG7",
        "aantalversnellingenondergrens":"7","aantalversnellingenbovengrens":"7",
    }
    basis = {
        **KEY_TGK,"voertuigcategorie":"M1",
        "begindatumrevisieuitvoering":"2012-01-01",
        "einddatumrevisieuitvoering":"2017-12-31",
    }
    designation = {
        "typegoedkeuringsnummer":KEY["typegoedkeuringsnummer"],
        "codevariantgk":KEY["variant"],"codeuitvoeringtgk":KEY["uitvoering"],
        "volgnummerrevisieuitvoering":"1","handelsbenamingfabrikant":"Golf",
        "typeaanduidingfabrikant":"AU","volgnummerhandelsbenamingfabr":"1",
    }
    return {
        "m9d7-ebf2":[vehicle],
        "4by9-ammk":[engine],
        "7rjk-eycs":[transmission],
        "byxc-wwua":[basis],
        "x5v3-sewk":[designation],
    }

def build_fixture_pack(root: Path, payloads=None):
    lock = root / "lock.json"
    lock_file(lock)
    payloads = payloads or fixtures()
    metadata_raws = {d:json.dumps({"id":d,"name":d,"rowsUpdatedAt":"2026-11-05T00:00:00Z"},sort_keys=True).encode() for d in DATASET_IDS}
    metadata = {d:{"rowsUpdatedAt":"2026-11-05T00:00:00Z","metadata_sha256":hashlib.sha256(metadata_raws[d]).hexdigest()} for d in DATASET_IDS}
    snapshots = []
    queries = {}
    for i,dataset_id in enumerate(DATASET_IDS):
        raw = json.dumps(payloads[dataset_id],sort_keys=True).encode()
        snapshots.append({
            "dataset_id":dataset_id,"page_number":0,"request_url":"https://example.invalid/"+dataset_id,
            "response_sha256":hashlib.sha256(raw).hexdigest(),"byte_size":len(raw),
            "row_count":len(payloads[dataset_id]),"snapshot_name":dataset_id+"-page-0000.json",
            "response_bytes":raw,
        })
        queries[dataset_id] = "https://example.invalid/"+dataset_id
    output = root / "pack"
    manifest = build_database(output,lock,payloads,metadata,snapshots,queries,"2026-11-05T00:00:00+00:00")
    metadata_dir=output/"metadata"
    metadata_dir.mkdir()
    metadata_files=[]
    for d in DATASET_IDS:
        raw=metadata_raws[d]
        p=metadata_dir/(d+"-metadata.json")
        p.write_bytes(raw)
        metadata_files.append({"dataset_id":d,"path":"metadata/"+p.name,"sha256":hashlib.sha256(raw).hexdigest(),"byte_size":len(raw)})
    manifest["metadata_files"]=metadata_files
    manifest["metadata_bundle_sha256"]=hashlib.sha256("".join(x["sha256"] for x in sorted(metadata_files,key=lambda x:x["dataset_id"])).encode()).hexdigest()
    (output/"manifest.json").write_text(json.dumps(manifest,sort_keys=True,indent=2),encoding="utf-8")
    return output,lock

class RdwVagTypeApprovalTests(unittest.TestCase):
    def test_unique_same_revision_engine_and_transmission_rows_create_candidate_only_pair(self):
        with tempfile.TemporaryDirectory() as tmp:
            output,lock=build_fixture_pack(Path(tmp))
            result=verify_pack(output,lock)
            self.assertEqual(result["counts"]["unique_source_row_pair_candidates"],1)
            db=sqlite3.connect(output/"rdw-vag-type-approval.sqlite")
            pair=db.execute("SELECT pairing_status,pairing_confirmed,exact_vehicle_fitment,ru_eaeu_applicability FROM engine_transmission_pair_candidates").fetchone()
            self.assertEqual(pair,("unique_source_rows_candidate",0,0,0))
            engine=db.execute("SELECT code_namespace,vag_factory_engine_code_verified FROM engine_approval_candidates").fetchone()
            trans=db.execute("SELECT code_namespace,vag_factory_gearbox_code_verified FROM transmission_approval_candidates").fetchone()
            self.assertEqual(engine,("RDW.motorcode",0))
            self.assertEqual(trans,("RDW.codetypeversnellingsbak",0))
            db.close()

    def test_multiple_engine_rows_never_form_a_confirmed_or_unique_pair(self):
        payloads=fixtures()
        second=dict(payloads["4by9-ammk"][0]); second["volgnummeraandrijving"]="2"; second["motorcode"]="CAVD"
        payloads["4by9-ammk"].append(second)
        with tempfile.TemporaryDirectory() as tmp:
            output,lock=build_fixture_pack(Path(tmp),payloads)
            db=sqlite3.connect(output/"rdw-vag-type-approval.sqlite")
            row=db.execute("SELECT engine_candidate_id,transmission_candidate_id,engine_row_count,transmission_row_count,pairing_status,pairing_confirmed FROM engine_transmission_pair_candidates").fetchone()
            self.assertEqual(row,(None,None,2,1,"ambiguous_multiple_rows_candidate",0))
            db.close()

    def test_same_approval_but_different_variant_or_execution_is_not_joined(self):
        payloads=fixtures()
        other=dict(payloads["4by9-ammk"][0]); other["codevarianttgk"]="OTHER"
        payloads["4by9-ammk"].append(other)
        with tempfile.TemporaryDirectory() as tmp:
            output,lock=build_fixture_pack(Path(tmp),payloads)
            db=sqlite3.connect(output/"rdw-vag-type-approval.sqlite")
            self.assertEqual(db.execute("SELECT count(*) FROM engine_approval_candidates").fetchone()[0],1)
            db.close()

    def test_non_vag_and_non_m1_vehicle_rows_are_excluded(self):
        rows=[
            {"merk":"VOLKSWAGEN","handelsbenaming":"GOLF","typegoedkeuringsnummer":"A","variant":"V","uitvoering":"E","europese_voertuigcategorie":"M1"},
            {"merk":"FORD","handelsbenaming":"FOCUS","typegoedkeuringsnummer":"B","variant":"V","uitvoering":"E","europese_voertuigcategorie":"M1"},
            {"merk":"VOLKSWAGEN","handelsbenaming":"CRAFTER","typegoedkeuringsnummer":"C","variant":"V","uitvoering":"E","europese_voertuigcategorie":"N1"},
        ]
        result=normalize_vehicle_rows(rows,"rdw-test")
        self.assertEqual(len(result),1)
        self.assertEqual(result[0]["make_name"],"VOLKSWAGEN")

    def test_registration_identifier_field_is_rejected(self):
        row={"merk":"VOLKSWAGEN","handelsbenaming":"GOLF","typegoedkeuringsnummer":"A","variant":"V","uitvoering":"E","europese_voertuigcategorie":"M1","kenteken":"AB-12-CD"}
        with self.assertRaises(ValueError):
            normalize_vehicle_rows([row],"rdw-test")

    def test_lock_fails_closed_without_cc0_or_reuse_rights(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"lock.json"; lock_file(path)
            data=json.loads(path.read_text()); data["rights"]["offline_cache_allowed"]=False
            path.write_text(json.dumps(data))
            with self.assertRaises(ValueError):
                validate_lock(data)

    def test_pack_has_no_generic_dtc_tables_or_ru_eaeu_claims(self):
        with tempfile.TemporaryDirectory() as tmp:
            output,lock=build_fixture_pack(Path(tmp))
            db=sqlite3.connect(output/"rdw-vag-type-approval.sqlite")
            names={x[0] for x in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            self.assertNotIn("dtc_definitions",names)
            self.assertNotIn("generic_dtc",names)
            self.assertEqual(db.execute("SELECT count(*) FROM vehicle_type_approval_candidates WHERE ru_eaeu_applicability<>0").fetchone()[0],0)
            db.close()

    def test_snapshot_tampering_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            output,lock=build_fixture_pack(Path(tmp))
            snapshot=next((output/"snapshots").glob("*.json"))
            snapshot.write_text("tampered",encoding="utf-8")
            with self.assertRaises(ValueError):
                verify_pack(output,lock)

if __name__ == "__main__":
    unittest.main()

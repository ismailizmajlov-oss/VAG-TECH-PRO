#!/usr/bin/env python3
"""Import VAG make/model/generation/engine-spec candidates into a separate research SQLite.

This does NOT populate production, infer factory engine/gearbox codes, or assign a market.
"""
from __future__ import annotations
import argparse, hashlib, json, sqlite3
from pathlib import Path

DATASET = "gor3a/vehicle-makes-models"
REVISION = "ee99776470a45214bf524cdfe22e5dbf4bd67f93"
LICENSE = "ODbL-1.0"
BRANDS = ("audi", "volkswagen", "skoda", "seat", "cupra")

DDL = """
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS research_sources(
 source_id TEXT PRIMARY KEY, publisher TEXT NOT NULL, dataset TEXT NOT NULL,
 upstream_revision TEXT NOT NULL, source_url TEXT NOT NULL, upstream_source TEXT NOT NULL,
 license TEXT NOT NULL, attribution TEXT NOT NULL, share_alike TEXT NOT NULL,
 source_sha256 TEXT NOT NULL CHECK(length(source_sha256)=64),
 market_scope TEXT NOT NULL CHECK(market_scope='UNKNOWN'),
 imported_at_utc TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS make_candidates(
 make_candidate_id INTEGER PRIMARY KEY, source_id TEXT NOT NULL REFERENCES research_sources,
 make_name TEXT NOT NULL, group_key TEXT NOT NULL, raw_json TEXT NOT NULL,
 review_status TEXT NOT NULL DEFAULT 'candidate'
);
CREATE TABLE IF NOT EXISTS model_candidates(
 model_candidate_id INTEGER PRIMARY KEY, make_candidate_id INTEGER NOT NULL REFERENCES make_candidates,
 model_name TEXT NOT NULL, year_start INTEGER, year_end INTEGER, raw_json TEXT NOT NULL,
 market_scope TEXT NOT NULL DEFAULT 'UNKNOWN', review_status TEXT NOT NULL DEFAULT 'candidate'
);
CREATE TABLE IF NOT EXISTS generation_candidates(
 generation_candidate_id INTEGER PRIMARY KEY, model_candidate_id INTEGER NOT NULL REFERENCES model_candidates,
 generation_name TEXT NOT NULL, year_start INTEGER, year_end INTEGER, body_type TEXT,
 raw_json TEXT NOT NULL, market_scope TEXT NOT NULL DEFAULT 'UNKNOWN',
 review_status TEXT NOT NULL DEFAULT 'candidate'
);
CREATE TABLE IF NOT EXISTS engine_variant_candidates(
 engine_candidate_id INTEGER PRIMARY KEY, generation_candidate_id INTEGER NOT NULL REFERENCES generation_candidates,
 engine_label TEXT NOT NULL, fuel_type TEXT, cylinders INTEGER, displacement_cc INTEGER,
 power_hp REAL, torque_nm REAL, transmission_description TEXT, drivetrain TEXT,
 raw_specs_json TEXT NOT NULL, raw_engine_json TEXT NOT NULL,
 engine_code TEXT, gearbox_code TEXT,
 code_extraction_status TEXT NOT NULL DEFAULT 'not_provided',
 market_scope TEXT NOT NULL DEFAULT 'UNKNOWN',
 review_status TEXT NOT NULL DEFAULT 'candidate'
);
CREATE INDEX IF NOT EXISTS idx_candidate_model_name ON model_candidates(model_name);
CREATE INDEX IF NOT EXISTS idx_candidate_generation ON generation_candidates(generation_name);
CREATE INDEX IF NOT EXISTS idx_candidate_engine_label ON engine_variant_candidates(engine_label);
"""

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--input-dir", required=True, type=Path)
    ap.add_argument("--output", required=True, type=Path)
    args=ap.parse_args()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    if args.output.exists(): args.output.unlink()
    db=sqlite3.connect(args.output)
    db.executescript(DDL)
    counts={"makes":0,"models":0,"generations":0,"engine_variants":0}
    for brand in BRANDS:
        path=args.input_dir/f"{brand}.json"
        raw_bytes=path.read_bytes()
        payload=json.loads(raw_bytes)
        if payload.get("group") != brand:
            raise ValueError(f"{path}: group mismatch; expected {brand!r}")
        digest=hashlib.sha256(raw_bytes).hexdigest()
        source_id=f"vehiclesdb-odbl-{brand}-{REVISION[:12]}"
        db.execute("""INSERT INTO research_sources VALUES(?,?,?,?,?,?,?,?,?,?,?,datetime('now'))""",
          (source_id,"gor3a/vehicle-makes-models",DATASET,REVISION,
           f"https://github.com/{DATASET}/blob/{REVISION}/data/json/{brand}.json",
           "autoevolution.com (as declared by upstream)",LICENSE,
           "Credit gor3a/vehicle-makes-models and autoevolution.com; link source and note changes",
           "Any publicly redistributed adapted database must be offered under ODbL 1.0",
           digest,"UNKNOWN"))
        for make in payload.get("makes",[]):
            cur=db.execute("""INSERT INTO make_candidates(source_id,make_name,group_key,raw_json)
                              VALUES(?,?,?,?)""",
                           (source_id,make["name"],brand,json.dumps(make,ensure_ascii=False)))
            make_id=cur.lastrowid; counts["makes"]+=1
            for model in make.get("models",[]):
                cur=db.execute("""INSERT INTO model_candidates
                  (make_candidate_id,model_name,year_start,year_end,raw_json)
                  VALUES(?,?,?,?,?)""",
                  (make_id,model["name"],model.get("yearStart"),model.get("yearEnd"),
                   json.dumps(model,ensure_ascii=False)))
                model_id=cur.lastrowid; counts["models"]+=1
                for gen in model.get("generations",[]):
                    cur=db.execute("""INSERT INTO generation_candidates
                      (model_candidate_id,generation_name,year_start,year_end,body_type,raw_json)
                      VALUES(?,?,?,?,?,?)""",
                      (model_id,gen["name"],gen.get("yearStart"),gen.get("yearEnd"),
                       gen.get("bodyType"),json.dumps(gen,ensure_ascii=False)))
                    gen_id=cur.lastrowid; counts["generations"]+=1
                    for engine in gen.get("engines",[]):
                        # Upstream records describe engine variants but provide no explicit engine/gearbox code fields.
                        if "engine_code" in engine or "gearbox_code" in engine:
                            raise ValueError("Upstream schema changed: review code fields before import")
                        db.execute("""INSERT INTO engine_variant_candidates
                          (generation_candidate_id,engine_label,fuel_type,cylinders,displacement_cc,
                           power_hp,torque_nm,transmission_description,drivetrain,
                           raw_specs_json,raw_engine_json,code_extraction_status)
                          VALUES(?,?,?,?,?,?,?,?,?,?,?,'not_provided')""",
                          (gen_id,engine.get("label",""),engine.get("fuelType"),engine.get("cylinders"),
                           engine.get("displacementCc"),engine.get("powerHp"),engine.get("torqueNm"),
                           engine.get("transmission"),engine.get("drivetrain"),
                           json.dumps(engine.get("specs",{}),ensure_ascii=False),
                           json.dumps(engine,ensure_ascii=False)))
                        counts["engine_variants"]+=1
        db.execute("UPDATE research_sources SET imported_at_utc=datetime('now') WHERE source_id=?",(source_id,))
        print(f"{brand}: sha256={digest}")
    db.commit()
    assert db.execute("PRAGMA integrity_check").fetchone()[0]=="ok"
    assert db.execute("PRAGMA foreign_key_check").fetchall()==[]
    for table,key in (("make_candidates","makes"),("model_candidates","models"),
                      ("generation_candidates","generations"),("engine_variant_candidates","engine_variants")):
        assert db.execute(f"SELECT count(*) FROM {table}").fetchone()[0]==counts[key]
    print(json.dumps({"revision":REVISION,"license":LICENSE,"counts":counts,
      "market_scope":"UNKNOWN","status":"research_only","production_import":False},ensure_ascii=False))
    db.close()

if __name__=="__main__": main()

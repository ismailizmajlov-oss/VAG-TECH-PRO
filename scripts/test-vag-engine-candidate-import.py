#!/usr/bin/env python3
"""Tests the isolated candidate importer using a synthetic upstream-shaped fixture."""
import json, sqlite3, subprocess, sys, tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
def main():
  with tempfile.TemporaryDirectory() as tmp:
    inp=Path(tmp)/"in"; inp.mkdir()
    for brand in ("audi","volkswagen","skoda","seat","cupra"):
      data={"group":brand,"makes":[{"name":brand.title(),"models":[{"name":"Fixture","yearStart":2000,
       "yearEnd":2005,"generations":[{"name":"Fixture Gen","yearStart":2000,"yearEnd":2005,
       "bodyType":"hatchback","engines":[{"label":"2.0L TDI 6-speed manual (140 HP)",
       "fuelType":"Diesel","cylinders":4,"displacementCc":1968,"powerHp":140,
       "torqueNm":320,"transmission":"6-speed manual","drivetrain":"Front Wheel Drive",
       "specs":{"ENGINE SPECS / Power":"140 HP"}}]}]}]}]}
      (inp/f"{brand}.json").write_text(json.dumps(data),encoding="utf-8")
    out=Path(tmp)/"research.sqlite"
    run=subprocess.run([sys.executable,str(ROOT/"scripts/import_vag_engine_candidates.py"),
      "--input-dir",str(inp),"--output",str(out)],capture_output=True,text=True)
    if run.returncode != 0:
      raise AssertionError(f"importer failed\\nSTDOUT:\\n{run.stdout}\\nSTDERR:\\n{run.stderr}")
    db=sqlite3.connect(out)
    assert db.execute("select count(*) from model_candidates").fetchone()[0]==5
    assert db.execute("select count(*) from generation_candidates").fetchone()[0]==5
    assert db.execute("select count(*) from engine_variant_candidates").fetchone()[0]==5
    row=db.execute("select engine_code,gearbox_code,code_extraction_status,market_scope from engine_variant_candidates limit 1").fetchone()
    assert row==(None,None,"not_provided","UNKNOWN"),row
    assert db.execute("pragma integrity_check").fetchone()[0]=="ok"
    assert db.execute("pragma foreign_key_check").fetchall()==[]
    db.close()
    print("PASS: isolated import, market UNKNOWN, no inferred engine/gearbox codes, integrity")
if __name__=="__main__": main()

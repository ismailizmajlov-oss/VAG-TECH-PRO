from __future__ import annotations
import csv,hashlib,importlib.util,json,shutil,tempfile,unittest
from datetime import date
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("cardir_builder",ROOT/"scripts/build_cardir_vag_open_data_pack.py")
builder=importlib.util.module_from_spec(spec); spec.loader.exec_module(builder)

class CardirVagOpenDataPackTests(unittest.TestCase):
    def setUp(self):
        self.temp=Path(tempfile.mkdtemp(prefix="cardir-vag-pack-test-"))
        self.csv=self.temp/"source.csv"; self.source=self.temp/"source-manifest.json"; self.snapshot=self.temp/"snapshot.json"; self.output=self.temp/"pack"
        rows=[
          ["Audi","A4","oil_volume_with_filter","Масло с фильтром","2.0 TFSI","4.6","л","Руководство по эксплуатации Audi A4, 2024","стр. 213","https://cardir.ru/istochnik/101/#page-213","https://cardir.ru/audi/a4/maslo/","2026-11-06"],
          ["Volkswagen","Golf","gearbox_oil_spec","Масло КПП","DSG DQ381 (0GC)","G 052 182 A2","","Руководство по эксплуатации Volkswagen Golf, 2024","стр. 144","https://cardir.ru/istochnik/102/#page-144","https://cardir.ru/volkswagen/golf/maslo-kpp/","2026-11-06"],
          ["Škoda","Octavia","coolant_spec","Антифриз","1.4 TSI","G12evo","","Руководство по эксплуатации Skoda Octavia, 2024","стр. 173","https://cardir.ru/istochnik/103/#page-173","https://cardir.ru/skoda/octavia/antifriz/","2026-11-06"],
          ["SEAT","Leon","service_interval_km","Межсервисный интервал","","15000","км","Руководство по эксплуатации SEAT Leon, 2022","стр. 88","https://cardir.ru/istochnik/104/#page-88","https://cardir.ru/seat/leon/to/","2026-11-06"],
          ["CUPRA","Formentor","spark_plug","Свеча зажигания","2.0 TSI","NGK example","","Руководство по эксплуатации CUPRA Formentor, 2024","стр. 201","https://cardir.ru/istochnik/105/#page-201","https://cardir.ru/cupra/formentor/svechi/","2026-11-06"],
          ["Porsche","Macan","tire_pressure_front","Давление передних шин","полная нагрузка","2.5","бар","Руководство по эксплуатации Porsche Macan, 2023","стр. 290","https://cardir.ru/istochnik/106/#page-290","https://cardir.ru/porsche/macan/shiny/","2026-11-06"],
          ["Bentley","Bentayga","brake_fluid_spec","Тормозная жидкость","","DOT 4","","Руководство по эксплуатации Bentley Bentayga, 2022","стр. 188","https://cardir.ru/istochnik/107/#page-188","https://cardir.ru/bentley/bentayga/tormoza/","2026-11-06"],
          ["Lamborghini","Urus","ac_refrigerant_type","Хладагент","","R1234yf","","Руководство по эксплуатации Lamborghini Urus, 2024","стр. 244","https://cardir.ru/istochnik/108/#page-244","https://cardir.ru/lamborghini/urus/kondicioner/","2026-11-06"],
          ["Audi supplier GmbH","Not VAG","oil_spec","Oil","","not retained","","Unrelated","1","https://cardir.ru/istochnik/109/","https://cardir.ru/audi-supplier/not-vag/","2026-11-06"],
        ]
        with self.csv.open("w",encoding="utf-8-sig",newline="") as stream:
            writer=csv.writer(stream); writer.writerow(builder.COLUMNS); writer.writerows(rows)
        self.source_obj={
          "source_id":builder.SOURCE_ID,"publisher":"CarDir","data_revision":"fixture-r1",
          "source_urls":{"csv":builder.DATA_URL,"dataset_page":builder.DATA_PAGE_URL},
          "data_scope":{"vag_brand_allowlist":["Audi","Volkswagen","Volkswagen Commercial Vehicles","Volkswagen Nutzfahrzeuge","Skoda","Škoda","SEAT","CUPRA","Porsche","Bentley","Lamborghini","VW"]},
          "rights":{"rights_status":"approved_by_published_CC_BY_4_0","permission_status":"not_required_under_published_CC_BY_4_0",
            "license_id":"CC-BY-4.0","license_url":builder.LICENSE_URL,"commercial_use_allowed":True,"display_allowed":True,
            "offline_cache_allowed":True,"bulk_reuse_allowed":True,"redistribution_allowed":True,"attribution_required":True,
            "attribution_text":"CarDir (https://cardir.ru/dannye/), CC BY 4.0."},
          "snapshot":{"expected_source_row_count":9,"expected_model_count":9},
          "applicability_policy":{"market_scope":"UNKNOWN","exact_engine_code_mapping":False,"exact_gearbox_code_mapping":False,
            "exact_engine_gearbox_pair":False,"model_generation_inferred":False,"model_year_inferred":False,"exact_vehicle_fitment":False,
            "ru_eaeu_applicability":False,"ecu_fitment":False,"dtc_fitment":False,"wiring_or_pinout_content":False,
            "repair_procedure_content":False,"production_fitment":False},
          "import_policy":{"research_pack_allowed":True,"production_import":False,"product_database_ingested":False,"product_import_allowed":False}
        }
        self.source.write_text(json.dumps(self.source_obj,ensure_ascii=False,sort_keys=True,indent=2)+"\n",encoding="utf-8")
        _,summary=builder.read_csv_rows(self.csv)
        self.snapshot_obj={"schema_version":1,"source_id":builder.SOURCE_ID,"source_file":"source.csv","source_url":builder.DATA_URL,
          "source_manifest_sha256":hashlib.sha256(self.source.read_bytes()).hexdigest(),"source_snapshot_sha256":hashlib.sha256(self.csv.read_bytes()).hexdigest(),
          "source_file_bytes":self.csv.stat().st_size,"retrieved_at_utc":"2026-11-07T11:00:00+00:00",**summary}
        self.snapshot.write_text(json.dumps(self.snapshot_obj,ensure_ascii=False,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    def tearDown(self): shutil.rmtree(self.temp,ignore_errors=True)
    def test_build_preserves_vag_rows_and_provenance(self):
        result=builder.build(self.csv,self.snapshot,self.source,self.output)
        self.assertEqual(result["status"],"verified_research_only")
        self.assertEqual(result["counts"]["vag_facts"],8)
        self.assertEqual(result["counts"]["vag_brands"],8)
        self.assertEqual(result["counts"]["vag_models"],8)
        self.assertEqual(result["market_scope"],["UNKNOWN"])
        self.assertFalse(result["product_import_allowed"]); self.assertFalse(result["production_import"])
        manifest=builder.read_json(self.output/"manifest.json")
        self.assertFalse(manifest["exact_engine_gearbox_pair"]); self.assertFalse(manifest["ru_eaeu_applicability"])
        self.assertEqual(manifest["publisher_verification_status"],"publisher_verified")
        self.assertEqual(manifest["technical_review_status"],"not_independently_reviewed")
    def test_exact_brand_allowlist_excludes_substrings(self):
        _,summary=builder.read_csv_rows(self.csv)
        self.assertEqual(summary["vag_row_count"],8)
        self.assertNotIn("Audi supplier GmbH",summary["vag_brand_values"])
        self.assertFalse(builder.is_vag_brand("Audi supplier GmbH"))
        self.assertFalse(builder.is_vag_brand("Volkswagen Group Parts"))
    def test_qualifier_is_not_mapped_to_engine_or_gearbox_code(self):
        builder.build(self.csv,self.snapshot,self.source,self.output)
        import sqlite3
        db=sqlite3.connect(self.output/"cardir-vag-owner-manual-facts.sqlite")
        try:
            row=db.execute("SELECT qualifier_raw,engine_code,transmission_code,exact_engine_gearbox_pair,market_scope FROM facts WHERE parameter_key='gearbox_oil_spec'").fetchone()
            self.assertEqual(row[0],"DSG DQ381 (0GC)"); self.assertIsNone(row[1]); self.assertIsNone(row[2]); self.assertEqual(row[3],0); self.assertEqual(row[4],"UNKNOWN")
        finally: db.close()
    def test_snapshot_hash_mismatch_fails_closed(self):
        bad=dict(self.snapshot_obj); bad["source_snapshot_sha256"]="0"*64
        self.snapshot.write_text(json.dumps(bad),encoding="utf-8")
        with self.assertRaisesRegex(ValueError,"SHA-256"): builder.build(self.csv,self.snapshot,self.source,self.output)
    def test_missing_redistribution_right_fails_closed(self):
        bad=dict(self.source_obj); bad["rights"]=dict(bad["rights"]); bad["rights"]["redistribution_allowed"]=False
        self.source.write_text(json.dumps(bad),encoding="utf-8")
        with self.assertRaisesRegex(ValueError,"permission/attribution"): builder.build(self.csv,self.snapshot,self.source,self.output)
    def test_external_source_host_is_rejected(self):
        rows,_=builder.read_csv_rows(self.csv); rows[0]["source_url"]="https://cardir.ru.evil.example/source"
        with self.assertRaisesRegex(ValueError,"official CarDir HTTPS host"): builder.validate_row(rows[0],2)
    def test_vin_like_value_is_rejected(self):
        rows,_=builder.read_csv_rows(self.csv); rows[0]["value"]="WVWZZZ1KZAW000001"
        with self.assertRaisesRegex(ValueError,"VIN-like identifier"): builder.validate_row(rows[0],2)
    def test_future_verified_date_is_rejected(self):
        rows,_=builder.read_csv_rows(self.csv); rows[0]["verified_at"]="2027-01-01"
        with self.assertRaisesRegex(ValueError,"future"): builder.validate_row(rows[0],2,retrieved_date=date(2026,11,7))
    def test_existing_output_is_never_overwritten(self):
        self.output.mkdir(); (self.output/"KEEP.txt").write_text("previous",encoding="utf-8")
        with self.assertRaises(FileExistsError): builder.build(self.csv,self.snapshot,self.source,self.output)
        self.assertEqual((self.output/"KEEP.txt").read_text(encoding="utf-8"),"previous")

if __name__=="__main__": unittest.main()

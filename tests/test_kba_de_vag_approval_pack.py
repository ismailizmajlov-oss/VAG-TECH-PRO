import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from openpyxl import Workbook

SCRIPT=Path(__file__).resolve().parents[1]/"scripts"/"build_kba_de_vag_approval_research_pack.py"
SPEC=importlib.util.spec_from_file_location("kba_approval_builder",SCRIPT)
BUILDER=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILDER)

class KbaApprovalResearchPackTests(unittest.TestCase):
    def make_workbook(self,path:Path):
        wb=Workbook()
        ws=wb.active
        ws.title="Tabelle1"
        for i,value in enumerate(BUILDER.HEADER,1):
            if value is not None: ws.cell(3,i).value=value
        rows=[
            ["Volkswagen AG","Golf","AU","Kraftfahrzeuge der Klasse M1","e1*2007/46*1234*01","KBA","Neuerteilung","2020-01-02","e1",None,"KBA",None,"",""],
            ["Mercedes-Benz AG","C-Class","W206","Kraftfahrzeuge der Klasse M1","e1*2007/46*5678*01","KBA","Erweiterung","2021-02-03","e1",None,"KBA",None,"",""],
            ["Audi_Sport","RS model","F5","Kraftfahrzeuge der Klasse M1","e1*2007/46*9999*01","KBA","Erweiterung","2022-03-04","e1",None,"KBA",None,"",""],
            ["Bugatti Automobiles S.A.S.","Chiron","C","Kraftfahrzeuge der Klasse M1","e1*2007/46*7777*01","KBA","Erweiterung","2023-04-05","e1",None,"KBA",None,"",""],
            ["Seat S.A.","Leon","KL","Kraftfahrzeuge der Klasse M1","e1*2007/46*2222*01","KBA","Erweiterung","2024-05-06","e1",None,"KBA",None,"",""],
        ]
        for rn,row in enumerate(rows,4):
            for col,value in enumerate(row,1):
                if value is not None: ws.cell(rn,col).value=value
        wb.save(path)

    def test_row_hash_binds_row_number_and_cells(self):
        cells=["Volkswagen AG","Golf",None]
        self.assertEqual(BUILDER.row_sha(4,cells),BUILDER.row_sha(4,cells))
        self.assertNotEqual(BUILDER.row_sha(4,cells),BUILDER.row_sha(5,cells))
        self.assertNotEqual(BUILDER.row_sha(4,cells),BUILDER.row_sha(4,["Volkswagen AG","Polo",None]))

    def test_exact_label_filter_does_not_fuzzy_map_or_include_bugatti(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/"fixture.xlsx"
            self.make_workbook(path)
            records,summary=BUILDER.extract(path)
        self.assertEqual(len(records),3)
        self.assertEqual({x["manufacturer_label"] for x in records},{"Volkswagen AG","Audi_Sport","Seat S.A."})
        self.assertEqual(summary["source_rows"],5)
        self.assertEqual(summary["excluded_source_label_counts"],{"Bugatti Automobiles S.A.S.":1})
        audi=next(x for x in records if x["manufacturer_label"]=="Audi_Sport")
        self.assertEqual(audi["manufacturer_label_mapping_status"],"unresolved_source_label")

    def test_invalid_zip_path_is_rejected(self):
        import zipfile
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/"unsafe.xlsx"
            with zipfile.ZipFile(path,"w") as archive: archive.writestr("../escape.txt","x")
            with self.assertRaises(ValueError): BUILDER.safe_xlsx(path)

    def test_source_rights_gate_rejects_product_import(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/"source.json"
            m={"source_id":BUILDER.SOURCE_ID,"resource_url":BUILDER.SOURCE_URL,"catalog_url":BUILDER.CATALOG_URL,
               "market_scope":["DE"],"product_import_allowed":True,"data_ingested":False,"rights":{},"snapshot":{}}
            path.write_text(json.dumps(m),encoding="utf-8")
            with self.assertRaises(ValueError): BUILDER.read_manifest(path)

if __name__=="__main__": unittest.main()

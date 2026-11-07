import io
import sys
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import probe_kba_whole_vehicle_approvals as probe


def synthetic_xlsx():
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", """<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="xml" ContentType="application/xml"/></Types>""")
        archive.writestr("xl/workbook.xml", """<?xml version="1.0"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Genehmigungen" sheetId="1" r:id="rId1"/></sheets></workbook>""")
        archive.writestr("xl/_rels/workbook.xml.rels", """<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/></Relationships>""")
        archive.writestr("xl/worksheets/sheet1.xml", """<?xml version="1.0"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData><row r="1"><c r="A1" t="inlineStr"><is><t>Liste der erteilten Typgenehmigungen</t></is></c></row><row r="2"><c r="A2" t="inlineStr"><is><t>Hersteller</t></is></c><c r="B2" t="inlineStr"><is><t>Handelsname</t></is></c><c r="C2" t="inlineStr"><is><t>Typgenehmigungsnummer</t></is></c></row><row r="3"><c r="A3" t="inlineStr"><is><t>VOLKSWAGEN AG</t></is></c><c r="B3" t="inlineStr"><is><t>Golf</t></is></c><c r="C3" t="inlineStr"><is><t>e1*2018/858*00001</t></is></c></row></sheetData></worksheet>""")
    return output.getvalue()


class KbaWholeVehicleApprovalProbeTests(unittest.TestCase):
    def test_only_official_kba_https_resource_is_accepted(self):
        probe.validate_official_url(probe.SOURCE_URL)
        with self.assertRaises(ValueError):
            probe.validate_official_url("https://example.com/file.xlsx")
        with self.assertRaises(ValueError):
            probe.validate_official_url("http://www.kba.de/file.xlsx")
        with self.assertRaises(ValueError):
            probe.validate_official_url("https://www.kba.de/file.csv")

    def test_xlsx_parser_extracts_sheet_headers_and_sample_without_import(self):
        parsed = probe.parse_xlsx_headers(synthetic_xlsx())
        self.assertEqual(parsed["sheet_count"], 1)
        self.assertEqual(parsed["sheets"][0]["name"], "Genehmigungen")
        self.assertEqual(parsed["sheets"][0]["header_row_number"], 2)
        self.assertEqual(parsed["sheets"][0]["header_status"], "candidate_header_by_known_field_names")
        self.assertEqual(
            parsed["sheets"][0]["header"],
            ["Hersteller", "Handelsname", "Typgenehmigungsnummer"],
        )
        self.assertEqual(
            parsed["sheets"][0]["sample_rows"][0],
            ["VOLKSWAGEN AG", "Golf", "e1*2018/858*00001"],
        )

    def test_xlsx_parser_rejects_non_xlsx_and_traversal(self):
        with self.assertRaises(ValueError):
            probe.parse_xlsx_headers(b"not an xlsx")
        with self.assertRaises(ValueError):
            probe._safe_zip_member("../outside.xml")
        with self.assertRaises(ValueError):
            probe._safe_zip_member("/absolute.xml")

    def test_xlsx_parser_rejects_external_workbook_relationships(self):
        payload = synthetic_xlsx()
        source = zipfile.ZipFile(io.BytesIO(payload))
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as target:
            for item in source.infolist():
                content = source.read(item.filename)
                if item.filename == "xl/_rels/workbook.xml.rels":
                    content = content.replace(
                        b'Target="worksheets/sheet1.xml"',
                        b'Target="https://example.com/sheet.xml" TargetMode="External"',
                    )
                target.writestr(item, content)
        with self.assertRaises(ValueError):
            probe.parse_xlsx_headers(output.getvalue())


if __name__ == "__main__":
    unittest.main()

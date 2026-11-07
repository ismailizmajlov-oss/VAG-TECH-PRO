import csv
import io
import unittest

from scripts.probe_astra_targa_emissionen import FIELDS, parse_preview, resolve_header_positions


def header():
    values = [f"field_{i}" for i in range(42)]
    names = {
        0: "TG-Code", 1: "Marke", 2: "Typ", 9: "Getriebe",
        10: "iAchse", 13: "Motormarke", 14: "Motortyp", 15: "Bauart",
        16: "Treibstoff", 19: "Hubraum", 20: "Leistung",
        22: "Drehmoment", 24: "Abgasreinigung", 26: "Antrieb", 41: "Homologationsdatum",
    }
    for index, value in names.items():
        values[index] = value
    return values


def row(make, engine, gearbox):
    values = [""] * 42
    values[FIELDS["approval_number"]] = "1AB701"
    values[FIELDS["make"]] = make
    values[FIELDS["type_variant_version"]] = "A6 Quattro; C4/C4B"
    values[FIELDS["gearbox_classification"]] = gearbox
    values[FIELDS["final_drive_ratio"]] = "4,11"
    values[FIELDS["engine_make"]] = "AUDI"
    values[FIELDS["engine_type"]] = engine
    values[FIELDS["fuel"]] = "D"
    values[FIELDS["displacement_cc"]] = "2459"
    values[FIELDS["power_kw"]] = "103"
    values[FIELDS["torque_nm"]] = "290"
    values[FIELDS["homologation_date"]] = "19950918"
    return values


class AstraTargaEmissionenProbeTests(unittest.TestCase):
    def test_documented_42_field_schema(self):
        resolve_header_positions(header())
        bad = header()
        bad[9] = "unknown"
        with self.assertRaisesRegex(ValueError, "Required ASTRA emissionen field"):
            resolve_header_positions(bad)

    def test_per_gearbox_row_is_preserved_without_oem_code_promotion(self):
        stream = io.StringIO()
        writer = csv.writer(stream, delimiter="\t", lineterminator="\n")
        writer.writerow(header())
        writer.writerow(row("AUDI", "AEL", "m6"))
        writer.writerow(row("VW", "ABF", "m5"))
        writer.writerow(row("VW GROUP", "ABF", "m5"))
        result = parse_preview(stream.getvalue().encode("cp1252"))
        self.assertEqual(result["vag_exact_make_counts_in_preview"], {"AUDI": 1, "VW": 1})
        self.assertEqual(result["first_vag_row_sample"]["engine_type"], "AEL")
        self.assertEqual(result["first_vag_row_sample"]["gearbox_classification"], "m6")
        self.assertIn("one row is emitted for each gearbox variant", result["documented_row_semantics"])
        self.assertTrue(any("not a confirmed VAG gearbox code" in x for x in result["limitations"]))

    def test_no_fuzzy_make_matching(self):
        stream = io.StringIO()
        writer = csv.writer(stream, delimiter="\t", lineterminator="\n")
        writer.writerow(header())
        writer.writerow(row("Audi AG", "AEL", "m6"))
        result = parse_preview(stream.getvalue().encode("cp1252"))
        self.assertEqual(result["vag_exact_make_counts_in_preview"], {})


if __name__ == "__main__":
    unittest.main()

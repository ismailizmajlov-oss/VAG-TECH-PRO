import csv
import io
import unittest

from scripts.probe_astra_targa_legacy import FIELDS, MIN_REQUIRED_COLUMNS, parse_preview


def make_row(make: str, engine_marking: str, gearbox: str) -> bytes:
    values = [""] * MIN_REQUIRED_COLUMNS
    values[FIELDS["approval_number"]] = "3VW123"
    values[FIELDS["approval_date"]] = "20200115"
    values[FIELDS["vehicle_group"]] = "10"
    values[FIELDS["vehicle_class"]] = "M1"
    values[FIELDS["make"]] = make
    values[FIELDS["type"]] = "GOLF"
    values[FIELDS["variant_version"]] = "GOLF;ABC"
    values[FIELDS["eu_whole_vehicle_approval"]] = "e1*2007/46*1234*01"
    values[FIELDS["gearbox_1"]] = gearbox
    values[FIELDS["engine_make"]] = "VOLKSWAGEN"
    values[FIELDS["engine_type"]] = "EA888"
    values[FIELDS["engine_marking"]] = engine_marking
    stream = io.StringIO()
    writer = csv.writer(stream, delimiter="\t", lineterminator="\n")
    writer.writerow(values)
    return stream.getvalue().encode("utf-8")


class AstraTargaProbeTests(unittest.TestCase):
    def test_exact_make_is_counted_without_fuzzy_aliases(self):
        payload = (
            make_row("VW", "CHHB", "m7a")
            + make_row("VW GROUP", "CHHB", "m7a")
            + make_row("Volkswagen", "CJSA", "m1a")
        )
        result = parse_preview(payload)
        self.assertEqual(result["vag_exact_make_counts_in_preview"], {
            "VOLKSWAGEN": 1,
            "VW": 1,
        })
        self.assertEqual(result["rows_meeting_published_field_schema"], 3)

    def test_raw_engine_marking_and_gearbox_are_preserved_as_source_values(self):
        result = parse_preview(make_row("AUDI", "EA888-XYZ", "m7a"))
        sample = result["first_vag_record_sample"]
        self.assertEqual(sample["engine_marking"], "EA888-XYZ")
        self.assertEqual(sample["gearbox_1"], "m7a")
        self.assertNotIn("confirmed_engine_code", sample)
        self.assertNotIn("confirmed_gearbox_code", sample)

    def test_short_rows_do_not_pass_published_schema_gate(self):
        payload = ("\t".join(["x"] * (MIN_REQUIRED_COLUMNS - 1)) + "\n").encode()
        result = parse_preview(payload)
        self.assertEqual(result["rows_meeting_published_field_schema"], 0)

    def test_empty_preview_is_rejected(self):
        with self.assertRaises(ValueError):
            parse_preview(b"")


if __name__ == "__main__":
    unittest.main()

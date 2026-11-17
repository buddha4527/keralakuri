import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "scripts"))
from kk.parse import (ValidationError, html_to_text, parse_list_page,  # noqa: E402
                      parse_result_text, validate)

FIX = pathlib.Path(__file__).parent / "fixtures"

LIST_HTML = """<table id='dtList'><tbody>
<tr><td class='text-left'>BHAGYATHARA(BT-80)</td><td >16/11/2026</td><td ><a href='https://result.keralalotteries.com/viewlotisresult.php?drawserial=75441' target='_blank'>View</a></td></tr>
<tr><td class='text-left'>SUVARNA KERALAM(SK-77)</td><td >13/11/2026</td><td ><a href='https://result.keralalotteries.com/viewlotisresult.php?drawserial=75438' target='_blank'>View</a></td></tr>
</tbody></table>"""


class ListPage(unittest.TestCase):
    def test_rows(self):
        rows = parse_list_page(LIST_HTML)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["code"], "BT")
        self.assertEqual(rows[0]["draw_no"], 80)
        self.assertEqual(rows[0]["date"], "2026-11-16")
        self.assertEqual(rows[1]["raw_name"], "SUVARNA KERALAM")
        self.assertEqual(rows[1]["drawserial"], 75438)


class ResultPage(unittest.TestCase):
    def setUp(self):
        self.tiers = parse_result_text(html_to_text((FIX / "result_sample.html").read_text()))
        self.by = {t["tier"]: t for t in self.tiers}

    def test_top_prizes(self):
        first = self.by["1"]
        self.assertEqual(first["amount"], 10000000)
        self.assertEqual(first["tickets"][0]["series"], "BV")
        self.assertEqual(first["tickets"][0]["number"], "543398")
        self.assertEqual(first["tickets"][0]["place"], "Testplace")
        self.assertEqual(self.by["2"]["tickets"][0]["number"], "362422")
        self.assertEqual(len(self.by["consolation"]["tickets"]), 11)

    def test_endings_skip_footer_and_header(self):
        self.assertEqual(len(self.by["4"]["endings"]), 19)
        self.assertNotIn("2026", self.by["7"]["endings"])
        self.assertEqual(self.by["7"]["endings"][-1], "4041")

    def test_valid(self):
        self.assertTrue(validate(self.tiers))

    def test_rejects_broken(self):
        broken = [t for t in self.tiers if t["tier"] != "2"]
        with self.assertRaises(ValidationError):
            validate(broken)
        bad = [dict(t) for t in self.tiers]
        for t in bad:
            if t["tier"] == "consolation":
                t["tickets"] = [{"series": "BN", "number": "111111", "place": None}]
        with self.assertRaises(ValidationError):
            validate(bad)


if __name__ == "__main__":
    unittest.main()

"""Tests for the regex parser's amount and the Excel export."""

import os
import tempfile
import unittest

from openpyxl import load_workbook

from core.exporter import write_to_excel_headless
from core.parser import parse_receipt


HARBOR = """HARBOR HARDWARE SUPPLY
412 Dock St
Date: 03/14/2026
ITEM          QTY  PRICE
Floor Trowel   1   18.99
Subtotal           38.98
Tax                 2.53
TOTAL              41.51
Paid: VISA ****1111"""


class TestAmount(unittest.TestCase):
    def test_total_wins_over_earlier_subtotal(self):
        self.assertEqual(parse_receipt(HARBOR)["Amount"], "41.51")

    def test_grand_total_wins(self):
        text = "SHOP\nSubtotal 123.47\nTax 8.02\nGrand Total 131.49"
        self.assertEqual(parse_receipt(text)["Amount"], "131.49")

    def test_amount_due(self):
        text = "SHOP\nSubtotal 10.00\nAmount Due: $10.80"
        self.assertEqual(parse_receipt(text)["Amount"], "10.80")

    def test_total_without_subtotal(self):
        text = "FUEL\nUnleaded 46.38\nTOTAL 51.37\nDEBIT CARD"
        self.assertEqual(parse_receipt(text)["Amount"], "51.37")

    def test_sub_total_with_space_is_not_the_total(self):
        text = "SHOP\nSub Total 20.00\nTotal 21.60"
        self.assertEqual(parse_receipt(text)["Amount"], "21.60")

    def test_total_tax_line_is_skipped(self):
        text = "SHOP\nTotal Tax 1.60\nTotal 21.60"
        self.assertEqual(parse_receipt(text)["Amount"], "21.60")

    def test_subtotal_used_when_no_total(self):
        text = "SHOP\nSubtotal 12.50"
        self.assertEqual(parse_receipt(text)["Amount"], "12.50")

    def test_dollar_sign_and_comma_removed(self):
        text = "SHOP\nTotal $1,234.50"
        self.assertEqual(parse_receipt(text)["Amount"], "1234.50")

    def test_no_amount(self):
        self.assertEqual(parse_receipt("SHOP\nThanks!")["Amount"], "")


class TestExcelExport(unittest.TestCase):
    def test_amounts_are_numbers_and_total_sums(self):
        rows = [
            ("a.png", "text", {"Company": "A", "Date": "", "Items": "",
                               "Amount": "41.51", "Payment Method": "Visa"}),
            ("b.png", "text", {"Company": "B", "Date": "", "Items": "",
                               "Amount": "$1,000.00", "Payment Method": "Cash"}),
            ("c.png", "text", {"Company": "C", "Date": "", "Items": "",
                               "Amount": "", "Payment Method": ""}),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "out.xlsx")
            write_to_excel_headless(path, rows)
            ws = load_workbook(path).active
            self.assertEqual(ws["E2"].value, 41.51)
            self.assertEqual(ws["E3"].value, 1000.0)
            self.assertIn(ws["E4"].value, ("", None))
            self.assertEqual(ws["A5"].value, "TOTAL")
            self.assertEqual(ws["E5"].value, "=SUM(E2:E4)")


class TestDownloadSectionHidden(unittest.TestCase):
    def test_hidden_attribute_beats_display_flex(self):
        css_path = os.path.join(os.path.dirname(__file__), "..", "web", "static", "style.css")
        with open(css_path) as f:
            css = f.read()
        self.assertIn("[hidden] { display: none !important; }", css)


if __name__ == "__main__":
    unittest.main()

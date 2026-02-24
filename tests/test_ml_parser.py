"""
Tests for core/ml_parser.py

Strategy: mock out the heavy dependencies (_run_donut, file_to_first_image,
extract_text_from_file) so the tests run without loading the 500 MB model
weights or requiring Tesseract/Poppler.
"""

import sys
import types
import threading
import unittest
from unittest.mock import patch, MagicMock


# ---------------------------------------------------------------------------
# Stub out torch and transformers before any import of ml_parser touches them
# ---------------------------------------------------------------------------
def _make_torch_stub():
    torch = types.ModuleType("torch")
    torch.no_grad = lambda: _NoOpCtx()
    torch.cuda = types.SimpleNamespace(is_available=lambda: False)
    return torch


class _NoOpCtx:
    def __enter__(self): return self
    def __exit__(self, *_): pass


for mod in ("torch", "transformers"):
    if mod not in sys.modules:
        sys.modules[mod] = types.ModuleType(mod)


# Now it's safe to import our module
import core.ml_parser as ml_parser  # noqa: E402


# ---------------------------------------------------------------------------
# Helper fixtures
# ---------------------------------------------------------------------------
OCR_TEXT_NORMAL = """\
Coffee House
123 Main St
Date: 01/15/2024
Latte          4.50
Muffin         2.75
Subtotal       7.25
Total          7.25
Cash
"""

OCR_TEXT_RECEIPT_ID_FIRST = """\
Receipt ID: 9982
Coffee House
Date: 03/22/2024
Espresso       3.00
Total          3.00
Visa
"""

CORD_NORMAL = {
    "menu": [
        {"nm": "Latte", "price": "$4.50"},
        {"nm": "Muffin", "price": "$2.75"},
    ],
    "total": {"total_price": "$7.25"},
}

CORD_NO_MENU = {
    "total": {"total_price": "$12.00"},
}

CORD_MENU_AS_DICT = {
    "menu": {"nm": "Burger", "price": "$9.99"},
    "total": {"total_price": "$9.99"},
}

CORD_EMPTY = {}


# ===========================================================================
# _extract_cord_fields
# ===========================================================================
class TestExtractCordFields(unittest.TestCase):

    def test_normal_menu_list(self):
        items, amount = ml_parser._extract_cord_fields(CORD_NORMAL)
        self.assertEqual(items, ["Latte $4.50", "Muffin $2.75"])
        self.assertEqual(amount, "$7.25")

    def test_menu_as_single_dict_is_wrapped(self):
        items, amount = ml_parser._extract_cord_fields(CORD_MENU_AS_DICT)
        self.assertEqual(items, ["Burger $9.99"])
        self.assertEqual(amount, "$9.99")

    def test_missing_menu_returns_empty_items(self):
        items, amount = ml_parser._extract_cord_fields(CORD_NO_MENU)
        self.assertEqual(items, [])
        self.assertEqual(amount, "$12.00")

    def test_empty_cord_dict(self):
        items, amount = ml_parser._extract_cord_fields(CORD_EMPTY)
        self.assertEqual(items, [])
        self.assertEqual(amount, "")

    def test_entry_with_only_name(self):
        cord = {"menu": [{"nm": "Coffee"}], "total": {}}
        items, _ = ml_parser._extract_cord_fields(cord)
        self.assertEqual(items, ["Coffee"])

    def test_entry_with_only_price(self):
        cord = {"menu": [{"price": "$1.00"}], "total": {}}
        items, _ = ml_parser._extract_cord_fields(cord)
        self.assertEqual(items, ["$1.00"])

    def test_blank_entries_are_skipped(self):
        cord = {"menu": [{"nm": "", "price": ""}, {"nm": "Tea", "price": "$2.00"}]}
        items, _ = ml_parser._extract_cord_fields(cord)
        self.assertEqual(items, ["Tea $2.00"])

    def test_total_block_not_a_dict(self):
        cord = {"total": "broken"}
        items, amount = ml_parser._extract_cord_fields(cord)
        self.assertEqual(amount, "")


# ===========================================================================
# _load_model — singleton / thread-safety
# ===========================================================================
class TestLoadModel(unittest.TestCase):

    def setUp(self):
        # Reset module-level singletons before each test
        ml_parser._model = None
        ml_parser._processor = None
        ml_parser._model_lock = threading.Lock()

    def _make_fake_model(self):
        fake_proc = MagicMock()
        fake_model = MagicMock()
        fake_model.eval.return_value = fake_model
        return fake_proc, fake_model

    def test_loads_once_and_caches(self):
        fake_proc, fake_model = self._make_fake_model()

        fake_transformers = MagicMock()
        fake_transformers.DonutProcessor.from_pretrained.return_value = fake_proc
        fake_transformers.VisionEncoderDecoderModel.from_pretrained.return_value = fake_model

        fake_torch = MagicMock()
        fake_torch.cuda.is_available.return_value = False

        with patch.dict("sys.modules", {"transformers": fake_transformers, "torch": fake_torch}):
            m1, p1 = ml_parser._load_model()
            m2, p2 = ml_parser._load_model()

        self.assertIs(m1, m2)
        self.assertIs(p1, p2)
        # from_pretrained should have been called exactly once each
        fake_transformers.DonutProcessor.from_pretrained.assert_called_once()
        fake_transformers.VisionEncoderDecoderModel.from_pretrained.assert_called_once()

    def test_returns_existing_model_without_reimport(self):
        sentinel_model = object()
        sentinel_proc = object()
        ml_parser._model = sentinel_model
        ml_parser._processor = sentinel_proc

        m, p = ml_parser._load_model()

        self.assertIs(m, sentinel_model)
        self.assertIs(p, sentinel_proc)


# ===========================================================================
# parse_receipt_ml — happy path
# ===========================================================================
class TestParseReceiptMlHappyPath(unittest.TestCase):

    def setUp(self):
        ml_parser._model = None
        ml_parser._processor = None

    @patch("core.ml_parser.extract_text_from_file", return_value=OCR_TEXT_NORMAL)
    @patch("core.ml_parser.file_to_first_image", return_value=MagicMock())
    @patch("core.ml_parser._run_donut", return_value=CORD_NORMAL)
    def test_cord_items_and_amount_preferred(self, mock_donut, mock_img, mock_ocr):
        parsed, ocr = ml_parser.parse_receipt_ml("/fake/receipt.png")

        self.assertEqual(ocr, OCR_TEXT_NORMAL)
        self.assertEqual(parsed["Items"], "Latte $4.50; Muffin $2.75")
        self.assertEqual(parsed["Amount"], "$7.25")

    @patch("core.ml_parser.extract_text_from_file", return_value=OCR_TEXT_NORMAL)
    @patch("core.ml_parser.file_to_first_image", return_value=MagicMock())
    @patch("core.ml_parser._run_donut", return_value=CORD_NORMAL)
    def test_company_comes_from_regex(self, mock_donut, mock_img, mock_ocr):
        parsed, _ = ml_parser.parse_receipt_ml("/fake/receipt.png")
        self.assertEqual(parsed["Company"], "Coffee House")

    @patch("core.ml_parser.extract_text_from_file", return_value=OCR_TEXT_NORMAL)
    @patch("core.ml_parser.file_to_first_image", return_value=MagicMock())
    @patch("core.ml_parser._run_donut", return_value=CORD_NORMAL)
    def test_payment_comes_from_regex(self, mock_donut, mock_img, mock_ocr):
        parsed, _ = ml_parser.parse_receipt_ml("/fake/receipt.png")
        self.assertEqual(parsed["Payment Method"], "Cash")

    @patch("core.ml_parser.extract_text_from_file", return_value=OCR_TEXT_NORMAL)
    @patch("core.ml_parser.file_to_first_image", return_value=MagicMock())
    @patch("core.ml_parser._run_donut", return_value=CORD_NORMAL)
    def test_date_comes_from_regex(self, mock_donut, mock_img, mock_ocr):
        parsed, _ = ml_parser.parse_receipt_ml("/fake/receipt.png")
        self.assertEqual(parsed["Date"], "01/15/2024")

    @patch("core.ml_parser.extract_text_from_file", return_value=OCR_TEXT_NORMAL)
    @patch("core.ml_parser.file_to_first_image", return_value=MagicMock())
    @patch("core.ml_parser._run_donut", return_value=CORD_NORMAL)
    def test_returns_tuple_of_dict_and_string(self, mock_donut, mock_img, mock_ocr):
        result = ml_parser.parse_receipt_ml("/fake/receipt.png")
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)
        parsed, ocr = result
        self.assertIsInstance(parsed, dict)
        self.assertIsInstance(ocr, str)

    @patch("core.ml_parser.extract_text_from_file", return_value=OCR_TEXT_NORMAL)
    @patch("core.ml_parser.file_to_first_image", return_value=MagicMock())
    @patch("core.ml_parser._run_donut", return_value=CORD_NORMAL)
    def test_parsed_dict_has_all_five_keys(self, mock_donut, mock_img, mock_ocr):
        parsed, _ = ml_parser.parse_receipt_ml("/fake/receipt.png")
        self.assertSetEqual(
            set(parsed.keys()),
            {"Company", "Date", "Items", "Amount", "Payment Method"},
        )


# ===========================================================================
# parse_receipt_ml — CORD has no menu → fall back to regex items
# ===========================================================================
class TestParseReceiptMlCordFallbackFields(unittest.TestCase):

    @patch("core.ml_parser.extract_text_from_file", return_value=OCR_TEXT_NORMAL)
    @patch("core.ml_parser.file_to_first_image", return_value=MagicMock())
    @patch("core.ml_parser._run_donut", return_value=CORD_NO_MENU)
    def test_regex_items_used_when_cord_menu_absent(self, *_):
        parsed, _ = ml_parser.parse_receipt_ml("/fake/receipt.png")
        # CORD gave no menu → regex items should fill in
        self.assertNotEqual(parsed["Items"], "")

    @patch("core.ml_parser.extract_text_from_file", return_value=OCR_TEXT_NORMAL)
    @patch("core.ml_parser.file_to_first_image", return_value=MagicMock())
    @patch("core.ml_parser._run_donut", return_value=CORD_NO_MENU)
    def test_cord_amount_still_used_when_menu_absent(self, *_):
        parsed, _ = ml_parser.parse_receipt_ml("/fake/receipt.png")
        self.assertEqual(parsed["Amount"], "$12.00")


# ===========================================================================
# parse_receipt_ml — fallback on Donut failure
# ===========================================================================
class TestParseReceiptMlFallback(unittest.TestCase):

    @patch("core.ml_parser.extract_text_from_file", return_value=OCR_TEXT_NORMAL)
    @patch("core.ml_parser.file_to_first_image", side_effect=RuntimeError("no image"))
    def test_falls_back_gracefully_on_image_error(self, mock_img, mock_ocr):
        parsed, ocr = ml_parser.parse_receipt_ml("/fake/receipt.png")
        self.assertIsInstance(parsed, dict)
        self.assertEqual(ocr, OCR_TEXT_NORMAL)

    @patch("core.ml_parser.extract_text_from_file", return_value=OCR_TEXT_NORMAL)
    @patch("core.ml_parser.file_to_first_image", return_value=MagicMock())
    @patch("core.ml_parser._run_donut", side_effect=Exception("model exploded"))
    def test_falls_back_gracefully_on_donut_error(self, *_):
        parsed, ocr = ml_parser.parse_receipt_ml("/fake/receipt.png")
        self.assertIsInstance(parsed, dict)
        self.assertSetEqual(
            set(parsed.keys()),
            {"Company", "Date", "Items", "Amount", "Payment Method"},
        )

    @patch("core.ml_parser.extract_text_from_file", return_value=OCR_TEXT_NORMAL)
    @patch("core.ml_parser.file_to_first_image", return_value=MagicMock())
    @patch("core.ml_parser._run_donut", side_effect=Exception("bad model id"))
    def test_fallback_still_extracts_company(self, *_):
        parsed, _ = ml_parser.parse_receipt_ml("/fake/receipt.png")
        self.assertEqual(parsed["Company"], "Coffee House")

    @patch("core.ml_parser.extract_text_from_file", return_value=OCR_TEXT_RECEIPT_ID_FIRST)
    @patch("core.ml_parser.file_to_first_image", return_value=MagicMock())
    @patch("core.ml_parser._run_donut", side_effect=Exception("bad model id"))
    def test_fallback_skips_receipt_id_line_for_company(self, *_):
        parsed, _ = ml_parser.parse_receipt_ml("/fake/receipt.png")
        self.assertEqual(parsed["Company"], "Coffee House")


# ===========================================================================
# parse_receipt_ml — company name heuristic (via regex path)
# ===========================================================================
class TestCompanyHeuristic(unittest.TestCase):
    """Drive the company-skip logic through the full fallback path."""

    def _parse(self, ocr_text):
        with patch("core.ml_parser.extract_text_from_file", return_value=ocr_text), \
             patch("core.ml_parser.file_to_first_image", side_effect=RuntimeError):
            parsed, _ = ml_parser.parse_receipt_ml("/fake/r.png")
        return parsed["Company"]

    def test_skips_blank_leading_lines(self):
        text = "\n\nBest Bakery\nDate: 05/01/2024\nTotal $5.00"
        self.assertEqual(self._parse(text), "Best Bakery")

    def test_skips_date_line(self):
        text = "01/15/2024\nStar Diner\nTotal $10.00"
        self.assertEqual(self._parse(text), "Star Diner")

    def test_skips_phone_number(self):
        text = "555-123-4567\nTaco Stand\nTotal $8.00"
        self.assertEqual(self._parse(text), "Taco Stand")

    def test_skips_tel_prefix(self):
        text = "Tel: 800-555-0000\nPizza Palace\nTotal $15.00"
        self.assertEqual(self._parse(text), "Pizza Palace")

    def test_skips_www_line(self):
        text = "www.example.com\nThe Noodle Bar\nTotal $12.00"
        self.assertEqual(self._parse(text), "The Noodle Bar")

    def test_skips_receipt_id(self):
        text = "Receipt ID: 00123\nGreen Grocer\nTotal $4.00"
        self.assertEqual(self._parse(text), "Green Grocer")

    def test_falls_through_to_empty_when_all_lines_skipped(self):
        text = "Receipt ID: 1\n01/01/2024\n555.000.0000\nwww.x.com\n\n"
        self.assertEqual(self._parse(text), "")


if __name__ == "__main__":
    unittest.main()

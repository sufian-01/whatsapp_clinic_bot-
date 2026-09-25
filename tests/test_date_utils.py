import unittest
from datetime import date

from app.tools.date_utils import parse_date


class DateUtilsTests(unittest.TestCase):
    def test_supported_natural_formats(self):
        expected = "2026-09-29"
        for value in ("29 sept 2026", "29 September 2026", "29 Sep 2026", "29/09/2026", "29-09-2026", "September 29 2026"):
            self.assertEqual(parse_date(value)["date"], expected)

    def test_relative_dates(self):
        self.assertEqual(parse_date("tomorrow", date(2026, 9, 25))["date"], "2026-09-26")
        self.assertEqual(parse_date("day after tomorrow", date(2026, 9, 25))["date"], "2026-09-27")
        self.assertEqual(parse_date("next Monday", date(2026, 9, 25))["date"], "2026-09-28")

    def test_invalid_date(self):
        result = parse_date("not a date")
        self.assertFalse(result["success"])
        self.assertEqual(result["error_code"], "INVALID_DATE")
import unittest

from utils.phone_formatter import mask_phone_number, normalize_iranian_mobile


class IranianMobileNormalizationTests(unittest.TestCase):
    def test_normalizes_common_mobile_formats(self):
        expected = "+989121234567"
        self.assertEqual(normalize_iranian_mobile("09121234567"), expected)
        self.assertEqual(normalize_iranian_mobile("9121234567"), expected)
        self.assertEqual(normalize_iranian_mobile("989121234567"), expected)
        self.assertEqual(normalize_iranian_mobile("+98 912 123 4567"), expected)
        self.assertEqual(normalize_iranian_mobile("0098 912 123 4567"), expected)

    def test_rejects_invalid_or_non_mobile_values(self):
        for value in ("", "12345", "02112345678", "not-a-number"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    normalize_iranian_mobile(value)

    def test_masks_phone_numbers_for_logs(self):
        self.assertEqual(mask_phone_number("+989121234567"), "***4567")
        self.assertEqual(mask_phone_number("12"), "***")


if __name__ == "__main__":
    unittest.main()

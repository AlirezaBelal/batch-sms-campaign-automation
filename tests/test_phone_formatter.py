import unittest

from utils.phone_formatter import convert_to_international_format, mask_phone_number


class PhoneFormatterTests(unittest.TestCase):
    def test_normalizes_common_iranian_mobile_formats(self):
        expected = "+989121234567"
        self.assertEqual(convert_to_international_format("09121234567"), expected)
        self.assertEqual(convert_to_international_format("9121234567"), expected)
        self.assertEqual(convert_to_international_format("989121234567"), expected)
        self.assertEqual(convert_to_international_format("+98 912 123 4567"), expected)
        self.assertEqual(convert_to_international_format("0098 912 123 4567"), expected)

    def test_rejects_invalid_numbers(self):
        for value in ("", "12345", "02112345678", "not-a-number"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    convert_to_international_format(value)

    def test_masks_phone_number_for_logs(self):
        self.assertEqual(mask_phone_number("+989121234567"), "***4567")
        self.assertEqual(mask_phone_number("12"), "***")


if __name__ == "__main__":
    unittest.main()

import unittest
from unittest.mock import patch

import main


class RuntimeConfigurationTests(unittest.TestCase):
    def test_dry_run_takes_precedence_over_live_send_switch(self):
        with (
            patch.object(main, "DRY_RUN_ENABLED", True),
            patch.object(main, "SEND_ENABLED", True),
            patch.object(main, "GATEWAY_USERNAME", ""),
            patch.object(main, "GATEWAY_PASSWORD", ""),
        ):
            self.assertTrue(main.validate_runtime_config())

    def test_live_mode_requires_gateway_credentials(self):
        with (
            patch.object(main, "DRY_RUN_ENABLED", False),
            patch.object(main, "SEND_ENABLED", True),
            patch.object(main, "GATEWAY_USERNAME", ""),
            patch.object(main, "GATEWAY_PASSWORD", ""),
        ):
            self.assertFalse(main.validate_runtime_config())

    def test_live_mode_requires_explicit_send_opt_in(self):
        with (
            patch.object(main, "DRY_RUN_ENABLED", False),
            patch.object(main, "SEND_ENABLED", False),
            patch.object(main, "GATEWAY_USERNAME", "configured-user"),
            patch.object(main, "GATEWAY_PASSWORD", "configured-password"),
        ):
            self.assertFalse(main.validate_runtime_config())

    def test_live_mode_accepts_complete_explicit_configuration(self):
        with (
            patch.object(main, "DRY_RUN_ENABLED", False),
            patch.object(main, "SEND_ENABLED", True),
            patch.object(main, "GATEWAY_USERNAME", "configured-user"),
            patch.object(main, "GATEWAY_PASSWORD", "configured-password"),
        ):
            self.assertTrue(main.validate_runtime_config())


if __name__ == "__main__":
    unittest.main()

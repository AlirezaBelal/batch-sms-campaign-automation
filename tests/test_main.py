import contextlib
from dataclasses import replace
from decimal import Decimal
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from campaign import CampaignResult
from config import Settings, load_settings
import main


class RuntimeConfigurationTests(unittest.TestCase):
    def live_settings(self):
        return Settings(
            dry_run=False,
            send_enabled=True,
            username="fixture",
            password="fixture",
            consent_scope="updates",
            exclusions_file="private/exclusions.csv",
            unit_cost=Decimal("1"),
            max_cost=Decimal("10"),
        )

    def test_dry_run_takes_precedence_over_live_send_switch(self):
        settings = load_settings({"SMS_DRY_RUN": "true", "SMS_SEND_ENABLED": "true"})
        self.assertTrue(settings.dry_run)
        with (
            patch("main.load_settings", return_value=settings),
            patch(
                "requests.sessions.Session.request",
                side_effect=AssertionError("No network"),
            ),
        ):
            with contextlib.redirect_stdout(io.StringIO()) as stdout:
                self.assertEqual(main.main([]), 0)
        self.assertEqual(json.loads(stdout.getvalue().splitlines()[-1])["simulated"], 2)
        with self.assertRaises(ValueError):
            settings.validate(live=True)

    def test_live_mode_requires_gateway_credentials(self):
        with self.assertRaises(ValueError):
            replace(self.live_settings(), username="").validate(live=True)

    def test_live_mode_requires_explicit_send_opt_in(self):
        with self.assertRaises(ValueError):
            replace(self.live_settings(), send_enabled=False).validate(live=True)

    def test_live_mode_accepts_complete_explicit_configuration(self):
        self.live_settings().validate(live=True)

    def test_defaults_and_strict_execution_flags(self):
        settings = load_settings({})
        self.assertTrue(settings.dry_run)
        self.assertFalse(settings.send_enabled)
        self.assertTrue(settings.endpoint.endswith("/3rdparty/v1/messages"))
        for name in ["SMS_DRY_RUN", "SMS_SEND_ENABLED"]:
            for value in ["yes", "1", "", "typo"]:
                with (
                    self.subTest(name=name, value=value),
                    self.assertRaises(ValueError),
                ):
                    load_settings({name: value})
        self.assertFalse(load_settings({"SMS_DRY_RUN": "false"}).dry_run)
        self.assertTrue(load_settings({"SMS_SEND_ENABLED": "true"}).send_enabled)

    def test_invalid_numeric_configuration_is_redacted(self):
        for name, value in [
            ("SMS_DELAY_BETWEEN_SMS", "-1"),
            ("SMS_DELAY_BETWEEN_SMS", "nan"),
            ("SMS_REQUEST_TIMEOUT", "inf"),
            ("SMS_REQUEST_TIMEOUT", "0"),
            ("SMS_MAX_RECIPIENTS", "1001"),
            ("SMS_MAX_RECIPIENTS", "0"),
            ("SMS_MAX_RECIPIENTS", "private-value"),
            ("SMS_ESTIMATED_UNIT_COST", "NaN"),
            ("SMS_MAX_ESTIMATED_COST", "-2"),
            ("SMS_ESTIMATED_UNIT_COST", "secret"),
            ("SMS_FIRST_NAME_COLUMN", "selected_phone"),
        ]:
            with (
                self.subTest(name=name, value=value),
                self.assertRaises(ValueError) as caught,
            ):
                load_settings({name: value})
            self.assertNotIn("private-value", str(caught.exception))
            self.assertNotIn("secret", str(caught.exception))

    def test_live_endpoint_must_be_tls_and_credentials_not_in_url(self):
        for url in [
            "http://localhost/messages",
            "https://u:p@gateway.example/messages",
            "https://gateway.example/messages?token=private",
            "https://gateway.example/messages#fragment",
            "not-url",
        ]:
            with self.subTest(url=url), self.assertRaises(ValueError):
                replace(self.live_settings(), endpoint=url).validate(live=True)
        with self.assertRaises(ValueError):
            replace(self.live_settings(), unit_cost=Decimal("0")).validate(live=True)

    def test_main_cli_never_sends_without_explicit_authorization(self):
        settings = replace(
            self.live_settings(),
            input_file="examples/contacts.example.csv",
            consent_scope="demo",
            exclusions_file="",
        )
        with (
            patch("main.load_settings", return_value=settings),
            patch(
                "requests.sessions.Session.request",
                side_effect=AssertionError("No network"),
            ) as http,
        ):
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main.main([]), 0)
                self.assertEqual(main.main(["--live"]), 2)
            http.assert_not_called()

    def test_main_summary_and_live_arguments_are_forwarded(self):
        result = CampaignResult(accepted_or_queued=1)
        with (
            patch("main.load_settings", return_value=self.live_settings()),
            patch("main.CampaignRunner") as runner,
        ):
            runner.return_value.run.return_value = result
            with contextlib.redirect_stdout(io.StringIO()) as stdout:
                self.assertEqual(
                    main.main(
                        [
                            "--live",
                            "--campaign-id",
                            "fixture",
                            "--confirm-campaign",
                            "fixture",
                        ]
                    ),
                    0,
                )
            arguments = runner.return_value.run.call_args.kwargs
            self.assertEqual(
                (
                    arguments["live"],
                    arguments["campaign_id"],
                    arguments["confirm_campaign"],
                ),
                (True, "fixture", "fixture"),
            )
            self.assertEqual(json.loads(stdout.getvalue())["accepted_or_queued"], 1)

    def test_missing_file_and_invalid_configuration_exit_nonzero_without_leak(self):
        for setting in [
            replace(Settings(), input_file="private-name-does-not-exist.csv"),
            Settings(template="{secret}"),
        ]:
            with patch("main.load_settings", return_value=setting):
                with (
                    self.assertLogs("main", level="ERROR") as logs,
                    contextlib.redirect_stdout(io.StringIO()) as stdout,
                ):
                    self.assertEqual(main.main([]), 2)
                combined = str(logs.output) + stdout.getvalue()
                self.assertNotIn("private-name", combined)
                self.assertNotIn("{secret}", combined)

    def test_interruption_and_disk_failure_have_unknown_exit(self):
        for error in [KeyboardInterrupt(), OSError("sensitive-file-path")]:
            with (
                patch("main.load_settings", return_value=Settings()),
                patch("main.CampaignRunner") as runner,
            ):
                runner.return_value.run.side_effect = error
                with (
                    self.assertLogs("main", level="ERROR") as logs,
                    contextlib.redirect_stdout(io.StringIO()),
                ):
                    self.assertEqual(main.main([]), 5)
                self.assertNotIn("sensitive-file-path", str(logs.output))

    def test_exit_code_semantics(self):
        for result, expected in [
            (CampaignResult(), 0),
            (CampaignResult(invalid_records=1), 2),
            (CampaignResult(accepted_or_queued=1, rejected=1), 3),
            (CampaignResult(rejected=1), 4),
            (CampaignResult(unknown=1), 5),
            (CampaignResult(previous_unknown=1), 5),
            (CampaignResult(previous_accepted=1, previous_rejected=1), 3),
            (CampaignResult(previous_rejected=1), 4),
        ]:
            self.assertEqual(main.result_exit_code(result), expected)

    def test_real_cli_dry_run_and_missing_input_exit_status(self):
        env = {k: v for k, v in os.environ.items() if not k.startswith("SMS_")}
        env.update({"SMS_DRY_RUN": "true", "SMS_SEND_ENABLED": "false"})
        # A sitecustomize hook forbids socket connections in the entire child process.
        with tempfile.TemporaryDirectory() as temporary:
            Path(temporary, "sitecustomize.py").write_text(
                'import socket\ndef blocked(*a, **k): raise AssertionError("Network forbidden")\nsocket.socket.connect = blocked\n'
            )
            env["PYTHONPATH"] = temporary
            run = subprocess.run(
                [sys.executable, "main.py"],
                env=env,
                capture_output=True,
                text=True,
                timeout=10,
            )
            self.assertEqual(run.returncode, 0, run.stderr)
            summary = json.loads(run.stdout.splitlines()[-1])
            self.assertEqual(
                (summary["simulated"], summary["accepted_or_queued"]), (2, 0)
            )
            env["SMS_CSV_FILE_PATH"] = "absent-private-input.csv"
            run = subprocess.run(
                [sys.executable, "main.py"],
                env=env,
                capture_output=True,
                text=True,
                timeout=10,
            )
            self.assertEqual(run.returncode, 2)
            self.assertNotIn("absent-private-input", run.stdout + run.stderr)

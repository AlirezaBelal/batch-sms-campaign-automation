import json
import tempfile
import unittest
from dataclasses import replace
from decimal import Decimal
from pathlib import Path
from unittest.mock import Mock, patch

import requests

from campaign import CampaignRunner, CampaignResult
from config import Settings
from manifest import CampaignManifest
from sms_service import SMSGatewayClient
from sms_service.sms_sender import Submission

HEADER = "first_name_per,selected_phone,consent_status,consent_scope,consent_source,consent_at\n"
ROW = "Sample,09000000000,granted,updates,synthetic-fixture,2020-01-01T00:00:00Z\n"


class CampaignRunnerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)
        self.csv = self.path / "input.csv"
        self.csv.write_text(HEADER + ROW, encoding="utf-8")
        self.exclusions = self.path / "exclusions.csv"
        self.exclusions.write_text("phone\n", encoding="utf-8")
        self.settings = Settings(
            input_file=str(self.csv),
            consent_scope="updates",
            exclusions_file=str(self.exclusions),
            manifest_dir=str(self.path / "state"),
            dry_run=False,
            send_enabled=True,
            username="fixture",
            password="fixture",
            unit_cost=Decimal("2"),
            max_cost=Decimal("100"),
        )
        self.gateway = SMSGatewayClient(
            "https://gateway.example/messages", "fixture", "fixture", "Hello {name}"
        )
        self.addCleanup(self.gateway.session.close)
        self.gateway.submit_message = Mock(
            return_value=Submission("accepted", "acknowledged")
        )

    def run_campaign(self, live=False, settings=None, campaign_id="fixture", **kwargs):
        return CampaignRunner(self.gateway, settings or self.settings).run(
            live=live, campaign_id=campaign_id, confirm_campaign=campaign_id, **kwargs
        )

    def test_processes_valid_rows_and_tracks_api_acceptance(self):
        result = self.run_campaign(live=True)
        self.assertEqual(
            (result.total_input, result.accepted_or_queued, result.api_acceptance_rate),
            (1, 1, 100),
        )
        self.gateway.submit_message.assert_called_once_with(
            "+989000000000", "Hello Sample"
        )

    def test_counts_missing_phone_as_invalid_without_submitting(self):
        self.csv.write_text(HEADER + ROW.replace("09000000000", ""))
        result = self.run_campaign()
        self.assertEqual(result.invalid_records, 1)
        self.assertEqual(result.api_acceptance_rate, 0)
        with self.assertRaises(ValueError):
            self.run_campaign(live=True)
        self.gateway.submit_message.assert_not_called()

    def test_dry_run_validates_and_renders_without_gateway_submission(self):
        with patch(
            "requests.sessions.Session.request",
            side_effect=AssertionError("No network"),
        ):
            result = self.run_campaign()
        self.assertEqual(
            (result.simulated, result.eligible_recipients, result.estimated_segments),
            (1, 1, 1),
        )
        self.gateway.submit_message.assert_not_called()
        self.assertFalse((self.path / "state").exists())

    def test_dry_run_counts_validation_failures_without_submitting(self):
        self.csv.write_text(HEADER + ROW.replace("09000000000", "invalid"))
        self.assertEqual(self.run_campaign().invalid_records, 1)
        self.gateway.submit_message.assert_not_called()

    def test_unexpected_error_does_not_include_recipient_data(self):
        self.gateway.render_message = Mock(
            side_effect=RuntimeError("SensitiveName 09000000000")
        )
        result = self.run_campaign()
        self.assertEqual(result.invalid_records, 1)
        self.assertNotIn("SensitiveName", json.dumps(result.summary()))

    def test_normalized_duplicates_use_first_message_and_conservative_consent(self):
        self.csv.write_text(
            HEADER + ROW + ROW.replace("Sample,09000000000", "Other,+989000000000")
        )
        result = self.run_campaign(live=True)
        self.assertEqual(
            (
                result.valid_records,
                result.skipped_duplicates,
                result.accepted_or_queued,
            ),
            (2, 1, 1),
        )
        self.csv.write_text(HEADER + ROW + ROW.replace("granted", "withdrawn"))
        result = self.run_campaign()
        self.assertEqual(
            (result.eligible_recipients, result.skipped_without_consent), (0, 1)
        )

    def test_missing_consent_legacy_csv_is_previewed_but_never_sent(self):
        self.csv.write_text("first_name_per,selected_phone\nSample,09000000000\n")
        self.assertEqual(self.run_campaign().skipped_without_consent, 1)
        with self.assertRaises(ValueError):
            self.run_campaign(live=True)
        self.gateway.submit_message.assert_not_called()

    def test_scope_source_date_and_status_are_required(self):
        for value in [
            ROW.replace("updates", "other"),
            ROW.replace("synthetic-fixture", ""),
            ROW.replace("2020-01-01T00:00:00Z", "2999-01-01T00:00:00Z"),
            ROW.replace("2020-01-01T00:00:00Z", "invalid"),
            ROW.replace("2020-01-01T00:00:00Z", "2020-01-01"),
            ROW.replace("granted", "true"),
        ]:
            with self.subTest(row=value):
                self.csv.write_text(HEADER + value)
                self.assertEqual(self.run_campaign().skipped_without_consent, 1)

    def test_opt_out_overrides_consent_after_normalization(self):
        self.exclusions.write_text("phone\n+۹۸۹۰۰۰۰۰۰۰۰۰\n", encoding="utf-8")
        result = self.run_campaign()
        self.assertEqual((result.skipped_excluded, result.simulated), (1, 0))
        with self.assertRaises(ValueError):
            self.run_campaign(live=True)
        self.gateway.submit_message.assert_not_called()

    def test_invalid_exclusion_or_schema_aborts_before_sending(self):
        for text in ["phone\ninvalid\n", "wrong\n09000000000\n"]:
            self.exclusions.write_text(text)
            with self.assertRaises(ValueError):
                self.run_campaign(live=True)
        self.gateway.submit_message.assert_not_called()

    def test_preflight_limits_are_atomic_and_cost_counts_unicode_segments(self):
        self.csv.write_text(HEADER + ROW + ROW.replace("09000000000", "09000000001"))
        with self.assertRaises(ValueError):
            self.run_campaign(
                live=True, settings=replace(self.settings, max_recipients=1)
            )
        self.gateway.message_template = "س" * 71
        result = self.run_campaign()
        self.assertEqual((result.estimated_segments, result.estimated_cost), (4, "8"))
        with self.assertRaises(ValueError):
            self.run_campaign(
                live=True, settings=replace(self.settings, max_cost=Decimal("7"))
            )
        with self.assertRaises(ValueError):
            self.run_campaign(live=True, settings=replace(self.settings, delay=3600))
        self.gateway.submit_message.assert_not_called()

    def test_requires_live_switches_confirmation_and_non_example_input(self):
        for settings in [
            replace(self.settings, dry_run=True),
            replace(self.settings, send_enabled=False),
            replace(self.settings, exclusions_file=""),
            replace(self.settings, consent_scope="demo"),
        ]:
            with self.assertRaises(ValueError):
                self.run_campaign(live=True, settings=settings)
        with self.assertRaises(ValueError):
            CampaignRunner(self.gateway, self.settings).run(
                live=True, campaign_id="fixture", confirm_campaign="wrong"
            )
        sample = self.path / "contacts.example.csv"
        sample.write_text(HEADER + ROW)
        with self.assertRaises(ValueError):
            self.run_campaign(
                live=True, settings=replace(self.settings, input_file=str(sample))
            )
        self.gateway.submit_message.assert_not_called()

    def test_safe_rerun_skips_accepted_without_resending(self):
        self.run_campaign(live=True)
        result = self.run_campaign(live=True)
        self.assertEqual(
            (
                result.skipped_previous,
                result.previous_accepted,
                result.accepted_or_queued,
            ),
            (1, 1, 0),
        )
        self.gateway.submit_message.assert_called_once()
        journal = (self.path / "state" / "fixture.json").read_text()
        for sensitive in [
            "09000000000",
            "+989000000000",
            "Hello Sample",
            "synthetic-fixture",
        ]:
            self.assertNotIn(sensitive, journal)

    def test_ambiguous_result_stops_and_is_not_retried(self):
        self.csv.write_text(HEADER + ROW + ROW.replace("09000000000", "09000000001"))
        self.gateway.submit_message.return_value = Submission(
            "unknown", "transport_error", True
        )
        first = self.run_campaign(live=True)
        self.assertEqual((first.unknown, first.not_attempted), (1, 1))
        second = self.run_campaign(live=True)
        self.assertEqual((second.previous_unknown, second.skipped_previous), (1, 1))
        self.assertEqual(second.not_attempted, 1)
        self.gateway.submit_message.assert_called_once()

    def test_rejected_result_is_retained_and_stops_campaign(self):
        self.gateway.submit_message.return_value = Submission(
            "rejected", "rate_limited", True
        )
        self.assertEqual(self.run_campaign(live=True).rejected, 1)
        self.assertEqual(self.run_campaign(live=True).previous_rejected, 1)
        self.gateway.submit_message.assert_called_once()

    def test_interruption_leaves_pending_and_resume_does_not_resend(self):
        self.gateway.submit_message.side_effect = KeyboardInterrupt
        with self.assertRaises(KeyboardInterrupt):
            self.run_campaign(live=True)
        result = self.run_campaign(live=True)
        self.assertEqual(result.previous_unknown, 1)
        self.gateway.submit_message.assert_called_once()

    def test_unexpected_gateway_exception_or_contract_is_unknown(self):
        self.gateway.submit_message.side_effect = RuntimeError("secret endpoint")
        self.assertEqual(self.run_campaign(live=True).unknown, 1)
        self.gateway.submit_message.side_effect = None
        self.gateway.submit_message.return_value = (True, {})
        self.assertEqual(self.run_campaign(live=True, campaign_id="other").unknown, 1)

    def test_changed_plan_lock_and_corrupt_journal_fail_closed(self):
        self.run_campaign(live=True)
        self.csv.write_text(HEADER + ROW.replace("Sample", "Changed"))
        with self.assertRaises(ValueError):
            self.run_campaign(live=True)
        self.assertFalse((self.path / "state" / "fixture.lock").exists())
        (self.path / "state" / "fixture.json").write_text("{broken")
        with self.assertRaises(ValueError):
            self.run_campaign(live=True)
        (self.path / "state" / "fixture.lock").touch()
        with self.assertRaises(FileExistsError):
            self.run_campaign(live=True)
        self.gateway.submit_message.assert_called_once()

    def test_pacing_only_between_new_submissions(self):
        self.csv.write_text(HEADER + ROW + ROW.replace("09000000000", "09000000001"))
        with patch("campaign.time.sleep") as sleep:
            self.run_campaign(live=True)
            sleep.assert_called_once_with(2)

    def test_input_errors_are_not_successful_empty_campaigns(self):
        for text in [
            "",
            "wrong,headers\nx,y\n",
            HEADER + ROW.rstrip() + ",extra\n",
            "first_name_per,selected_phone,selected_phone\na,b,c\n",
            HEADER + "short\n",
            HEADER + '"unclosed',
        ]:
            with self.subTest(text=text):
                self.csv.write_text(text)
                with self.assertRaises(ValueError):
                    self.run_campaign()
        self.csv.write_bytes(b"\xff\xfe")
        with self.assertRaises(ValueError):
            self.run_campaign()
        self.csv.unlink()
        with self.assertRaises(ValueError):
            self.run_campaign()

    def test_utf8_bom_and_unicode_personalization(self):
        self.csv.write_text(
            "\ufeff"
            + HEADER
            + ROW.replace("Sample", "علی").replace("09000000000", "۰۹۰۰۰۰۰۰۰۰۰"),
            encoding="utf-8",
        )
        self.run_campaign(live=True)
        self.gateway.submit_message.assert_called_once_with(
            "+989000000000", "Hello علی"
        )

    def test_input_bounds(self):
        with patch("campaign.Path.stat") as stat:
            stat.return_value.st_size = 6 * 1024 * 1024
            with self.assertRaises(ValueError):
                self.run_campaign()
        self.csv.write_text(HEADER + ROW * 10001)
        with self.assertRaises(ValueError):
            self.run_campaign()

    def test_manifest_identifier_and_atomic_write_failure(self):
        with self.assertRaises(ValueError):
            CampaignManifest(str(self.path), "../bad", "binding")
        with patch("manifest.os.replace", side_effect=OSError("disk failure")):
            with self.assertRaises(OSError):
                with CampaignManifest(str(self.path / "broken"), "fixture", "binding"):
                    pass
        self.assertFalse((self.path / "broken" / "fixture.lock").exists())
        self.assertEqual(list((self.path / "broken").glob("*.tmp")), [])

    def test_acceptance_denominator_excludes_input_and_simulation(self):
        result = CampaignResult(
            accepted_or_queued=1,
            rejected=1,
            unknown=2,
            invalid_records=50,
            simulated=40,
        )
        self.assertEqual(result.api_acceptance_rate, 25)


class SMSGatewayClientTests(unittest.TestCase):
    def make_client(self, **kwargs):
        client = SMSGatewayClient(
            "https://gateway.example/messages",
            "test-user",
            "test-password",
            kwargs.get("template", "Hello {name}"),
            kwargs.get("timeout", 3),
            live_authorized=True,
        )
        self.addCleanup(client.session.close)
        return client

    def response(self, status=202, body=None):
        return Mock(
            status_code=status,
            json=Mock(
                return_value=body
                if body is not None
                else {"state": "Pending", "id": "fixture-id"}
            ),
        )

    def test_submit_message_normalizes_recipient_and_redacts_logs(self):
        client = self.make_client()
        client.session.post = Mock(return_value=self.response())
        with self.assertLogs("sms_service.sms_sender", level="INFO") as captured:
            result = client.submit_message("09000000000", "Hello Sample")
        self.assertEqual(result.status, "accepted")
        client.session.post.assert_called_once_with(
            "https://gateway.example/messages",
            json={
                "textMessage": {"text": "Hello Sample"},
                "phoneNumbers": ["+989000000000"],
                "ttl": 3600,
            },
            headers={"Content-Type": "application/json"},
            auth=("test-user", "test-password"),
            timeout=3,
            allow_redirects=False,
        )
        self.assertNotIn("09000000000", str(captured.output))
        self.assertNotIn("Hello Sample", str(captured.output))
        self.assertFalse(client.session.trust_env)

    def test_timeout_returns_unknown_without_raising_or_retrying(self):
        client = self.make_client()
        for exception in [
            requests.Timeout,
            requests.ConnectionError,
            requests.RequestException,
        ]:
            client.session.post = Mock(
                side_effect=exception("https://secret.example/?password=private")
            )
            with self.assertLogs("sms_service.sms_sender", level="INFO") as logs:
                result = client.submit_message("09000000000", "Private message")
            self.assertEqual(result.status, "unknown")
            self.assertTrue(result.stop)
            client.session.post.assert_called_once()
            self.assertNotIn("private", str(logs.output))
            self.assertNotIn("secret.example", str(logs.output))

    def test_rejected_response_does_not_log_provider_body(self):
        client = self.make_client()
        client.session.post = Mock(
            return_value=self.response(429, {"error": "private phone"})
        )
        with self.assertLogs("sms_service.sms_sender", level="INFO") as logs:
            result = client.submit_message("09000000000", "Hello")
        self.assertEqual((result.status, result.reason), ("rejected", "rate_limited"))
        self.assertNotIn("private phone", str(logs.output))

    def test_http_outcomes_and_schema_validation(self):
        for code, expected in [
            (400, "rejected"),
            (401, "rejected"),
            (403, "rejected"),
            (404, "rejected"),
            (429, "rejected"),
            (500, "unknown"),
            (503, "unknown"),
            (302, "unknown"),
        ]:
            with self.subTest(code=code):
                self.assertEqual(
                    SMSGatewayClient._classify(self.response(code)).status, expected
                )
        for body in [
            {"id": "x", "state": []},
            {"id": "x", "state": {}},
            [],
            {},
            {"id": "x"},
            {"id": "", "state": "Pending"},
            {"id": 12, "state": "Pending"},
            {"id": "x", "state": "new-state"},
            {"state": "Pending"},
        ]:
            self.assertEqual(
                SMSGatewayClient._classify(self.response(body=body)).status, "unknown"
            )
        response = self.response()
        response.json.side_effect = ValueError("sensitive response")
        self.assertEqual(
            SMSGatewayClient._classify(response).reason, "malformed_response"
        )
        for state in ["Pending", "Processed", "Sent", "Delivered"]:
            self.assertEqual(
                SMSGatewayClient._classify(
                    self.response(body={"id": "x", "state": state})
                ).status,
                "accepted",
            )
        for state in ["Failed", "Cancelled"]:
            self.assertEqual(
                SMSGatewayClient._classify(
                    self.response(body={"id": "x", "state": state})
                ).status,
                "rejected",
            )

    def test_invalid_template_name_message_and_timeout(self):
        for template in [
            "{bad}",
            "{name.__class__}",
            "{name!r}",
            "{name:>20}",
            "{",
            "",
            "x" * 481,
        ]:
            with self.subTest(template=template), self.assertRaises(ValueError):
                self.make_client(template=template)
        for timeout in [0, -1, float("nan"), float("inf"), 61]:
            with self.assertRaises(ValueError):
                self.make_client(timeout=timeout)
        client = self.make_client()
        for name in ["line\nbreak", "x" * 101, "\x00"]:
            with self.assertRaises(ValueError):
                client.render_message(name)
        self.assertEqual(client.render_message("علی"), "Hello علی")


class DirectGatewaySafetyTests(unittest.TestCase):
    def test_default_client_refuses_http_submission(self):
        client = SMSGatewayClient(
            "https://gateway.example/messages", "", "", "Hello {name}"
        )
        self.addCleanup(client.session.close)
        with patch.object(client.session, "post") as post:
            with self.assertRaises(ValueError):
                client.submit_message("09000000000", "Hello")
            post.assert_not_called()


class ResumeAfterSafePauseTests(unittest.TestCase):
    setUp = CampaignRunnerTests.setUp
    run_campaign = CampaignRunnerTests.run_campaign

    def test_interrupt_between_accepted_requests_resumes_only_remaining(self):
        self.csv.write_text(HEADER + ROW + ROW.replace("09000000000", "09000000001"))
        with patch("campaign.time.sleep", side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                self.run_campaign(live=True)
        result = self.run_campaign(live=True)
        self.assertEqual((result.previous_accepted, result.accepted_or_queued), (1, 1))
        self.assertEqual(self.gateway.submit_message.call_count, 2)

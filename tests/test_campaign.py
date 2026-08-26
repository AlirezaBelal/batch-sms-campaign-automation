import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

import requests

from campaign import CampaignRunner
from sms_service import SMSGatewayClient


class FakeGateway:
    def __init__(self):
        self.submissions = []
        self.validated_recipients = []

    def render_message(self, recipient_name):
        return f"Hello {recipient_name}"

    def validate_recipient(self, phone_number):
        if phone_number == "invalid":
            raise ValueError("Invalid phone number")
        self.validated_recipients.append(phone_number)
        return phone_number

    def submit_message(self, phone_number, message):
        self.validate_recipient(phone_number)
        self.submissions.append((phone_number, message))
        return True, {"state": "Pending"}


class ExplodingGateway(FakeGateway):
    def render_message(self, recipient_name):
        raise RuntimeError(f"sensitive-recipient={recipient_name}")


class CampaignRunnerTests(unittest.TestCase):
    def test_processes_valid_rows_and_tracks_api_acceptance(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            input_file = Path(temp_dir) / "contacts.csv"
            input_file.write_text(
                "first_name_per,selected_phone\nAli,09121234567\nSara,09351234567\n",
                encoding="utf-8",
            )

            gateway = FakeGateway()
            campaign = CampaignRunner(
                gateway=gateway,
                input_file=str(input_file),
                recipient_name_column="first_name_per",
                recipient_phone_column="selected_phone",
                request_delay_seconds=0,
            )

            result = campaign.run()

            self.assertEqual(result.total_processed, 2)
            self.assertEqual(result.accepted_or_queued, 2)
            self.assertEqual(result.simulated, 0)
            self.assertEqual(result.failed, 0)
            self.assertEqual(len(gateway.submissions), 2)

    def test_counts_missing_phone_as_failed_without_submitting(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            input_file = Path(temp_dir) / "contacts.csv"
            input_file.write_text(
                "first_name_per,selected_phone\nAli,\n",
                encoding="utf-8",
            )

            gateway = FakeGateway()
            campaign = CampaignRunner(
                gateway=gateway,
                input_file=str(input_file),
                recipient_name_column="first_name_per",
                recipient_phone_column="selected_phone",
            )

            result = campaign.run()

            self.assertEqual(result.total_processed, 1)
            self.assertEqual(result.accepted_or_queued, 0)
            self.assertEqual(result.simulated, 0)
            self.assertEqual(result.failed, 1)
            self.assertEqual(gateway.submissions, [])

    def test_dry_run_validates_and_renders_without_gateway_submission(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            input_file = Path(temp_dir) / "contacts.csv"
            input_file.write_text(
                "first_name_per,selected_phone\nAli,09121234567\nSara,09351234567\n",
                encoding="utf-8",
            )

            gateway = FakeGateway()
            campaign = CampaignRunner(
                gateway=gateway,
                input_file=str(input_file),
                recipient_name_column="first_name_per",
                recipient_phone_column="selected_phone",
                dry_run=True,
            )

            result = campaign.run()

            self.assertEqual(result.total_processed, 2)
            self.assertEqual(result.accepted_or_queued, 0)
            self.assertEqual(result.simulated, 2)
            self.assertEqual(result.failed, 0)
            self.assertEqual(gateway.submissions, [])
            self.assertEqual(len(gateway.validated_recipients), 2)

    def test_dry_run_counts_validation_failures_without_submitting(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            input_file = Path(temp_dir) / "contacts.csv"
            input_file.write_text(
                "first_name_per,selected_phone\nAli,invalid\n",
                encoding="utf-8",
            )

            gateway = FakeGateway()
            campaign = CampaignRunner(
                gateway=gateway,
                input_file=str(input_file),
                recipient_name_column="first_name_per",
                recipient_phone_column="selected_phone",
                dry_run=True,
            )

            result = campaign.run()

            self.assertEqual(result.total_processed, 1)
            self.assertEqual(result.simulated, 0)
            self.assertEqual(result.failed, 1)
            self.assertEqual(gateway.submissions, [])

    def test_unexpected_error_logs_do_not_include_recipient_data(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            input_file = Path(temp_dir) / "contacts.csv"
            input_file.write_text(
                "first_name_per,selected_phone\nHighlySensitiveName,09121234567\n",
                encoding="utf-8",
            )

            campaign = CampaignRunner(
                gateway=ExplodingGateway(),
                input_file=str(input_file),
                recipient_name_column="first_name_per",
                recipient_phone_column="selected_phone",
            )

            with self.assertLogs("campaign", level="ERROR") as captured:
                result = campaign.run()

            log_output = "\n".join(captured.output)
            self.assertEqual(result.failed, 1)
            self.assertIn("RuntimeError", log_output)
            self.assertNotIn("HighlySensitiveName", log_output)
            self.assertNotIn("09121234567", log_output)
            self.assertNotIn("sensitive-recipient", log_output)


class SMSGatewayClientTests(unittest.TestCase):
    def make_client(self):
        return SMSGatewayClient(
            endpoint="https://gateway.example/messages",
            username="test-user",
            password="test-password",
            message_template="Hello {name}",
            timeout_seconds=3,
        )

    def test_submit_message_normalizes_recipient_and_masks_logs(self):
        client = self.make_client()
        response = Mock()
        response.status_code = 202
        response.json.return_value = {"state": "Pending", "id": "example-id"}
        response.text = ""
        client.session.post = Mock(return_value=response)

        with self.assertLogs("sms_service.sms_sender", level="INFO") as captured:
            accepted, response_data = client.submit_message("09121234567", "Hello Ali")

        self.assertTrue(accepted)
        self.assertEqual(response_data["state"], "Pending")
        client.session.post.assert_called_once_with(
            "https://gateway.example/messages",
            json={"message": "Hello Ali", "phoneNumbers": ["+989121234567"]},
            headers={"Content-Type": "application/json"},
            auth=("test-user", "test-password"),
            timeout=3,
        )

        log_output = "\n".join(captured.output)
        self.assertIn("***4567", log_output)
        self.assertNotIn("09121234567", log_output)
        self.assertNotIn("+989121234567", log_output)

    def test_timeout_returns_failure_without_raising(self):
        client = self.make_client()
        client.session.post = Mock(side_effect=requests.exceptions.Timeout())

        with self.assertLogs("sms_service.sms_sender", level="ERROR") as captured:
            accepted, detail = client.submit_message("09121234567", "Hello Ali")

        self.assertFalse(accepted)
        self.assertEqual(detail, "Request timed out")
        self.assertNotIn("09121234567", "\n".join(captured.output))

    def test_rejected_response_does_not_log_full_recipient(self):
        client = self.make_client()
        response = Mock()
        response.status_code = 429
        response.text = "rate limited"
        client.session.post = Mock(return_value=response)

        with self.assertLogs("sms_service.sms_sender", level="ERROR") as captured:
            accepted, detail = client.submit_message("09121234567", "Hello Ali")

        self.assertFalse(accepted)
        self.assertEqual(detail, "rate limited")
        log_output = "\n".join(captured.output)
        self.assertIn("***4567", log_output)
        self.assertNotIn("09121234567", log_output)
        self.assertNotIn("+989121234567", log_output)


if __name__ == "__main__":
    unittest.main()

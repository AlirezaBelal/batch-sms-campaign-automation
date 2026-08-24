import tempfile
import unittest
from pathlib import Path

from campaign import CampaignRunner


class FakeGateway:
    def __init__(self):
        self.submissions = []

    def render_message(self, recipient_name):
        return f"Hello {recipient_name}"

    def submit_message(self, phone_number, message):
        self.submissions.append((phone_number, message))
        return True, {"state": "Pending"}


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
            self.assertEqual(result.failed, 1)
            self.assertEqual(gateway.submissions, [])


if __name__ == "__main__":
    unittest.main()

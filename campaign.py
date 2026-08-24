"""Campaign orchestration for controlled batch SMS submission."""

import csv
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, Tuple

logger = logging.getLogger(__name__)


class MessageGateway(Protocol):
    """Minimal interface required by the campaign runner."""

    def render_message(self, recipient_name: str) -> str:
        ...

    def submit_message(self, phone_number: str, message: str) -> Tuple[bool, object]:
        ...


@dataclass
class CampaignResult:
    """Aggregate submission outcome for one campaign run."""

    accepted_or_queued: int = 0
    failed: int = 0

    @property
    def total_processed(self) -> int:
        return self.accepted_or_queued + self.failed

    @property
    def api_acceptance_rate(self) -> float:
        if self.total_processed == 0:
            return 0.0
        return (self.accepted_or_queued / self.total_processed) * 100


class CampaignRunner:
    """Process a contact CSV and submit personalized messages through a gateway."""

    def __init__(
        self,
        gateway: MessageGateway,
        input_file: str,
        recipient_name_column: str,
        recipient_phone_column: str,
        request_delay_seconds: float = 0,
    ) -> None:
        self.gateway = gateway
        self.input_file = Path(input_file)
        self.recipient_name_column = recipient_name_column
        self.recipient_phone_column = recipient_phone_column
        self.request_delay_seconds = max(0.0, request_delay_seconds)

    def run(self) -> CampaignResult:
        """Execute one campaign run and return API submission counts."""
        result = CampaignResult()

        if not self.input_file.exists():
            logger.error("Campaign input file not found: %s", self.input_file)
            return result

        try:
            with self.input_file.open("r", encoding="utf-8", newline="") as contact_file:
                reader = csv.DictReader(contact_file)
                if not self._has_required_columns(reader.fieldnames):
                    return result

                for row_number, row in enumerate(reader, start=2):
                    self._process_row(row_number, row, result)
        except OSError as exc:
            logger.error("Unable to read campaign input file %s: %s", self.input_file, exc)

        return result

    def _has_required_columns(self, fieldnames) -> bool:
        if not fieldnames:
            logger.error("Campaign input file is empty: %s", self.input_file)
            return False

        required = {self.recipient_name_column, self.recipient_phone_column}
        missing = required.difference(fieldnames)
        if missing:
            logger.error("Missing required CSV columns: %s", ", ".join(sorted(missing)))
            return False

        return True

    def _process_row(self, row_number: int, row: dict, result: CampaignResult) -> None:
        try:
            recipient_name = (row.get(self.recipient_name_column) or "").strip()
            phone_number = (row.get(self.recipient_phone_column) or "").strip()

            if not phone_number:
                logger.warning("Row %s has no phone number; skipping", row_number)
                result.failed += 1
                return

            message = self.gateway.render_message(recipient_name)
            accepted_by_api, _ = self.gateway.submit_message(phone_number, message)

            if accepted_by_api:
                result.accepted_or_queued += 1
            else:
                result.failed += 1

            if self.request_delay_seconds:
                time.sleep(self.request_delay_seconds)
        except Exception as exc:
            logger.error("Failed to process row %s: %s", row_number, exc)
            result.failed += 1

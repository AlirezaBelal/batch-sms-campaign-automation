"""Bounded preflight, consent filtering and sequential campaign submission."""

import csv
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
import math
from pathlib import Path
import time

from manifest import CampaignManifest
from sms_service.sms_sender import Submission


@dataclass
class CampaignResult:
    total_input: int = 0
    valid_records: int = 0
    invalid_records: int = 0
    eligible_recipients: int = 0
    skipped_duplicates: int = 0
    skipped_without_consent: int = 0
    skipped_excluded: int = 0
    skipped_previous: int = 0
    previous_accepted: int = 0
    previous_rejected: int = 0
    previous_unknown: int = 0
    exclusion_file_changed: bool = False
    simulated: int = 0
    accepted_or_queued: int = 0
    rejected: int = 0
    unknown: int = 0
    not_attempted: int = 0
    estimated_segments: int = 0
    estimated_cost: str = "0"

    @property
    def api_acceptance_rate(self):
        attempted = self.accepted_or_queued + self.rejected + self.unknown
        return 100 * self.accepted_or_queued / attempted if attempted else 0.0

    def summary(self):
        return {
            **asdict(self),
            "api_acceptance_rate": round(self.api_acceptance_rate, 2),
        }


def _csv_rows(path, required):
    """Read only bounded UTF-8 CSVs, rejecting schema and row-shape ambiguity."""
    try:
        path = Path(path)
        if path.stat().st_size > 5 * 1024 * 1024:
            raise ValueError("CSV exceeds the 5 MiB input limit")
        with path.open(encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream, strict=True)
            fields = reader.fieldnames
            if (
                not fields
                or len(fields) != len(set(fields))
                or not required.issubset(fields)
            ):
                raise ValueError("CSV is empty or has invalid/missing headers")
            rows = []
            for row in reader:
                if None in row or any(v is None for v in row.values()):
                    raise ValueError("CSV contains an inconsistent row shape")
                rows.append(row)
                if len(rows) > 10000:
                    raise ValueError("CSV exceeds the 10000-record input limit")
            if not rows and required != {"phone"}:
                raise ValueError("Campaign CSV has no records")
            return rows
    except (OSError, UnicodeError, csv.Error):
        raise ValueError("Unable to read a valid UTF-8 CSV; details omitted") from None


def _exclusion_digest(path):
    """Hash the bounded suppression file without retaining its contents in memory."""
    digest = hashlib.sha256()
    try:
        with Path(path).open("rb") as stream:
            seen = 0
            while True:
                chunk = stream.read(65536)
                if not chunk:
                    break
                seen += len(chunk)
                if seen > 5 * 1024 * 1024:
                    raise ValueError("Exclusion CSV exceeds the input size limit")
                digest.update(chunk)
    except OSError:
        raise ValueError("Unable to verify exclusion CSV") from None
    return digest.digest()


def _consented(row, scope):
    if not scope or row.get("consent_status", "").strip() != "granted":
        return False
    if row.get("consent_scope", "").strip() != scope:
        return False
    if not 1 <= len(row.get("consent_source", "").strip()) <= 128:
        return False
    try:
        recorded = datetime.fromisoformat(
            row.get("consent_at", "").strip().replace("Z", "+00:00")
        )
        return recorded.tzinfo is not None and recorded <= datetime.now(timezone.utc)
    except ValueError:
        return False


class CampaignRunner:
    def __init__(self, gateway, settings):
        self.gateway = gateway
        self.settings = settings
        self.result = CampaignResult()
        self.recipients = []
        self.binding = ""
        self.exclusion_digest = None

    def prepare(self):
        """Complete all validation and render messages before any submission."""
        self.settings.validate()
        result = CampaignResult()
        exclusions = set()
        if self.settings.exclusions_file:
            self.exclusion_digest = _exclusion_digest(self.settings.exclusions_file)
            for row in _csv_rows(self.settings.exclusions_file, {"phone"}):
                try:
                    exclusions.add(
                        self.gateway.validate_recipient(row["phone"].strip())
                    )
                except ValueError:
                    raise ValueError(
                        "Exclusion CSV contains an invalid phone number"
                    ) from None
            if _exclusion_digest(self.settings.exclusions_file) != self.exclusion_digest:
                raise ValueError("Exclusion CSV changed during preflight")
        rows = _csv_rows(
            self.settings.input_file,
            {self.settings.name_column, self.settings.phone_column},
        )
        result.total_input = len(rows)
        unique = {}
        for row in rows:
            try:
                phone = self.gateway.validate_recipient(
                    row[self.settings.phone_column].strip()
                )
                message = self.gateway.render_message(
                    row[self.settings.name_column].strip()
                )
            except Exception:
                # Never echo names, numbers, templates or provider exception details.
                result.invalid_records += 1
                continue
            result.valid_records += 1
            eligible = _consented(row, self.settings.consent_scope)
            if phone in unique:
                result.skipped_duplicates += 1
                # A contradictory consent row denies permission for the entire number.
                unique[phone][1] = unique[phone][1] and eligible
            else:
                unique[phone] = [message, eligible]
        recipients = []
        for phone, (message, eligible) in unique.items():
            if phone in exclusions:
                result.skipped_excluded += 1
            elif not eligible:
                result.skipped_without_consent += 1
            else:
                recipients.append((phone, message))
        result.eligible_recipients = len(recipients)
        if len(recipients) > self.settings.max_recipients:
            raise ValueError("Eligible recipients exceed SMS_MAX_RECIPIENTS")
        # Conservative UCS-2/UTF-16 segment estimate, even for basic Latin text.
        for _, message in recipients:
            units = len(message.encode("utf-16-be")) // 2
            result.estimated_segments += 1 if units <= 70 else math.ceil(units / 67)
        result.estimated_cost = str(
            Decimal(result.estimated_segments) * self.settings.unit_cost
        )
        self.result, self.recipients = result, recipients
        self.binding = hashlib.sha256(
            json.dumps(
                [
                    self.settings.endpoint,
                    self.settings.consent_scope,
                    sorted(recipients),
                ],
                ensure_ascii=True,
                separators=(",", ":"),
            ).encode()
        ).hexdigest()
        return result

    def run(self, *, live=False, campaign_id="", confirm_campaign="", preflight=None):
        result = self.prepare()
        if preflight is not None:
            preflight(result.summary())
        if not live:
            result.simulated = len(self.recipients)
            return result
        self.settings.validate(live=True)
        if not campaign_id or confirm_campaign != campaign_id:
            raise ValueError(
                "Live execution requires matching --campaign-id and --confirm-campaign"
            )
        if Path(self.settings.input_file).name == "contacts.example.csv":
            raise ValueError(
                "The bundled example must never be used for live execution"
            )
        if result.invalid_records:
            raise ValueError("Live execution refuses invalid input records")
        if not self.recipients:
            raise ValueError("No eligible recipients; nothing may be submitted")
        if Decimal(result.estimated_cost) > self.settings.max_cost:
            raise ValueError(
                "Conservative cost estimate exceeds SMS_MAX_ESTIMATED_COST"
            )
        if len(self.recipients) * (self.settings.delay + self.settings.timeout) > 3600:
            raise ValueError("Campaign exceeds the conservative one-hour runtime bound")
        with CampaignManifest(
            self.settings.manifest_dir, campaign_id, self.binding
        ) as journal:
            pending = []
            for phone, message in self.recipients:
                previous = journal.status(phone)
                if previous:
                    result.skipped_previous += 1
                    if previous == "accepted":
                        result.previous_accepted += 1
                    elif previous == "rejected":
                        result.previous_rejected += 1
                    else:
                        result.previous_unknown += 1
                else:
                    pending.append((phone, message))
            if result.previous_unknown or result.previous_rejected:
                result.not_attempted = len(pending)
                return result
            for index, (phone, message) in enumerate(pending):
                # Withdrawals recorded while the campaign is running must stop
                # further submissions. This is a file-snapshot guard, not an
                # inbound STOP service or a guarantee against every race.
                try:
                    unchanged = (
                        _exclusion_digest(self.settings.exclusions_file)
                        == self.exclusion_digest
                    )
                except ValueError:
                    unchanged = False
                if not unchanged:
                    result.exclusion_file_changed = True
                    result.not_attempted = len(pending) - index
                    break
                # If the process dies after this fsync, the outcome remains conservatively unknown.
                journal.record(phone, "pending")
                try:
                    outcome = self.gateway.submit_message(phone, message)
                    if not isinstance(outcome, Submission) or outcome.status not in {
                        "accepted",
                        "rejected",
                        "unknown",
                    }:
                        outcome = Submission("unknown", "invalid_gateway_result", True)
                except Exception:
                    outcome = Submission("unknown", "unexpected_gateway_error", True)
                journal.record(phone, outcome.status)
                if outcome.status == "accepted":
                    result.accepted_or_queued += 1
                elif outcome.status == "rejected":
                    result.rejected += 1
                else:
                    result.unknown += 1
                if outcome.stop or outcome.status != "accepted":
                    result.not_attempted = len(pending) - index - 1
                    break
                if index < len(pending) - 1:
                    time.sleep(self.settings.delay)
        return result

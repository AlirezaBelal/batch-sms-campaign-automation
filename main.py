"""Safe-by-default CLI with explicit live authorization and aggregate JSON output."""

import argparse
import json
import logging
import sys

from campaign import CampaignRunner
from config import load_settings
from sms_service import SMSGatewayClient
from utils.logger import configure_logging

logger = logging.getLogger(__name__)


def result_exit_code(result):
    if result.unknown or result.previous_unknown:
        return 5
    if result.rejected or result.previous_rejected:
        return 3 if result.accepted_or_queued or result.previous_accepted else 4
    if result.invalid_records:
        return 2
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Preview a consent-based SMS campaign; no network by default"
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Request live execution (also requires both environment switches)",
    )
    parser.add_argument(
        "--campaign-id",
        default="",
        help="Stable ID; reuse it when resuming the same campaign",
    )
    parser.add_argument(
        "--confirm-campaign",
        default="",
        help="Repeat the reviewed campaign ID to authorize live submission",
    )
    args = parser.parse_args(argv)
    configure_logging()
    try:
        settings = load_settings()
        settings.validate(live=args.live)
        gateway = SMSGatewayClient(
            settings.endpoint,
            settings.username,
            settings.password,
            settings.template,
            settings.timeout,
            live_authorized=args.live,
        )
        runner = CampaignRunner(gateway, settings)
        try:
            result = runner.run(
                live=args.live,
                campaign_id=args.campaign_id,
                confirm_campaign=args.confirm_campaign,
                preflight=lambda data: print(
                    json.dumps(
                        {
                            "event": "preflight",
                            "mode": "live" if args.live else "dry_run",
                            **data,
                        }
                    ),
                    flush=True,
                ),
            )
        finally:
            gateway.session.close()
        code = result_exit_code(result)
        print(
            json.dumps(
                {
                    "event": "summary",
                    "mode": "live" if args.live else "dry_run",
                    "exit_code": code,
                    **result.summary(),
                }
            ),
            flush=True,
        )
        return code
    except ValueError:
        logger.error(
            "Invalid configuration or input; consult the documented schema and safety requirements"
        )
        print(
            json.dumps(
                {
                    "event": "error",
                    "classification": "invalid_configuration_or_input",
                    "exit_code": 2,
                }
            )
        )
        return 2
    except KeyboardInterrupt:
        logger.error(
            "Interrupted; reconcile the journal before any further live execution"
        )
        print(
            json.dumps(
                {
                    "event": "error",
                    "classification": "interrupted_unknown",
                    "exit_code": 5,
                }
            )
        )
        return 5
    except Exception:
        logger.error(
            "Operational failure; reconcile the journal before any further live execution"
        )
        print(
            json.dumps(
                {
                    "event": "error",
                    "classification": "operational_unknown",
                    "exit_code": 5,
                }
            )
        )
        return 5


if __name__ == "__main__":
    sys.exit(main())

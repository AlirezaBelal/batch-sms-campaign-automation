"""Console diagnostics contain aggregate counts and fixed classifications only."""

import logging


def configure_logging():
    logging.basicConfig(
        level=logging.INFO, format="%(levelname)s %(name)s: %(message)s"
    )
    # HTTP library debug logs may include endpoint URLs; never enable them here.
    for name in ("urllib3", "requests"):
        logging.getLogger(name).setLevel(logging.CRITICAL)

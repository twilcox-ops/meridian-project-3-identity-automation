"""Audit check: devices that are non-compliant or haven't checked in
(DECISIONS.md: "haven't checked in" threshold = 90 days).

Requires Device.Read.All (application); a widening specific to this check
(DECISIONS.md rule). Granted and admin-consented in Entra; not yet run
against the real tenant.
"""
import argparse
import logging
from datetime import datetime, timedelta, timezone

from graph_client import GraphClient

log = logging.getLogger("audit_devices")

DEVICES_PATH = "/devices"
SELECT = "displayName,operatingSystem,isCompliant,approximateLastSignInDateTime"
STALE_DAYS = 90


def flagged_devices(client: GraphClient):
    """Yield device records that are non-compliant or stale (no check-in for STALE_DAYS+)."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=STALE_DAYS)
    for record in client.get_paginated(DEVICES_PATH, params={"$select": SELECT}):
        last_check_in = record.get("approximateLastSignInDateTime")
        last_check_in_dt = datetime.fromisoformat(last_check_in.replace("Z", "+00:00")) if last_check_in else None
        stale = last_check_in_dt is None or last_check_in_dt < cutoff
        if record.get("isCompliant") is False or stale:
            yield record


def _demo():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    client = GraphClient()
    count = 0
    for record in flagged_devices(client):
        count += 1
        log.info(
            "flagged device: %s compliant=%s last_check_in=%s",
            record.get("displayName"), record.get("isCompliant"), record.get("approximateLastSignInDateTime"),
        )
    log.info("total flagged devices: %d", count)


if __name__ == "__main__":
    argparse.ArgumentParser(description="List non-compliant or stale devices.").parse_args()
    _demo()

"""Audit check: accounts that haven't signed in for 90+ days but still hold
a license (DECISIONS.md: threshold = signInActivity.lastSignInDateTime).

Requires AuditLog.Read.All (already granted for the MFA check) to read the
signInActivity property; User.Read.All covers assignedLicenses.
"""
import argparse
import logging
from datetime import datetime, timedelta, timezone

from graph_client import GraphClient

log = logging.getLogger("audit_stale_licensed")

USERS_PATH = "/users"
SELECT = "userPrincipalName,displayName,signInActivity,assignedLicenses"
STALE_DAYS = 90


def _last_sign_in(record) -> datetime | None:
    value = (record.get("signInActivity") or {}).get("lastSignInDateTime")
    return datetime.fromisoformat(value.replace("Z", "+00:00")) if value else None


def stale_licensed_accounts(client: GraphClient):
    """Yield user records that hold a license and haven't signed in for STALE_DAYS+."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=STALE_DAYS)
    for record in client.get_paginated(USERS_PATH, params={"$select": SELECT}):
        if not record.get("assignedLicenses"):
            continue
        last_sign_in = _last_sign_in(record)
        if last_sign_in is None or last_sign_in < cutoff:
            yield record


def _demo():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    client = GraphClient()
    count = 0
    for record in stale_licensed_accounts(client):
        count += 1
        log.info("stale but licensed: %s (%s)", record.get("userPrincipalName"), record.get("displayName"))
    log.info("total stale licensed accounts: %d", count)


if __name__ == "__main__":
    argparse.ArgumentParser(description="List licensed accounts stale 90+ days.").parse_args()
    _demo()

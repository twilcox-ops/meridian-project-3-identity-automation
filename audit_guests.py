"""Audit check: guest accounts and how long they've been in the tenant.

Inventory, not a filter -- every guest is returned with tenure_days added.
Requires only User.Read.All (already granted).
"""
import argparse
import logging
from datetime import datetime, timezone

from graph_client import GraphClient

log = logging.getLogger("audit_guests")

USERS_PATH = "/users"
SELECT = "userPrincipalName,displayName,createdDateTime,externalUserState"
FILTER = "userType eq 'Guest'"


def guest_accounts(client: GraphClient):
    """Yield guest user records with a computed tenure_days field."""
    now = datetime.now(timezone.utc)
    params = {"$select": SELECT, "$filter": FILTER}
    for record in client.get_paginated(USERS_PATH, params=params):
        created = record.get("createdDateTime")
        record["tenure_days"] = (
            (now - datetime.fromisoformat(created.replace("Z", "+00:00"))).days
            if created else None
        )
        yield record


def _demo():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    client = GraphClient()
    count = 0
    for record in guest_accounts(client):
        count += 1
        log.info(
            "guest: %s tenure=%sd state=%s",
            record.get("userPrincipalName"), record.get("tenure_days"), record.get("externalUserState"),
        )
    log.info("total guest accounts: %d", count)


if __name__ == "__main__":
    argparse.ArgumentParser(description="List guest accounts and their tenure.").parse_args()
    _demo()

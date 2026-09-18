"""Audit check: service principal credentials nearing expiry
(DECISIONS.md: threshold = 30 days; also catches already-expired creds).

Requires Application.Read.All (application) -- a widening specific to this
check (DECISIONS.md rule). Granted and admin-consented in Entra; not yet
run against the real tenant.
"""
import argparse
import logging
from datetime import datetime, timedelta, timezone

from graph_client import GraphClient

log = logging.getLogger("audit_sp_creds")

SP_PATH = "/servicePrincipals"
SELECT = "appId,displayName,keyCredentials,passwordCredentials"
NEARING_EXPIRY_DAYS = 30


def expiring_sp_credentials(client: GraphClient):
    """Yield (service_principal, credential, kind) for creds within NEARING_EXPIRY_DAYS."""
    cutoff = datetime.now(timezone.utc) + timedelta(days=NEARING_EXPIRY_DAYS)
    for sp in client.get_paginated(SP_PATH, params={"$select": SELECT}):
        for kind in ("keyCredentials", "passwordCredentials"):
            for cred in sp.get(kind) or []:
                end_date = cred.get("endDateTime")
                if end_date and datetime.fromisoformat(end_date.replace("Z", "+00:00")) <= cutoff:
                    yield sp, cred, kind


def _demo():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    client = GraphClient()
    count = 0
    for sp, cred, kind in expiring_sp_credentials(client):
        count += 1
        log.info(
            "expiring %s on %s: ends %s",
            kind, sp.get("displayName"), cred.get("endDateTime"),
        )
    log.info("total expiring service principal credentials: %d", count)


if __name__ == "__main__":
    argparse.ArgumentParser(description="List service principal credentials nearing expiry.").parse_args()
    _demo()

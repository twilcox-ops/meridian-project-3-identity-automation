"""Audit check: users without MFA registered.

Requires Reports.Read.All AND AuditLog.Read.All (both application). The
aggregated-report approach was chosen over UserAuthenticationMethod.Read.All
because it's one call instead of one call per user. AuditLog.Read.All was
not the original plan; Graph's actual 403 body named it as also required
when only Reports.Read.All was granted.

NOT YET GRANTED in Entra as of this build. Before running: App
registrations > (this app) > API permissions > Add a permission >
Microsoft Graph > Application permissions > add both Reports.Read.All and
AuditLog.Read.All, then Grant admin consent.
"""
import argparse
import logging

from graph_client import GraphClient

log = logging.getLogger("audit_mfa")

REPORT_PATH = "/reports/authenticationMethods/userRegistrationDetails"


def users_without_mfa(client: GraphClient):
    """Yield userRegistrationDetails records for users with isMfaRegistered == False."""
    for record in client.get_paginated(REPORT_PATH):
        if not record.get("isMfaRegistered"):
            yield record


def _demo():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    client = GraphClient()
    count = 0
    for record in users_without_mfa(client):
        count += 1
        log.info("no MFA: %s (%s)", record.get("userPrincipalName"), record.get("userDisplayName"))
    log.info("total users without MFA registered: %d", count)


if __name__ == "__main__":
    argparse.ArgumentParser(description="List users without MFA registered.").parse_args()
    _demo()

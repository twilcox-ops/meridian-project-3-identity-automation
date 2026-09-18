"""Audit check: users holding privileged (activated) directory roles.

Requires RoleManagement.Read.Directory (application) to list directory
roles and their members -- a widening specific to this check (DECISIONS.md:
widen only when a specific check requires it). Granted and admin-consented
in Entra; not yet run against the real tenant.
"""
import argparse
import logging

from graph_client import GraphClient

log = logging.getLogger("audit_privileged_roles")

ROLES_PATH = "/directoryRoles"


def privileged_role_holders(client: GraphClient):
    """Yield (role, member) pairs for every activated directory role's members."""
    for role in client.get_paginated(ROLES_PATH):
        members_path = f"/directoryRoles/{role['id']}/members"
        for member in client.get_paginated(members_path):
            yield role, member


def _demo():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    client = GraphClient()
    count = 0
    for role, member in privileged_role_holders(client):
        count += 1
        log.info(
            "privileged role: %s -> %s (%s)",
            role.get("displayName"), member.get("userPrincipalName") or member.get("displayName"), member.get("id"),
        )
    log.info("total privileged role assignments: %d", count)


if __name__ == "__main__":
    argparse.ArgumentParser(description="List privileged directory role holders.").parse_args()
    _demo()
